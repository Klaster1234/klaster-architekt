"""Odczytuje podzialke liniowa z wektorowego PDF-u i zwraca punkty na metr.

    python skala.py rzut.pdf
Szuka ciagu przylegajacych prostokatow o rownej wysokosci (klasyczna podzialka
czarno-biala) i liczy dlugosc jednego segmentu. Wynik trzeba potwierdzic opisem
przy podzialce, bo segment moze znaczyc 1 m albo 5 m.
"""
import sys, collections
import fitz

def znajdz(pdf, strona=0):
    p = fitz.open(pdf)[strona]
    kandydaci = collections.defaultdict(list)
    for d in p.get_drawings():
        for it in d["items"]:
            if it[0] != "re":
                continue
            r = it[1]
            if r.width < 1 or r.height < 1:
                continue
            dl, gr = max(r.width, r.height), min(r.width, r.height)
            if not (2 < dl / gr < 40):
                continue
            pion = r.height > r.width
            klucz = (pion, round(gr, 1), round(r.x0 if pion else r.y0, 1))
            kandydaci[klucz].append(r)
    najlepszy = None
    for klucz, rects in kandydaci.items():
        if len(rects) < 3:
            continue
        pion = klucz[0]
        rects.sort(key=lambda r: r.y0 if pion else r.x0)
        dl = [(r.height if pion else r.width) for r in rects]
        sr = sum(dl) / len(dl)
        if max(abs(d - sr) for d in dl) > 0.06 * sr:
            continue
        if najlepszy is None or len(rects) > len(najlepszy[1]):
            najlepszy = (sr, rects)
    return najlepszy

if __name__ == "__main__":
    w = znajdz(sys.argv[1])
    if not w:
        sys.exit("nie znalazlem podzialki")
    seg, rects = w
    print("segmentow: %d, segment = %.3f pkt" % (len(rects), seg))
    print("jesli segment to 1 m:  1 m = %.3f pkt" % seg)
    print("jesli segment to 5 m:  1 m = %.3f pkt" % (seg / 5))
