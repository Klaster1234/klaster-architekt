"""Przekroje i elewacje modelu zamierzenia: arkusze P-11, P-12, ... (SVG, PNG, PDF).

    python rysunki/przekroj.py przyklad/ogrod/model/projekt.json
    python rysunki/przekroj.py przyklad/ogrod/model/projekt.json --przekroj B --numer P-21 --wyjscie robocze/

Przekroj to pionowa plaszczyzna przez linie z sekcji przekroje modelu. Widok siega w lewo od linii
(patrzac od pierwszego do drugiego punktu) na glebokosc przekroju (bez glebokosci - do konca
modelu), wiec linia poprowadzona obok budynku daje elewacje. Arkusz: elementy przeciete
(przeciecia siatek 3D z zamierzenie/bryly.py z plaszczyzna - trimesh mesh_plane - gruba linia,
wypelnienie z legendy albo kolor bryly, kreskowanie), powierzchnie przeciete jako pas na terenie,
widok za plaszczyzna (trojkaty siatek przyciete do zasiegu widoku, rzutowane na plaszczyzne,
malowane od najdalszych, z krawedziami i obrysem), profil terenu z gruntem, poziomy z rzednymi
(±0,00 i wzgledne w m), rzedne kalenic, okapow i gory bryl, rzedne terenu na koncach oraz plan
z linia przekroju i zasiegiem widoku. W konsoli: przeciete i w widoku (id obiektow i modulow).
Bez --przekroj kazdy przekroj modelu dostaje wlasny arkusz, numery kolejno od --numer (domyslnie
P-11) wedlug pozycji w sekcji przekroje; --przekroj ID bez --numer daje numer z tej kolejnosci.
Linia bez dwoch roznych punktow albo ujemna glebokosc: komunikat i kod 1. Model lokalu:
komunikat i kod 2. Wynik: <id>_<numer>_przekroj_<id przekroju>.
"""
import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import linemerge, polygonize, unary_union
from trimesh import intersections

from wspolne import arkusz, slonce, svg, wzory
from wspolne.opisy import rect_tekstu
from zamierzenie import bryly, model, rysuj, teren

KROK_TERENU = 150.0          # cm: najdluzsza krawedz trojkata terenu w widoku (kolejnosc malowania)
PRZESUNIECIE = {"teren": 100.0, "powierzchnia": 50.0, "bryla": 0.0}   # cm: w tej samej glebokosci teren i powierzchnie pod bryla
KAT_KRAWEDZI = math.radians(25)   # krawedz miedzy scianami widoku rysowana od tego kata
GRUNT_POD = 100.0            # cm gruntu pod profilem terenu
SWIATLO = (-0.8, 0.25, 0.6)  # kierunek swiatla: od patrzacego, z prawej, z gory (n, u, z)
KRAWEDZ = ("#3C3C3C", 0.45)
CIECIE = ("#111111", 1.8)
GRUNT = ("#FFFFFF", "#B39B7A", "#5B4A33")          # wypelnienie, kreskowanie, linia profilu
POZIOM = ("#666666", 0.6, "12 3 2 3")
LINIA_PRZEKROJU = "#B03A2E"
ZNACZNIK = "#222222"
PLAN_MAKS = 480              # najwieksza wysokosc planu z linia przekroju na arkuszu
MIN_POLE = 100.0             # cm2: mniejsza widoczna czesc nie trafia do listy "w widoku"


def uklad(M, p):
    """(a, u, n, dl, gl): poczatek linii, kierunek linii (na arkuszu w prawo), kierunek patrzenia
    (w lewo od linii), dlugosc i glebokosc widoku w cm (bez glebokosci - do konca zakresu modelu)."""
    (x0, y0), (x1, y1) = p["linia"][0], p["linia"][-1]
    dl = math.hypot(x1 - x0, y1 - y0)
    u = ((x1 - x0) / dl, (y1 - y0) / dl)
    n = (-u[1], u[0])
    gl = p.get("glebokosc")
    if gl is None:
        zk = model.zakres(M)
        gl = max([0.0] + [(x - x0) * n[0] + (y - y0) * n[1] for x in (zk[0], zk[2]) for y in (zk[1], zk[3])]) if zk else 0.0
    return (float(x0), float(y0)), u, n, dl, max(0.0, float(gl))


def azymut(M, k):
    """Azymut kierunku k (uklad modelu) od polnocy zgodnie z zegarem."""
    return (model.azymut_polnocy(M) + math.degrees(math.atan2(k[0], k[1]))) % 360


def _id(nazwa):
    """Id obiektu albo modulu z nazwy siatki ("<modul>:<element>" -> modul)."""
    return nazwa.split(":")[0]


def _ciecie(m, A, U, N, dl):
    """Odcinki przeciecia siatki z plaszczyzna [((s0, z0), (s1, z1))] przyciete do 0 <= s <= dl."""
    wynik = []
    for q0, q1 in intersections.mesh_plane(m, N, A):
        s0, s1, z0, z1 = float((q0 - A) @ U), float((q1 - A) @ U), float(q0[2]), float(q1[2])
        if s0 > s1:
            s0, s1, z0, z1 = s1, s0, z1, z0
        if s1 < 0 or s0 > dl:
            continue
        if s1 - s0 > 1e-9:
            t0, t1 = max(0.0, (0 - s0) / (s1 - s0)), min(1.0, (dl - s0) / (s1 - s0))
            s0, s1, z0, z1 = s0 + (s1 - s0) * t0, s0 + (s1 - s0) * t1, z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1
        wynik.append(((s0, z0), (s1, z1)))
    return wynik


