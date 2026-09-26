"""Karta pomieszczenia: aranzacja jednego pomieszczenia na arkuszu (SVG, PNG, PDF).

    python rysunki/karta_pomieszczenia.py przyklad/mieszkanie/model/lokal_projekt.json P3
    python rysunki/karta_pomieszczenia.py przyklad/mieszkanie/model/lokal_projekt.json P1 P2 --wyjscie robocze/

Pomieszczenie w kadrze z otoczeniem: sciany, otwory pomieszczenia z lukami, meble z
frontami i segmentami (styl wg kategorii), elementy zaczynajace sie od 130 cm w gore
przerywana bez wypelnienia, punkty elektryczne pomieszczenia, lancuchy wzdluz scian
(oscieza, konce lic i meble przy scianach, dlugosci lic, calosc), wymiary kontrolne
i pas kontroli (aranzacja[nr].kontrole) nad rysunkiem. Numer pomieszczenia jest
wymagany. Wynik: <wyjscie>/<id>_karta_<nr>.svg|png|pdf.
"""
import argparse
import math
import sys
import textwrap
from pathlib import Path

from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import svg, arkusz
from wspolne.opisy import Opisy, blok_tekstu, rect_tekstu, szer_tekstu
from lokal import model, geometria, plan
from zamierzenie import model as zmodel

DOTYK = 5            # element lub punkt "przy scianie": nie dalej niz 5 cm od lica
ODSTEP_PX = 26       # odstep kolejnych lancuchow na arkuszu
KOLOR_KONTROLI = "#2E7D54"
NAZWY_KATEGORII = {
    "siedzisko": "siedziska", "stol": "stoły, biurka", "stolik": "stoliki", "lozko": "łóżka",
    "sofa": "sofy, narożniki", "zabudowa_niska": "zabudowa niska, szafki", "zabudowa_wysoka": "szafy, zabudowa wysoka",
    "wiszaca": "szafki wiszące, półki", "sanitariat": "ceramika sanitarna", "prysznic": "prysznic",
    "urzadzenie": "urządzenia AGD", "murek": "murki", "szklo": "szkło", "lustro": "lustra", "inne": "inne elementy",
}
# bok pomieszczenia -> (kierunek na zewnatrz, os wzdluz boku)
BOKI = {"N": ((0, 1), 0), "S": ((0, -1), 0), "E": ((1, 0), 1), "W": ((-1, 0), 1)}


def w_srodku(k, r, zapas=2.0):
    return k[0] >= r[0] + zapas and k[2] <= r[2] - zapas and k[1] >= r[1] + zapas and k[3] <= r[3] - zapas


def os_lica(lico):
    """0 dla lica wzdluz X, 1 dla lica wzdluz Y."""
    nx, ny = lico["normalna"]
    return 0 if abs(ny) >= abs(nx) else 1


def przy_licu(lico, b, tol=DOTYK):
    """Zakres (od, do) prostokata b wzdluz osi lica, gdy b dotyka lica od strony pomieszczenia."""
    nx, ny = lico["normalna"]
    ax, ay = lico["a"]
    s = [(x - ax) * nx + (y - ay) * ny for x in (b[0], b[2]) for y in (b[1], b[3])]
    if min(s) > tol or max(s) <= 0:
        return None
    os = os_lica(lico)
    lo, hi = sorted((lico["a"][os], lico["b"][os]))
    od, do = max(min(b[os], b[os + 2]), lo), min(max(b[os], b[os + 2]), hi)
    return (od, do) if do - od > 1 else None


def lico_punktu(M, xy, tol=DOTYK, nr=None):
    """Lico (dowolnego albo wskazanego pomieszczenia), przy ktorym lezy punkt; None dla punktow w polu."""
    for n in ([nr] if nr else geometria.wielokaty(M)):
        for l in geometria.lica(M, n):
            nx, ny = l["normalna"]
            (ax, ay), (bx, by) = l["a"], l["b"]
            s = (xy[0] - ax) * nx + (xy[1] - ay) * ny
            t = ((xy[0] - ax) * (bx - ax) + (xy[1] - ay) * (by - ay)) / l["dl"]
            if abs(s) <= tol and -1 <= t <= l["dl"] + 1:
                return l
    return None


