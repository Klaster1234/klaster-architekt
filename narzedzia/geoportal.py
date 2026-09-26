"""Otoczenie lokalu z otwartych uslug GUGiK: dzialka i budynek z EGiB, budynki w promieniu (BDOT10k
i EGiB) z wysokoscia NMPT - NMT, ortofotomapa z podzialka, wysokosc terenu i kierunek polnocy.
Opcjonalnie budynki z OpenStreetMap (--osm; poza Polska jedyne zrodlo: --xy dlugosc,szerokosc --osm),
z domyslnej instancji Overpass API (overpass-api.de) albo innej podanej przez --overpass URL.

    python narzedzia/geoportal.py --adres "Warszawa, Plac Defilad 1" --promien 40
    python narzedzia/geoportal.py --xy 21.0063,52.2318 --orto 0.2 --podloga 9.0
    python narzedzia/geoportal.py --dzialka 146510_8.0309.24/35
    python narzedzia/geoportal.py --xy 21.0063,52.2318 --osm --orto 0
    python narzedzia/geoportal.py --xy 21.0063,52.2318 --osm --overpass https://adres-innej-instancji/api/interpreter
    python narzedzia/geoportal.py --dzialka 146510_8.0309.24/35 --teren 2

Wynik w metrach od punktu bazowego (srodek budynku albo dzialki, zaokraglony do 1 m):
<nazwa>.dxf (mm), <nazwa>_odcinki.json (obrysy budynkow), <nazwa>_meta.json (punkt bazowy
w EPSG:2180, zrodla, dokladnosc), <nazwa>_kontekst.json (budynki sasiednie jako rekordy
"kontekst" modelu w cm), <nazwa>_orto.png z .pgw (georeferencja EPSG:2180) i podglad
z obrysami, podzialka i polnoca. --teren KROK_M: <nazwa>_teren.json - punkty NMT co KROK_M m
w granicy dzialki (bez dzialki: w promieniu) + 10 m, [x_cm, y_cm, z_m_npm] od punktu bazowego
(dla zamierzenie/z_geoportalu.py); siatka ponad 10 000 punktow - bez pobierania NMT, komunikat
z wiekszym krokiem (reszta wynikow powstaje).
Os +Y to polnoc siatki PL-1992, nie geograficzna: skrypt
wypisuje azymut osi +Y do meta.polnoc modelu (zbieznosc poludnikow). Wysokosc budynku to
mediana NMPT - NMT w obrysie (skaning lotniczy, stan z daty nalotu); bez tych danych jest
ZALOZENIEM (kondygnacje z BDOT10k x 3,0 m) i tak trzeba ja opisac w modelu. --podloga to
wysokosc podlogi lokalu nad terenem: przesuwa "wys" kontekstu do ukladu modelu (0 = podloga).
Ortofoto pokazuje dachy, a wysokie budynki sa na nim przechylone: obrys bierz z EGiB.
Dane GUGiK sa otwarte; OSM: (c) wspoltworcy OpenStreetMap, licencja ODbL.
"""
import argparse
import http.client
import io
import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import ezdxf
import numpy as np
import shapely
from PIL import Image, ImageDraw
from shapely import wkt
from shapely.affinity import translate
from shapely.errors import ShapelyError
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lokal.model import json_zwarty
from raster_do_dxf import czcionka

UA = "klaster-architekt/1.0 (narzedzia/geoportal.py)"
UUG = "https://services.gugik.gov.pl/uug/"
ULDK = "https://uldk.gugik.gov.pl/"
ORTO = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/HighResolution"
NMT = "https://services.gugik.gov.pl/nmt/"
WFS_BU = "https://mapy.geoportal.gov.pl/wss/service/wfsBU/guest"
WCS = {"NMPT": ("https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMPT/GRID1/WCS/DigitalSurfaceModel", "DSM_PL-EVRF2007-NH"),
       "NMT": ("https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModel", "DTM_PL-EVRF2007-NH")}
OVERPASS = "https://overpass-api.de/api/interpreter"  # inna instancja: --overpass URL
PL1992 = dict(lon0=19.0, k0=0.9993, fe=500000.0, fn=-5300000.0)
KONDYGNACJA = 3.0
BLEDY = (OSError, http.client.HTTPException, ET.ParseError, ShapelyError, ValueError, KeyError, IndexError, StopIteration)
bledy = []
SSL = ssl.create_default_context()
try:  # Python z python.org na macOS bywa bez certyfikatow CA; certifi (jesli jest) je uzupelnia
    import certifi
    SSL.load_verify_locations(certifi.where())
except ImportError:
    pass


def pobierz(url, parametry=None, dane=None, czas=20):
    if parametry:
        url += "?" + urllib.parse.urlencode(parametry, quote_via=urllib.parse.quote, safe=",:()/")
    zadanie = urllib.request.Request(url, data=dane, headers={"User-Agent": UA})
    for proba in range(2):
        try:
            with urllib.request.urlopen(zadanie, timeout=czas, context=SSL) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:  # 5xx bywa chwilowe: jedna powtorka
            if e.code < 500 or proba:
                raise
            time.sleep(1)


def usluga(nazwa, f, *args, **kw):
    """Wywolanie uslugi; blad sieci albo odpowiedzi -> komunikat i None zamiast wyjatku."""
    try:
        return f(*args, **kw)
    except BLEDY as e:
        komunikat = "%s: %s" % (nazwa, getattr(e, "reason", None) or e)
        print("BLAD uslugi " + komunikat)
        if "CERTIFICATE_VERIFY_FAILED" in komunikat:
            print("  Python nie ma certyfikatow CA: macOS - uruchom 'Install Certificates.command' z folderu Pythona "
                  "albo pip install certifi")
        bledy.append(komunikat)
        return None


