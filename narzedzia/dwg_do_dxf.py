"""Zamienia DWG na DXF przez ODA File Converter i wypisuje, co jest w srodku.

    python narzedzia/dwg_do_dxf.py rzut.dwg
    python narzedzia/dwg_do_dxf.py rzut.dwg --wyjscie robocze/ --wersja ACAD2013

ODA File Converter (darmowy, opendesign.com) szuka sie w zmiennej ODA_CONVERTER, w PATH
i w typowych miejscach macOS i Windows (najnowsza wersja). Konwerter pracuje na katalogach,
wiec plik przechodzi przez katalog tymczasowy. Raport: wersja DXF, bledy audytu, $INSUNITS,
zakres rysunku, warstwy z liczba encji wg typu. Jednostek nie zakladaj: DWG bywa w mm, cm
albo m, a $INSUNITS bywa puste, wiec sprawdz je jednym znanym wymiarem (np. encja DIMENSION).
Do digitalizacji bierz lica scian, wymiary i opisy pomieszczen; sasiednie lokale pomijaj.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ezdxf import bbox, recover
from ezdxf.lldxf.const import DXFError

# konsola Windows z kodowa strona inna niz UTF-8 inaczej wysypuje sie na polskich znakach w wydruku
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

JEDNOSTKI = {0: "brak", 1: "cale", 2: "stopy", 4: "mm", 5: "cm", 6: "m"}
WERSJE = ("ACAD9", "ACAD10", "ACAD12", "ACAD13", "ACAD14", "ACAD2000", "ACAD2004", "ACAD2007",
          "ACAD2010", "ACAD2013", "ACAD2018")


def _wersja(sciezka):
    return [int(n) for n in re.findall(r"\d+", sciezka)]


def znajdz_oda():
    """ODA_CONVERTER -> PATH -> /Applications i ~/Applications (macOS) -> Program Files (Windows) -> /usr/bin."""
    env = os.environ.get("ODA_CONVERTER")
    if env:
        if Path(env).is_file():
            return Path(env)
        print("uwaga: ODA_CONVERTER wskazuje nieistniejacy plik: %s" % env)
    for nazwa in ("ODAFileConverter", "ODAFileConverter.exe"):
        if shutil.which(nazwa):
            return Path(shutil.which(nazwa))
    kandydaci = []
    for wzor in ("/Applications/ODAFileConverter*.app/Contents/MacOS/ODAFileConverter",
                 str(Path.home() / "Applications/ODAFileConverter*.app/Contents/MacOS/ODAFileConverter"),
                 "C:/Program Files/ODA/ODAFileConverter*/ODAFileConverter.exe",
                 "/usr/bin/ODAFileConverter"):
        kandydaci += sorted(glob.glob(wzor), key=_wersja, reverse=True)
    return Path(kandydaci[0]) if kandydaci else None


def konwertuj(oda, dwg, cel, wersja):
    """DWG -> DXF w katalogu tymczasowym; zwraca sciezke DXF albo None."""
    with tempfile.TemporaryDirectory() as tmp:
        we, wy = Path(tmp, "we"), Path(tmp, "wy")
        we.mkdir()
        wy.mkdir()
        shutil.copy2(dwg, we / "plik.dwg")
        # argumenty ODA: katalog wejscia, wyjscia, wersja, typ, rekursja, audyt, filtr
        polecenie = [str(oda), str(we), str(wy), wersja, "DXF", "0", "1", "*.dwg"]
        try:
            wynik = subprocess.run(polecenie, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as e:
            print("ODA nie uruchomil sie: %s" % e)
            return None
        for err in wy.glob("*.err"):
            print("audyt ODA (%s):" % err.name)
            print(err.read_text(encoding="utf-8", errors="replace").strip()[:2000])
        dxf = sorted(wy.glob("*.dxf"))
        if not dxf:
            print("ODA nie utworzyl DXF (kod %s). %s" % (wynik.returncode, (wynik.stderr or wynik.stdout).strip()[:500]))
            return None
        cel.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dxf[0]), str(cel))
    return cel


def raport(sciezka):
    doc, audyt = recover.readfile(str(sciezka))
    msp = doc.modelspace()
    ins = doc.header.get("$INSUNITS", 0)
    print("\n%s (%.1f MB): DXF %s, bledy audytu: %d" % (sciezka.name, sciezka.stat().st_size / 1e6,
                                                       doc.dxfversion, len(audyt.errors)))
    print("$INSUNITS = %d (%s)" % (ins, JEDNOSTKI.get(ins, "inne")))
    zakres = bbox.extents(msp, fast=True)
    if zakres.has_data:
        (x0, y0, _), (x1, y1, _) = zakres.extmin, zakres.extmax
        print("zakres: %.1f x %.1f jednostek (od %.1f, %.1f do %.1f, %.1f)" % (x1 - x0, y1 - y0, x0, y0, x1, y1))
        if ins == 0:
            print("jednostki nieznane - zakres to %.1f x %.1f m przy mm, %.1f x %.1f m przy cm, %.1f x %.1f m przy m"
                  % ((x1 - x0) / 1000, (y1 - y0) / 1000, (x1 - x0) / 100, (y1 - y0) / 100, x1 - x0, y1 - y0))
    warstwy = {}
    for e in msp:
        typy = warstwy.setdefault(e.dxf.layer, {})
        typy[e.dxftype()] = typy.get(e.dxftype(), 0) + 1
    print("warstwy z encjami w modelu: %d (w pliku zdefiniowanych: %d), bloki: %d" % (
        len(warstwy), len(doc.layers), len([b for b in doc.blocks if not b.name.startswith("*")])))
    for nazwa in sorted(warstwy, key=lambda w: -sum(warstwy[w].values())):
        typy = ", ".join("%s:%d" % t for t in sorted(warstwy[nazwa].items(), key=lambda t: -t[1]))
        print("  %-40s %6d  (%s)" % (nazwa, sum(warstwy[nazwa].values()), typy))
    return doc


def main():
    ap = argparse.ArgumentParser(description="DWG -> DXF przez ODA File Converter + raport zawartosci")
    ap.add_argument("dwg")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog pliku>/wyjscie)")
    ap.add_argument("--nazwa", help="nazwa pliku DXF bez rozszerzenia (domyslnie jak DWG)")
    ap.add_argument("--wersja", default="ACAD2018", choices=WERSJE, help="wersja DXF (domyslnie ACAD2018)")
    a = ap.parse_args()
    dwg = Path(a.dwg)
    if not dwg.is_file():
        print("brak pliku %s" % dwg)
        return 1
    oda = znajdz_oda()
    if oda is None:
        print("Nie znaleziono ODA File Converter. Zainstaluj go (darmowy: https://www.opendesign.com/guestfiles/"
              "oda_file_converter) albo ustaw zmienna ODA_CONVERTER na sciezke programu, np.\n"
              "  Windows: C:/Program Files/ODA/ODAFileConverter <wersja>/ODAFileConverter.exe\n"
              "  macOS:   /Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter")
        return 2
    print("ODA:", oda)
    cel = (Path(a.wyjscie) if a.wyjscie else dwg.parent / "wyjscie") / ((a.nazwa or dwg.stem) + ".dxf")
    if konwertuj(oda, dwg, cel, a.wersja) is None:
        return 3
    print("zapisano", cel)
    try:
        raport(cel)
    except (IOError, DXFError) as e:
        print("DXF zapisany, ale nie da sie go odczytac do raportu:", e)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
