"""Paruje rownolegle linie rzutu, zeby wyliczyc rzeczywiste grubosci scian.

    python sciany_z_rzutu.py sciany.json wynik.json --ymin 43

Rzut rysuje sciane dwiema liniami: obie jej lica. Program szuka par
rownoleglych, blisko siebie i pokrywajacych sie wzdluz, i zwraca prostokaty
scian z gruboscia. Wynik to podstawa do wyciagniecia bryly 3D.
Wejscie: JSON z lista odcinkow [x1,y1,x2,y2] w metrach.
"""
import argparse, json, math

def paruj(seg, dmin=0.06, dmax=0.75, min_dl=0.35, tol_kat=0.035, min_pokrycie=0.6):
    def dlugosc(s): return math.hypot(s[2] - s[0], s[3] - s[1])
    def kat(s): return math.atan2(s[3] - s[1], s[2] - s[0]) % math.pi
    seg = [s for s in seg if dlugosc(s) > min_dl]
    pary, uzyte = [], set()
    for i, a in enumerate(seg):
        if i in uzyte:
            continue
        la = dlugosc(a)
        ux, uy = (a[2] - a[0]) / la, (a[3] - a[1]) / la
        aa = kat(a)
        naj = None
        for j, b in enumerate(seg):
            if j <= i or j in uzyte:
                continue
            if min(abs(kat(b) - aa), math.pi - abs(kat(b) - aa)) > tol_kat:
                continue
            d = abs(-uy * (b[0] - a[0]) + ux * (b[1] - a[1]))
            if not (dmin < d < dmax):
                continue
            t1 = ux * (b[0] - a[0]) + uy * (b[1] - a[1])
            t2 = ux * (b[2] - a[0]) + uy * (b[3] - a[1])
            pokr = max(0.0, min(max(t1, t2), la) - max(min(t1, t2), 0.0))
            if pokr < min_pokrycie * min(la, dlugosc(b)):
                continue
            if naj is None or d < naj[0]:
                naj = (d, j)
        if naj:
            pary.append([a, seg[naj[1]], round(naj[0], 3)])
            uzyte.add(i); uzyte.add(naj[1])
    return pary, len(seg) - len(uzyte)

def prostokat(a, b, d):
    """Zamienia pare linii na czworokat sciany."""
    L = math.hypot(a[2] - a[0], a[3] - a[1])
    ux, uy = (a[2] - a[0]) / L, (a[3] - a[1]) / L
    nx, ny = -uy, ux
    s = 1.0 if (-uy * (b[0] - a[0]) + ux * (b[1] - a[1])) > 0 else -1.0
    t = [0.0, L, ux * (b[0] - a[0]) + uy * (b[1] - a[1]), ux * (b[2] - a[0]) + uy * (b[3] - a[1])]
    lo, hi = max(0.0, min(t[2], t[3])), min(L, max(t[2], t[3]))
    if hi - lo < 0.3:
        return None
    p0 = (a[0] + ux * lo, a[1] + uy * lo)
    p1 = (a[0] + ux * hi, a[1] + uy * hi)
    q = (nx * d * s, ny * d * s)
    return [p0, p1, (p1[0] + q[0], p1[1] + q[1]), (p0[0] + q[0], p0[1] + q[1])]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("wejscie"); ap.add_argument("wyjscie")
    ap.add_argument("--ymin", type=float, default=None)
    a = ap.parse_args()
    seg = json.load(open(a.wejscie))
    if a.ymin is not None:
        seg = [s for s in seg if min(s[1], s[3]) >= a.ymin]
    pary, niesparowane = paruj(seg)
    json.dump(pary, open(a.wyjscie, "w"))
    gr = sorted(p[2] for p in pary)
    print("par: %d, niesparowanych odcinkow: %d" % (len(pary), niesparowane))
    if gr:
        print("grubosci: min %.2f, mediana %.2f, max %.2f m" % (gr[0], gr[len(gr)//2], gr[-1]))
