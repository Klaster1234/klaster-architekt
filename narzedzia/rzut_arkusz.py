"""Sklada arkusz rzutu w skali z wektorowego PDF-u, z podzialka liniowa.

    python rzut_arkusz.py rzut.pdf arkusz.pdf --skala 30.768 --x0 272.64 --y1 2241.38 \
        --zakres 3.6 20.4 42.8 71.2 --tytul "RZUT WNETRZA"

Kreska zostaje oryginalna, zmienia sie tylko grubosc i szarosc wedlug warstwy,
zeby mur byl czarny, a wyposazenie jasne. Skala rysunkowa domyslnie 1:100.
"""
import argparse
import fitz

STYL = {(0.328,0.328,0.328): ((0.10,0.10,0.10), 1.2),
        (0.0,0.0,0.0):       ((0.10,0.10,0.10), 0.9),
        (0.73,0.73,0.73):    ((0.45,0.45,0.45), 0.5),
        (0.859,0.859,0.859): ((0.55,0.55,0.55), 0.4),
        (0.5,0.5,0.5):       ((0.45,0.45,0.45), 0.5),
        (1.0,0.496,0.0):     ((0.62,0.62,0.62), 0.4),
        (0.0,0.723,0.359):   ((0.60,0.60,0.60), 0.4)}

def klucz(c): return tuple(round(v,3) for v in c) if c else None

def arkusz(pdf, out, skala_pdf, x0, y1, zakres, tytul, podtytul="", rys=100, strona=0):
    X0, X1, Y0, Y1 = zakres
    SC = 2834.65 / rys                      # 1 m w punktach przy skali 1:rys
    Wpt, Hpt = (X1-X0)*SC + 120, (Y1-Y0)*SC + 200
    sp = fitz.open(pdf)[strona]
    doc = fitz.open(); pg = doc.new_page(width=Wpt, height=Hpt)
    P = lambda x, y: fitz.Point(60 + (x-X0)*SC, Hpt - 130 - (y-Y0)*SC)
    mm = lambda x, y: ((x-x0)/skala_pdf, (y1-y)/skala_pdf)
    n = 0
    for d in sp.get_drawings():
        st = STYL.get(klucz(d.get("color"))) or STYL.get(klucz(d.get("fill")))
        if st is None:
            continue
        col, wd = st
        r = d["rect"]
        if mm(r.x0, r.y1)[1] < Y0 - 0.3:
            continue
        sh = pg.new_shape()
        for it in d["items"]:
            if it[0] == "l":
                sh.draw_line(P(*mm(it[1].x, it[1].y)), P(*mm(it[2].x, it[2].y)))
            elif it[0] == "re":
                q = it[1]; a, b = mm(q.x0, q.y1), mm(q.x1, q.y0)
                sh.draw_rect(fitz.Rect(P(*a).x, P(*a).y, P(*b).x, P(*b).y))
            elif it[0] == "qu":
                u = it[1]
                sh.draw_polyline([P(*mm(u.ul.x,u.ul.y)), P(*mm(u.ur.x,u.ur.y)),
                                  P(*mm(u.lr.x,u.lr.y)), P(*mm(u.ll.x,u.ll.y)),
                                  P(*mm(u.ul.x,u.ul.y))])
            elif it[0] == "c":
                sh.draw_bezier(P(*mm(it[1].x,it[1].y)), P(*mm(it[2].x,it[2].y)),
                               P(*mm(it[3].x,it[3].y)), P(*mm(it[4].x,it[4].y)))
        sh.finish(color=col, width=wd, lineCap=1, lineJoin=1)
        sh.commit(); n += 1
    sh = pg.new_shape()
    for i in range(5):
        sh.draw_rect(fitz.Rect(60+i*SC, Hpt-75, 60+(i+1)*SC, Hpt-66))
        sh.finish(color=(0,0,0), fill=(0,0,0) if i % 2 == 0 else (1,1,1), width=0.6)
    sh.commit()
    pg.insert_text(fitz.Point(60, Hpt-84), "0", fontsize=8)
    pg.insert_text(fitz.Point(60+5*SC-10, Hpt-84), "5 m", fontsize=8)
    pg.insert_text(fitz.Point(60, 42), "%s   1:%d" % (tytul, rys), fontname="hebo", fontsize=14)
    if podtytul:
        pg.insert_text(fitz.Point(60, 58), podtytul, fontsize=8)
    pg.insert_text(fitz.Point(60, Hpt-46), "%d obiektow rysunkowych" % n, fontsize=8)
    doc.save(out)
    return n

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("out")
    ap.add_argument("--skala", type=float, required=True)
    ap.add_argument("--x0", type=float, required=True)
    ap.add_argument("--y1", type=float, required=True)
    ap.add_argument("--zakres", nargs=4, type=float, required=True, metavar=("X0","X1","Y0","Y1"))
    ap.add_argument("--tytul", default="RZUT")
    ap.add_argument("--podtytul", default="")
    ap.add_argument("--rys", type=int, default=100)
    a = ap.parse_args()
    print("obiektow:", arkusz(a.pdf, a.out, a.skala, a.x0, a.y1, a.zakres, a.tytul, a.podtytul, a.rys))