def _rgb(kolor):
    """(r, g, b) z "#RRGGBB" albo "#RGB"; inny zapis - szary."""
    h = str(kolor or "").lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    try:
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)] if len(h) == 6 else [200, 200, 200]
    except ValueError:
        return [200, 200, 200]


def _widok(m, A, U, N, dl, gl, zmin, kolor, rodzaj):
    """Widoczne trojkaty siatki za plaszczyzna: [(glebokosc, klucz, [(s, z)] x 3, kolor, krawedzie)].
    Siatka przycieta do zasiegu widoku (0 <= glebokosc <= gl, 0 <= s <= dl, z >= zmin + 6 cm - dol
    ciecia chowa sie pod gruntem, ktory siega do zmin); w bryle
    zamknietej tylko sciany zwrocone do patrzacego. Krawedz: brzeg siatki, krawedz miedzy sciana
    widoczna i niewidoczna (obrys) albo miedzy scianami pod katem > KAT_KRAWEDZI; rysowana z blizsza
    sciana. Klucz kolejnosci = glebokosc + PRZESUNIECIE[rodzaj]."""
    Z = np.array([0.0, 0.0, 1.0])
    cz = intersections.slice_mesh_plane(m, np.array([N, -N, U, -U, Z]),
                                        np.array([A, A + gl * N, A, A + dl * U, [0.0, 0.0, zmin + 6]]))
    if cz is None or len(cz.faces) == 0:
        return []
    v, f = np.asarray(cz.vertices), np.asarray(cz.faces)
    if rodzaj == "teren":
        v, f = trimesh.remesh.subdivide_to_size(v, f, KROK_TERENU)
    cz = trimesh.Trimesh(v, f)       # scalone wierzcholki: sasiedztwo scian do krawedzi
    V, F = cz.vertices, cz.faces
    if len(F) == 0:
        return []
    s, d, z = (V - A) @ U, (V - A) @ N, V[:, 2]
    P = V[F]
    nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    dlug = np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)
    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    pole = 0.5 * np.abs((s[b] - s[a]) * (z[c] - z[a]) - (s[c] - s[a]) * (z[b] - z[a]))
    wid = pole > 0.5
    if rodzaj == "bryla" and m.is_watertight:
        wid &= nrm @ N < -1e-9 * dlug
    L = SWIATLO[0] * N + SWIATLO[1] * U + SWIATLO[2] * Z
    sw = (nrm / dlug[:, None]) @ (L / np.linalg.norm(L))
    k = 0.86 + 0.14 * np.clip(sw if rodzaj == "bryla" else np.abs(sw), 0, 1)
    dsr = d[F].mean(axis=1)
    kr = [[] for _ in range(len(F))]
    es = cz.edges_sorted
    for i in trimesh.grouping.group_rows(es, require_count=1):
        kr[cz.edges_face[i]].append(es[i])
    for (f0, f1), e, kat in zip(cz.face_adjacency, cz.face_adjacency_edges, cz.face_adjacency_angles):
        if wid[f0] and wid[f1]:
            if kat > KAT_KRAWEDZI:
                kr[f0 if dsr[f0] <= dsr[f1] else f1].append(e)
        elif wid[f0] or wid[f1]:
            kr[f0 if wid[f0] else f1].append(e)
    rgb = _rgb(kolor)
    wynik = []
    for i in np.flatnonzero(wid):
        kk = round(float(k[i]) * 50) / 50
        kol = "#%02X%02X%02X" % tuple(min(255, round(x * kk)) for x in rgb)
        pk = [(float(s[j]), float(z[j])) for j in F[i]]
        kraw = [((float(s[p]), float(z[p])), (float(s[q]), float(z[q]))) for p, q in kr[i]
                if z[p] > zmin + 6.01 or z[q] > zmin + 6.01]      # bez krawedzi ciecia na dole rysunku (pod gruntem)
        wynik.append((float(dsr[i]), float(dsr[i]) + PRZESUNIECIE[rodzaj], pk, kol, kraw))
    return wynik