def zasieg_za_licem(M, lico):
    """Jak daleko za licem (w strone przeciwna do pomieszczenia) siega sciana albo szacht, w cm."""
    if lico["sciana"]:
        b = next(s["pas"] for s in M["sciany"] if s["id"] == lico["sciana"])
    elif lico["szacht"]:
        b = next(s["box"] for s in M.get("szachty", []) if s["id"] == lico["szacht"])
    else:
        return 0.0
    b = geometria.prostokat(b).bounds
    nx, ny = lico["normalna"]
    ax, ay = lico["a"]
    return max(0.0, max(-((x - ax) * nx + (y - ay) * ny) for x in (b[0], b[2]) for y in (b[1], b[3])))


def lancuchy_bokow(M, nr):
    """Dla kazdego boku: rzedy podzialow (od najblizszego sciany) i zasieg scian za bokiem obwiedni."""
    w = geometria.wielokaty(M)[nr]
    x0, y0, x1, y1 = w.bounds
    krawedz = {"N": y1, "S": -y0, "E": x1, "W": -x0}
    elementy = [geometria.prostokat(e["box"]).bounds for e in model.elementy(M, nr)]
    # tylko lica obrysu zewnetrznego (bez dziur: szacht albo slup stojacy w pomieszczeniu)
    obrys = [l for l in geometria.lica(M, nr)
             if w.exterior.distance(Point((l["a"][0] + l["b"][0]) / 2, (l["a"][1] + l["b"][1]) / 2)) < 0.5]
    wynik = {}
    for bok, (o, os) in BOKI.items():
        lica_b = [l for l in obrys if (l["normalna"][0] * -o[0] + l["normalna"][1] * -o[1]) > 0.7]
        if not lica_b:
            wynik[bok] = {"rzedy": [], "zasieg": 0.0, "niepewny": False}
            continue
        konce, rzad_a, zasieg = set(), set(), 0.0
        for l in lica_b:
            lo, hi = sorted((l["a"][os], l["b"][os]))
            konce.update((round(lo, 1), round(hi, 1)))
            if l["sciana"]:
                for ot in M.get("otwory", []):
                    if ot["sciana"] == l["sciana"]:
                        rzad_a.update(round(v, 1) for v in ot["zakres"] if lo + 0.5 < v < hi - 0.5)
            for b in elementy:
                z = przy_licu(l, b)
                if z:
                    rzad_a.update(round(v, 1) for v in z)
            poz = l["a"][0] * o[0] + l["a"][1] * o[1]
            zasieg = max(zasieg, poz + zasieg_za_licem(M, l) - krawedz[bok])
        rzedy = [sorted(konce | rzad_a)]
        if sorted(konce) != rzedy[-1]:
            rzedy.append(sorted(konce))
        if [min(konce), max(konce)] != rzedy[-1]:
            rzedy.append([min(konce), max(konce)])
        wynik[bok] = {"rzedy": rzedy, "zasieg": zasieg,
                      "niepewny": any(plan.niepewna(M, l["sciana"]) for l in lica_b)}
    return wynik


def widok(M, nr, boki, pole):
    """Kadr pomieszczenia z miejscem na lancuchy; najwieksza skala z arkusz.SKALE, ktora sie miesci."""
    x0, y0, x1, y1 = geometria.wielokaty(M)[nr].bounds
    zakres = None
    for m in arkusz.SKALE:
        sk = arkusz.jednostek_na_cm(m)
        marg = {b: boki[b]["zasieg"] + (len(boki[b]["rzedy"]) * ODSTEP_PX + 26) / sk for b in BOKI}
        zakres = (x0 - marg["W"], y0 - marg["S"], x1 + marg["E"], y1 + marg["N"])
        if (zakres[2] - zakres[0]) * sk <= pole[2] - pole[0] and (zakres[3] - zakres[1]) * sk <= pole[3] - pole[1]:
            return arkusz.Widok(zakres, pole, sk), "1:%d (A3)" % m
    return arkusz.Widok(zakres, pole), "bez skali"


