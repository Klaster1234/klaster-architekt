"""Sprawdza przynaleznosc punktow elektryki i wod-kan do wlasciwych pomieszczen.

    python lokal/punkty.py przyklad/mieszkanie/model/lokal_projekt.json
    python lokal/punkty.py przyklad/mieszkanie/model/lokal_projekt.json --tol 2

Dla kazdego punktu z "elektryka" i "wod_kan.punkty" (srodek odcinka dla
"linia") liczy fizyczne pomieszczenie z geometrii modelu
(geometria.pomieszczenie_punktu) i porownuje je z zadeklarowanym polem
"pomieszczenie". Roznica bez pola "wyjatek" to blad; z polem "wyjatek" to
swiadomy wyjatek (wypisany osobno, np. lacznik swiatla lazienki zamontowany
w holu). Punkty, ktore nie trafiaja w zaden wielokat pomieszczenia (nawet
w granicy tolerancji), sa wypisywane osobno do recznego sprawdzenia. Kod
wyjscia 1, gdy sa bledy albo punkty poza wielokatami.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lokal import model, geometria
from zamierzenie import model as zmodel


def _xy(rekord):
    """Wspolrzedne punktu: pole "xy" wprost albo srodek odcinka "linia"."""
    if "xy" in rekord:
        return tuple(rekord["xy"])
    a, b = rekord["linia"]
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _punkty(M):
    """Wszystkie punkty do sprawdzenia jako pary (sekcja, rekord)."""
    wynik = [("elektryka", r) for r in M.get("elektryka", [])]
    wynik += [("wod_kan", r) for r in (M.get("wod_kan") or {}).get("punkty", [])]
    return wynik


def sprawdz(M, tol):
    """(bledy, wyjatki, poza) — gotowe do wypisania opisy problemow."""
    bledy, wyjatki, poza = [], [], []
    for sekcja, r in _punkty(M):
        nr = r.get("pomieszczenie")
        fiz = geometria.pomieszczenie_punktu(M, _xy(r), tol)
        if fiz == nr:
            continue
        if fiz is None:
            poza.append("[%s] %s (%s): xy=%s nie trafia w zadne pomieszczenie (deklarowane %s)"
                        % (sekcja, r["id"], r.get("typ", ""), _xy(r), nr))
            continue
        if r.get("wyjatek"):
            wyjatki.append("[%s] %s: deklarowane %s, fizycznie %s — %s"
                           % (sekcja, r["id"], nr, fiz, r["wyjatek"]))
            continue
        bledy.append("[%s] %s: deklarowane %s, fizycznie %s — %s"
                     % (sekcja, r["id"], nr, fiz, r.get("opis", "")))
    return bledy, wyjatki, poza


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--tol", type=float, default=1.0, help="tolerancja w cm (domyslnie 1)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj rysunki/wszystko.py (kontrola punktow kazdego modulu wnetrz); "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        return 2
    bledy, wyjatki, poza = sprawdz(M, a.tol)
    n = len(M.get("elektryka", [])) + len((M.get("wod_kan") or {}).get("punkty", []))
    print("PUNKTY: %d (bledow: %d, wyjatkow: %d, poza wielokatami: %d)"
          % (n, len(bledy), len(wyjatki), len(poza)))
    if bledy:
        print("\nBLEDY PRZYNALEZNOSCI:")
        for b in bledy:
            print("  -", b)
    if wyjatki:
        print("\nWYJATKI (swiadome):")
        for w in wyjatki:
            print("  -", w)
    if poza:
        print("\nPOZA WSZYSTKIMI WIELOKATAMI:")
        for p in poza:
            print("  -", p)
    zle = len(bledy) + len(poza)
    print("\nWYNIK:", "OK" if not zle else "%d problemow" % zle)
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