def przekroj(M, p, siatki=None):
    """Przekroj p modelu M: {"uklad": (a, u, n, dl, gl), "przeciete": {nazwa siatki: [odcinki (s, z)]},
    "wielokaty": {nazwa: (wielokat przeciecia albo None, odcinki luzne)} (bryly), "trojkaty": [(glebokosc,
    klucz, [(s, z)] x 3, kolor, krawedzie, nazwa)] od najdalszych, "profil": [(s, z)], "rodzaje": {nazwa:
    "teren" | "powierzchnia" | "bryla"}, "zakres_z": (zmin, zmax), "widocznosc": {id: (pole cm2, (s, z),
    promien cm)}, "w_widoku": [id obiektow i modulow widocznych za plaszczyzna, nieprzecietych]}; s w cm od
    poczatku linii, z wzgledem +-0. Teren nie trafia do przecietych (rysuje go profil)."""
    a, u, n, dl, gl = uklad(M, p)
    A, U, N = np.array([a[0], a[1], 0.0]), np.array([u[0], u[1], 0.0]), np.array([n[0], n[1], 0.0])
    siatki = bryly.siatki(M) if siatki is None else siatki
    plaskie = rysuj.plaskie(M)
    rodzaje = {nazwa: "teren" if nazwa == "teren" else "powierzchnia" if nazwa in plaskie else "bryla"
               for nazwa, _, _ in siatki}
    profil = teren.profil(teren.siatka(M), a, (a[0] + u[0] * dl, a[1] + u[1] * dl), 25)
    przeciete = {}
    for nazwa, m, _ in siatki:
        if rodzaje[nazwa] != "teren":
            odc = _ciecie(m, A, U, N, dl)
            if odc:
                przeciete[nazwa] = odc
    wielokaty = {nazwa: _wielokaty(odc) for nazwa, odc in przeciete.items() if rodzaje[nazwa] == "bryla"}
    zc = [q[1] for o in przeciete.values() for od in o for q in od]
    poz = [float(x.get("z", 0)) for x in model.poziomy(M)] + [0.0]
    zmin = min([min(z for _, z in profil) - GRUNT_POD] + [z - 30 for z in poz] + [z - 20 for z in zc])
    trojkaty = []
    if gl > 0:
        for nazwa, m, wyglad in siatki:
            kolor = wyglad if isinstance(wyglad, str) else wyglad[0]
            trojkaty += [t + (nazwa,) for t in _widok(m, A, U, N, dl, gl, zmin, kolor, rodzaje[nazwa])]
    trojkaty.sort(key=lambda t: -t[1])
    zv = [q[1] for t in trojkaty for q in t[2]]
    zmax = max([z for _, z in profil] + zc + zv + poz) + 60
    R = {"uklad": (a, u, n, dl, gl), "przeciete": przeciete, "wielokaty": wielokaty, "trojkaty": trojkaty, "profil": profil,
         "rodzaje": rodzaje, "zakres_z": (zmin, zmax)}
    R["widocznosc"] = _widocznosc(R)
    ciete = {_id(x) for x in przeciete}
    R["w_widoku"] = sorted((i for i, w in R["widocznosc"].items() if i not in ciete and i != "teren" and w[0] >= MIN_POLE),
                           key=rysuj.klucz_id)
    return R


def _ziemia(R):
    """Grunt w przekroju (uklad s, z): od profilu terenu do dolu rysunku."""
    dl, (zmin, _) = R["uklad"][3], R["zakres_z"]
    pk = [(max(0.0, min(dl, s)), z) for s, z in R["profil"]]
    return Polygon([(0, zmin)] + pk + [(dl, zmin)]).buffer(0)


def _widocznosc(R):
    """{id: (pole widoczne cm2, najglebszy punkt widocznej czesci (s, z), jego odleglosc od brzegu cm)}
    z rastra indeksow (Pillow, tryb "I"): trojkaty widoku w kolejnosci malowania, potem grunt i
    wielokaty przeciec - jak na arkuszu; id = obiekt, sasiedztwo albo modul (powierzchnie przeciete
    rysuje pas na terenie, bez rastra)."""
    dl, (zmin, zmax) = R["uklad"][3], R["zakres_z"]
    rozdz = max(2.0, max(dl, zmax - zmin) / 1200)
    szer, wys = int(math.ceil(dl / rozdz)) + 1, int(math.ceil((zmax - zmin) / rozdz)) + 1
    ids = sorted({_id(t[5]) for t in R["trojkaty"]} | {_id(x) for x in R["wielokaty"]})
    nr = {x: i for i, x in enumerate(ids)}
    im = Image.new("I", (szer, wys), -1)
    dr = ImageDraw.Draw(im)
    P = lambda q: (q[0] / rozdz, (zmax - q[1]) / rozdz)
    for t in R["trojkaty"]:
        dr.polygon([P(q) for q in t[2]], fill=nr[_id(t[5])])
    for g, wartosc in [(_ziemia(R), -1)] + [(g, nr[_id(x)]) for x, (g, _) in sorted(R["wielokaty"].items()) if g is not None]:
        for cz in getattr(g, "geoms", [g]):
            if cz.geom_type == "Polygon" and not cz.is_empty:
                dr.polygon([P(q) for q in cz.exterior.coords], fill=wartosc)
                for dz in cz.interiors:
                    dr.polygon([P(q) for q in dz.coords], fill=-1)
    tab = np.array(im)
    wynik = {}
    for x, i in nr.items():
        maska = np.pad(tab == i, 1)
        ile = int(maska.sum())
        if not ile:
            continue
        odl = ndimage.distance_transform_edt(maska)
        wi, ko = np.nonzero(odl >= 0.9 * odl.max())    # z punktow najdalszych od brzegu - najblizszy srodka
        mw, mk = np.nonzero(maska)
        j = int(np.argmin((wi - mw.mean()) ** 2 + (ko - mk.mean()) ** 2))
        # np.pad przesuwa indeksy o 1: srodek piksela rastra to indeks - 0.5
        wynik[x] = (ile * rozdz * rozdz, ((ko[j] - 0.5) * rozdz, zmax - (wi[j] - 0.5) * rozdz), float(odl[wi[j], ko[j]]) * rozdz)
    return wynik


