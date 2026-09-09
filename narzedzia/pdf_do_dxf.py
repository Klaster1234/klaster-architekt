"""Zamienia wektorowy rzut PDF na warstwowy DXF w milimetrach.

    python pdf_do_dxf.py rzut.pdf wynik.dxf --skala 30.768 --x0 272.64 --y1 2241.38

--skala to punkty PDF na metr (patrz skala.py), --x0 i --y1 to punkt zerowy
rysunku w ukladzie PDF. Kolory kreski ida na warstwy, bo w rzutach budowlanych
kolor niesie znaczenie: mur, wyposazenie, zielen, instalacje.
"""
import argparse
import fitz

WARSTWY = {
    (0.328, 0.328, 0.328): ("MURY", 8),
    (0.0, 0.0, 0.0): ("BUDYNEK", 7),
    (0.73, 0.73, 0.73): ("ZABUDOWA", 9),
    (0.859, 0.859, 0.859): ("ZABUDOWA", 9),
    (0.5, 0.5, 0.5): ("ZABUDOWA", 9),
    (1.0, 0.496, 0.0): ("WYPOSAZENIE", 30),
    (0.0, 0.723, 0.359): ("ZIELEN", 3),
    (0.0, 1.0, 0.0): ("TRASY", 3),
    (0.867, 0.543, 0.43): ("TRASY", 1),
    (0.586, 0.0, 0.438): ("BAR", 6),
    (0.0, 0.867, 0.648): ("INSTALACJE", 4),
    (0.0, 0.0, 1.0): ("INSTALACJE", 4),
}

def klucz(c):
    return tuple(round(v, 3) for v in c) if c else None

def bezier(a, b, c, d, n=6):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3*a.x + 3*u*u*t*b.x + 3*u*t*t*c.x + t**3*d.x,
                    u**3*a.y + 3*u*u*t*b.y + 3*u*t*t*c.y + t**3*d.y))
    return out

def konwertuj(pdf, dxf, skala, x0, y1, strona=0, ymin_m=None):
    p = fitz.open(pdf)[strona]
    mm = lambda x, y: (round((x - x0) / skala * 1000, 2), round((y1 - y) / skala * 1000, 2))
    ent, uzyte = [], {}

    def zapisz(lay, pts, zamkniety=False):
        if len(pts) < 2:
            return
        if ymin_m is not None and min(q[1] for q in pts) < ymin_m * 1000:
            return
        s = ["0\nLWPOLYLINE\n8\n%s\n100\nAcDbEntity\n100\nAcDbPolyline\n90\n%d\n70\n%d\n"
             % (lay, len(pts), 1 if zamkniety else 0)]
        for x, y in pts:
            s.append("10\n%.2f\n20\n%.2f\n" % (x, y))
        ent.append("".join(s))

    for d in p.get_drawings():
        c, f = klucz(d.get("color")), klucz(d.get("fill"))
        lay = WARSTWY.get(c) or WARSTWY.get(f)
        if lay is None:
            lay = ("OPISY", 8) if (c == (0.0, 0.0, 0.0) or f == (0.0, 0.0, 0.0)) else ("INNE", 2)
        nazwa, aci = lay
        uzyte[nazwa] = aci
        biezacy = []
        for it in d["items"]:
            if it[0] == "l":
                a, b = mm(it[1].x, it[1].y), mm(it[2].x, it[2].y)
                if biezacy and biezacy[-1] == a:
                    biezacy.append(b)
                else:
                    zapisz(nazwa, biezacy)
                    biezacy = [a, b]
            elif it[0] == "c":
                a = mm(it[1].x, it[1].y)
                if not (biezacy and biezacy[-1] == a):
                    zapisz(nazwa, biezacy)
                    biezacy = [a]
                biezacy += [mm(x, y) for x, y in bezier(it[1], it[2], it[3], it[4])]
            elif it[0] in ("re", "qu"):
                zapisz(nazwa, biezacy)
                biezacy = []
                if it[0] == "re":
                    r = it[1]
                    q = [mm(r.x0, r.y0), mm(r.x1, r.y0), mm(r.x1, r.y1), mm(r.x0, r.y1)]
                else:
                    u = it[1]
                    q = [mm(u.ul.x, u.ul.y), mm(u.ur.x, u.ur.y), mm(u.lr.x, u.lr.y), mm(u.ll.x, u.ll.y)]
                zapisz(nazwa, q, True)
        zapisz(nazwa, biezacy)

    tabela = "".join("0\nLAYER\n2\n%s\n70\n0\n62\n%d\n6\nCONTINUOUS\n" % (n, a)
                     for n, a in sorted(uzyte.items()))
    naglowek = ("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n9\n$MEASUREMENT\n70\n1\n0\nENDSEC\n"
                "0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n%d\n%s0\nENDTAB\n0\nENDSEC\n"
                % (len(uzyte), tabela))
    with open(dxf, "w") as fh:
        fh.write(naglowek + "0\nSECTION\n2\nENTITIES\n" + "".join(ent) + "0\nENDSEC\n0\nEOF\n")
    return len(ent), sorted(uzyte)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("dxf")
    ap.add_argument("--skala", type=float, required=True, help="punkty PDF na metr")
    ap.add_argument("--x0", type=float, required=True)
    ap.add_argument("--y1", type=float, required=True)
    ap.add_argument("--ymin", type=float, default=None, help="obetnij ponizej tej wspolrzednej Y w metrach")
    a = ap.parse_args()
    n, w = konwertuj(a.pdf, a.dxf, a.skala, a.x0, a.y1, ymin_m=a.ymin)
    print("encji: %d, warstwy: %s" % (n, ", ".join(w)))
