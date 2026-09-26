"""Podklad uzbrojenia terenu z uslugi GUGiK Krajowa Integracja Uzbrojenia Terenu (WMS GetMap): PNG
z przezroczystym tlem i plikiem .pgw (EPSG:2180), np. dla rysunki/rozpoznanie.py --uzbrojenie.

    python narzedzia/uzbrojenie.py --meta wyjscie/geoportal_meta.json
    python narzedzia/uzbrojenie.py --bbox 636900,486920,637000,487020 --rozdz 0.05 --wyjscie wyjscie --nazwa plac
    python narzedzia/uzbrojenie.py --meta wyjscie/geoportal_meta.json --warstwy przewod_wodociagowy,przewod_kanalizacyjny

Obszar z --meta (wynik narzedzia/geoportal.py): granica dzialki + 10 m, bez dzialki promien + 10 m wokol
punktu bazowego; --bbox E0,N0,E1,N1 w metrach EPSG:2180. Wynik <nazwa>_uzbrojenie.png i .pgw, domyslnie
obok pliku --meta. Usluga zbiorcza pokazuje dane powiatow wlaczonych do integracji. Obraz ma najwyzej
4096 px na bok i 9 Mpx (wiekszy usluga odrzuca wyjatkiem), wiec duzy obszar dostaje mniejsza
rozdzielczosc. Warstwy przewod_* maja w GetCapabilities skale do 1:1000 (0,28 m/px); uslugi powiatow
rysuja je zwykle i przy mniejszej skali, ale nie przy kazdej. Obraz bez zadnego elementu (brak danych,
powiat poza integracja, za mala skala albo chwilowy brak odpowiedzi uslugi powiatu): komunikat, bez
zapisu, kod 1. Mapa informacyjna - nie zastepuje mapy do celow projektowych.
"""
import argparse
import io
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geoportal import pobierz, usluga

KIUT = "https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaUzbrojeniaTerenu"
WARSTWY = ("przewod_wodociagowy,przewod_kanalizacyjny,przewod_cieplowniczy,przewod_gazowy,przewod_elektroenergetyczny,"
           "przewod_telekomunikacyjny,przewod_specjalny,przewod_niezidentyfikowany,przewod_urzadzenia")
MAKS_ROZDZ = 0.28   # m/px: skala 1:1000 przy pikselu 0,28 mm - granica warstw przewod_* w GetCapabilities
MAKS_PX = 9000000   # obraz 10 Mpx usluga odrzuca wyjatkiem (9,7 Mpx jeszcze przechodzi)


def obszar_z_meta(meta):
    """(E0, N0, E1, N1): dzialka + 10 m, bez dzialki promien + 10 m wokol punktu bazowego."""
    pb = meta["punkt_bazowy"]
    if pb.get("epsg") != 2180:
        raise ValueError("punkt bazowy poza Polska - usluga obejmuje tylko Polske")
    E, N = float(pb["E"]), float(pb["N"])
    if meta.get("dzialka"):
        x0, y0, x1, y1 = Polygon([(E + x, N + y) for x, y in meta["dzialka"]["obrys_m"]]).bounds
        return x0 - 10, y0 - 10, x1 + 10, y1 + 10
    r = float((meta.get("parametry") or {}).get("promien_m") or 50) + 10
    return E - r, N - r, E + r, N + r