def _wielokaty(odcinki):
    """(wielokat przeciecia albo None, odcinki spoza niego) z odcinkow (s, z): scianki z polygonize,
    dziury wedlug parzystosci zagniezdzenia obrysow."""
    linie = [LineString([(round(p[0], 2), round(p[1], 2)), (round(q[0], 2), round(q[1], 2))]) for p, q in odcinki]
    linie = [l for l in linie if l.length > 0]
    if not linie:
        return None, []
    twarze = list(polygonize(unary_union(MultiLineString([l.coords for l in linie]))))
    pelne = [t for t in twarze if sum(1 for w in twarze if w is not t and Polygon(w.exterior).contains(t.representative_point())) % 2 == 0]
    g = unary_union(pelne) if pelne else None
    brzeg = g.boundary.buffer(0.5) if g is not None else None
    return g, [l for l in linie if brzeg is None or not l.within(brzeg)]


def _kolory(M, siatki):
    """{nazwa: kolor przeciecia}: wypelnienie z legendy, inaczej kolor bryly; siatka spoza obiektow
    (sasiedztwo, moduly) - kolor siatki."""
    wynik = {}
    for nazwa, _, wyglad in siatki:
        hex_ = wyglad if isinstance(wyglad, str) else wyglad[0]
        try:
            st = model.styl(M, model.obiekt(M, nazwa).get("kategoria"))
            wynik[nazwa] = st["plan"]["wypelnienie"] or st["bryla"]["kolor"] or hex_
        except KeyError:
            wynik[nazwa] = hex_
    return wynik


def _znacznik(Ws, miejsca, s, z, tekst, pusty=False, kolor=ZNACZNIK):
    """Rzedna: trojkat ostrzem w punkcie (s, z) i opis obok (napis bez kolizji)."""
    X, Y = Ws.p(s, z)
    tri = svg.polilinia([(X, Y), (X - 3.6, Y - 6), (X + 3.6, Y - 6)], kolor, 0.8, wyp="#FFFFFF" if pusty else kolor, zamknij=True)
    miejsca.zajmij((X - 4, Y - 7, X + 4, Y + 0.5))
    linie = [(tekst, 8)]
    r = rect_tekstu(0, 0, linie)
    w = (r[2] - r[0]) / 2
    kand = [(X + 7 + w, Y - 7), (X - 7 - w, Y - 7), (X + 7 + w, Y - 18), (X - 7 - w, Y - 18), (X + 7 + w, Y + 7), (X - 7 - w, Y + 7)]
    return tri, rysuj.napis(miejsca, kand, linie, kolor, kotwica=(X, Y - 3))


def _znaczniki_dachu(o, m, R, z0, z1, nie):
    """Rzedne dachu [(s, z, opis)]: kalenica (dach plaski - gora plyty) i okap z wierzcholkow siatki m
    w zasiegu widoku (0 <= s <= dl i 0 <= glebokosc <= gl, z tolerancja 1 cm). Gdy zadnego nie ma -
    gora (dla okapu dol) narysowanej czesci dachu: przeciecia, inaczej widocznych trojkatow, opisana
    "kalenica" tylko wtedy, gdy siega jej rzednej, inaczej "dach"; dachu ani w przecieciu, ani
    w widoku - bez znacznika."""
    a, u, n, dl, gl = R["uklad"]
    V = np.asarray(m.vertices)
    ss, dd = (V[:, :2] - np.array(a)) @ np.array(u), (V[:, :2] - np.array(a)) @ np.array(n)
    w_zasiegu = (ss >= -1) & (ss <= dl + 1) & (dd >= -1) & (dd <= gl + 1)
    pk = [q for od in R["przeciete"].get(o["id"], []) for q in od] or [q for t in R["trojkaty"] if t[5] == o["id"] for q in t[2]]
    plaski = o["dach"].get("typ") == "plaski"
    wynik = []
    for z, nazwa, gora in ((z1, "dach" if plaski else "kalenica", True),) + (() if plaski else ((z0, "okap", False),)):
        w = ss[w_zasiegu & (np.abs(V[:, 2] - z) < 1)]
        if len(w):
            wynik.append((max(0.0, min(dl, float((w.min() + w.max()) / 2 if gora else w.max()))), z,
                          "%s %s" % (nazwa, rysuj.rzedna_txt(z, nie))))
        elif pk:
            zz = max(q[1] for q in pk) if gora else min(q[1] for q in pk)
            w = [q[0] for q in pk if abs(q[1] - zz) < 1]
            wynik.append(((min(w) + max(w)) / 2 if gora else max(w), zz,
                          "%s %s" % (nazwa if gora and abs(zz - z) < 1 else "dach", rysuj.rzedna_txt(zz, nie))))
    return wynik


