"""Makieta 3D lokalu (GLB) z kolorami z modelu: sciany z otworami, podlogi, sufit,
szachty, grzejniki, meble, okladziny, farba scian per pomieszczenie i szyby.
Model zamierzenia: teren, sasiedztwo, obiekty z legendy i moduly wnetrz (zamierzenie/bryly.py).

    python rysunki/glb.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/glb.py model.json --sufit --wybory V1=1,V3=1
    python rysunki/glb.py przyklad/ogrod/model/projekt.json

Kazdy obiekt ma wlasny material PBR (metalicznosc 0) i nazwe rowna ID z modelu,
wiec plik czyta sie wprost w Blenderze, three.js czy przegladarce glTF. Uklad jest
zgodny z glTF: metry, os Y w gore (model ma Z w gore, stad obrot przy eksporcie),
kolory materialow liniowe (tokeny sRGB sa przeliczane).
Kolory scian, frontow i okladzin uwzgledniaja warianty (--wybory).
Elementy modulu wnetrz maja nazwy "<id modulu>:<nazwa>". Model zamierzenia bez zadnej siatki 3D
(np. jedyny modul bez pliku): komunikat, bez pliku GLB, kod 0.
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import shapely
import trimesh
from trimesh.visual.material import PBRMaterial

from lokal import model, geometria
from zamierzenie import bryly, model as zmodel

CM = 0.01
PODLOGI = {"panele": "#C8A27A", "deska": "#B08A5B", "gres": "#D9D6D0", "płyty tarasowe": "#A9A59E"}
NEUTRALNE = {"sciana": "#EDEBE6", "szacht": "#E6E1E8", "grzejnik": "#F4F4F2", "kontekst": "#DADADA",
             "mebel": "#E9E4DA", "sufit": "#F7F6F3", "szyba": "#DCEBF2"}


def _liniowy(c):
    """Skladowa sRGB (0..1) -> liniowa; glTF czyta baseColorFactor jako wartosc liniowa."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgba(hex_, alfa=1.0):
    h = hex_.lstrip("#")
    return [_liniowy(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)] + [alfa]


def _material(nazwa, hex_, alfa=1.0, szorstkosc=0.8):
    return PBRMaterial(name=nazwa, baseColorFactor=_rgba(hex_, alfa), metallicFactor=0.0,
                       roughnessFactor=szorstkosc, alphaMode="BLEND" if alfa < 1 else "OPAQUE",
                       doubleSided=alfa < 1)


def _prostopadloscian(x0, y0, x1, y1, z0, z1):
    ext = [(x1 - x0) * CM, (y1 - y0) * CM, (z1 - z0) * CM]
    if min(ext) <= 0:
        return None
    m = trimesh.creation.box(extents=ext)
    m.apply_translation([(x0 + x1) / 2 * CM, (y0 + y1) / 2 * CM, (z0 + z1) / 2 * CM])
    return m


def _plyta(wielokat, z0, z1):
    """Wielokat wyciagniety w pionie; triangulacja z shapely (bez dodatkowych silnikow)."""
    wierzcholki, trojkaty, indeks = [], [], {}
    for tr in shapely.constrained_delaunay_triangles(wielokat).geoms:
        pkt = list(tr.exterior.coords)[:3]
        if (pkt[1][0] - pkt[0][0]) * (pkt[2][1] - pkt[0][1]) - (pkt[1][1] - pkt[0][1]) * (pkt[2][0] - pkt[0][0]) < 0:
            pkt = pkt[::-1]
        f = []
        for x, y in pkt:
            k = (round(x, 3), round(y, 3))
            if k not in indeks:
                indeks[k] = len(wierzcholki)
                wierzcholki.append(k)
            f.append(indeks[k])
        trojkaty.append(f)
    m = trimesh.creation.extrude_triangulation(np.array(wierzcholki) * CM, np.array(trojkaty), (z1 - z0) * CM)
    m.apply_translation([0, 0, z0 * CM])
    return m


def _os(lico):
    """0, gdy lico biegnie wzdluz osi X, 1 gdy wzdluz Y."""
    return 0 if abs(lico["b"][0] - lico["a"][0]) >= abs(lico["b"][1] - lico["a"][1]) else 1