def rysuj_lancuchy(W, M, nr, boki, miejsca):
    """Lancuchy na zewnatrz scian; pasy lancuchow zajmuja miejsce dla pozniejszych opisow."""
    x0, y0, x1, y1 = geometria.wielokaty(M)[nr].bounds
    s = []
    for bok, (o, os) in BOKI.items():
        d = boki[bok]
        for i, rzad in enumerate(d["rzedy"]):
            lo, hi = rzad[0], rzad[-1]
            a, b = {"N": ((lo, y1), (hi, y1)), "S": ((lo, y0), (hi, y0)),
                    "E": ((x1, lo), (x1, hi)), "W": ((x0, lo), (x0, hi))}[bok]
            ostatni = i == len(d["rzedy"]) - 1
            s.append(plan.lancuch(W, a, b, o, d["zasieg"] + (i + 1) * ODSTEP_PX / W.sk,
                                  [v - lo for v in rzad[1:-1]], d["niepewny"],
                                  kolor=plan.KOLOR["wymiar_zewn"] if ostatni else plan.KOLOR["wymiar"],
                                  r=9.5 if ostatni else 8.5))
        if d["rzedy"]:
            lo, hi = d["rzedy"][0][0], d["rzedy"][0][-1]
            k0 = d["zasieg"] + 4 / W.sk
            k1 = d["zasieg"] + (len(d["rzedy"]) * ODSTEP_PX + 16) / W.sk
            if os == 0:
                yb = y1 if bok == "N" else y0
                P, Q = W.p(lo, yb + o[1] * k0), W.p(hi, yb + o[1] * k1)
            else:
                xb = x1 if bok == "E" else x0
                P, Q = W.p(xb + o[0] * k0, lo), W.p(xb + o[0] * k1, hi)
            miejsca.zajmij((min(P[0], Q[0]), min(P[1], Q[1]), max(P[0], Q[0]), max(P[1], Q[1])))
    return "".join(s)


def rect_elementu(W, e):
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    X0, Y0 = W.p(x0, y1)
    X1, Y1 = W.p(x1, y0)
    return (X0, Y0, X1, Y1)


def krawedzie_mebli(W, M, nr):
    """Krawedzie elementow i linie podzialu segmentow jako przeszkody (opisy ich nie przecinaja)."""
    wynik = []
    for e in model.elementy(M, nr):
        X0, Y0, X1, Y1 = rect_elementu(W, e)
        wynik += [(X0, Y0, X1, Y0), (X0, Y1, X1, Y1), (X0, Y0, X0, Y1), (X1, Y0, X1, Y1)]
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        for os, v in plan.podzialy_segmentow(e):
            (A, B) = (W.p(v, y0), W.p(v, y1)) if os == "x" else (W.p(x0, v), W.p(x1, v))
            wynik.append((min(A[0], B[0]), min(A[1], B[1]), max(A[0], B[0]), max(A[1], B[1])))
    return wynik


def kolor_kategorii(e):
    return plan.KOLORY_MEBLI.get(model.kategoria(e.get("rodzaj")), plan.KOLORY_MEBLI["inne"])[1]


def opis_wymiarow(e):
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    if e.get("ksztalt") == "kolo":
        rozm = "⌀%s" % svg.fmt(x1 - x0) if abs((x1 - x0) - (y1 - y0)) < 0.5 else \
            "⌀%s×%s" % (svg.fmt(x1 - x0), svg.fmt(y1 - y0))
    elif e.get("front") in ("E", "W"):
        rozm = "%s×%s" % (svg.fmt(y1 - y0), svg.fmt(x1 - x0))   # szerokosc frontu x glebokosc
    else:
        rozm = "%s×%s" % (svg.fmt(x1 - x0), svg.fmt(y1 - y0))
    wys = e.get("wys")
    if wys:
        h = "h %s–%s" % (svg.fmt(wys[0]), svg.fmt(wys[1])) if wys[0] else "h %s" % svg.fmt(wys[1])
        rozm += " · " + h + (" do sufitu" if e.get("do_sufitu") else "")
    return rozm


def punkt_elementu(W, e, t, g):
    """Punkt arkusza w elemencie: t - ulamek dlugosci frontu od lewej patrzac na front, g - ulamek glebokosci od frontu."""
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    f = e.get("front") or "S"
    if f == "S":
        return W.p(x0 + (x1 - x0) * t, y0 + (y1 - y0) * g)
    if f == "N":
        return W.p(x1 - (x1 - x0) * t, y1 - (y1 - y0) * g)
    if f == "E":
        return W.p(x1 - (x1 - x0) * g, y0 + (y1 - y0) * t)
    return W.p(x0 + (x1 - x0) * g, y1 - (y1 - y0) * t)


def rect_czesci(W, e, t0, t1):
    a, b = punkt_elementu(W, e, t0, 0), punkt_elementu(W, e, t1, 1)
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def zakresy_segmentow(e):
    """[(t0, t1, segment)] - ulamki dlugosci frontu kolejnych segmentow (od lewej patrzac na front)."""
    if not e.get("segmenty") or not e.get("front"):
        return []
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    dl = (x1 - x0) if e["front"] in ("N", "S") else (y1 - y0)
    wynik, kursor = [], 0.0
    for seg in e["segmenty"]:
        wynik.append((kursor / dl, min(1.0, (kursor + seg["dl"]) / dl), seg))
        kursor += seg["dl"]
    return wynik