def _opis(Ws, miejsca, R, ident, kolor=rysuj.KOLOR_OPISU, r=8.5):
    """Id w najglebszym punkcie widocznej czesci (raster widocznosci), gdy sie tam miesci; inaczej
    obok, z odnosnikiem do tego punktu."""
    _, (s, z), promien = R["widocznosc"][ident]
    X, Y = Ws.p(s, z)
    linie = [(ident, r)]
    x0, y0, x1, y1 = rect_tekstu(X, Y, linie)
    kand = [(X, Y)] if math.hypot(x1 - x0, y1 - y0) / 2 + 1 <= promien * Ws.sk else []
    return rysuj.napis(miejsca, kand, linie, kolor, kotwica=(X, Y))


def rysunek_przekroju(M, R, Ws, miejsca, siatki):
    """(rysunek, opisy) przekroju na widoku Ws (uklad s, z)."""
    a, u, n, dl, gl = R["uklad"]
    rodzaje, przeciete, trojkaty = R["rodzaje"], R["przeciete"], R["trojkaty"]
    kol_ciecia = _kolory(M, siatki)
    s_ = teren.siatka(M)
    nie_teren = model.niepewny((M.get("miejsce") or {}).get("teren") or {})
    rys, op = [], []
    # 1. widok za plaszczyzna, od najdalszych trojkatow
    for _, _, pk, kol, kraw, _ in trojkaty:
        rys.append(svg.polilinia([Ws.p(*q) for q in pk], kol, 0.35, wyp=kol, zamknij=True))
        for q0, q1 in kraw:
            (X0, Y0), (X1, Y1) = Ws.p(*q0), Ws.p(*q1)
            rys.append(svg.linia(X0, Y0, X1, Y1, *KRAWEDZ))
    # 2. grunt i profil terenu
    ziemia = _ziemia(R)
    pk = [(max(0.0, min(dl, s)), z) for s, z in R["profil"]]
    rys += [svg.sciezka(ziemia, Ws.p, GRUNT[0], None), wzory.kreskowanie(ziemia, Ws.p, 5.0, 45, GRUNT[1], 0.4),
            svg.polilinia([Ws.p(*q) for q in pk], GRUNT[2], 1.6)]
    # 3. poziomy: linia przez caly rysunek (takze przez grunt), rzedna i nazwa na lewym marginesie
    poziomy = {}
    for x in model.poziomy(M):
        poziomy.setdefault(round(float(x.get("z", 0)), 1), []).append("%s%s" % (x["id"], " " + x["nazwa"] if x.get("nazwa") else ""))
    poziomy.setdefault(0.0, [])
    for z, nazwy in sorted(poziomy.items()):
        X0, Y = Ws.p(0, z)
        X1 = Ws.p(dl, z)[0]
        rys.append(svg.linia(X0 - 30, Y, X1 + 8, Y, POZIOM[0], POZIOM[1], POZIOM[2]))
        rys.append(svg.polilinia([(X0 - 34, Y), (X0 - 37.6, Y - 6), (X0 - 30.4, Y - 6)], ZNACZNIK, 0.8, wyp=ZNACZNIK, zamknij=True))
        op.append(svg.tekst(X0 - 42, Y - 2, rysuj.rzedna_txt(z), 8.5, "end", kolor=ZNACZNIK, waga="bold"))
        if nazwy:
            op.append(svg.tekst(X0 - 42, Y + 9, ", ".join(nazwy), 7.5, "end", kolor="#555555"))
        miejsca.zajmij((X0 - 150, Y - 12, X0 - 28, Y + 12))
    # 4. powierzchnie przeciete: pas na terenie
    pasy = {}
    for nazwa in sorted(przeciete, key=rysuj.klucz_id):
        if rodzaje[nazwa] != "powierzchnia":
            continue
        g = linemerge([LineString(od) for od in przeciete[nazwa] if od[0] != od[1]])
        pasy[nazwa] = g
        for l in getattr(g, "geoms", [g]):
            rys.append(svg.polilinia([Ws.p(*q) for q in l.coords], kol_ciecia[nazwa], 3.2))
    # 5. bryly przeciete: wypelnienie, kreskowanie, gruba linia
    for nazwa in sorted(R["wielokaty"], key=rysuj.klucz_id):
        g, luzne = R["wielokaty"][nazwa]
        if g is not None:
            rys += [svg.sciezka(g, Ws.p, kol_ciecia[nazwa], None), wzory.kreskowanie(g, Ws.p, 5.0, 45, "#333333", 0.5),
                    svg.sciezka(g, Ws.p, "none", *CIECIE)]
        for l in luzne:
            rys.append(svg.sciezka(l, Ws.p, "none", *CIECIE))
    # 6. rzedne: kalenice i okapy dachow, gora bryl, teren na koncach
    znaczniki = []
    for ident in sorted({_id(x) for x in przeciete if rodzaje[x] == "bryla"} | set(R["w_widoku"]), key=rysuj.klucz_id):
        try:
            o = model.obiekt(M, ident)
        except KeyError:
            continue                        # sasiedztwo, modul
        z0, z1 = model.zakres_z(M, o, s_)
        nie = model.niepewny(o)
        if o.get("dach"):
            znaczniki += _znaczniki_dachu(o, next(x[1] for x in siatki if x[0] == ident), R, z0, z1, nie)
        elif rysuj.grupa(M, o) == 1 and all(abs(z1 - zp) > 0.5 for zp in poziomy):
            pk_o = [q for od in przeciete.get(ident, []) for q in od] or [q for t in trojkaty if t[5] == ident for q in t[2]]
            gora = [q[0] for q in pk_o if abs(q[1] - z1) < 1]
            if gora:
                znaczniki.append((max(gora), z1, rysuj.rzedna_txt(z1, nie)))
    for s, z, t in znaczniki:
        znak, opis = _znacznik(Ws, miejsca, s, z, t)
        rys.append(znak)
        op.append(opis)
    for s, z in (pk[0], pk[-1]):
        znak, opis = _znacznik(Ws, miejsca, s, z, "teren " + rysuj.rzedna_txt(z, nie_teren), pusty=True)
        rys.append(znak)
        op.append(opis)
    # 7. opisy: bryly przeciete, bryly widoczne za plaszczyzna (od najwiekszych), powierzchnie przeciete pod terenem
    ciete = {_id(x) for x in R["wielokaty"]}
    for ident in sorted(ciete, key=rysuj.klucz_id):
        if ident in R["widocznosc"]:
            op.append(_opis(Ws, miejsca, R, ident))
    for g, _ in R["wielokaty"].values():        # przekroje bryl bez cudzych opisow
        if g is not None:
            (X0, Y1), (X1, Y0) = Ws.p(*g.bounds[:2]), Ws.p(*g.bounds[2:])
            miejsca.zajmij((X0, Y0, X1, Y1))
    widoczne = [i for i in R["w_widoku"] if i != "teren" and i not in ciete and not all(
        rodzaje.get(x) == "powierzchnia" for x in rodzaje if _id(x) == i)]
    for ident in sorted(widoczne, key=lambda i: -R["widocznosc"][i][0]):
        op.append(_opis(Ws, miejsca, R, ident, r=8))
    for nazwa, g in pasy.items():
        kand = []
        for l in sorted(getattr(g, "geoms", [g]), key=lambda l: -l.length):
            for f in (0.5, 0.3, 0.7, 0.15, 0.85):
                X, Y = Ws.p(*l.interpolate(f, normalized=True).coords[0])
                kand += [(X, Y + 11), (X, Y + 21)]
        op.append(rysuj.napis(miejsca, kand, [(_id(nazwa), 7.5)], "#555555", pomin=True))
    return "".join(rys), "".join(op)