def _lico_panel(lico, a0, a1, z0, z1, odsuniecie=0.3, grubosc=0.2):
    """Cienki panel na licu pomieszczenia miedzy a0 i a1 (wspolrzedne wzdluz osi lica)."""
    (ax, ay), (bx, by) = lico["a"], lico["b"]
    nx, ny = lico["normalna"]
    if abs(bx - ax) >= abs(by - ay):
        y = ay + ny * odsuniecie
        return _prostopadloscian(min(a0, a1), min(y, y + ny * grubosc), max(a0, a1), max(y, y + ny * grubosc), z0, z1)
    x = ax + nx * odsuniecie
    return _prostopadloscian(min(x, x + nx * grubosc), min(a0, a1), max(x, x + nx * grubosc), max(a0, a1), z0, z1)


def siatki_lokalu(M, wybory=None, sufit=False):
    """[(nazwa, siatka, hex, alfa, szorstkosc)] - wszystko, z czego scena() sklada makiete
    lokalu; siatki w metrach, os Z w gore (uklad modelu)."""
    wynik = []
    H, RS = model.wysokosc(M), model.rzedna_sufitu(M)
    gora = RS if sufit else H

    def dodaj(mesh, nazwa, hex_, alfa=1.0, szorstkosc=0.8):
        if mesh is not None:
            wynik.append((nazwa, mesh, hex_, alfa, szorstkosc))

    sufit_hex = model.hex_tokenu(M, (M.get("wykonczenie") or {}).get("sufit"), NEUTRALNE["sufit"])
    sciany = {s["id"]: s for s in M["sciany"]}
    for s in M["sciany"]:
        for i, (x0, y0, x1, y1, z0, z1, rodzaj) in enumerate(geometria.kawalki_sciany(M, s)):
            dodaj(_prostopadloscian(x0, y0, x1, y1, z0, z1), "%s_%s_%d" % (s["id"], rodzaj, i), NEUTRALNE["sciana"])
    for o in M.get("otwory", []):
        if o["rodzaj"] in ("okno", "portfenetr"):
            x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
            if geometria.wzdluz_x(sciany[o["sciana"]]["pas"]):
                y0, y1 = (y0 + y1) / 2 - 0.5, (y0 + y1) / 2 + 0.5
            else:
                x0, x1 = (x0 + x1) / 2 - 0.5, (x0 + x1) / 2 + 0.5
            dodaj(_prostopadloscian(x0, y0, x1, y1, o.get("parapet") or 0, o.get("wys_otw", 205)),
                  o["id"] + "_szyba", NEUTRALNE["szyba"], 0.25, 0.05)
    for sz in M.get("szachty", []):
        x0, y0, x1, y1 = geometria.prostokat(sz["box"]).bounds
        dodaj(_prostopadloscian(x0, y0, x1, y1, 0, H), sz["id"], NEUTRALNE["szacht"])
    for g in M.get("grzejniki", []):
        x0, y0, x1, y1 = geometria.prostokat(g["box"]).bounds
        dodaj(_prostopadloscian(x0, y0, x1, y1, *g.get("wys", [15, 75])), g["id"], NEUTRALNE["grzejnik"], szorstkosc=0.4)
    for k in M.get("kontekst", []):
        x0, y0, x1, y1 = geometria.prostokat(k["box"]).bounds
        dodaj(_prostopadloscian(x0, y0, x1, y1, *k.get("wys", [0, H])), k["id"], NEUTRALNE["kontekst"])

    for nr, w in geometria.wielokaty(M).items():
        if w is None:
            continue
        p = model.pomieszczenie(M, nr)
        podloga = p.get("podloga", "")
        hex_podlogi = model.hex_tokenu(M, podloga, PODLOGI.get(podloga, "#CFC8BC"))
        dodaj(_plyta(w, -2, 0), nr + "_podloga", hex_podlogi, szorstkosc=0.6)
        if p.get("zewnetrzne"):
            continue
        if sufit:
            dodaj(_plyta(w, RS, RS + 2), nr + "_sufit", sufit_hex)
        farba = model.kolor(M, ("sciany", nr), wybory)
        if not farba:
            continue
        for j, lico in enumerate(geometria.lica(M, nr)):
            os = _os(lico)
            lo, hi = sorted((lico["a"][os], lico["b"][os]))
            if lico["szacht"]:
                dodaj(_lico_panel(lico, lo, hi, 0, gora), "%s_farba_%d" % (nr, j), farba)
            if not lico["sciana"]:
                continue
            for i, (x0, y0, x1, y1, z0, z1, rodzaj) in enumerate(geometria.kawalki_sciany(M, sciany[lico["sciana"]])):
                k0, k1 = ((x0, x1) if os == 0 else (y0, y1))
                a0, a1 = max(lo, k0), min(hi, k1)
                if a1 - a0 > 0.5:
                    dodaj(_lico_panel(lico, a0, a1, z0, min(z1, gora)), "%s_farba_%d_%d" % (nr, j, i), farba)

    for e in model.elementy(M):
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        z0, z1 = e.get("wys", [0, 75])
        if e.get("ksztalt") == "kolo":
            m = trimesh.creation.cylinder(radius=(x1 - x0) / 2 * CM, height=max(z1 - z0, 1) * CM, sections=32)
            m.apply_translation([(x0 + x1) / 2 * CM, (y0 + y1) / 2 * CM, (z0 + z1) / 2 * CM])
        else:
            m = _prostopadloscian(x0, y0, x1, y1, z0, z1)
        dodaj(m, e["id"], model.kolor(M, ("element", e["id"]), wybory) or NEUTRALNE["mebel"])

    for o in (M.get("wykonczenie") or {}).get("okladziny", []):
        lico = _lico_okladziny(M, o)
        if lico is None:
            print("okladzina %s: nie lezy na licu pomieszczenia %s, pominieta" % (o["id"], o["pomieszczenie"]))
            continue
        os = _os(lico)
        (a, b) = o["odcinek"]
        dodaj(_lico_panel(lico, a[os], b[os], o["z"][0], o["z"][1], odsuniecie=0.5, grubosc=1.0),
              o["id"], model.kolor(M, ("okladzina", o["id"]), wybory), szorstkosc=0.35)
    return wynik