def opisz(miejsca, W, e, linie, r, glebokosci, pozycje, kolory):
    """Opis w pierwszym wolnym miejscu wewnatrz prostokata r (najpierw poziomo, potem pionowo)."""
    for pion in (False, True):
        for g in glebokosci:
            for t in pozycje:
                k = rect_tekstu(*punkt_elementu(W, e, t, g), linie, pion)
                if w_srodku(k, r) and miejsca.wolne(k):
                    miejsca.zajmij(k)
                    return blok_tekstu(k, linie, pion, kolory)
    return ""


def opis_obok(miejsca, r, linie, kolory):
    """Opis poza zbyt malym elementem, z cienkim odnosnikiem."""
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    w0 = rect_tekstu(0, 0, linie)
    w, h = w0[2] - w0[0], w0[3] - w0[1]
    kand = []
    for odl in (6, 18, 34):
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            px = cx + dx * ((r[2] - r[0]) / 2 + odl + w / 2)
            py = cy + dy * ((r[3] - r[1]) / 2 + odl + h / 2)
            kand.append(rect_tekstu(px, py, linie))
    k = miejsca.wybierz(kand) or kand[0]
    kx = min(max(cx, k[0]), k[2])
    ky = min(max(cy, k[1]), k[3])
    return (svg.linia(cx, cy, kx, ky, "#999", 0.5) + svg.prostokat(*k, "#FFFFFF", None, przezr=0.85)
            + blok_tekstu(k, linie, False, kolory))


def opisy_mebli(W, M, nr, miejsca):
    """Opisy segmentow ('zlew · 60') i elementow ('K1 ciag kuchenny' + wymiary i wysokosc)."""
    s = []
    for e in sorted(model.elementy(M, nr), key=lambda e: e.get("wys", [0, 0])[0]):
        r = rect_elementu(W, e)
        kolor = kolor_kategorii(e)
        wysoko = e.get("wys", [0, 0])[0] >= plan.CIECIE
        segs = zakresy_segmentow(e)
        for t0, t1, seg in segs:
            tekst = "%s · %s" % (seg["opis"], svg.fmt(seg["dl"])) if seg.get("opis") else svg.fmt(seg["dl"])
            s.append(opisz(miejsca, W, e, [(tekst, 7.5)], rect_czesci(W, e, t0, t1),
                           (0.62, 0.78, 0.48, 0.34) if wysoko else (0.12, 0.25, 0.4, 0.55),
                           [t0 + (t1 - t0) * f for f in (0.5, 0.3, 0.7)], [kolor]))
        linie = [("%s %s" % (e["id"], e.get("rodzaj", "")), 8.5), (opis_wymiarow(e), 7.5)]
        if segs:
            srodki = sorted(((t0 + t1) / 2, t1 - t0) for t0, t1, _ in segs)
            srodki.sort(key=lambda c: abs(c[0] - 0.5))
            pozycje = [c for c, _ in srodki] + [c + z * d * 0.28 for c, d in srodki for z in (1, -1)]
            glebokosci = (0.3, 0.45, 0.15, 0.6) if wysoko else (0.3, 0.42, 0.55, 0.7, 0.85)
        else:
            pozycje = [0.5, 0.35, 0.65, 0.2, 0.8]
            glebokosci = (0.5, 0.35, 0.65, 0.22, 0.78)
        opis = opisz(miejsca, W, e, linie, r, glebokosci, pozycje, [kolor, "#555"])
        s.append(opis or opis_obok(miejsca, r, linie, [kolor, "#555"]))
    return "".join(s)


def otwory_pomieszczenia(M, nr):
    return [o for o in M.get("otwory", []) if nr in geometria.pokoje_otworu(M, o)]