def plan_przekroju(M, p, R, pole):
    """(svg, skala_txt): plan (obiekty szare, bez opisow) z linia przekroju, strzalkami kierunku
    widoku, id na koncach i zasiegiem widoku (linia przerywana)."""
    a, u, n, dl, gl = R["uklad"]
    b = (a[0] + u[0] * dl, a[1] + u[1] * dl)
    strefa = Polygon([a, b, (b[0] + n[0] * gl, b[1] + n[1] * gl), (a[0] + n[0] * gl, a[1] + n[1] * gl)]) if gl > 0 else None
    zk = [z for z in [model.zakres(M), LineString([a, b]).bounds, strefa.bounds if strefa is not None else None] if z]
    zakres = (min(z[0] for z in zk) - 150, min(z[1] for z in zk) - 150, max(z[2] for z in zk) + 150, max(z[3] for z in zk) + 150)
    sk, skala_txt = None, "bez skali"
    for m in arkusz.SKALE:
        if m >= 200:
            k = arkusz.jednostek_na_cm(m)
            if (zakres[2] - zakres[0]) * k <= pole[2] - pole[0] and (zakres[3] - zakres[1]) * k <= pole[3] - pole[1]:
                sk, skala_txt = k, "1:%d" % m
                break
    W = arkusz.Widok(zakres, pole, sk)
    s = [rysuj.sasiedztwo(W, M, opisy=False), rysuj.obiekty(W, M, tryb="bez_zmian", opisy=False),
         rysuj.moduly(W, M, czesci=True)[0], rysuj.dzialka(W, M, czesci=True)[0]]
    if strefa is not None:
        s.append(svg.sciezka(strefa, W.p, "none", LINIA_PRZEKROJU, 0.7, "6 3"))
    (X0, Y0), (X1, Y1) = W.p(*a), W.p(*b)
    s.append(svg.linia(X0, Y0, X1, Y1, LINIA_PRZEKROJU, 2.2, "16 3 3 3"))
    nx, ny = n[0], -n[1]                       # kierunek patrzenia na arkuszu (os Y w dol)
    ux, uy = u[0], -u[1]
    for (X, Y), znak in (((X0, Y0), -1), ((X1, Y1), 1)):
        s.append(svg.linia(X, Y, X + nx * 16, Y + ny * 16, LINIA_PRZEKROJU, 1.4))
        grot = [(X + nx * 20, Y + ny * 20), (X + nx * 12 - ny * 4, Y + ny * 12 + nx * 4), (X + nx * 12 + ny * 4, Y + ny * 12 - nx * 4)]
        s.append(svg.polilinia(grot, LINIA_PRZEKROJU, 0.8, wyp=LINIA_PRZEKROJU, zamknij=True))
        s.append(svg.tekst(X + znak * ux * 13, Y + znak * uy * 13 + 4.5, p["id"], 12, "middle", kolor=LINIA_PRZEKROJU, waga="bold"))
    s.append(svg.strzalka_polnocy(pole[2] - 30, pole[1] + 30, model.azymut_polnocy(M), r=16))
    return "".join(s), skala_txt


