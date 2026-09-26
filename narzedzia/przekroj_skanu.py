"""Przekroj poziomy skanu 3D (LiDAR telefonem, fotogrametria, chmura punktow, makieta GLB/OBJ)
na wysokosci --h nad podloga: odcinki scian w metrach, DXF w mm, podglad PNG oraz poziom
podlogi i sufitu, czyli wysokosc pomieszczenia.

    python narzedzia/przekroj_skanu.py skan.obj
    python narzedzia/przekroj_skanu.py skan.glb --h 1.2
    python narzedzia/przekroj_skanu.py chmura.ply --os-pionowa z --skala 0.001
    python narzedzia/sciany_z_rzutu.py wyjscie/skan_odcinki.json wyjscie/skan_pary.json

Os pionowa: auto (glTF: Y; inne formaty: os, wzdluz ktorej plaskie powierzchnie skupiaja sie
na dwoch poziomach, podlodze i suficie) albo --os-pionowa x|y|z. --skala zamienia jednostki
pliku na metry (0.001 dla mm, 0.01 dla cm). Podloga to najnizsza duza powierzchnia zwrocona
w gore, sufit najwieksza zwrocona w dol ponad podloga + 1,8 m; gdy skan nie ma sufitu, liczy
sie gorna krawedz scian. Chmura punktow (PLY bez scianek): pas +-2 cm wokol ciecia, raster
1 cm/px i detektor linii. Wynik w ukladzie pliku, w metrach: x w prawo, y w glab rzutu (przy
osi pionowej Y: y = -z pliku, jak w glTF). Ciecie trafia tez w meble: szafa albo regal daja
pare linii jak sciana; --tylko-pelne zostawia linie powtarzajace sie 8 cm pod sufitem (znikaja
meble i grzejniki, ale tez balustrady). Skan z wnetrza nie widzi lica zewnetrznego, wiec grubosc
scian zewnetrznych wychodzi tylko w osciezach. Skan telefonem ma blad skali rzedu 1-2 %:
sprawdz jeden wymiar z natury.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import shapely
import trimesh
from PIL import Image, ImageDraw
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raster_do_dxf import scal, podziel, zapisz_wyniki, czcionka

# wiersze: (x rzutu, y rzutu, wysokosc) z osi pliku; same obroty, bez odbic
OSIE = {"x": [[0, 1, 0], [0, 0, 1], [1, 0, 0]], "y": [[1, 0, 0], [0, 0, -1], [0, 1, 0]], "z": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}


def wczytaj(sciezka):
    g = trimesh.load(str(sciezka))
    if isinstance(g, trimesh.Scene):
        czesci = g.dump()
        siatki = [c for c in czesci if isinstance(c, trimesh.Trimesh) and len(c.faces)]
        if siatki:
            return trimesh.util.concatenate(siatki)
        pkt = [np.asarray(c.vertices) for c in czesci if hasattr(c, "vertices")]
        return trimesh.PointCloud(np.vstack(pkt)) if pkt else None
    if isinstance(g, trimesh.Trimesh) and not len(g.faces):
        return trimesh.PointCloud(g.vertices)
    return g


def os_auto(sciezka, g):
    """Os pionowa: glTF -> y; inaczej ta, wzdluz ktorej plaskie powierzchnie leza na dwoch poziomach."""
    if sciezka.suffix.lower() in (".glb", ".gltf"):
        return "y", "glTF: os Y w gore"
    siatka = isinstance(g, trimesh.Trimesh)
    wynik = {}
    for nazwa, i in (("x", 0), ("y", 1), ("z", 2)):
        if siatka:
            m = np.abs(g.face_normals[:, i]) > 0.95
            wart, wagi = g.triangles_center[m, i], g.area_faces[m]
        else:
            wart = np.asarray(g.vertices)[:, i]
            wagi = np.ones(len(wart))
        if not len(wart) or wagi.sum() <= 0:
            wynik[nazwa] = 0.0
            continue
        b = np.floor((wart - wart.min()) / 0.02).astype(int)
        h = np.convolve(np.bincount(b, weights=wagi), [1, 1, 1], "same")
        p1 = int(np.argmax(h))
        daleko = np.abs(np.arange(len(h)) - p1) >= 25  # drugi poziom co najmniej 0,5 m dalej
        p2 = h[daleko].max() if daleko.any() else 0.0
        wynik[nazwa] = float((h[p1] + p2) / (3 * wagi.sum()))
    kolejne = sorted(wynik, key=wynik.get, reverse=True)
    opis = "skupienie na dwoch poziomach: " + ", ".join("%s %.2f" % (k, wynik[k]) for k in "xyz")
    if wynik[kolejne[0]] < 1.3 * wynik[kolejne[1]]:
        return "z", opis + " - niejednoznaczne, przyjeto z (podaj --os-pionowa)"
    return kolejne[0], opis


def poziom(z, wagi, prog=0.3, od_gory=False):
    """Najnizszy (albo najwyzszy) poziom z histogramu 1 cm o wadze >= prog * maksimum; (wysokosc, waga)."""
    if not len(z):
        return None, 0.0
    b = np.floor(z / 0.01).astype(int)
    b0 = b.min()
    h = np.convolve(np.bincount(b - b0, weights=wagi), [1, 1, 1], "same")
    kand = np.where(h >= prog * h.max())[0]
    i = kand[-1] if od_gory else kand[0]
    blisko = np.abs(z - (i + b0 + 0.5) * 0.01) <= 0.015
    return float(np.average(z[blisko], weights=wagi[blisko])), float(h[i])


def podloga_sufit_siatki(m):
    n, z, A = m.face_normals[:, 2], m.triangles_center[:, 2], m.area_faces
    gora = n > 0.9
    podloga, a_podl = poziom(z[gora], A[gora])
    if podloga is None:
        sys.exit("brak powierzchni zwroconych w gore - sprawdz --os-pionowa")
    dol = (n < -0.9) & (z > podloga + 1.8)
    if dol.any():
        b = np.floor(z[dol] / 0.01).astype(int)
        h = np.convolve(np.bincount(b - b.min(), weights=A[dol]), [1, 1, 1], "same")
        if h.max() >= 0.3 * a_podl:
            i = int(np.argmax(h)) + b.min()
            blisko = dol & (np.abs(z - (i + 0.5) * 0.01) <= 0.015)
            return podloga, float(np.average(z[blisko], weights=A[blisko])), "powierzchnia sufitu"
    # brak sufitu w skanie: tam, gdzie konczy sie najwiecej scian (spadek dlugosci przekroju)
    pion = np.abs(n) < 0.3
    zt = m.triangles[pion][:, :, 2]
    z0, z1, a = zt.min(1), zt.max(1), A[pion]
    k0 = np.clip(np.round((z0 - podloga) / 0.01).astype(int), 0, None)
    k1 = np.clip(np.round((z1 - podloga) / 0.01).astype(int), 0, None)
    roz = np.zeros(k1.max() + 3)
    np.add.at(roz, k0, a / np.maximum(z1 - z0, 0.01))
    np.add.at(roz, k1, -a / np.maximum(z1 - z0, 0.01))
    L = np.cumsum(roz)
    spadek = np.zeros_like(L)
    spadek[2:-2] = L[:-4] - L[4:]
    spadek[:180] = 0
    zc = podloga + int(np.argmax(spadek)) * 0.01
    blisko = np.abs(z1 - zc) <= 0.03
    sufit = float(np.median(z1[blisko])) if blisko.any() else zc
    return podloga, sufit, "gorna krawedz scian (w skanie brak sufitu)"


def podloga_sufit_chmury(p):
    z = p[:, 2]
    podloga, a_podl = poziom(z, np.ones(len(z)))
    wyzej = z[z > podloga + 1.8]
    if len(wyzej):
        # sufit: najgestszy poziom ponad podloga + 1,8 m, jesli ma co najmniej 30 % gestosci podlogi
        sufit, a = poziom(wyzej, np.ones(len(wyzej)), prog=1.0)
        if a >= 0.3 * a_podl:
            return podloga, sufit, "gesty poziom punktow (sufit)"
    return podloga, float(np.percentile(z, 99.5)), "gorna granica chmury (sufit nieuchwycony)"


def przekroj_siatki(m, zc, tol):
    seg3 = trimesh.intersections.mesh_plane(m, [0, 0, 1], [0, 0, zc])
    seg2 = np.round(np.asarray(seg3)[:, :, :2], 5)
    seg2 = [s.tolist() for s in seg2 if np.abs(s[0] - s[1]).max() > 1e-6]
    if not seg2:
        return np.zeros((0, 4)), 0.0
    linie = linemerge(MultiLineString(seg2))
    odc, reszty = [], []
    for g in getattr(linie, "geoms", [linie]):
        u = g.simplify(tol)
        reszty.append(shapely.distance(u, shapely.points(np.asarray(g.coords))))
        c = np.asarray(u.coords)
        odc += [[*c[i], *c[i + 1]] for i in range(len(c) - 1)]
    rms = float(np.sqrt(np.mean(np.concatenate(reszty) ** 2)))
    return scal(odc, tol_kat=2.0, tol_odl=tol, przerwa=3 * tol), rms


def przekroj_chmury(p, zc, rozdz=0.01, pas=0.02):
    q = p[np.abs(p[:, 2] - zc) <= pas][:, :2]
    if len(q) < 10:
        return np.zeros((0, 4))
    x0, y0 = q.min(0) - 5 * rozdz
    ij = np.floor((q - [x0, y0]) / rozdz).astype(int)
    W, H = ij.max(0) + 6
    maska = np.zeros((H, W), np.uint8)
    maska[H - 1 - ij[:, 1], ij[:, 0]] = 255
    maska = cv2.morphologyEx(maska, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    linie = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(255 - maska)[0]
    if linie is None:
        return np.zeros((0, 4))
    s = linie.reshape(-1, 4).astype(float)
    xy = np.column_stack([x0 + (s[:, 0] + 0.5) * rozdz, y0 + (H - 0.5 - s[:, 1]) * rozdz,
                          x0 + (s[:, 2] + 0.5) * rozdz, y0 + (H - 0.5 - s[:, 3]) * rozdz])
    seg = scal(xy, tol_kat=2.0, tol_odl=3 * rozdz, przerwa=10 * rozdz)
    # detektor widzi krawedzie sladu w rastrze, nie jego srodek: linia na mediane punktow wokol niej
    for _ in range(2):
        for i, (xa, ya, xb, yb) in enumerate(seg):
            L = np.hypot(xb - xa, yb - ya)
            u = np.array([xb - xa, yb - ya]) / L
            n = np.array([-u[1], u[0]])
            t, o = (q - [xa, ya]) @ u, (q - [xa, ya]) @ n
            m = (t >= 0) & (t <= L) & (np.abs(o) <= 3 * rozdz)
            if m.sum() >= 5:
                seg[i] += np.tile(n * np.median(o[m]), 2)
    return scal(seg, tol_kat=2.0, tol_odl=rozdz, przerwa=10 * rozdz)


def tylko_pelne(seg, gorne, tol, min_dl):
    """Czesci odcinkow, ktore powtarzaja sie w cieciu pod sufitem: sciany pelnej wysokosci."""
    if not len(gorne):
        return np.zeros((0, 4))
    bufor = shapely.unary_union([LineString([(a, b), (c, d)]).buffer(2 * tol, cap_style="flat") for a, b, c, d in gorne])
    wynik = []
    for a, b, c, d in seg:
        czesc = LineString([(a, b), (c, d)]).intersection(bufor)
        for g in getattr(czesc, "geoms", [czesc]):
            if g.geom_type == "LineString" and g.length >= min_dl:
                wynik.append([*g.coords[0], *g.coords[-1]])
    return np.array(wynik).reshape(-1, 4)


def podglad(seg, tytul, sciezka, maks=1600):
    x0, y0 = seg[:, [0, 2]].min() - 0.5, seg[:, [1, 3]].min() - 0.8
    x1, y1 = seg[:, [0, 2]].max() + 0.5, seg[:, [1, 3]].max() + 0.5
    k = maks / max(x1 - x0, y1 - y0)
    im = Image.new("RGB", (int((x1 - x0) * k), int((y1 - y0) * k)), "white")
    d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - x0) * k, (y1 - y) * k)
    for x in np.arange(np.ceil(x0), x1, 1.0):
        d.line([P(x, y0), P(x, y1)], fill=(232, 232, 232))
    for y in np.arange(np.ceil(y0), y1, 1.0):
        d.line([P(x0, y), P(x1, y)], fill=(232, 232, 232))
    for a, b, c, e in seg:
        d.line([P(a, b), P(c, e)], fill=(20, 20, 20), width=max(2, int(k / 150)))
    f = czcionka(max(14, int(im.width / 60)))
    X, Y = P(x0 + 0.2, y0 + 0.35)
    for i in range(5):
        d.rectangle([X + i * k, Y, X + (i + 1) * k, Y + 8], outline=(0, 0, 0), fill=(0, 0, 0) if i % 2 == 0 else (255, 255, 255))
    d.text((X + 5 * k + 8, Y - 6), "5 m (siatka 1 m)", fill=(0, 0, 0), font=f)
    d.text((10, 8), tytul, fill=(0, 0, 0), font=f)
    im.save(sciezka)


def main():
    ap = argparse.ArgumentParser(description="Przekroj poziomy skanu 3D -> odcinki scian, wysokosc pomieszczenia")
    ap.add_argument("plik", help="OBJ, GLB/GLTF, PLY (siatka albo chmura punktow), STL")
    ap.add_argument("--h", type=float, default=1.0, help="wysokosc ciecia nad podloga w m")
    ap.add_argument("--os-pionowa", choices=("auto", "x", "y", "z"), default="auto")
    ap.add_argument("--skala", type=float, default=1.0, help="mnoznik jednostek pliku na metry")
    ap.add_argument("--tol", type=float, default=0.01, help="tolerancja upraszczania i scalania w m")
    ap.add_argument("--min-dl", type=float, default=0.1, help="najkrotszy zachowany odcinek w m")
    ap.add_argument("--tylko-pelne", action="store_true",
                    help="zostaw linie obecne tez 8 cm pod sufitem (sciany; meble, grzejniki i balustrady znikaja)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog pliku>/wyjscie)")
    ap.add_argument("--nazwa", help="przedrostek plikow wynikowych (domyslnie nazwa pliku)")
    a = ap.parse_args()
    sciezka = Path(a.plik)
    if not sciezka.is_file():
        sys.exit("brak pliku %s" % sciezka)
    g = wczytaj(sciezka)
    if g is None or not len(g.vertices):
        sys.exit("w pliku nie ma siatki ani punktow")
    siatka = isinstance(g, trimesh.Trimesh)
    os_, uzasadnienie = (a.os_pionowa, "podana") if a.os_pionowa != "auto" else os_auto(sciezka, g)
    R = np.eye(4)
    R[:3, :3] = np.array(OSIE[os_], float) * a.skala
    g.apply_transform(R)
    print("%s: %d wierzcholkow%s, os pionowa %s (%s)" % (
        sciezka.name, len(g.vertices), ", %d scianek" % len(g.faces) if siatka else " (chmura punktow)", os_, uzasadnienie))
    rozmiar = g.bounds[1] - g.bounds[0]
    if rozmiar.max() > 200:
        print("uwaga: zakres %.0f jednostek - plik moze byc w mm albo cm (--skala 0.001 / 0.01)" % rozmiar.max())

    if siatka:
        podloga, sufit, metoda = podloga_sufit_siatki(g)
        tnij = lambda z: przekroj_siatki(g, z, a.tol)
    else:
        pkt = np.asarray(g.vertices)
        podloga, sufit, metoda = podloga_sufit_chmury(pkt)
        tnij = lambda z: (przekroj_chmury(pkt, z), None)
    seg, rms = tnij(podloga + a.h)
    dokl = max(1.0, round(3 * rms * 100, 1)) if siatka else 2.0
    seg = seg[np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1]) >= a.min_dl]
    if a.tylko_pelne:
        przed = len(seg)
        seg = tylko_pelne(seg, tnij(sufit - 0.08)[0], a.tol, a.min_dl)
        print("tylko pelna wysokosc (drugie ciecie %.2f m): %d -> %d odcinkow" % (sufit - 0.08, przed, len(seg)))
    # sciany_z_rzutu.py paruje 1:1, wiec lico ciagle dzieli sie naprzeciw konca lica przerwanego
    seg = podziel(seg, 0.75, min_dl=0.05)
    seg = seg[np.argsort(-np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1]))]
    wys = sufit - podloga
    print("podloga %.3f m, sufit %.3f m (%s)" % (podloga, sufit, metoda))
    print("wysokosc pomieszczenia: %s m" % ("%.2f" % wys).replace(".", ","))
    if not 1.9 <= wys <= 5.0:
        print("uwaga: nietypowa wysokosc - sprawdz --os-pionowa i --skala")
    print("przekroj na %.2f m nad podloga: %d odcinkow%s" % (
        a.h, len(seg), ", szum %.1f mm" % (rms * 1000) if rms is not None else ""))
    if not len(seg):
        sys.exit("przekroj pusty - zmien --h albo --os-pionowa")

    wyjscie = Path(a.wyjscie) if a.wyjscie else sciezka.parent / "wyjscie"
    baza = wyjscie / (a.nazwa or sciezka.stem)
    meta = {
        "zrodlo": sciezka.name, "rodzaj": "skan 3D / model: %s" % ("siatka" if siatka else "chmura punktow"),
        "data": date.today().isoformat(), "dokladnosc_cm": dokl,
        "dokladnosc_opis": "dopasowanie linii do przekroju; bez bledu skali skanera (LiDAR telefonu: 1-2 % dlugosci)",
        "uklad": "metry; x w prawo, y w glab rzutu (os pionowa %s pliku), 0 jak w pliku" % os_,
        "os_pionowa": os_, "os_pionowa_uzasadnienie": uzasadnienie, "skala": a.skala,
        "podloga_m": round(podloga, 4), "sufit_m": round(sufit, 4), "sufit_metoda": metoda,
        "wysokosc_pomieszczenia_m": round(wys, 3), "ciecie_m": round(podloga + a.h, 4),
        "szum_mm": round(rms * 1000, 2) if rms is not None else None, "odcinkow": len(seg),
        "parametry": {"h_m": a.h, "tol_m": a.tol, "min_dl_m": a.min_dl, "tylko_pelne": a.tylko_pelne},
    }
    x0, y0 = seg[:, [0, 2]].min(), seg[:, [1, 3]].min()
    teksty = [((x0, y0 - 0.4), "wysokość %.2f m, cięcie %.2f m nad podłogą" % (wys, a.h), 120)]
    for p in zapisz_wyniki(baza, seg, meta, "PRZEKROJ", teksty):
        print("zapisano", p)
    podglad(seg, "przekrój na %s m nad podłogą · wysokość pomieszczenia %s m" % (
        ("%.2f" % a.h).replace(".", ","), ("%.2f" % wys).replace(".", ",")), baza.parent / (baza.name + "_podglad.png"))
    print("zapisano", baza.parent / (baza.name + "_podglad.png"))


if __name__ == "__main__":
    main()