def opisy_otworow(W, M, nr, miejsca, przeszkody=()):
    """'D1 100/210' (szerokosc / gorna krawedz, parapet) od strony pomieszczenia, przy otworze."""
    w = geometria.wielokaty(M)[nr]
    s = []
    for o in otwory_pomieszczenia(M, nr):
        x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
        sc = next(x for x in M["sciany"] if x["id"] == o["sciana"])
        poziomo = geometria.wzdluz_x(sc["pas"])
        szer = o.get("szer_otw") or ((x1 - x0) if poziomo else (y1 - y0))
        t = "%s %s/%s" % (o["id"], svg.fmt(szer), svg.fmt(o.get("wys_otw", 205)))
        if o.get("parapet"):
            t += " · par. %s" % svg.fmt(o["parapet"])
        kol = plan.KOLOR["okno"] if o["rodzaj"] == "okno" else plan.KOLOR["drzwi"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if poziomo:
            n = (0, 1) if w.distance(Point(cx, y1 + 2)) < w.distance(Point(cx, y0 - 2)) else (0, -1)
            lico = (cx, y1 if n[1] > 0 else y0)
        else:
            n = (1, 0) if w.distance(Point(x1 + 2, cy)) < w.distance(Point(x0 - 2, cy)) else (-1, 0)
            lico = (x1 if n[0] > 0 else x0, cy)
        X, Y = W.p(*lico)
        linie = [(t, 8)]
        kand = []
        for pion in ((False, True) if not poziomo else (False,)):
            for odl in (9, 20, 32, 46):
                w0 = rect_tekstu(0, 0, linie, pion)
                hw, hh = (w0[2] - w0[0]) / 2, (w0[3] - w0[1]) / 2
                kand.append(rect_tekstu(X + n[0] * (odl + hw), Y - n[1] * (odl + hh), linie, pion))
        k = miejsca.wybierz(kand, przeszkody) or miejsca.wybierz(kand)
        if k:
            pion = (k[3] - k[1]) > (k[2] - k[0])
            s.append(svg.prostokat(*k, "#FFFFFF", None, przezr=0.75))
            s.append(blok_tekstu(k, linie, pion, [kol]))
    return "".join(s)


def rect_grzejnikow(W, M, nr):
    wynik = []
    for g in M.get("grzejniki", []):
        if g.get("pomieszczenie") == nr:
            x0, y0, x1, y1 = geometria.prostokat(g["box"]).bounds
            (X0, Y0), (X1, Y1) = W.p(x0, y1), W.p(x1, y0)
            wynik.append((X0, Y0, X1, Y1))
    return wynik


def opisy_grzejnikow(W, M, nr, miejsca, przeszkody=()):
    s = []
    wyp, obr = plan.KOLOR["grzejnik"]
    for g in M.get("grzejniki", []):
        if g.get("pomieszczenie") != nr:
            continue
        x0, y0, x1, y1 = geometria.prostokat(g["box"]).bounds
        X0, Y0 = W.p(x0, y1)
        X1, Y1 = W.p(x1, y0)
        linie = [("%s %s" % (g["id"], g.get("typ", "")), 7.5)]
        l = lico_punktu(M, ((x0 + x1) / 2, (y0 + y1) / 2), 25, nr)
        kier = [(l["normalna"][0], -l["normalna"][1])] if l else []
        kier += [(0, 1), (0, -1), (1, 0), (-1, 0)]
        w0 = rect_tekstu(0, 0, linie)
        hw, hh = (w0[2] - w0[0]) / 2, (w0[3] - w0[1]) / 2
        kand = []
        for odl in (4, 12):
            for dx, dy in kier:
                cx = (X0 + X1) / 2 + dx * ((X1 - X0) / 2 + odl + hw)
                cy = (Y0 + Y1) / 2 + dy * ((Y1 - Y0) / 2 + odl + hh)
                kand.append(rect_tekstu(cx, cy, linie))
        k = miejsca.wybierz(kand, przeszkody) or miejsca.wybierz(kand)
        if k:
            s.append(blok_tekstu(k, linie, False, [obr]))
    return "".join(s)


def punkty(M, nr):
    """Punkty E pomieszczenia: przypisane do niego albo lezace w nim (np. lacznik z wyjatkiem)."""
    w = geometria.wielokaty(M)[nr]
    return [e for e in M.get("elektryka", [])
            if e.get("pomieszczenie") == nr
            or w.distance(Point(*e["xy"])) <= DOTYK and geometria.pomieszczenie_punktu(M, e["xy"], DOTYK) == nr]


def rysuj_punkty(W, M, lista, miejsca):
    """Symbole punktow E i opisy 'E14 h120' (h tylko dla punktow na scianach) od strony wnetrza."""
    s, opisy = [], []
    for e in lista:
        X, Y = W.p(*e["xy"])
        miejsca.zajmij((X - 6, Y - 6, X + 6, Y + 6))
    for e in lista:
        X, Y = W.p(*e["xy"])
        s.append(plan.symbol_e(e["typ"], X, Y, 5))
        l = lico_punktu(M, e["xy"])
        t = e["id"] + (" h%s" % svg.fmt(e["h"]) if l is not None and e.get("h") is not None else "")
        w, h = szer_tekstu(t, 7.5), 9.0
        if l is not None:
            nx, ny = l["normalna"]
            kier = [(nx, -ny), (-ny, -nx), (ny, nx)]   # do wnetrza (os Y arkusza w dol), potem wzdluz sciany
        else:
            kier = [(1, 0), (-1, 0), (0, -1), (0, 1)]
        kier += [(0.7, -0.7), (-0.7, -0.7), (0.7, 0.7), (-0.7, 0.7)]
        kand = []
        for odl in (8, 16, 26):
            for dx, dy in kier:
                cx, cy = X + dx * (odl + w / 2), Y + dy * (odl + h / 2)
                kand.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        r = miejsca.wybierz(kand) or kand[0]
        opisy.append(svg.prostokat(r[0] - 1, r[1], r[2] + 1, r[3], "#FFFFFF", None, przezr=0.8))
        opisy.append(svg.tekst((r[0] + r[2]) / 2, r[3] - 2.2, t, 7.5, "middle",
                               kolor=plan.KOLORY_E.get(e["typ"], "#555"), waga="bold"))
    return "".join(s), "".join(opisy)


def wymiary_kontrolne(W, M, nr, miejsca):
    s = []
    for wk in M.get("aranzacja", {}).get(nr, {}).get("wymiary_kontrolne", []):
        (ax, ay), (bx, by) = wk["od"], wk["do"]
        A, B = W.p(ax, ay), W.p(bx, by)
        s.append(svg.linia(*A, *B, KOLOR_KONTROLI, 1.1, "6 3"))
        for q in (A, B):
            s.append(svg.okrag(*q, 2.4, KOLOR_KONTROLI, None))
        dl = svg.fmt(math.hypot(bx - ax, by - ay))
        t = "%s — %s" % (dl, wk["opis"]) if wk.get("opis") else dl
        pion = abs(B[0] - A[0]) < abs(B[1] - A[1])
        cx, cy = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        linie = [(t, 8)]
        kand = []
        for d in (8, 14, 22):
            for znak in (1, -1):
                kand.append(rect_tekstu(cx + znak * d, cy, linie, True) if pion
                            else rect_tekstu(cx, cy + znak * d, linie))
        r = miejsca.wybierz(kand) or kand[0]
        s.append(svg.prostokat(*r, "#FFFFFF", None, przezr=0.8))
        if pion:
            s.append(svg.tekst((r[0] + r[2]) / 2 + 3, (r[1] + r[3]) / 2, t, 8, "middle", -90, KOLOR_KONTROLI, "bold"))
        else:
            s.append(svg.tekst((r[0] + r[2]) / 2, (r[1] + r[3]) / 2 + 3, t, 8, "middle", 0, KOLOR_KONTROLI, "bold"))
    return "".join(s)


def etykieta_pomieszczenia(W, M, nr, miejsca, przeszkody):
    """Numer, nazwa i pole w wolnym miejscu (poza meblami) jak najblizej punktu stamp."""
    p = model.pomieszczenie(M, nr)
    w = geometria.wielokaty(M)[nr]
    pole = geometria.pola(M).get(nr)
    linie = [(nr, 14), (p.get("nazwa", ""), 10)] + ([("%s m²" % svg.fmt(pole, 2), 10)] if pole is not None else [])
    sx, sy = p["stamp"] if w.contains(Point(*p["stamp"])) else (w.representative_point().x, w.representative_point().y)
    x0, y0, x1, y1 = w.bounds
    kand = [(0, sx, sy)]
    for i in range(int((x1 - x0) / 10) + 1):
        for j in range(int((y1 - y0) / 10) + 1):
            x, y = x0 + i * 10, y0 + j * 10
            if w.contains(Point(x, y)):
                kand.append((math.hypot(x - sx, y - sy), x, y))
    kand.sort()
    rect = None
    for _, x, y in kand:
        r = rect_tekstu(*W.p(x, y), linie)
        if miejsca.wolne(r, 4, przeszkody):
            rect = r
            break
    rect = rect or rect_tekstu(*W.p(sx, sy), linie)
    miejsca.zajmij(rect)
    return blok_tekstu(rect, linie, False, ["#111", "#444", "#444"])


def etykiety_sasiadow(W, M, nr, pole, miejsca):
    """Szare podpisy sasiednich pomieszczen w polu rysunku (dla orientacji)."""
    s = []
    for n, w in geometria.wielokaty(M).items():
        if w is None or n == nr:
            continue
        p = model.pomieszczenie(M, n)
        rp = Point(*p["stamp"]) if w.contains(Point(*p["stamp"])) else w.representative_point()
        linie = [("%s %s" % (n, p.get("nazwa", "")), 9)]
        k = rect_tekstu(*W.p(rp.x, rp.y), linie)
        if w_srodku(k, pole, 6) and miejsca.wolne(k, 4):
            miejsca.zajmij(k)
            s.append(blok_tekstu(k, linie, False, ["#999"]))
    return "".join(s)


def pas_kontroli(M, nr, x, y, szer):
    """Status, pole i kontrole aranzacji nad rysunkiem; zwraca (svg, wysokosc)."""
    ar = M.get("aranzacja", {}).get(nr, {})
    p = model.pomieszczenie(M, nr)
    pole = geometria.pola(M).get(nr)
    info = ["aranżacja: %s" % (ar.get("status") or "bez statusu")]
    if pole is not None:
        info.append("pole %s m²" % svg.fmt(pole, 2))
    if p.get("podloga"):
        info.append("podłoga: %s" % p["podloga"])
    token = model.token_celu(M, ("sciany", nr))
    if token:
        info.append("ściany: %s" % token)
    s = [svg.tekst(x, y + 12, " · ".join(info), 11, kolor="#444")]
    yy = y + 30
    znakow = int(szer / (10.5 * 0.5))
    for k in ar.get("kontrole", []):
        for j, lin in enumerate(textwrap.wrap(k, znakow - 4) or [""]):
            s.append(svg.tekst(x + (0 if j == 0 else 16), yy, ("✓ " if j == 0 else "") + lin, 10.5, kolor=KOLOR_KONTROLI))
            yy += 14
    return "".join(s), yy - y


def maska(pole):
    """Biala rama zaslaniajaca rysunek poza polem (MuPDF nie obsluguje clipPath)."""
    X0, Y0, X1, Y1 = pole
    d = "M 0 0 L %d 0 L %d %d L 0 %d Z M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (
        arkusz.SZER, arkusz.SZER, arkusz.WYS, arkusz.WYS, X0, Y0, X1, Y0, X1, Y1, X0, Y1)
    return '<path d="%s" fill="#FFFFFF" fill-rule="evenodd" stroke="none"/>' % d