# odwzorowanie poprzeczne Merkatora na GRS80 (szeregi Krugera, dokladnosc ponizej 1 mm)
_n = (1 / 298.257222101) / (2 - 1 / 298.257222101)
_A = 6378137.0 / (1 + _n) * (1 + _n ** 2 / 4 + _n ** 4 / 64)
_ALFA = (_n / 2 - 2 * _n ** 2 / 3 + 5 * _n ** 3 / 16, 13 * _n ** 2 / 48 - 3 * _n ** 3 / 5, 61 * _n ** 3 / 240)
_BETA = (_n / 2 - 2 * _n ** 2 / 3 + 37 * _n ** 3 / 96, _n ** 2 / 48 + _n ** 3 / 15, 17 * _n ** 3 / 480)
_DELTA = (2 * _n - 2 * _n ** 2 / 3 - 2 * _n ** 3, 7 * _n ** 2 / 3 - 8 * _n ** 3 / 5, 56 * _n ** 3 / 15)


def do_tm(lat, lon, lon0, k0, fe, fn):
    """(szerokosc, dlugosc) ETRS89/WGS84 -> (E, N)."""
    f, lam = math.radians(lat), math.radians(lon - lon0)
    e = 2 * math.sqrt(_n) / (1 + _n)
    t = math.sinh(math.atanh(math.sin(f)) - e * math.atanh(e * math.sin(f)))
    xi, eta = math.atan2(t, math.cos(lam)), math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    E = eta + sum(a * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, a in enumerate(_ALFA, 1))
    N = xi + sum(a * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, a in enumerate(_ALFA, 1))
    return fe + k0 * _A * E, fn + k0 * _A * N


def z_tm(E, N, lon0, k0, fe, fn):
    """(E, N) -> (szerokosc, dlugosc)."""
    xi, eta = (N - fn) / (k0 * _A), (E - fe) / (k0 * _A)
    xi1 = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    eta1 = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = math.asin(math.sin(xi1) / math.cosh(eta1))
    lat = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(_DELTA, 1))
    return math.degrees(lat), lon0 + math.degrees(math.atan2(math.sinh(eta1), math.cos(xi1)))


def azymut_osi_y(lat, lon, uklad):
    """Azymut (od polnocy geograficznej, zgodnie z zegarem) kierunku +Y siatki w punkcie."""
    E1, N1 = do_tm(lat, lon, **uklad)
    E2, N2 = do_tm(lat + 1e-4, lon, **uklad)
    return round(-math.degrees(math.atan2(E2 - E1, N2 - N1)), 6) + 0.0


def budynek(ident, geom, zrodlo, tagi=None, kondygnacje=None):
    return {"id": ident, "geom": geom, "zrodlo": zrodlo, "tagi": tagi or {}, "kondygnacje": kondygnacje}


def uldk(zapytanie, **p):
    """[(id, geometria EPSG:2180, zrodlo danych)]; pusta lista, gdy brak obiektu."""
    linie = pobierz(ULDK, dict(request=zapytanie, srid="2180", **p))[0].decode("utf-8", "replace").strip().splitlines()
    if not linie or linie[0].strip().startswith("-"):
        return []
    wynik = []
    for linia in linie[1:]:
        cz = linia.split("|")
        if len(cz) >= 2 and "SRID=" in cz[1]:
            wynik.append((cz[0].strip(), wkt.loads(cz[1].split(";", 1)[1]), cz[2].strip() if len(cz) > 2 else ""))
    return wynik


def bdot_budynki(srodek, promien):
    """Budynki BDOT10k z WFS INSPIRE w kole: jedno zapytanie, obrys i liczba kondygnacji."""
    E0, N0 = srodek
    r = promien + 5
    # EPSG:2180 zapisany jako urn ma kolejnosc osi polnoc, wschod (BBOX i posList)
    t = pobierz(WFS_BU, {"SERVICE": "WFS", "REQUEST": "GetFeature", "VERSION": "2.0.0", "TYPENAMES": "bu-core2d:Building",
                         "COUNT": 2000, "SRSNAME": "urn:ogc:def:crs:EPSG::2180",
                         "BBOX": "%.2f,%.2f,%.2f,%.2f,urn:ogc:def:crs:EPSG::2180" % (N0 - r, E0 - r, N0 + r, E0 + r)},
                czas=60)[0]
    gml = "{http://www.opengis.net/gml/3.2}"
    wynik = []
    for b in ET.fromstring(t).iter("{http://inspire.ec.europa.eu/schemas/bu-core2d/4.0}Building"):
        czesci = []
        for p in b.iter(gml + "Polygon"):
            pierscienie = []
            for pl in p.iter(gml + "posList"):
                v = [float(x) for x in pl.text.split()]
                pierscienie.append(list(zip(v[1::2], v[0::2])))
            czesci.append(Polygon(pierscienie[0], pierscienie[1:]).buffer(0))
        g = unary_union(czesci) if czesci else None
        if g is None or g.is_empty or g.distance(Point(E0, N0)) > promien:
            continue
        ident = next(b.iter("{http://inspire.ec.europa.eu/schemas/base/3.3}localId")).text
        k = b.find("{http://inspire.ec.europa.eu/schemas/bu-base/4.0}numberOfFloorsAboveGround")
        wynik.append(budynek("BDOT10k_" + ident, g, "BDOT10k (WFS INSPIRE)",
                             kondygnacje=int(k.text) if k is not None and (k.text or "").isdigit() else None))
    return wynik


