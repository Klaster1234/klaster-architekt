"""Bryly 3D modelu zamierzenia: teren, sasiedztwo, obiekty ogolne i moduly wnetrz.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model, bryly
    M = model.wczytaj("przyklad/ogrod/model/projekt.json")
    for nazwa, siatka, wyglad in bryly.siatki(M):
        print(nazwa, siatka.bounds.round(), wyglad)

Siatki trimesh w cm, os Z w gore, w ukladzie modelu (rysunki/glb.py przelicza je na glTF):
- bryla: wielokat wyciagniety od z0 do z1 (model.zakres_z); dach: bryla z dach();
- powierzchnia: na poziomie albo na +-0 plyta 2 cm; na terenie arkusz trojkatow pociety
  siatka co 100 cm (krawedzie tez), kazdy wierzcholek na terenie + 1 cm;
- linia z wysokoscia: pas 10 cm (bufor 5 cm, konce plaskie) wyciagniety; na terenie
  podstawa w kazdym wierzcholku (co <= 100 cm) na terenie; linia bez wysokosci - bez bryly;
- punkt: roslina (symbol drzewo albo krzew, z srednica i wys) - pien r = max(5, 0,05
  srednicy) do 0,4 wys i korona (elipsoida srednica x 0,6 wys) na szczycie; inny punkt -
  walec r 10 cm o wysokosci wys (albo 30 cm);
- sasiedztwo: od terenu w srodku obrysu do + wys; modul: siatki makiety lokalu.
"""
import math

import numpy as np
import shapely
import trimesh
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from zamierzenie import model, moduly, teren

KROK = 100.0   # cm: najdluzszy odcinek krawedzi drapowanej po terenie i bok siatki arkusza
TEREN = "#D0D0D0"
SASIEDZTWO = "#DADADA"
# wierzcholki 0-3 to dol bryly dachu, 4-5 kalenica (albo gorna krawedz polaci jednospadowej)
SCIANY_DACHU = [(0, 2, 1), (0, 3, 2), (0, 1, 5), (0, 5, 4), (2, 3, 4), (2, 4, 5), (0, 4, 3), (1, 2, 5)]
SCIANY_PIRAMIDY = [(0, 2, 1), (0, 3, 2), (0, 1, 4), (2, 3, 4), (0, 4, 3), (1, 2, 4)]


def dach(obrys, typ, kat, z0, kalenica="dluzszy", okap=0, nizej=None):
    """Bryla dachu (wodoszczelna) na prostokacie obrysu scian; z0 - rzedna polaci nad linia scian.

    plaski - plyta z0..z0 + 30 na obrysie powiekszonym o okap; jednospadowy - polac od nizszego
    boku rownoleglego do kalenicy na z0 do przeciwleglego na z0 + b * tg (ta krawedz na linii
    sciany, bez okapu); strone nizsza wybiera model.osie_dachu (nizej: N, E, S, W; bez nizej W,
    gdy boki rownolegle do kalenicy sa w granicach 10 st. od osi Y, inaczej S); dwuspadowy -
    kalenica na z0 + b / 2 * tg; czterospadowy - kalenica dlugosci a - b (zawsze wzdluz
    dluzszego boku), polacie pod tym samym katem. Kalenica wzdluz dluzszego boku albo krotszego
    (kalenica="krotszy"); okap wysuwa polacie o okap w poziomie i obniza ich krawedz do
    z0 - okap * tg; dol bryly na tej rzednej. Nieznany typ albo nizej spoza N, E, S, W: ValueError.
    """
    if typ not in model.TYPY_DACHU:
        raise ValueError("nieznany typ dachu %r (dozwolone: %s)" % (typ, ", ".join(model.TYPY_DACHU)))
    if nizej is not None and (not isinstance(nizej, str) or nizej not in model.STRONY):
        raise ValueError("nieprawidlowe dach.nizej %r (dozwolone: %s)" % (nizej, ", ".join(model.STRONY)))
    c, u, v, a, b, _ = model.osie_dachu(obrys, kalenica if typ in ("jednospadowy", "dwuspadowy") else "dluzszy",
                                        nizej if typ == "jednospadowy" else None)
    c, u, v = np.array(c), np.array(u), np.array(v)
    A, B, o, tg = a / 2, b / 2, okap, math.tan(math.radians(kat))
    zb = z0 - o * tg
    sciany = SCIANY_DACHU
    if typ == "plaski":
        m = trimesh.creation.box(extents=(2 * (A + o), 2 * (B + o), 30))
        lok, sciany = m.vertices + [0, 0, z0 + 15], m.faces
    elif typ == "jednospadowy":
        zt = z0 + b * tg
        lok = [(-A - o, -B - o, zb), (A + o, -B - o, zb), (A + o, B, zb), (-A - o, B, zb), (-A - o, B, zt), (A + o, B, zt)]
    elif typ == "dwuspadowy":
        zr = z0 + B * tg
        lok = [(-A - o, -B - o, zb), (A + o, -B - o, zb), (A + o, B + o, zb), (-A - o, B + o, zb), (-A - o, 0, zr), (A + o, 0, zr)]
    else:   # czterospadowy
        zr, R = z0 + B * tg, A - B
        lok = [(-A - o, -B - o, zb), (A + o, -B - o, zb), (A + o, B + o, zb), (-A - o, B + o, zb), (-R, 0, zr), (R, 0, zr)]
        if R < 1e-6:
            lok, sciany = lok[:5], SCIANY_PIRAMIDY
    lok = np.array(lok, dtype=float)
    xy = c + np.outer(lok[:, 0], u) + np.outer(lok[:, 1], v)
    return trimesh.Trimesh(np.column_stack([xy, lok[:, 2]]), np.array(sciany), process=False)