def legenda(M, nr, lista_e):
    poz, kategorie = [], []
    elementy = model.elementy(M, nr)
    for e in elementy:
        k = model.kategoria(e.get("rodzaj"))
        if k not in kategorie:
            kategorie.append(k)
    for k in kategorie:
        wyp, obr = plan.KOLORY_MEBLI.get(k, plan.KOLORY_MEBLI["inne"])
        poz.append((svg.prostokat(0, 2, 24, 14, wyp if wyp != "none" else "#FFFFFF", obr, 1), NAZWY_KATEGORII.get(k, k)))
    if any(e.get("front") for e in elementy):
        poz.append((svg.prostokat(0, 3, 24, 13, "none", "#5C6E3A", 0.8) + svg.linia(0, 13, 24, 13, "#5C6E3A", 2.2),
                    "front elementu (gruba linia) i podziały segmentów"))
    if any(e.get("wys", [0, 0])[0] >= plan.CIECIE for e in elementy):
        poz.append((svg.prostokat(0, 2, 24, 14, "none", "#3B5B8C", 1, "5 3"),
                    "element od %d cm w górę (nad płaszczyzną cięcia)" % plan.CIECIE))
    if any(e.get("mobilne") for e in elementy):
        poz.append((svg.prostokat(0, 2, 24, 14, "none", "#4A7D3A", 1, "4 3"), "element ruchomy"))
    if any(g.get("pomieszczenie") == nr for g in M.get("grzejniki", [])):
        poz.append((svg.prostokat(0, 5, 24, 11, plan.KOLOR["grzejnik"][0], plan.KOLOR["grzejnik"][1], 1.1), "grzejnik"))
    typy = []
    for e in lista_e:
        if e["typ"] not in typy:
            typy.append(e["typ"])
    for t in typy:
        poz.append((plan.symbol_e(t, 12, 8, 5), "punkt: %s" % t))
    if typy:
        poz.append((svg.tekst(12, 12, "h", 10, "middle", kolor="#555", waga="bold"),
                    "E1 h110 — numer punktu i wysokość osi od podłogi wykończonej"))
    if M.get("aranzacja", {}).get(nr, {}).get("wymiary_kontrolne"):
        poz.append((svg.linia(0, 8, 24, 8, KOLOR_KONTROLI, 1.1, "6 3"), "wymiar kontrolny (odstęp)"))
    poz.append((svg.tekst(12, 12, "≈", 12, "middle", kolor=plan.KOLOR["wymiar"], waga="bold"),
                "wymiar ze źródła o niepełnej dokładności"))
    return poz


