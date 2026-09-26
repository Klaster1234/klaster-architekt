"""Wzory wypelnien (kreskowanie, kropki), linie przerywane i symbole punktow planu jako jawne
linie i okregi SVG.

    from wspolne import wzory
    s = wzory.kreskowanie(g, W.p, krok_px=7, kat=45) + wzory.kropki(g, W.p)
    s += wzory.kreski(g, W.p, "8 3") + wzory.symbol("drzewo", X, Y, 20)

PyMuPDF (SVG -> PNG, PDF) nie obsluguje <pattern> ani stroke-dasharray, wiec wzor to zwykle
linie i kropki przyciete do geometrii, a linia przerywana to ciag krotkich odcinkow. geom to
geometria shapely w ukladzie modelu, a P mapuje (x, y) modelu na arkusz (arkusz.Widok.p; dla
geometrii juz w jednostkach arkusza: lambda x, y: (x, y)).
Odstepy, promienie i grubosci sa w jednostkach arkusza; kat w stopniach przeciwnie do ruchu
wskazowek zegara, tak jak widac go na arkuszu: 0 - poziome, 45 - "/", 90 - pionowe, 135 - "\\".
Symbole punktow: drzewo (korona i pien), krzew (falista obwodka), kolo, krzyz, kwadrat;
r to promien symbolu w jednostkach arkusza.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString

from wspolne import svg

SYMBOLE = ("drzewo", "krzew", "kolo", "krzyz", "kwadrat")


def _na_arkusz(geom, P):
    """Wielokaty geometrii przeliczone punkt po punkcie przez P (model -> arkusz)."""
    czesci = [g for g in shapely.get_parts(geom) if g.geom_type == "Polygon" and not g.is_empty]
    if not czesci:
        return None
    g = shapely.transform(shapely.multipolygons(czesci),
                          lambda xy: np.array([P(x, y) for x, y in xy], dtype=float).reshape(-1, 2))
    return g if g.is_valid else g.buffer(0)


def kreskowanie(geom, P, krok_px=7.0, kat=45, kolor="#555555", gr=0.6):
    """Rownolegle linie co krok_px pod katem kat, przyciete do wielokatow geom."""
    g = _na_arkusz(geom, P) if geom is not None and not geom.is_empty else None
    if g is None or g.is_empty:
        return ""
    k = math.radians(kat)
    dx, dy = math.cos(k), -math.sin(k)          # kierunek linii na arkuszu (os Y w dol)
    nx, ny = -dy, dx
    x0, y0, x1, y1 = g.bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = math.hypot(x1 - x0, y1 - y0) / 2 + 1
    n = int(R / krok_px) + 1
    linie = [LineString([(cx + nx * t - dx * R, cy + ny * t - dy * R), (cx + nx * t + dx * R, cy + ny * t + dy * R)])
             for t in (i * krok_px for i in range(-n, n + 1))]
    s = []
    for c in shapely.intersection(linie, g):
        for odc in shapely.get_parts(c):
            if odc.geom_type == "LineString" and odc.length > 0.3:
                (ax, ay), (bx, by) = odc.coords[0], odc.coords[-1]
                s.append(svg.linia(ax, ay, bx, by, kolor, gr))
    return "".join(s)


def kropki(geom, P, krok_px=8.0, r=0.9, kolor="#555555"):
    """Kropki w siatce co krok_px (co drugi rzad przesuniety o pol kroku) wewnatrz wielokatow geom."""
    g = _na_arkusz(geom, P) if geom is not None and not geom.is_empty else None
    if g is None or g.is_empty:
        return ""
    x0, y0, x1, y1 = g.bounds
    xy = [(x, y) for i, y in enumerate(np.arange(y0 + krok_px / 2, y1, krok_px))
          for x in np.arange(x0 + krok_px * (0.75 if i % 2 else 0.25), x1, krok_px)]
    if not xy:
        return ""
    xy = np.array(xy)
    wewnatrz = shapely.contains_xy(g, xy[:, 0], xy[:, 1])
    return "".join(svg.okrag(x, y, r, kolor, None) for (x, y), w in zip(xy, wewnatrz) if w)


def kreski(geom, P, wzor="8 3", kolor="#222222", gr=1.0):
    """Obrysy wielokatow i linie geometrii shapely (uklad modelu, P - na arkusz) linia przerywana;
    przekazuje dalej do wspolne.svg.sciezka (jawne odcinki - PyMuPDF pomija stroke-dasharray)."""
    return svg.sciezka(geom, P, "none", kolor, gr, wzor)


def symbol(nazwa, X, Y, r, kolor="#333333", gr=0.8, wyp="none", kreski=None):
    """Symbol punktu w (X, Y) o promieniu r; nazwa spoza SYMBOLE rysuje kolo; kreski - obrys
    przerywany, jak w wzorze stroke-dasharray (dalej do wspolne.svg - jawne odcinki)."""
    if kreski:
        a = 0.75 * r
        if nazwa == "krzyz":
            return svg.linia(X - a, Y - a, X + a, Y + a, kolor, gr, kreski) + \
                svg.linia(X - a, Y + a, X + a, Y - a, kolor, gr, kreski)
        if nazwa == "kwadrat":
            a = 0.8 * r
            return svg.prostokat(X - a, Y - a, X + a, Y + a, wyp, kolor, gr, kreski)
        s = svg.okrag(X, Y, r, wyp, kolor, gr, kreski)
        if nazwa == "drzewo":
            s += svg.okrag(X, Y, max(1.2, min(2.5, 0.05 * r)), kolor or "#333333", None)
        return s
    if nazwa == "drzewo":
        return svg.okrag(X, Y, r, wyp, kolor, gr) + svg.okrag(X, Y, max(1.2, min(2.5, 0.05 * r)), kolor or "#333333", None)
    if nazwa == "krzew":
        n = max(8, min(40, int(2 * math.pi * r / 5)))
        pkt = [(X + r * math.cos(2 * math.pi * i / n), Y + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        rr = 1.2 * r * math.sin(math.pi / n)    # luk nad cieciwa - falista obwodka korony
        d = "M %.1f %.1f " % pkt[0] + " ".join("A %.1f %.1f 0 0 1 %.1f %.1f" % (rr, rr, x, y) for x, y in pkt[1:]) + " Z"
        styl = ' fill="%s" stroke="%s"' % (wyp, kolor or "none")
        if kolor:
            styl += ' stroke-width="%.2f"' % gr
        return '<path d="%s"%s/>' % (d, styl)
    if nazwa == "krzyz":
        a = 0.75 * r
        return svg.linia(X - a, Y - a, X + a, Y + a, kolor, gr) + svg.linia(X - a, Y + a, X + a, Y - a, kolor, gr)
    if nazwa == "kwadrat":
        a = 0.8 * r
        return svg.prostokat(X - a, Y - a, X + a, Y + a, wyp, kolor, gr)
    return svg.okrag(X, Y, r, wyp, kolor, gr)