def _trojkaty(wielokaty):
    """(xy, trojkaty CCW, krawedzie pierscieni) - triangulacja z ograniczeniami (shapely),
    wierzcholki wspolne dla trojkatow i pierscieni."""
    xy, klucze = [], {}

    def nr(q):
        k = (round(q[0], 6), round(q[1], 6))
        if k not in klucze:
            klucze[k] = len(xy)
            xy.append((q[0], q[1]))
        return klucze[k]

    trojkaty, krawedzie = [], []
    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(np.array(wielokaty, dtype=object))):
        p, q, r = t.exterior.coords[:3]
        if (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) < 0:
            q, r = r, q
        trojkaty.append((nr(p), nr(q), nr(r)))
    for w in wielokaty:
        for pierscien in (w.exterior, *w.interiors):
            k = [nr(q) for q in pierscien.coords[:-1]]
            krawedzie += [(i, j) for i, j in zip(k, k[1:] + k[:1]) if i != j]
    return np.array(xy, dtype=float).reshape(-1, 2), trojkaty, krawedzie


def _z(f, xy):
    return np.array([f(x, y) for x, y in xy], dtype=float) if callable(f) else np.full(len(xy), float(f))


def _bryla(g, dol, gora):
    """Wielokat (albo multi-) wyciagniety od dol do gora - liczby albo funkcje (x, y) -> z."""
    w = [orient(p, 1.0) for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty]
    if not w:
        return None
    xy, tr, kr = _trojkaty(w)
    n = len(xy)
    v = np.vstack([np.column_stack([xy, _z(dol, xy)]), np.column_stack([xy, _z(gora, xy)])])
    f = [(a + n, b + n, c + n) for a, b, c in tr] + [(a, c, b) for a, b, c in tr]
    f += [(i, j, j + n) for i, j in kr] + [(i, j + n, i + n) for i, j in kr]
    return trimesh.Trimesh(v, np.array(f), process=False)


def _drapuj(g, s, dz=1.0):
    """Arkusz trojkatow na terenie: wielokat pociety siatka co KROK, wierzcholki na terenie + dz."""
    g = shapely.segmentize(g, KROK)
    x0, y0, x1, y1 = g.bounds
    X, Y = np.meshgrid(np.arange(math.floor(x0 / KROK) * KROK, x1, KROK), np.arange(math.floor(y0 / KROK) * KROK, y1, KROK))
    X, Y = X.ravel(), Y.ravel()
    czesci = [p for p in shapely.get_parts(shapely.intersection(shapely.box(X, Y, X + KROK, Y + KROK), g))
              if p.geom_type == "Polygon" and p.area > 1e-6]
    if not czesci:
        return None
    xy, tr, _ = _trojkaty(czesci)
    return trimesh.Trimesh(np.column_stack([xy, _z(lambda x, y: teren.rzedna(s, x, y) + dz, xy)]), np.array(tr), process=False)


def _elipsoida(rx, rz):
    t = np.linspace(-math.pi / 2, math.pi / 2, 9)
    profil = np.column_stack([np.cos(t), np.sin(t)])
    profil[[0, -1], 0] = 0.0
    m = trimesh.creation.revolve(profil, sections=16)
    m.apply_scale([rx, rx, rz])
    return m