def karta(M, nr):
    if geometria.wielokaty(M).get(nr) is None:
        raise SystemExit("pomieszczenie %s nie daje zamknietego wielokata (sprawdz stamp i sciany)" % nr)
    p = model.pomieszczenie(M, nr)
    X0, Y0, X1, Y1 = arkusz.POLE
    pas, h_pasa = pas_kontroli(M, nr, X0, Y0, X1 - X0)
    pole = (X0, Y0 + h_pasa + 10, X1, Y1)
    boki = lancuchy_bokow(M, nr)
    W, skala_txt = widok(M, nr, boki, pole)
    lista_e = punkty(M, nr)
    miejsca = Opisy()
    # otwory tylko tego pomieszczenia (luki i oscieza); pozostale zostaja przerwami w scianach
    M_otw = dict(M, otwory=otwory_pomieszczenia(M, nr), _cache={})
    rysunek = ["".join(svg.sciezka(w, W.p, "#F3F3F1", None) for n, w in geometria.wielokaty(M).items()
                       if w is not None and n != nr),
               plan.pomieszczenia(W, M, nr=nr), plan.grzejniki(W, M, opisy=False),
               plan.meble(W, M, nr=nr, opisy=False), plan.sciany(W, M), plan.szachty(W, M),
               plan.otwory(W, M_otw, opisy=False), rysuj_lancuchy(W, M, nr, boki, miejsca)]
    symbole, opisy_e = rysuj_punkty(W, M, lista_e, miejsca)
    for r in krawedzie_mebli(W, M, nr):
        miejsca.zajmij(r)
    meble_rect = [rect_elementu(W, e) for e in model.elementy(M, nr)]
    grzejniki_rect = rect_grzejnikow(W, M, nr)
    rysunek += [opisy_mebli(W, M, nr, miejsca), opisy_grzejnikow(W, M, nr, miejsca, meble_rect),
                opisy_otworow(W, M, nr, miejsca, meble_rect + grzejniki_rect), wymiary_kontrolne(W, M, nr, miejsca),
                symbole, opisy_e, etykieta_pomieszczenia(W, M, nr, miejsca, meble_rect + grzejniki_rect),
                etykiety_sasiadow(W, M, nr, pole, miejsca)]
    kod = "KP-%s" % nr
    tytul = "Karta pomieszczenia %s — %s" % (nr, p.get("nazwa", ""))
    # rysunek poza polem przykrywa maska; rama, naglowek, pas kontroli, podzialka i polnoc ida na wierzch
    metry = max(1, min(5, int(round(450 / W.px_na_m))))
    tresc = ("".join(rysunek) + maska(pole) + arkusz.ramka() + arkusz.naglowek(M, kod, tytul) + pas
             + svg.podzialka(pole[0] + 10, 1782, W.px_na_m, metry)
             + svg.strzalka_polnocy(X1 - 34, 62, M.get("meta", {}).get("polnoc", {}).get("azymut_osi_Y_stopnie", 0)))
    poz = legenda(M, nr, lista_e)
    polowa = (len(poz) + 1) // 2
    tresc += arkusz.legenda(poz[:polowa], 50, 1800, 320)[0] + arkusz.legenda(poz[polowa:], 375, 1800, 320, tytul="")[0]
    return arkusz.arkusz(M, kod, tytul, skala_txt, tresc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("nr", nargs="+", help="numer pomieszczenia (jeden lub kilka)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj rysunki/wszystko.py (karty pomieszczen kazdego modulu wnetrz); "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        sys.exit(2)
    for nr in a.nr:
        try:
            model.pomieszczenie(M, nr)
        except KeyError:
            raise SystemExit("brak pomieszczenia %s w modelu" % nr)
        for p in svg.zapisz(karta(M, nr), model.sciezka_wyniku(M, "karta_%s" % nr, a.wyjscie), pdf=True):
            print("zapisano", p)


if __name__ == "__main__":
    main()