def mapa(bbox, rozdz, warstwy, png):
    """GetMap (WMS 1.3.0, EPSG:2180: BBOX w kolejnosci osi N, E) jako PNG przezroczysty z plikiem .pgw;
    zwraca liczbe niepustych pikseli, 0 - nic nie zapisano (3 proby: przeciazona usluga oddaje pusty obraz)."""
    E0, N0, E1, N1 = bbox
    w, h = max(1, int(round((E1 - E0) / rozdz))), max(1, int(round((N1 - N0) / rozdz)))
    k = min(1.0, 4096 / max(w, h), math.sqrt(MAKS_PX / (w * h)))
    if k < 1:
        w, h = max(1, int(w * k)), max(1, int(h * k))
        print("uzbrojenie: limit uslugi (4096 px na bok, %d Mpx), rozdzielczosc %.2f m/px" % (MAKS_PX / 1e6, (E1 - E0) / w))
    for proba in range(3):
        dane, typ = pobierz(KIUT, {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": warstwy, "STYLES": "",
                                   "CRS": "EPSG:2180", "BBOX": "%.2f,%.2f,%.2f,%.2f" % (N0, E0, N1, E1), "WIDTH": w, "HEIGHT": h,
                                   "FORMAT": "image/png", "TRANSPARENT": "TRUE"}, czas=120)
        if not typ.startswith("image/"):
            raise ValueError("WMS zwrocil %s: %s" % (typ, dane[:300].decode("utf-8", "replace")))
        n = int((np.asarray(Image.open(io.BytesIO(dane)).convert("RGBA"))[:, :, 3] > 0).sum())
        if n:
            break
        time.sleep(1)
    else:
        return 0
    png.write_bytes(dane)
    dx, dy = (E1 - E0) / w, (N1 - N0) / h
    with open(png.with_suffix(".pgw"), "w", encoding="utf-8") as f:
        f.write("%.6f\n0\n0\n%.6f\n%.3f\n%.3f\n" % (dx, -dy, E0 + dx / 2, N1 - dy / 2))
    return n


def main():
    ap = argparse.ArgumentParser(description="Podklad uzbrojenia terenu z uslugi GUGiK (PNG z .pgw w EPSG:2180).")
    grupa = ap.add_mutually_exclusive_group(required=True)
    grupa.add_argument("--meta", help="<nazwa>_meta.json z narzedzia/geoportal.py (obszar: dzialka + 10 m)")
    grupa.add_argument("--bbox", help="E0,N0,E1,N1 w metrach EPSG:2180")
    ap.add_argument("--rozdz", type=float, default=0.1, help="rozdzielczosc w m/px (domyslnie 0.1; obraz najwyzej 9 Mpx)")
    ap.add_argument("--warstwy", default=WARSTWY, help="warstwy uslugi po przecinku (domyslnie wszystkie przewod_*)")
    ap.add_argument("--wyjscie", help="katalog wyniku (domyslnie katalog pliku --meta albo ./wyjscie)")
    ap.add_argument("--nazwa", help="przedrostek pliku (domyslnie z nazwy pliku --meta albo geoportal)")
    a = ap.parse_args()
    if a.rozdz <= 0:
        ap.error("--rozdz: rozdzielczosc w m/px wieksza od 0")
    if a.meta:
        try:
            with open(a.meta, encoding="utf-8") as f:
                bbox = obszar_z_meta(json.load(f))
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("plik %s nieczytelny albo bez punktu bazowego: %s" % (a.meta, e))
            return 1
    else:
        try:
            bbox = tuple(float(v) for v in a.bbox.split(","))
            if len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                raise ValueError
        except ValueError:
            ap.error("--bbox: E0,N0,E1,N1 w metrach EPSG:2180 (E1 > E0, N1 > N0)")
    if a.rozdz > MAKS_ROZDZ:
        print("uwaga: powyzej %.2f m/px (skala mniejsza niz 1:1000 z GetCapabilities) usluga moze nie rysowac przewodow" % MAKS_ROZDZ)
    nazwa = a.nazwa or (re.sub(r"_meta$", "", Path(a.meta).stem) if a.meta else "geoportal")
    kat = Path(a.wyjscie or (Path(a.meta).parent if a.meta else "wyjscie"))
    kat.mkdir(parents=True, exist_ok=True)
    png = kat / ("%s_uzbrojenie.png" % nazwa)
    E0, N0, E1, N1 = bbox
    print("uzbrojenie terenu: E %.1f-%.1f, N %.1f-%.1f (%.0f x %.0f m), %s m/px" % (E0, E1, N0, N1, E1 - E0, N1 - N0, a.rozdz))
    n = usluga("KIUT (Krajowa Integracja Uzbrojenia Terenu)", mapa, bbox, a.rozdz, a.warstwy, png)
    if n is None:
        return 1
    if not n:
        print("pusty obraz: usluga nie pokazala uzbrojenia w tym obszarze (brak danych, powiat poza integracja, "
              "za mala skala albo chwilowy brak odpowiedzi) - nic nie zapisano")
        return 1
    print("zapisano", png)
    print("zapisano", png.with_suffix(".pgw"))
    print("mapa uzbrojenia: informacyjnie, nie zastepuje mapy do celow projektowych")
    return 0


if __name__ == "__main__":
    sys.exit(main())