def budynki_w_promieniu(srodek, promien, znane):
    """Siatka punktow co max(10 m, promien/10) w kole; GetBuildingByXY tylko poza znanymi budynkami."""
    E0, N0 = srodek
    krok = max(10.0, promien / 10)
    k = int(promien // krok)
    punkty = sorted(((E0 + i * krok, N0 + j * krok) for i in range(-k, k + 1) for j in range(-k, k + 1)
                     if (i * i + j * j) * krok * krok <= promien * promien),
                    key=lambda p: math.hypot(p[0] - E0, p[1] - N0))

    def zapytaj(p):
        try:
            return uldk("GetBuildingByXY", xy="%.2f,%.2f" % p, result="id,geom_wkt")
        except BLEDY:
            return None

    zapytan, nieudane = 0, 0
    with ThreadPoolExecutor(6) as pula:
        while punkty and nieudane < 3:
            partia = []
            while punkty and len(partia) < 12:
                p = punkty.pop(0)
                if not any(b["geom"].distance(Point(p)) <= 0.5 for b in znane.values()):
                    partia.append(p)
            for wynik in pula.map(zapytaj, partia):
                zapytan += 1
                if wynik is None:
                    nieudane += 1
                for ident, g, _ in wynik or []:
                    znane.setdefault(ident, budynek(ident, g, "EGiB (ULDK)"))
    if nieudane >= 3:
        print("BLAD uslugi ULDK: przerwano szukanie budynkow po %d nieudanych zapytaniach" % nieudane)
        bledy.append("ULDK: szukanie budynkow w promieniu przerwane")
    return zapytan


def osm_budynki(lat, lon, promien, uklad, overpass_url=OVERPASS):
    """Budynki OSM w promieniu (way i relation building) w ukladzie `uklad`."""
    q = ('[out:json][timeout:25];(way["building"](around:%d,%.6f,%.6f);relation["building"](around:%d,%.6f,%.6f););'
         'out geom;' % (promien, lat, lon, promien, lat, lon))
    d = usluga("Overpass " + overpass_url.split("/")[2], lambda: json.loads(
        pobierz(overpass_url, dane=urllib.parse.urlencode({"data": q}).encode(), czas=40)[0].decode("utf-8")))
    rzut = lambda pts: [do_tm(p["lat"], p["lon"], **uklad) for p in pts]
    wynik = []
    for e in (d or {}).get("elements", []):
        if e["type"] == "way" and len(e.get("geometry", [])) >= 4:
            g = Polygon(rzut(e["geometry"]))
        elif e["type"] == "relation":
            linie = [LineString(rzut(m["geometry"])) for m in e.get("members", [])
                     if m.get("role") == "outer" and len(m.get("geometry", [])) >= 2]
            g = unary_union(list(polygonize(unary_union(linie)))) if linie else None
        else:
            continue
        if g is not None and not g.is_empty and g.is_valid:
            wynik.append(budynek("osm_%s%d" % (e["type"][0], e["id"]), g, "OSM", e.get("tags", {})))
    return wynik


def siatka_wcs(nazwa, E0, N0, w, h, krok):
    """Siatka wysokosci (Arc/Info ASCII Grid) z WCS GUGiK: (z[wiersz od polnocy, kolumna], E lewej, N dolnej, dx, dy)."""
    url, pokrycie = WCS[nazwa]
    t = pobierz(url, {"SERVICE": "WCS", "VERSION": "1.0.0", "REQUEST": "GetCoverage", "FORMAT": "image/x-aaigrid",
                      "COVERAGE": pokrycie, "BBOX": "%.2f,%.2f,%.2f,%.2f" % (E0, N0, E0 + w * krok, N0 + h * krok),
                      "CRS": "EPSG:2180", "RESPONSE_CRS": "EPSG:2180", "WIDTH": w, "HEIGHT": h}, czas=90)[0]
    linie = t.decode("ascii", "replace").splitlines()
    nag = {}
    while linie and linie[0].split() and linie[0].split()[0][0].isalpha():
        k, v = linie.pop(0).split()[:2]
        nag[k.lower()] = float(v)
    z = np.array(" ".join(linie).split(), float).reshape(int(nag["nrows"]), int(nag["ncols"]))
    if "nodata_value" in nag:
        z[z == nag["nodata_value"]] = np.nan
    return z, nag["xllcorner"], nag["yllcorner"], nag.get("cellsize", nag.get("dx")), nag.get("cellsize", nag.get("dy"))


def teren_siatka(obszar, E0, N0, krok, limit=10000):
    """Punkty NMT co krok m w obszarze (shapely, EPSG:2180): [[x_cm, y_cm, z_m_npm]] wzgledem (E0, N0);
    wezly siatki co krok od punktu bazowego (punkt bazowy jest wezlem), bez komorek nodata. Siatka
    (w x h wezlow) wieksza niz limit: komunikat z proponowanym krokiem i None - bez zapytania WCS."""
    x0, y0, x1, y1 = obszar.bounds
    i0, i1 = math.floor((x0 - E0) / krok), math.ceil((x1 - E0) / krok)
    j0, j1 = math.floor((y0 - N0) / krok), math.ceil((y1 - N0) / krok)
    n = (i1 - i0 + 1) * (j1 - j0 + 1)
    if n > limit:
        k = krok_terenu(n, krok, limit)
        print("teren: siatka %d x %d = %d punktow co %g m (limit %d) - NMT nie pobrany; uruchom ponownie z wiekszym "
              "krokiem: --teren %g (ok. %d punktow)" % (i1 - i0 + 1, j1 - j0 + 1, n, krok, limit, k, n * (krok / k) ** 2))
        return None
    z, xll, yll, dx, dy = siatka_wcs("NMT", E0 + (i0 - 0.5) * krok, N0 + (j0 - 0.5) * krok, i1 - i0 + 1, j1 - j0 + 1, krok)
    EE, NN = np.meshgrid(xll + (np.arange(z.shape[1]) + 0.5) * dx, yll + (z.shape[0] - np.arange(z.shape[0]) - 0.5) * dy)
    m = shapely.contains_xy(obszar, EE, NN) & np.isfinite(z)
    return [[int(round((e - E0) * 100)), int(round((n - N0) * 100)), round(float(h), 2)] for e, n, h in zip(EE[m], NN[m], z[m])]


def krok_terenu(n, krok, limit=10000):
    """Wiekszy krok (co 0,5 m, ponizej 1 m co 0,1 m), przy ktorym n punktow co krok spada do limitu."""
    k = krok * math.sqrt(n / limit)
    return math.ceil(k * 2) / 2 if k >= 1 else math.ceil(k * 10) / 10


def wysokosci(budynki):
    """Dopisuje h (mediana NMPT - NMT w obrysie zwezonym o 0,5 m), h90 i teren (mediana NMT); zwraca liczbe."""
    E0, N0, E1, N1 = unary_union([b["geom"] for b in budynki]).buffer(2).bounds
    krok = max(0.5, max(E1 - E0, N1 - N0) / 400)
    w, h = int(math.ceil((E1 - E0) / krok)), int(math.ceil((N1 - N0) / krok))
    s = usluga("WCS NMPT", siatka_wcs, "NMPT", E0, N0, w, h, krok)
    t = usluga("WCS NMT", siatka_wcs, "NMT", E0, N0, w, h, krok) if s is not None else None
    if s is None or t is None or s[0].shape != t[0].shape:
        return 0
    zs, xll, yll, dx, dy = s
    zt = t[0]
    EE, NN = np.meshgrid(xll + (np.arange(zs.shape[1]) + 0.5) * dx, yll + (zs.shape[0] - np.arange(zs.shape[0]) - 0.5) * dy)
    n = 0
    for b in budynki:
        g = b["geom"].buffer(-0.5)
        m = shapely.contains_xy(g if g.area > 4 else b["geom"], EE, NN)
        dh = (zs - zt)[m]
        dh = dh[np.isfinite(dh)]
        if len(dh) >= 3:
            b.update(h=float(np.median(dh)), teren=float(np.nanmedian(zt[m])),
                     wys_zrodlo="NMPT-NMT mediana w obrysie (90 perc. %.1f m)" % np.percentile(dh, 90))
            n += 1
    return n


def wysokosc_zalozona(b):
    """Gdy brak pomiaru: tag OSM height, inaczej kondygnacje (OSM, BDOT10k) x 3,0 m jako ZALOZENIE."""
    t = b["tagi"]
    try:
        if "height" in t:
            b.update(h=float(t["height"].replace("m", "").replace(",", ".").strip()), wys_zrodlo="OSM height")
            return
        n = float(t["building:levels"].replace(",", ".")) if "building:levels" in t else b["kondygnacje"]
    except ValueError:
        return
    if n:
        b.update(h=n * KONDYGNACJA, wys_zrodlo="ZALOZENIE: %g kondygnacji x %.1f m (%s)" % (
            n, KONDYGNACJA, "OSM building:levels" if "building:levels" in t else "BDOT10k"))


def orto(srodek, pol, rozdz, png):
    """Wycinek ortofotomapy WMS (EPSG:2180) z plikiem georeferencji .pgw; zwraca uzyta rozdzielczosc."""
    E0, N0 = srodek
    px = int(round(2 * pol / rozdz))
    if px > 4096:
        px, rozdz = 4096, 2 * pol / 4096
        print("ortofoto: limit uslugi 4096 px, rozdzielczosc %.2f m/px" % rozdz)
    # WMS 1.3.0: EPSG:2180 ma kolejnosc osi polnoc, wschod. Przeciazona usluga oddaje pusty
    # (jednolity) obraz z kodem 200, wiec ponawia sie kilka razy.
    for proba in range(8):
        dane, typ = pobierz(ORTO, {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": "Raster",
                                   "STYLES": "", "CRS": "EPSG:2180", "WIDTH": px, "HEIGHT": px, "FORMAT": "image/png",
                                   "BBOX": "%.2f,%.2f,%.2f,%.2f" % (N0 - pol, E0 - pol, N0 + pol, E0 + pol)}, czas=90)
        if not typ.startswith("image/"):
            raise ValueError("WMS zwrocil %s: %s" % (typ, dane[:300].decode("utf-8", "replace")))
        lo, hi = Image.open(io.BytesIO(dane)).convert("L").getextrema()
        if hi - lo > 10:
            break
        time.sleep(0.5)
    else:
        raise ValueError("8 razy pusty obraz (przeciazenie uslugi albo brak zdjec w tym miejscu) - sprobuj pozniej")
    if proba:
        print("ortofoto: obraz dopiero za %d. razem (usluga oddawala puste obrazy)" % (proba + 1))
    png.write_bytes(dane)
    with open(png.with_suffix(".pgw"), "w", encoding="utf-8") as f:
        f.write("%.6f\n0\n0\n%.6f\n%.3f\n%.3f\n" % (rozdz, -rozdz, E0 - pol + rozdz / 2, N0 + pol - rozdz / 2))
    return rozdz


def pierscienie(g):
    for p in getattr(g, "geoms", [g]):
        yield list(p.exterior.coords)
        for h in p.interiors:
            yield list(h.coords)


def kierunek_scian(g):
    """Kat (-45..45 st., przeciwnie do zegara) dominujacego kierunku krawedzi obrysu wzgledem osi X."""
    s = c = 0.0
    for r in pierscienie(g):
        for (x1, y1), (x2, y2) in zip(r[:-1], r[1:]):
            k, dl = math.atan2(y2 - y1, x2 - x1), math.hypot(x2 - x1, y2 - y1)
            s, c = s + dl * math.sin(4 * k), c + dl * math.cos(4 * k)
    return math.degrees(math.atan2(s, c) / 4)


def podglad(png, srodek, pol, rozdz, dzialka, glowny, sasiednie, promien, szukanie, azymut, sciezka):
    """Ortofoto z obrysami (dzialka, budynek, sasiednie), wysokosciami, kolem szukania, podzialka i polnoca."""
    im = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(im)
    E0, N0 = srodek
    P = lambda E, N: ((E - E0 + pol) / rozdz, (N0 + pol - N) / rozdz)
    gr = max(2, im.width // 400)
    f = czcionka(max(14, im.width // 55))
    warstwy = [(dzialka, (255, 215, 0), gr)] + [(b["geom"], (0, 220, 255), gr) for b in sasiednie]
    for g, kolor, grubosc in warstwy + ([(glowny["geom"], (255, 40, 40), gr + 1)] if glowny else []):
        for r in pierscienie(g) if g is not None else []:
            d.line([P(*p) for p in r], fill=kolor, width=grubosc)
    for b in sasiednie + ([glowny] if glowny else []):
        X, Y = P(*b["geom"].representative_point().coords[0])
        if b.get("h") is not None and 0 < X < im.width and 0 < Y < im.height:
            d.text((X, Y), ("%.1f m" % b["h"]).replace(".", ","), fill=(255, 255, 255), font=f, anchor="mm",
                   stroke_width=3, stroke_fill=(0, 0, 0))
    if promien:
        X, Y = P(*szukanie)
        r = promien / rozdz
        for i in range(0, 360, 6):
            d.arc([X - r, Y - r, X + r, Y + r], i, i + 3, fill=(255, 255, 255), width=max(1, gr // 2))
    X, Y = P(E0, N0)
    d.line([X - 12, Y, X + 12, Y], fill=(255, 255, 255), width=gr)
    d.line([X, Y - 12, X, Y + 12], fill=(255, 255, 255), width=gr)
    m = next(v for v in (5, 10, 20, 50, 100, 200) if v / rozdz >= im.width / 6 or v == 200)
    x0, y0 = 20, im.height - 36
    d.rectangle([x0 - 8, y0 - 30, x0 + m / rozdz + 70, y0 + 16], fill=(255, 255, 255))
    for i in range(5):
        d.rectangle([x0 + i * m / rozdz / 5, y0, x0 + (i + 1) * m / rozdz / 5, y0 + 8], outline=(0, 0, 0),
                    fill=(0, 0, 0) if i % 2 == 0 else (255, 255, 255))
    d.text((x0, y0 - 26), "0", fill=(0, 0, 0), font=f)
    d.text((x0 + m / rozdz - 8, y0 - 26), "%d m" % m, fill=(0, 0, 0), font=f)
    # strzalka polnocy geograficznej: gora obrazu to polnoc siatki, geograficzna odchylona o -azymut
    cx, cy, r = im.width - 50, 60, 34
    k = math.radians(-azymut)
    d.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=(255, 255, 255))
    d.line([cx, cy, cx + r * math.sin(k), cy - r * math.cos(k)], fill=(200, 60, 20), width=4)
    d.text((cx, cy + 16), "N", fill=(200, 60, 20), font=f, anchor="mm")
    d.text((10, 10), "Ortofotomapa: GUGiK (geoportal.gov.pl) · czerwony: budynek, niebieski: sąsiednie, żółty: działka",
           fill=(255, 255, 255), font=czcionka(max(12, im.width // 80)), stroke_width=2, stroke_fill=(0, 0, 0))
    im.save(sciezka)


def main():
    ap = argparse.ArgumentParser(description="Dzialka, budynki, ortofoto i wysokosci z uslug GUGiK (albo OSM)")
    grupa = ap.add_mutually_exclusive_group(required=True)
    grupa.add_argument("--adres", help='adres w Polsce, np. "Warszawa, Plac Defilad 1"')
    grupa.add_argument("--xy", help="dlugosc,szerokosc geograficzna (WGS84), np. 21.0063,52.2318")
    grupa.add_argument("--dzialka", help="identyfikator dzialki (np. 146510_8.0309.24/35) albo \"obreb numer\"")
    ap.add_argument("--promien", type=float, default=50, help="promien szukania budynkow w m (domyslnie 50)")
    ap.add_argument("--orto", type=float, default=0.1, help="rozdzielczosc ortofoto w m/px, 0 = bez ortofoto")
    ap.add_argument("--osm", action="store_true", help="budynki z OpenStreetMap zamiast EGiB/BDOT10k (poza Polska jedyne)")
    ap.add_argument("--overpass", default=OVERPASS, help="adres innej instancji Overpass API (domyslnie %s)" % OVERPASS)
    ap.add_argument("--podloga", type=float, default=0.0, help="wysokosc podlogi lokalu nad terenem w m (dla wys kontekstu)")
    ap.add_argument("--wyjscie", default="wyjscie", help="katalog wynikow (domyslnie ./wyjscie)")
    ap.add_argument("--nazwa", default="geoportal", help="przedrostek plikow wynikowych")
    ap.add_argument("--teren", type=float, metavar="KROK_M",
                    help="punkty terenu z NMT co KROK_M m w granicy dzialki (albo promienia) + 10 m -> <nazwa>_teren.json")
    a = ap.parse_args()
    if a.teren is not None and a.teren <= 0:
        ap.error("--teren: krok w metrach wiekszy od 0")

    # 1. punkt wejsciowy (EPSG:2180 w Polsce, poza Polska lokalne odwzorowanie TM)
    dzialka = dzialka_id = zrodlo_dzialki = None
    if a.adres:
        r = usluga("UUG", lambda: json.loads(pobierz(UUG, {"request": "GetAddress", "address": a.adres})[0].decode("utf-8")))
        if r is None:
            sys.exit("usluga adresowa UUG nie odpowiada - sprawdz polaczenie albo podaj --xy dlugosc,szerokosc")
        wyniki = r.get("results") or {}
        if not wyniki:
            sys.exit("nie znaleziono adresu \"%s\" (UUG obsluguje tylko adresy w Polsce; poza Polska uzyj --xy)" % a.adres)
        w = wyniki[sorted(wyniki, key=int)[0]]
        E, N = float(w["x"]), float(w["y"])
        print("adres: %s %s %s, %s (typ %s, dokladnosc %s, znalezionych %s)" % (
            w.get("city") or "", w.get("street") or "", w.get("number") or "", w.get("code") or "",
            r.get("type"), w.get("accuracy"), r.get("found objects")))
        if float(w.get("accuracy") or 0) < 1:
            print("uwaga: adres dopasowany niedokladnie - sprawdz punkt na podgladzie ortofoto")
        lat, lon = z_tm(E, N, **PL1992)
    elif a.xy:
        lon, lat = (float(v) for v in a.xy.split(","))
        E, N = do_tm(lat, lon, **PL1992)
    else:
        r = usluga("ULDK", uldk, "GetParcelByIdOrNr", id=a.dzialka, result="id,geom_wkt,datasource")
        if r is None:
            sys.exit("usluga ULDK nie odpowiada - sprawdz polaczenie")
        if not r:
            sys.exit("nie znaleziono dzialki \"%s\"" % a.dzialka)
        if len(r) > 1:
            print("uwaga: %d dzialek pasuje, biore pierwsza: %s" % (len(r), ", ".join(x[0] for x in r[:5])))
        dzialka_id, dzialka, zrodlo_dzialki = r[0]
        E, N = dzialka.representative_point().coords[0]
        lat, lon = z_tm(E, N, **PL1992)
    polska = 49.0 <= lat <= 54.9 and 14.1 <= lon <= 24.2
    uklad = PL1992 if polska else dict(lon0=round(lon, 6), k0=1.0, fe=0.0, fn=0.0)
    if not polska:
        if not a.osm:
            sys.exit("punkt poza Polska: uslugi GUGiK nie dzialaja, uzyj --osm")
        E, N = do_tm(lat, lon, **uklad)
    print("punkt: %.6f, %.6f (szer., dl.); %s E %.2f N %.2f" % (lat, lon, "PL-1992" if polska else "lokalny TM", E, N))

    # 2. dzialka, budynek w punkcie (EGiB) i budynki w promieniu: BDOT10k, EGiB z siatki punktow albo OSM
    budynki, bdot = {}, None
    zapytan = 0
    if polska and dzialka is None:
        r = usluga("ULDK", uldk, "GetParcelByXY", xy="%.2f,%.2f" % (E, N), result="id,geom_wkt,datasource")
        if r:
            dzialka_id, dzialka, zrodlo_dzialki = r[0]
    if a.osm:
        budynki = {b["id"]: b for b in osm_budynki(lat, lon, a.promien, uklad, a.overpass)}
    elif polska:
        r = usluga("ULDK", uldk, "GetBuildingByXY", xy="%.2f,%.2f" % (E, N), result="id,geom_wkt")
        if r:
            budynki[r[0][0]] = budynek(r[0][0], r[0][1], "EGiB (ULDK)")
        if a.promien > 0:
            # BDOT10k daje wszystkie budynki w kole jednym zapytaniem (z kondygnacjami), ale bywa starszy
            # niz EGiB; siatka ULDK pyta tylko poza znanymi budynkami i doklada nowsze budynki z EGiB
            bdot = usluga("WFS BDOT10k", bdot_budynki, (E, N), a.promien)
            budynki.update({b["id"]: b for b in bdot or []})
            if r is not None:
                zapytan = usluga("ULDK siatka", budynki_w_promieniu, (E, N), a.promien, budynki) or 0
        for e in [b for b in budynki.values() if b["zrodlo"].startswith("EGiB")]:
            for b in [b for b in budynki.values() if b["zrodlo"].startswith("BDOT")]:
                if e["geom"].intersection(b["geom"]).area > 0.5 * min(e["geom"].area, b["geom"].area):
                    e["kondygnacje"] = e["kondygnacje"] or b["kondygnacje"]
                    del budynki[b["id"]]
    pkt = Point(E, N)
    glowny = None
    if a.dzialka and budynki:
        na_dzialce = [b for b in budynki.values() if b["geom"].intersects(dzialka)]
        glowny = max(na_dzialce, key=lambda b: b["geom"].intersection(dzialka).area) if na_dzialce else None
    elif budynki:
        glowny = min(budynki.values(), key=lambda b: b["geom"].distance(pkt))
        if glowny["geom"].distance(pkt) > 0:
            print("punkt poza obrysem budynku: przyjeto najblizszy (%.1f m)" % glowny["geom"].distance(pkt))
    sasiednie = sorted((b for b in budynki.values() if b is not glowny), key=lambda b: b["geom"].distance(pkt))
    for i, b in enumerate(sasiednie, 1):
        b["kontekst"] = "XG%d" % i

    # 3. punkt bazowy: srodek budynku, dzialki albo punkt, zaokraglony do 1 m
    c = (glowny["geom"] if glowny else dzialka if dzialka is not None else pkt).centroid
    E0, N0 = float(round(c.x)), float(round(c.y))
    lat0, lon0 = z_tm(E0, N0, **uklad)
    az = azymut_osi_y(lat0, lon0, uklad)
    print("punkt bazowy (0, 0): E %.0f N %.0f (%s)" % (E0, N0, "EPSG:2180" if polska else "lokalny TM"))

    # 4. wysokosci: NMPT - NMT (pomiar), inaczej tag OSM albo kondygnacje x 3,0 m (ZALOZENIE)
    if polska and budynki:
        wysokosci(list(budynki.values()))
    for b in budynki.values():
        if b.get("h") is None:
            wysokosc_zalozona(b)
    teren = usluga("NMT", lambda: float(pobierz(NMT, {"request": "GetHbyXY", "x": "%.2f" % N0, "y": "%.2f" % E0})[0])) \
        if polska else None
    teren0 = glowny.get("teren") if glowny and glowny.get("teren") is not None else teren
    # punkty terenu (--teren): NMT co KROK_M m w granicy dzialki (bez dzialki: w promieniu) + 10 m
    teren_pkt = None
    if a.teren and not polska:
        print("teren: NMT GUGiK tylko w Polsce - pominieto --teren")
    elif a.teren:
        obszar = (dzialka if dzialka is not None else Point(E0, N0).buffer(a.promien)).buffer(10)
        teren_pkt = usluga("WCS NMT (teren)", teren_siatka, obszar, E0, N0, a.teren)

    # 5. ortofoto z podgladem
    wyjscie = Path(a.wyjscie)
    wyjscie.mkdir(parents=True, exist_ok=True)
    baza = wyjscie / a.nazwa
    plik = lambda koncowka: baza.parent / (baza.name + koncowka)
    pol = max(a.promien, 20) + 10
    rozdz = usluga("WMS ORTO", orto, (E0, N0), pol, a.orto, plik("_orto.png")) if polska and a.orto > 0 else None
    if rozdz:
        podglad(plik("_orto.png"), (E0, N0), pol, rozdz, dzialka, glowny, sasiednie, a.promien, (E, N), az,
                plik("_orto_podglad.png"))

    # 6. zapis: DXF (mm), odcinki (m), kontekst (cm), meta
    L = lambda g: translate(g, -E0, -N0)
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for nazwa, kolor in (("GEO_DZIALKA", 2), ("GEO_BUDYNEK", 1), ("GEO_SASIEDNIE", 5), ("GEO_PROMIEN", 8), ("GEO_OPISY", 7)):
        doc.layers.add(nazwa, color=kolor)
    msp = doc.modelspace()
    odcinki = []
    for warstwa, g in [("GEO_DZIALKA", dzialka)] + [("GEO_BUDYNEK" if b is glowny else "GEO_SASIEDNIE", b["geom"])
                                                     for b in budynki.values()]:
        for r in pierscienie(L(g)) if g is not None else []:
            msp.add_lwpolyline([(x * 1000, y * 1000) for x, y in r[:-1]], close=True, dxfattribs={"layer": warstwa})
            if warstwa != "GEO_DZIALKA":
                odcinki += [[round(v, 3) for v in (*p, *q)] for p, q in zip(r[:-1], r[1:])]
    if a.promien:
        msp.add_circle(((E - E0) * 1000, (N - N0) * 1000), a.promien * 1000, dxfattribs={"layer": "GEO_PROMIEN"})
    for b in budynki.values():
        p = L(b["geom"]).representative_point()
        t = b.get("kontekst", "BUDYNEK") + (" h=%.1f m" % b["h"] if b.get("h") is not None else "")
        msp.add_text(t, height=max(300, min(1500, a.promien * 20)), dxfattribs={"layer": "GEO_OPISY"}).set_placement(
            (p.x * 1000, p.y * 1000), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(plik(".dxf"))

    kontekst = []
    for b in sasiednie:
        x0, y0, x1, y1 = L(b["geom"]).bounds
        rek = {"id": b["kontekst"], "rodzaj": "budynek", "box": [round(v * 100) for v in (x0, y0, x1, y1)]}
        if b.get("h") is not None:
            z0 = (b["teren"] - teren0 if b.get("teren") is not None and teren0 is not None else 0.0) - a.podloga
            rek["wys"] = [round(z0 * 100), round((z0 + b["h"]) * 100)]
            rek["opis"] = "%s %s; wysokość %.1f m: %s" % (b["zrodlo"], b["id"], b["h"], b["wys_zrodlo"])
            if b["h"] < 2:
                rek["opis"] += "; niski obiekt: budynek podziemny, wiata albo stan sprzed budowy - sprawdź"
        else:
            rek["opis"] = "%s %s; wysokość nieznana: ZAŁOŻENIE kondygnacje × %.1f m, do uzupełnienia" % (
                b["zrodlo"], b["id"], KONDYGNACJA)
        if b["kondygnacje"]:
            rek["opis"] += "; BDOT10k: %d kondygnacji" % b["kondygnacje"]
        kontekst.append(rek)
    obrys = lambda g: [[round(x, 3), round(y, 3)] for x, y in next(pierscienie(L(g)))[:-1]]
    rekord = lambda b: {"id": b["id"], "kontekst": b.get("kontekst"), "zrodlo": b["zrodlo"], "pole_m2": round(b["geom"].area, 1),
                        "odl_m": round(b["geom"].distance(pkt), 1), "wys_m": round(b["h"], 2) if b.get("h") is not None else None,
                        "wys_zrodlo": b.get("wys_zrodlo"), "teren_m": round(b["teren"], 2) if b.get("teren") is not None else None,
                        "kondygnacje": b["kondygnacje"],
                        "tagi_osm": {k: v for k, v in b["tagi"].items() if k in ("building", "building:levels", "height")} or None,
                        "obrys_m": obrys(b["geom"])}
    kat = kierunek_scian(glowny["geom"]) if glowny else None
    zrodla = ["GUGiK UUG (adres)" if a.adres else "wspolrzedne" if a.xy else "GUGiK ULDK (dzialka)"]
    zrodla += ["GUGiK ULDK: EGiB dzialka%s (%s)" % ("" if a.osm else " i budynki", zrodlo_dzialki or "powiat")] if polska else []
    zrodla += ["GUGiK WFS INSPIRE Budynki (BDOT10k): budynki w promieniu, kondygnacje"] if bdot is not None else []
    zrodla += ["OpenStreetMap przez Overpass API: (c) wspoltworcy OpenStreetMap, ODbL 1.0"] if a.osm else []
    zrodla += ["GUGiK WCS NMPT i NMT (PL-EVRF2007-NH): wysokosci budynkow"] if polska and budynki else []
    zrodla += (["GUGiK WMS ORTO HighResolution"] if rozdz else []) + (["GUGiK NMT GetHbyXY"] if teren is not None else [])
    meta = {
        "zrodlo": zrodla, "data": date.today().isoformat(), "dokladnosc_cm": 200 if a.osm else 50,
        "dokladnosc_opis": "EGiB: 10-50 cm zaleznie od zrodla pomiaru; BDOT10k (sasiednie): zwykle z EGiB, do ok. 1 m; "
                           "OSM: 1-3 m; wysokosci NMPT-NMT ok. 0,5 m, stan z daty nalotu; ortofoto: dachy przesuniete "
                           "wzgledem obrysu (przechylenie); wszystko to ZALOZENIE do sprawdzenia pomiarem",
        "uklad": "lokalny, metry od punktu bazowego; +X = wschod, +Y = polnoc siatki %s" % (
            "PL-1992 (EPSG:2180)" if polska else "lokalnego odwzorowania TM (poludnik %.6f)" % lon),
        "punkt_bazowy": {"epsg": 2180 if polska else None, "E": E0, "N": N0, "lat": round(lat0, 7), "lon": round(lon0, 7)},
        "polnoc": {"azymut_osi_Y_stopnie": round(az, 3),
                   "lokalizacja": {"lat": round(lat0, 5), "lon": round(lon0, 5), "strefa": "Europe/Warsaw" if polska else None},
                   "uwaga": "+Y to polnoc siatki, geograficzna ma azymut 0; model z osiami wzdluz scian budynku ma "
                            "azymut_osi_Y = %.2f - obrot scian (st.)" % az},
        "georef": {"epsg": 2180, "x0": E0, "y0": N0, "obrot_stopnie": 0.0,
                   "uwaga": "x0 = E (wschod), y0 = N (polnoc) punktu (0, 0) tego wyniku"} if polska else None,
        "teren_m_npm": teren if teren is not None else (round(teren0, 2) if teren0 is not None else None),
        "podloga_nad_terenem_m": a.podloga,
        "dzialka": {"id": dzialka_id, "pole_m2": round(dzialka.area, 1), "obrys_m": obrys(dzialka)} if dzialka is not None else None,
        "budynek": dict(rekord(glowny), obrot_scian_stopnie=round(kat, 2)) if glowny else None,
        "sasiednie": [rekord(b) for b in sasiednie],
        "orto": {"plik": plik("_orto.png").name, "pgw": plik("_orto.pgw").name, "rozdzielczosc_m": round(rozdz, 4),
                 "bbox_2180": [E0 - pol, N0 - pol, E0 + pol, N0 + pol]} if rozdz else None,
        "bledy_uslug": bledy or None,
        "parametry": {"adres": a.adres, "xy": a.xy, "dzialka": a.dzialka, "promien_m": a.promien, "orto_m_px": a.orto,
                      "osm": a.osm, "zapytan_uldk_w_promieniu": zapytan},
    }
    for koncowka, dane in (("_meta.json", meta), ("_odcinki.json", odcinki), ("_kontekst.json", kontekst)):
        with open(plik(koncowka), "w", encoding="utf-8") as f:
            f.write(json_zwarty(dane) + "\n")
    if teren_pkt:
        with open(plik("_teren.json"), "w", encoding="utf-8") as f:
            f.write(json_zwarty({"zrodlo": "GUGiK NMT (WCS GRID1)", "data": date.today().isoformat(), "krok_m": a.teren,
                                 "dokladnosc_cm": 30, "punkty": teren_pkt}) + "\n")

    # 7. podsumowanie
    if dzialka is not None:
        print("dzialka: %s, %.0f m2" % (dzialka_id, dzialka.area))
    if glowny:
        print("budynek: %s (%s), %.0f m2%s" % (glowny["id"], glowny["zrodlo"], glowny["geom"].area,
                                               ", wysokosc %.1f m (%s)" % (glowny["h"], glowny["wys_zrodlo"])
                                               if glowny.get("h") is not None else ""))
        print("sciany budynku obrocone o %.2f st. wzgledem siatki (przeciwnie do zegara)" % kat)
    ile = {}
    for b in sasiednie:
        ile[b["zrodlo"]] = ile.get(b["zrodlo"], 0) + 1
    print("budynki sasiednie w promieniu %.0f m: %d (%s)%s" % (a.promien, len(sasiednie), ", ".join(
        "%s: %d" % z for z in ile.items()) or "-", "; zapytan ULDK w siatce: %d" % zapytan if zapytan else ""))
    for b, rek in zip(sasiednie, kontekst):
        print("  %-5s box %s cm, wys %s%s%s" % (rek["id"], rek["box"], rek.get("wys", "nieznana"),
                                             ", h %.1f m" % b["h"] if b.get("h") is not None else "",
                                             ", %d kond. (BDOT10k)" % b["kondygnacje"] if b["kondygnacje"] else ""))
    if any(b.get("h") is None for b in budynki.values()):
        print("wysokosc czesci budynkow nieznana: przyjmij kondygnacje x %.1f m jako ZALOZENIE i opisz to w modelu" % KONDYGNACJA)
    if teren0 is not None:
        print("teren: %s m n.p.m. (%s)" % (("%.1f" % (teren if teren is not None else teren0)).replace(".", ","),
                                           "NMT w punkcie bazowym" if teren is not None else "mediana NMT pod budynkiem"))
    if teren_pkt:
        print("punkty terenu: %d co %g m (%s + 10 m)" % (len(teren_pkt), a.teren, "dzialka" if dzialka is not None else "promien"))
    elif teren_pkt is not None:
        print("punkty terenu: NMT bez danych w obszarze - bez pliku _teren.json")
    print("azymut osi +Y (polnoc siatki) od polnocy geograficznej: %.2f st.%s" % (
        az, "; wzor przyblizony (dl - 19) x sin(szer) = %.2f st." % ((lon0 - 19) * math.sin(math.radians(lat0))) if polska else ""))
    if glowny:
        print("model z osiami wzdluz scian budynku: meta.polnoc.azymut_osi_Y_stopnie = %.2f (albo +-90)" % (az - kat))
    for koncowka in (".dxf", "_odcinki.json", "_kontekst.json", "_meta.json") + (
            ("_orto.png", "_orto.pgw", "_orto_podglad.png") if rozdz else ()) + (("_teren.json",) if teren_pkt else ()):
        print("zapisano", plik(koncowka))
    if bledy:
        print("uwaga: %d uslug nie odpowiedzialo - wynik niepelny (lista w meta.bledy_uslug)" % len(bledy))
    return 0 if (budynki or dzialka is not None) else 1


if __name__ == "__main__":
    sys.exit(main())
