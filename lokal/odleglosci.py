"""Audyt wzajemnych odleglosci elementow aranzacji jednego pomieszczenia.

    python lokal/odleglosci.py przyklad/mieszkanie/model/lokal_projekt.json P3
    python lokal/odleglosci.py przyklad/mieszkanie/model/lokal_projekt.json P3 --prog 60

Nakladki w rzucie: pary elementow, ktorych prostokaty "box" sie przecinaja.
Rozlaczne przedzialy wysokosci ("wys") tlumacza nakladke (np. polka nad
stolem) i nie sa bledem; reszta to twarde kolizje. Luki: pary blizej siebie
niz prog, posortowane rosnaco, do przegladu (np. czy zostawiono min. 90 cm
przejscia). Kod wyjscia 1, gdy sa twarde kolizje.
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lokal import model, geometria
from zamierzenie import model as zmodel


def _bounds(e):
    return geometria.prostokat(e["box"]).bounds


def _luka(a, b):
    """(odleglosc, kierunek) miedzy dwoma prostokatami (x0,y0,x1,y1); 0 = styk/nakladka."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    if dx > 0 and dy > 0:
        return math.hypot(dx, dy), "przekatna"
    if dx > 0:
        return dx, "x"
    if dy > 0:
        return dy, "y"
    return 0.0, "styk"


def audyt(M, nr, prog):
    """(twarde, ciche, luki) — opisy kolizji/nakladek i lista luk (odl, id1, id2, kierunek)."""
    elementy = model.elementy(M, nr)
    twarde, ciche, luki = [], [], []
    for i in range(len(elementy)):
        for j in range(i + 1, len(elementy)):
            e1, e2 = elementy[i], elementy[j]
            a, b = _bounds(e1), _bounds(e2)
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 0.01 and oy > 0.01:
                w1, w2 = e1.get("wys"), e2.get("wys")
                if w1 and w2 and (w1[1] <= w2[0] or w2[1] <= w1[0]):
                    ciche.append("%s x %s: %.1f x %.1f cm w rzucie, rozlaczne wysokosci"
                                % (e1["id"], e2["id"], ox, oy))
                else:
                    twarde.append("%s x %s: %.1f x %.1f cm" % (e1["id"], e2["id"], ox, oy))
                continue
            g, kier = _luka(a, b)
            if 0 < g < prog:
                luki.append((g, e1["id"], e2["id"], kier))
    luki.sort()
    return twarde, ciche, luki


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("nr", help="numer pomieszczenia")
    ap.add_argument("--prog", type=float, default=120.0, help="prog luki w cm (domyslnie 120)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj zamierzenie/waliduj.py (kolizje obiektow); "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        return 2
    try:
        model.pomieszczenie(M, a.nr)
    except KeyError as e:
        sys.exit(e.args[0])
    twarde, ciche, luki = audyt(M, a.nr, a.prog)
    print("NAKLADKI w %s:" % a.nr)
    for t in twarde:
        print("  BLAD", t)
    for c in ciche:
        print("  ok  ", c)
    if not twarde and not ciche:
        print("  brak")
    print("\nLUKI < %g cm w %s (posortowane):" % (a.prog, a.nr))
    for g, id1, id2, kier in luki:
        print("  %-4s <-> %-4s %6.1f cm (%s)" % (id1, id2, g, kier))
    if not luki:
        print("  brak")
    print("\nWYNIK:", "OK" if not twarde else "%d twardych kolizji" % len(twarde))
    return 1 if twarde else 0


if __name__ == "__main__":
    sys.exit(main())