def _punkt(o, st, g, z0, z1):
    if st["plan"]["symbol"] in ("drzewo", "krzew") and o.get("srednica") and o.get("wys"):
        sr, wys = float(o["srednica"]), float(o["wys"])
        pien = trimesh.creation.cylinder(radius=max(5.0, 0.05 * sr), height=0.4 * wys, sections=16)
        pien.apply_translation([g.x, g.y, z0 + 0.2 * wys])
        korona = _elipsoida(sr / 2, 0.3 * wys)
        korona.apply_translation([g.x, g.y, z0 + 0.7 * wys])
        return trimesh.util.concatenate([pien, korona])
    h = z1 - z0 if z1 > z0 else 30.0
    m = trimesh.creation.cylinder(radius=10.0, height=h, sections=16)
    m.apply_translation([g.x, g.y, z0 + h / 2])
    return m


def _obiekt(M, o, s):
    st, g = model.styl(M, o.get("kategoria")), model.ksztalt(o)
    ks = st["ksztalt"] or {"Polygon": "powierzchnia", "LineString": "linia", "Point": "punkt"}[g.geom_type]
    if o.get("dach"):
        d = o["dach"]
        return dach(g, d.get("typ"), d.get("kat", 0), model.baza_z(M, o, s) + d.get("z0", 0),
                    d.get("kalenica", "dluzszy"), d.get("okap", 0), d.get("nizej"))
    z0, z1 = model.zakres_z(M, o, s)
    if ks == "punkt":
        return _punkt(o, st, g, z0, z1)
    if ks == "linia":
        if z1 <= z0:
            return None
        pas = g.buffer(5, cap_style="flat", join_style="mitre")
        if not o.get("na_terenie"):
            return _bryla(pas, z0, z1)
        b = model.baza_z(M, o, s)   # podstawa w srodku ciezkosci; w 3D kazdy wierzcholek na terenie
        return _bryla(shapely.segmentize(pas, KROK), lambda x, y: teren.rzedna(s, x, y) + z0 - b,
                      lambda x, y: teren.rzedna(s, x, y) + z1 - b)
    if ks == "powierzchnia" or z1 <= z0:
        return _drapuj(g, s) if o.get("na_terenie") else _bryla(g, z0, z0 + 2)
    return _bryla(g, z0, z1)


def _teren(s):
    tr = s["tri"].copy()
    a, b, c = (s["pkt"][tr[:, i], :2] for i in range(3))
    zle = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]) < 0
    tr[zle] = tr[zle][:, [0, 2, 1]]
    return trimesh.Trimesh(s["pkt"].copy(), tr, process=False)


def siatki(M, wybory=None):
    """[(nazwa, siatka, wyglad)]: teren, sasiedztwo i obiekty (wyglad = hex z legendy), elementy
    modulow jako "<modul>:<nazwa>" z wygladem (hex, alfa, szorstkosc) makiety lokalu."""
    s = teren.siatka(M)
    wynik = [("teren", _teren(s), TEREN)] if s is not None else []
    for x in (M.get("miejsce") or {}).get("sasiedztwo") or []:
        g = Polygon(x["obrys"])
        zt = teren.rzedna(s, g.centroid.x, g.centroid.y)
        if x.get("wys"):
            wynik.append((x["id"], _bryla(g, zt, zt + x["wys"]), SASIEDZTWO))
    for o in model.obiekty(M):
        m = _obiekt(M, o, s)
        if m is not None:
            wynik.append((o["id"], m, model.styl(M, o.get("kategoria"))["bryla"]["kolor"]))
    if moduly.moduly(M):
        from rysunki import glb   # tu, bo rysunki/glb.py importuje ten plik
        for mod in moduly.moduly(M):
            T = moduly.transformacja(M, mod)
            macierz = trimesh.transformations.translation_matrix([T["dx"], T["dy"], T["z0"]]) @ \
                trimesh.transformations.rotation_matrix(math.radians(T["kat"]), [0, 0, 1]) @ np.diag([100.0, 100.0, 100.0, 1.0])
            for nazwa, m, hex_, alfa, szorstkosc in glb.siatki_lokalu(moduly.wczytaj_modul(M, mod), wybory):
                m.apply_transform(macierz)
                wynik.append(("%s:%s" % (mod["id"], nazwa), m, (hex_, alfa, szorstkosc)))
    return wynik