def legenda_przekroju(R):
    I = lambda x, y: (x, y)
    kw = Polygon([(1, 3), (23, 3), (23, 13), (1, 13)])
    poz = [(svg.prostokat(1, 3, 23, 13, "#BDBDBD", None) + wzory.kreskowanie(kw, I, 5.0, 45, "#333333", 0.5)
            + svg.prostokat(1, 3, 23, 13, "none", CIECIE[0], CIECIE[1]),
            "element przecięty (wypełnienie z legendy modelu albo kolor bryły)")]
    if R["trojkaty"]:
        poz.append((svg.prostokat(1, 3, 23, 13, "#D9D9D9", KRAWEDZ[0], KRAWEDZ[1]), "widok za płaszczyzną przekroju"))
    ziemia = Polygon([(0, 7), (8, 6), (16, 7.5), (24, 6), (24, 15), (0, 15)])
    poz.append((svg.sciezka(ziemia, I, GRUNT[0], None) + wzory.kreskowanie(ziemia, I, 5.0, 45, GRUNT[1], 0.4)
                + svg.polilinia([(0, 7), (8, 6), (16, 7.5), (24, 6)], GRUNT[2], 1.6), "grunt w przekroju i profil terenu"))
    if any(r == "powierzchnia" for n_, r in R["rodzaje"].items() if n_ in R["przeciete"]):
        poz.append((svg.linia(0, 8, 24, 8, GRUNT[2], 1.6) + svg.linia(0, 6.6, 24, 6.6, "#8FA27F", 3.2),
                    "powierzchnia przecięta (kolor z legendy modelu)"))
    poz.append((svg.linia(0, 11, 24, 11, POZIOM[0], POZIOM[1], POZIOM[2]) + svg.polilinia([(8, 11), (4.4, 5), (11.6, 5)], ZNACZNIK, 0.8,
                                                                                             wyp=ZNACZNIK, zamknij=True),
                "poziom i rzędna w m względem ±0 (kalenica, okap, góra bryły)"))
    poz.append((svg.polilinia([(12, 12), (8.4, 6), (15.6, 6)], ZNACZNIK, 0.8, wyp="#FFFFFF", zamknij=True), "rzędna terenu na końcu przekroju"))
    poz.append((svg.linia(0, 8, 24, 8, LINIA_PRZEKROJU, 2.2, "16 3 3 3") + svg.linia(12, 8, 12, 15, LINIA_PRZEKROJU, 1.2),
                "linia przekroju na planie, strzałki — kierunek widoku"))
    return poz


def arkusz_przekroju(M, p, numer, siatki=None):
    """(dokument SVG, wynik przekroj()) dla przekroju p."""
    siatki = bryly.siatki(M) if siatki is None else siatki
    R = przekroj(M, p, siatki)
    a, u, n, dl, gl = R["uklad"]
    zmin, zmax = R["zakres_z"]
    patrzy = slonce.strona_swiata(azymut(M, n))
    tytul = "Przekrój %s–%s%s" % (p["id"], p["id"], ": " + p["tytul"] if p.get("tytul") else "")
    teren_jest = teren.siatka(M) is not None
    uwagi = ["Płaszczyzna pionowa przez linię %s; widok w lewo od linii — na %s — na głębokość %s m. Elementy przecięte grubą "
             "linią z kreskowaniem; widok to rzut ścian brył modelu 3D (bez krawędzi niewidocznych)." % (p["id"], patrzy, rysuj.metry(gl)),
             "Rzędne w metrach względem ±0 projektu; kalenica i okap z danych dachu w modelu, „≈” — dane niepewne.",
             ("Teren z punktów wysokościowych modelu (interpolacja liniowa między punktami); grunt pod profilem umownie 1 m."
              if teren_jest else "Model bez punktów terenu: teren płaski na ±0."),
             "Rysunek generowany z modelu zamierzenia — zmiany wprowadza się w modelu, nie na rysunku."]
    dol, y_stopki = rysuj.stopka(legenda_przekroju(R), uwagi)
    pole_dol = min(arkusz.POLE[3], y_stopki - 25)
    # skala przekroju: najwieksza z arkusz.SKALE, przy ktorej rysunek miesci sie nad planem
    X0, X1, Y0 = 200, 1370, 170
    h_maks = max(200, pole_dol - Y0 - 110 - 300)
    sk, skala_txt = None, "bez skali"
    for m in arkusz.SKALE:
        k = arkusz.jednostek_na_cm(m)
        if dl * k <= X1 - X0 and (zmax - zmin) * k <= h_maks:
            sk, skala_txt = k, "1:%d (A3)" % m
            break
    if sk is None:
        sk = min((X1 - X0) / dl, h_maks / (zmax - zmin))
    Ws = arkusz.Widok((0, zmin, dl, zmax), (X0, Y0, X1, Y0 + (zmax - zmin) * sk), sk)
    y_dol = Y0 + (zmax - zmin) * sk
    miejsca = rysuj.Miejsca()
    for r in ((0, 0, arkusz.SZER, Y0 - 22), (0, y_dol + 2, arkusz.SZER, arkusz.WYS), (0, 0, 40, arkusz.WYS), (1440, 0, arkusz.SZER, arkusz.WYS)):
        miejsca.zajmij(r)              # opisy przekroju tylko w jego polu (pod nim strony swiata, podzialka i plan)
    rys, op = rysunek_przekroju(M, R, Ws, miejsca, siatki)
    tresc = [svg.tekst(50, Y0 - 32, "Widok na %s, głębokość widoku %s m" % (patrzy, rysuj.metry(gl)), 10, kolor="#555555"), rys, op]
    Xl, Xp = Ws.p(0, zmin)[0], Ws.p(dl, zmin)[0]
    tresc.append(svg.tekst(Xl, y_dol + 14, slonce.strona_swiata(azymut(M, (-u[0], -u[1]))), 8, kolor="#555555"))
    tresc.append(svg.tekst(Xp, y_dol + 14, slonce.strona_swiata(azymut(M, u)), 8, "end", kolor="#555555"))
    metrow = 5 if Ws.px_na_m >= 16 else 10
    tresc.append(svg.podzialka(Xl, y_dol + 34, Ws.px_na_m, metrow))
    # plan z linia przekroju
    y_planu = y_dol + 80
    pole_planu = (50, y_planu + 18, 1430, min(pole_dol, y_planu + 18 + PLAN_MAKS))
    plan, skala_planu = plan_przekroju(M, p, R, pole_planu)
    podpis = "Położenie przekroju %s — plan" % p["id"] + (", skala " + skala_planu if skala_planu != "bez skali" else "")
    tresc += [svg.tekst(50, y_planu, podpis, 11, waga="bold"), plan]
    dok = arkusz.arkusz(M, numer, tytul, skala_txt, "".join(tresc) + dol, jednostki="rzędne w m względem ±0")
    return dok, R