def scena(M, wybory=None, sufit=False):
    """Scena trimesh w ukladzie glTF (metry, Y w gore)."""
    sc = trimesh.Scene()
    for nazwa, mesh, hex_, alfa, szorstkosc in siatki_lokalu(M, wybory, sufit):
        mesh.visual = trimesh.visual.TextureVisuals(material=_material(nazwa, hex_, alfa, szorstkosc))
        sc.add_geometry(mesh, node_name=nazwa, geom_name=nazwa)
    sc.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    return sc


def scena_zamierzenia(M, wybory=None):
    """Scena modelu zamierzenia z bryly.siatki w ukladzie glTF (metry, Y w gore)."""
    sc = trimesh.Scene()
    for nazwa, mesh, wyglad in bryly.siatki(M, wybory):
        mesh.apply_scale(CM)
        mat = _material(nazwa, *wyglad) if isinstance(wyglad, tuple) else _material(nazwa, wyglad)
        mesh.visual = trimesh.visual.TextureVisuals(material=mat)
        sc.add_geometry(mesh, node_name=nazwa, geom_name=nazwa)
    if sc.geometry:     # pusta scena (model bez siatek 3D): trimesh jej nie obraca ani nie eksportuje
        sc.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    return sc


def _lico_okladziny(M, okl):
    """Lico pomieszczenia, na ktorym lezy odcinek okladziny."""
    (ax, ay), (bx, by) = okl["odcinek"]
    for lico in geometria.lica(M, okl["pomieszczenie"]):
        (px, py), (qx, qy) = lico["a"], lico["b"]
        dl = lico["dl"]
        odl = lambda x, y: abs((qx - px) * (y - py) - (qy - py) * (x - px)) / dl
        if odl(ax, ay) < 1 and odl(bx, by) < 1:
            return lico
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--wybory", default="", help="warianty, np. V1=1,V2=0")
    ap.add_argument("--sufit", action="store_true", help="dodaj sufit na rzednej sufitu (model lokalu)")
    ap.add_argument("--wyjscie")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    rodzaj = zmodel.rodzaj_pliku(M)
    if rodzaj is None:
        print("Nie rozpoznano modelu: lokal ma sekcje sciany, zamierzenie meta.rodzaj i obiekty, moduly albo miejsce.")
        return 2
    wybory = model.wybory_z_tekstu(a.wybory)
    sc = scena(M, wybory, a.sufit) if rodzaj == "lokal" else scena_zamierzenia(M, wybory)
    if not sc.geometry:
        print("model bez siatek 3D (teren, obiekty, sasiedztwo, moduly) - makieta GLB nie powstala")
        return 0
    baza = model.sciezka_wyniku(M, "makieta", a.wyjscie)
    sciezka = baza.with_name(baza.name + ".glb")
    sc.export(str(sciezka))
    ponownie = trimesh.load(str(sciezka))
    print("zapisano %s (%.0f kB), obiektow: %d" % (sciezka, sciezka.stat().st_size / 1024, len(ponownie.geometry)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
