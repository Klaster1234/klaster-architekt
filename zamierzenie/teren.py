"""Teren z punktow wysokosciowych: siatka trojkatow, rzedna w punkcie, profil, warstwice.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model, teren
    M = model.wczytaj("przyklad/ogrod/model/projekt.json")
    s = teren.siatka(M)
    print(teren.rzedna(s, 1200, 1000), teren.profil(s, (1200, 0), (1200, 3000))[-1])

Punkty miejsce.teren.punkty to [x, y, z] w cm (z wzgledem +-0). Siatka to triangulacja
Delaunaya w rzucie: wewnatrz niej rzedna jest interpolowana liniowo w trojkacie, poza
nia rowna rzednej najblizszego punktu. Bez terenu (mniej niz 3 punkty albo punkty na
jednej linii) siatka to None, a teren jest plaski na z = 0.
"""
import math

import numpy as np
from scipy.spatial import Delaunay, QhullError
from shapely.geometry import MultiLineString
from shapely.ops import linemerge


def siatka(M):
    t = (M.get("miejsce") or {}).get("teren") or {}
    # punkty o innej postaci niz [x, y, z] sa pomijane (zglasza je zamierzenie/waliduj.py)
    pkt = np.array([p for p in t.get("punkty") or [] if isinstance(p, list) and len(p) == 3], dtype=float).reshape(-1, 3)
    if len(pkt) < 3:
        return None
    try:
        tri = Delaunay(pkt[:, :2]).simplices
    except QhullError:
        return None
    a, b, c = (pkt[tri[:, i], :2] for i in range(3))
    pole = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    d = t.get("dokladnosc_cm")
    # trojkaty zdegenerowane (punkty wspolliniowe) nic nie wnosza, a psulyby interpolacje
    return {"pkt": pkt, "tri": tri[np.abs(pole) > 1e-9], "dokladnosc_cm": None if d is None else float(d)}


def rzedna(s, x, y):
    """Rzedna terenu w punkcie (cm); bez siatki 0.0."""
    if s is None:
        return 0.0
    p, t = s["pkt"], s["tri"]
    a, b, c = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / det
    l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / det
    l3 = 1 - l1 - l2
    w = np.flatnonzero((l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9))
    if len(w):
        i = w[0]
        return float(l1[i] * a[i, 2] + l2[i] * b[i, 2] + l3[i] * c[i, 2])
    return float(p[np.argmin((p[:, 0] - x) ** 2 + (p[:, 1] - y) ** 2), 2])


def profil(s, a, b, krok=50):
    """[(odleglosc_cm, z_cm)] od a do b w rownych odstepach nie wiekszych niz krok, z oboma koncami."""
    dl = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, math.ceil(dl / krok))
    return [(dl * i / n, rzedna(s, a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)) for i in range(n + 1)]


def warstwice(s, co=50):
    """[(z, [[(x, y), ...], ...])] - warstwice co `co` cm; odcinki z trojkatow scalone w polilinie."""
    if s is None:
        return []
    p, wynik = s["pkt"], []
    for k in range(math.ceil(p[:, 2].min() / co), math.floor(p[:, 2].max() / co) + 1):
        h = k * co
        odcinki = set()
        for tr in s["tri"]:
            pk = []
            for e0, e1 in ((0, 1), (1, 2), (0, 2)):
                i, j = sorted((tr[e0], tr[e1]))   # ta sama kolejnosc w obu trojkatach krawedzi -> ten sam punkt
                (x0, y0, z0), (x1, y1, z1) = p[i], p[j]
                if (z0 > h) != (z1 > h):
                    u = (h - z0) / (z1 - z0)
                    pk.append((float(x0 + u * (x1 - x0)), float(y0 + u * (y1 - y0))))
            if len(pk) == 2 and pk[0] != pk[1]:
                odcinki.add(tuple(sorted(pk)))
        if odcinki:
            g = linemerge(MultiLineString(sorted(odcinki)))
            wynik.append((h, [list(l.coords) for l in getattr(g, "geoms", [g])]))
    return wynik