def numery(numer, ile):
    """Numery kolejnych arkuszy: P-11 -> P-11, P-12, ...; numer bez cyfr na koncu -> numer.1, numer.2, ..."""
    m = re.match(r"^(.*?)(\d+)$", numer)
    if not m:
        return [numer] if ile == 1 else ["%s.%d" % (numer, i + 1) for i in range(ile)]
    return ["%s%0*d" % (m.group(1), len(m.group(2)), int(m.group(2)) + i) for i in range(ile)]


def main():
    ap = argparse.ArgumentParser(description="Przekroje i elewacje modelu zamierzenia (arkusze P-11, P-12, ...).")
    ap.add_argument("model")
    ap.add_argument("--przekroj", help="id przekroju (domyslnie wszystkie z sekcji przekroje)")
    ap.add_argument("--numer", help="numer arkusza (domyslnie P-11, P-12, ... wedlug pozycji w sekcji przekroje; "
                                    "z --przekroj - dokladnie ten numer)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    blad = rysuj.komunikat_rodzaju(M, "sciany lokalu w widoku rysuje rysunki/klady.py")
    if blad:
        print(blad)
        return 2
    wszystkie = M.get("przekroje") or []
    # numer wedlug pozycji w sekcji przekroje (--przekroj B bez --numer daje ten sam numer co pelny przebieg)
    kolejne = numery(a.numer or "P-11", len(wszystkie))
    lista = [(p, a.numer if a.przekroj and a.numer else kolejne[i]) for i, p in enumerate(wszystkie)
             if not a.przekroj or p.get("id") == a.przekroj]
    if not lista:
        print("Nieznany przekroj %s (przekroje: %s)." % (a.przekroj, ", ".join(str(p.get("id")) for p in wszystkie) or "brak")
              if a.przekroj else "Model bez przekrojow (sekcja przekroje, zamierzenie/SCHEMAT.md).")
        return 1
    bledy = []
    for p, _ in lista:
        linia, gl = p.get("linia") or [], p.get("glebokosc")
        if len(linia) < 2 or math.hypot(linia[-1][0] - linia[0][0], linia[-1][1] - linia[0][1]) < 1:
            bledy.append("przekroj %s: linia bez dwoch roznych punktow" % p.get("id"))
        if gl is not None and (isinstance(gl, bool) or not isinstance(gl, (int, float)) or gl < 0):
            bledy.append("przekroj %s: glebokosc %s - musi byc liczba nieujemna (cm)" % (p.get("id"), gl))
    if bledy:
        print("Bledne przekroje: %s." % "; ".join(bledy))
        return 1
    siatki = bryly.siatki(M)
    for p, numer in lista:
        dok, R = arkusz_przekroju(M, p, numer, siatki)
        _, _, n, _, gl = R["uklad"]
        print("przekroj %s (patrzy na azymut %.0f st., glebokosc %.0f cm)" % (p["id"], azymut(M, n), gl))
        print("  przeciete: %s" % (", ".join(sorted({_id(x) for x in R["przeciete"]}, key=rysuj.klucz_id)) or "-"))
        print("  w widoku: %s" % (", ".join(sorted({_id(x) for x in R["w_widoku"]}, key=rysuj.klucz_id)) or "-"))
        nazwa = "%s_przekroj_%s" % (numer, re.sub(r"[^A-Za-z0-9_.-]", "_", str(p["id"])))
        for f in svg.zapisz(dok, model.sciezka_wyniku(M, nazwa, a.wyjscie), pdf=True):
            print("zapisano", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
