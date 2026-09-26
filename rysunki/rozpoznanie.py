"""Plansza rozpoznania z modelu zamierzenia: arkusz R-01 (SVG, PNG, PDF).

    python rysunki/rozpoznanie.py przyklad/ogrod/model/istniejacy.json
    python rysunki/rozpoznanie.py model/istniejacy.json --orto wyjscie/dzialka_orto.png --uzbrojenie uzbrojenie.png --numer R-02

Dzialka z numerem i polem, sasiedztwo z wysokosciami, warstwice co 25 cm z rzednymi, rzedne terenu
w naroznikach dzialki, obiekty i obrysy modulow cienka szara linia z id (stan z pliku), polnoc,
podzialka, ramka planu miejscowego nad tabliczka (nazwa, symbol, przeznaczenie, parametry,
odnosnik) i miejsce.uwarunkowania jako uwagi. Podklad rastrowy --orto (ortofotomapa, rozjasniona)
i --uzbrojenie (mapa uzbrojenia, na wierzchu) - PNG z plikiem .pgw w EPSG:2180 (np. z
narzedzia/geoportal.py) - tylko przy meta.georef modelu: narozniki rastra przeliczone do ukladu
modelu odwrotnoscia georef (przesuniecie o x0, y0, obrot o -obrot_stopnie, metry na cm), raster
przepisany przez Pillow w pole rysunku (przyciety, bez obrotu) i osadzony w SVG jako
<image href="data:image/png;base64,...">. PyMuPDF rysuje taki obraz w PNG i PDF, ale nie przycina
clipPath i pomija opacity, dlatego przyciecie i rozjasnienie sa w samym rastrze. Bez --orto
i --uzbrojenie arkusz jest wylacznie wektorowy, a georef nic w nim nie zmienia. Model lokalu:
komunikat i kod 2; podklad bez meta.georef (albo bez x0, y0), bez pliku .pgw, w ukladzie innym niz
EPSG:2180 albo poza kadrem rysunku: komunikat i kod 1. Z podkladem sasiedztwo samym obrysem, zeby
nie zaslanialo rastra. Wynik: <id>_<numer>_rozpoznanie.
"""
import argparse
import base64
import io
import math
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Polygon

from wspolne import arkusz, svg, wzory
from zamierzenie import model, moduly, rysuj, teren

WARSTWICE_CO = 25        # cm
SZARY = "#8A8A8A"        # obiekty modelu
ROZJASNIENIE = 0.45      # orto: udzial bieli
PARAMETRY = {"pbc_min_proc": ("powierzchnia biologicznie czynna min.", " %"),
             "zabudowa_max_proc": ("powierzchnia zabudowy maks.", " %"), "wys_max": ("wysokość zabudowy maks.", " m")}


def parametry(par):
    """Linie opisu parametrow planu miejscowego: znane z jednostka (wys_max w cm -> m), reszta "klucz: wartosc"."""
    wynik = []
    for k, v in par.items():
        if k in PARAMETRY and isinstance(v, (int, float)):
            nazwa, jedn = PARAMETRY[k]
            wynik.append("%s %s%s" % (nazwa, rysuj.metry(v) if k == "wys_max" else svg.fmt(v, 2), jedn))
        else:
            wynik.append("%s: %s" % (str(k).replace("_", " "), v))
    return wynik


def ramka_planu(M, x, y, szer=720):
    """(svg, wysokosc): ramka planu miejscowego w stylu tabliczki - naglowek i wiersze nazwa, symbol,
    przeznaczenie, parametry (po jednym w linii), odnosnik; bez danych w modelu - informacja o tym."""
    pm = (M.get("miejsce") or {}).get("plan_miejscowy")
    znakow = int((szer - 150) / 5.2)
    if not pm:
        wiersze = [("", ["brak danych w modelu (miejsce.plan_miejscowy)"])]
    else:
        wiersze = [(et, textwrap.wrap(str(pm[k]), znakow) or [""]) for k, et in
                   (("nazwa", "NAZWA"), ("symbol", "SYMBOL"), ("przeznaczenie", "PRZEZNACZENIE")) if pm.get(k)]
        par = [l for t in parametry(pm.get("parametry") or {}) for l in textwrap.wrap(t, znakow)]
        if par:
            wiersze.append(("PARAMETRY", par))
        if pm.get("odnosnik"):
            wiersze.append(("ODNOŚNIK", textwrap.wrap(str(pm["odnosnik"]), znakow)))
    h_nagl = 22
    wys = [10 + 12 * max(1, len(l)) for _, l in wiersze]
    razem = h_nagl + sum(wys)
    s = [svg.prostokat(x, y, x + szer, y + razem, "#FFFFFF", "#111", 1.6), svg.prostokat(x, y, x + szer, y + h_nagl, "#EDEDED", None),
         svg.linia(x, y + h_nagl, x + szer, y + h_nagl, "#111", 0.8), svg.tekst(x + 10, y + 15, "PLAN MIEJSCOWY", 10, waga="bold")]
    yy = y + h_nagl
    s.append(svg.linia(x + 130, yy, x + 130, y + razem, "#111", 0.8))
    for i, ((etykieta, linie), h) in enumerate(zip(wiersze, wys)):
        if i:
            s.append(svg.linia(x, yy, x + szer, yy, "#111", 0.8))
        s.append(svg.tekst(x + 10, yy + h / 2 + 3.5, etykieta, 9, waga="bold"))
        for j, lin in enumerate(linie):
            s.append(svg.tekst(x + 142, yy + h / 2 + 3.5 + (j - (len(linie) - 1) / 2) * 12, lin, 9.5))
        yy += h
    return "".join(s), razem


def podklad(M, W, pole, png, rozjasnij=0.0):
    """(<image> z rastrem png przepisanym w pole rysunku, opis do konsoli). Raster z plikiem .pgw
    (EPSG:2180): piksel -> uklad 2180 (plik swiata), -> model (odwrotnosc meta.georef: przesuniecie
    o x0, y0, obrot o -obrot_stopnie, m na cm), -> arkusz (Widok W). Pillow przepisuje raster
    przeksztalceniem odwrotnym w prostokat arkusza (czesc pola pokryta rastrem), rozjasnia go
    (rozjasnij - udzial bieli) i zapisuje jako PNG z przezroczystoscia poza rastrem. ValueError
    z opisem, gdy brak meta.georef, pliku .pgw, uklad inny niz EPSG:2180 albo raster poza polem."""
    png = Path(png)
    g = (M.get("meta") or {}).get("georef")
    if not g:
        raise ValueError("Podklad %s pominiety: model bez meta.georef (punkt 0,0 modelu w EPSG:2180 i obrot osi, "
                         "zamierzenie/SCHEMAT.md) - bez niego rastra nie da sie polozyc na rysunku." % png.name)
    if int(g.get("epsg", 2180)) != 2180:
        raise ValueError("Podklad %s: meta.georef w ukladzie EPSG:%s, a plik .pgw musi byc w EPSG:2180." % (png.name, g.get("epsg")))
    pgw = png.with_suffix(".pgw")
    if not png.is_file() or not pgw.is_file():
        raise ValueError("Podklad %s: brak pliku %s." % (png.name, png.name if not png.is_file() else pgw.name))
    try:
        x0, y0, k = float(g["x0"]), float(g["y0"]), math.radians(float(g.get("obrot_stopnie", 0.0)))
    except (KeyError, TypeError, ValueError):
        raise ValueError("Podklad %s: meta.georef musi miec liczby x0 i y0 (punkt 0,0 modelu w EPSG:2180, m) "
                         "i opcjonalnie obrot_stopnie." % png.name)
    try:
        A, D, B, E, C, F = (float(v) for v in pgw.read_text(encoding="utf-8").split()[:6])
        im = Image.open(png).convert("RGBA")
    except (ValueError, OSError):
        raise ValueError("Podklad %s: nieczytelny obraz albo plik %s (6 liczb)." % (png.name, pgw.name))
    if abs(A * E - B * D) < 1e-12:
        raise ValueError("Podklad %s: plik %s bez rozmiaru piksela (macierz osobliwa)." % (png.name, pgw.name))
    # piksel (krawedzie: piksel i to [i, i + 1]) -> EPSG:2180 -> model (cm) -> arkusz, jako macierze 3 x 3
    swiat = np.array([[A, B, C - A / 2 - B / 2], [D, E, F - D / 2 - E / 2], [0, 0, 1]])
    do_modelu = np.array([[100 * math.cos(k), 100 * math.sin(k), 0], [-100 * math.sin(k), 100 * math.cos(k), 0], [0, 0, 1]]) @ \
        np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])
    zx0, _, _, zy1 = W.zakres
    do_arkusza = np.array([[W.sk, 0, W.X0 - zx0 * W.sk], [0, -W.sk, W.Y0 + zy1 * W.sk], [0, 0, 1]])
    H = do_arkusza @ do_modelu @ swiat
    w, h = im.size
    naroza = [H @ [x, y, 1] for x, y in ((0, 0), (w, 0), (w, h), (0, h))]
    X0, Y0 = max(pole[0], min(p[0] for p in naroza)), max(pole[1], min(p[1] for p in naroza))
    X1, Y1 = min(pole[2], max(p[0] for p in naroza)), min(pole[3], max(p[1] for p in naroza))
    if X1 - X0 < 1 or Y1 - Y0 < 1:
        raise ValueError("Podklad %s lezy poza kadrem rysunku - sprawdz meta.georef i plik %s." % (png.name, pgw.name))
    q = min(2.0, max(0.5, math.hypot(*(H[:2, 0]))))     # jednostek arkusza na piksel wyniku ~ piksel rastra
    n, m = int(math.ceil((X1 - X0) / q)), int(math.ceil((Y1 - Y0) / q))
    odwr = np.linalg.inv(H) @ np.array([[q, 0, X0], [0, q, Y0], [0, 0, 1]])
    wynik = im.transform((n, m), Image.Transform.AFFINE, tuple(odwr[:2].ravel()), Image.Resampling.BILINEAR,
                         fillcolor=(255, 255, 255, 0))
    if rozjasnij:
        t = np.asarray(wynik).astype(float)
        t[:, :, :3] = 255 - (255 - t[:, :, :3]) * (1 - rozjasnij)
        wynik = Image.fromarray(np.round(t).astype(np.uint8), "RGBA")
    buf = io.BytesIO()
    wynik.save(buf, "PNG", optimize=True)
    obraz = '<image x="%.2f" y="%.2f" width="%.2f" height="%.2f" preserveAspectRatio="none" href="data:image/png;base64,%s"/>' % (
        X0, Y0, n * q, m * q, base64.b64encode(buf.getvalue()).decode("ascii"))
    return obraz, "podklad %s: %d x %d px po %s m -> %d x %d px w polu rysunku" % (png.name, w, h, svg.fmt(math.hypot(A, D), 3), n, m)


class BladPodkladu(Exception):
    """Podkladu nie da sie osadzic; tresc to komunikat dla uzytkownika (main: kod 1)."""


def obiekty_szare(W, M, miejsca):
    """(rysunek, opisy): obiekty i obrysy modulow wnetrz cienka szara linia bez wypelnien (podklad
    pozostaje widoczny), dach obrysem okapu linia przerywana, punkty symbolem z legendy; id szare
    (punkty bez miejsca pominiete)."""
    rys, op = [], []
    for mod in moduly.moduly(M):
        g = moduly.obrys_modulu(M, mod)
        rys.append(svg.sciezka(g, W.p, "none", SZARY, 1.0))
        X, Y = W.p(*g.representative_point().coords[0])
        linie = [(mod["id"], 7.5)]
        op.append(rysuj.napis(miejsca, [(X, Y)] + rysuj.wokol(X, Y, linie, 4), linie, "#6A6A6A", kotwica=(X, Y)))
    for o in sorted(model.obiekty(M), key=lambda o: (rysuj.grupa(M, o), -(o.get("srednica") or 0))):
        g, gr = model.ksztalt(o), rysuj.grupa(M, o)
        linie = [(o["id"], 7.5)]
        if gr == 2:
            d = rysuj.dach_w_planie(M, o)
            obrys, kalenice, _ = d if d else (g, [], None)
            rys.append(svg.sciezka(obrys, W.p, "none", SZARY, 0.7, rysuj.KRESKI_DACHU))
            rys += [svg.sciezka(LineString([a, b]), W.p, "none", SZARY, 0.6) for a, b in kalenice]
            X, Y = W.p(*g.representative_point().coords[0])
            kand, kotwica, pomin = [(X, Y + 14)] + rysuj.wokol(X, Y, linie, 10), (X, Y), False
        elif g.geom_type == "Point":
            X, Y = W.p(g.x, g.y)
            r = max(3.0, W.d(o["srednica"] / 2)) if o.get("srednica") else 4.0
            rys.append(wzory.symbol(model.styl(M, o.get("kategoria"))["plan"]["symbol"] or "kolo", X, Y, r, SZARY, 0.7))
            kand, kotwica, pomin = [(X + 12, Y - 8), (X - 12, Y - 8)] + rysuj.wokol(X, Y, linie, r + 2), None, True
        else:
            rys.append(svg.sciezka(g, W.p, "none", SZARY, 1.0 if gr == 3 else 0.7))
            X, Y = W.p(*(g.interpolate(0.5, normalized=True) if gr == 3 else g.representative_point()).coords[0])
            kand, kotwica, pomin = ([] if gr == 3 else [(X, Y)]) + rysuj.wokol(X, Y, linie, 4), (X, Y), False
        op.append(rysuj.napis(miejsca, kand, linie, "#6A6A6A", kotwica=kotwica, pomin=pomin))
    return "".join(rys), "".join(op)


def legenda_rozpoznania(M, podklady):
    I = lambda x, y: (x, y)
    kw = Polygon([(1, 3), (23, 3), (23, 13), (1, 13)])
    miejsce = M.get("miejsce") or {}
    poz = []
    if miejsce.get("dzialki"):
        kol, gr, kreski = rysuj.DZIALKA
        poz.append((svg.linia(0, 8, 24, 8, kol, gr, kreski), "granica działki (numer, pole)"))
    if miejsce.get("sasiedztwo"):
        wyp, obr, kr = rysuj.SASIEDZTWO
        symbol = svg.prostokat(1, 3, 23, 13, "none", obr, 1.0) if podklady else \
            svg.prostokat(1, 3, 23, 13, wyp, None) + wzory.kreskowanie(kw, I, 6.0, 45, kr, 0.5) + svg.prostokat(1, 3, 23, 13, "none", obr, 1.0)
        poz.append((symbol, "obiekt sąsiedni; h — wysokość nad terenem"))
    if teren.siatka(M) is not None:
        poz.append((svg.polilinia([(0, 11), (8, 8), (16, 7), (24, 4)], rysuj.KOLOR_WARSTWIC, 0.8),
                    "warstwica co %s m z rzędną (co 1 m grubsza)" % rysuj.metry(WARSTWICE_CO)))
        poz.append((wzory.symbol("krzyz", 12, 8, 3.4, "#222222", 0.9), "rzędna terenu"))
    if model.obiekty(M) or moduly.moduly(M):
        poz.append((svg.prostokat(1, 3, 23, 13, "none", SZARY, 0.7), "obiekt albo moduł wnętrz z modelu (stan w pliku), id"))
    for nazwa, png in podklady:
        symbol = svg.prostokat(1, 3, 23, 13, "#D8D2C4", "#999999", 0.5) if nazwa == "ortofotomapa" else \
            "".join(svg.linia(0, y, 24, y, k, 1.4) for y, k in ((4, "#C0392B"), (8, "#2E6DB4"), (12, "#D4A017")))
        poz.append((symbol, "podkład: %s (%s)" % (nazwa, Path(png).name)))
    poz.append((svg.tekst(12, 12, "≈", 12, "middle", kolor=rysuj.KOLOR_WYMIARU, waga="bold"),
                "wartość ze źródła o niepełnej dokładności — sprawdzić pomiarem"))
    return poz


def rysunek(M, orto=None, uzbrojenie=None, numer="R-01"):
    """(dokument SVG, Widok planu) arkusza rozpoznania; BladPodkladu z opisem, gdy podkladu nie da sie
    osadzic (ValueError z podklad()). Z podkladem sasiedztwo samym obrysem - PyMuPDF pomija opacity,
    wiec wypelnienie zaslonioby raster. W konsoli: opis podkladow i opisy pominiete z braku miejsca."""
    podklady = [(n, p) for n, p in (("ortofotomapa", orto), ("uzbrojenie terenu", uzbrojenie)) if p]
    miejsce = M.get("miejsce") or {}
    teren_jest = teren.siatka(M) is not None
    npm = (M.get("meta") or {}).get("zero_npm_m")
    uwagi = [str(t) for t in miejsce.get("uwarunkowania") or []]
    uwagi.append("Warstwice i rzędne terenu w metrach względem ±0 projektu%s; plan miejscowy i uwarunkowania według modelu "
                 "(miejsce.plan_miejscowy, miejsce.uwarunkowania)." % (" (±0 = %s m n.p.m.)" % svg.fmt(npm, 2) if npm is not None else ""))
    if not teren_jest:
        uwagi.append("Model bez punktów terenu (teren płaski na ±0): bez warstwic i rzędnych terenu.")
    if podklady:
        uwagi.append("Podkład rastrowy położony według pliku .pgw (EPSG:2180) i meta.georef modelu — dokładność taka jak "
                     "georeferencji%s." % ("; ortofotomapa pokazuje dachy przesunięte względem obrysu budynków" if orto else ""))
    uwagi.append("Rysunek generowany z modelu zamierzenia — zmiany wprowadza się w modelu, nie na rysunku.")
    dol, y_stopki = rysuj.stopka(legenda_rozpoznania(M, podklady), uwagi)
    ramka, h_ramki = ramka_planu(M, 0, 0)
    y_ramki = 1800 - 14 - h_ramki
    pole = (arkusz.POLE[0], arkusz.POLE[1], arkusz.POLE[2], min(arkusz.POLE[3], y_stopki - 25, y_ramki - 25))
    W, skala_txt = rysuj.widok(M, pole)
    x0, y0, x1, y1 = pole
    metrow = 5 if W.px_na_m >= 16 else 10
    miejsca = rysuj.miejsca_arkusza(pole, metrow, W.px_na_m)
    rysuj.zajmij_granice(miejsca, W, M)
    obrazy = []
    for i, (nazwa, png) in enumerate(podklady):
        try:
            obraz, opis = podklad(M, W, pole, png, ROZJASNIENIE if i == 0 and orto else 0.0)
        except ValueError as e:
            raise BladPodkladu(str(e)) from None
        obrazy.append(obraz)
        print(opis)
    # opisy od najwazniejszych: rzedne naroznikow dzialek, dzialka, sasiedztwo, obiekty, warstwice
    narozniki = [(x, y, (x - g.centroid.x, y - g.centroid.y))
                 for g in (Polygon(d["granica"]) for d in miejsce.get("dzialki") or []) for x, y in g.exterior.coords[:-1]]
    rz = rysuj.rzedne(W, M, narozniki, miejsca, czesci=True) if teren_jest else ("", "")
    dz = rysuj.dzialka(W, M, miejsca, czesci=True)
    sas = rysuj.sasiedztwo(W, M, True, miejsca, czesci=True)
    if podklady:            # sam obrys (opisy wysokosci bez zmian)
        sas = ("".join(svg.sciezka(Polygon(x["obrys"]), W.p, "none", rysuj.SASIEDZTWO[1], 1.0)
                       for x in miejsce.get("sasiedztwo") or []), sas[1])
    ob = obiekty_szare(W, M, miejsca)
    war = rysuj.warstwice(W, M, WARSTWICE_CO, miejsca, czesci=True) if teren_jest else ("", "")
    tresc = "".join(obrazy) + "".join(c[0] for c in (sas, war, ob, dz, rz)) + "".join(c[1] for c in (war, ob, sas, dz, rz))
    tresc += svg.strzalka_polnocy(x1 - 40, y0 + 40, model.azymut_polnocy(M))
    tresc += svg.podzialka(x0 + 10, y1 - 20, W.px_na_m, metrow)
    tresc += rysuj.notka_pominietych(miejsca, pole, metrow, W.px_na_m)
    tresc += '<g transform="translate(720 %.1f)">%s</g>' % (y_ramki, ramka)
    dok = arkusz.arkusz(M, numer, "Plansza rozpoznania", skala_txt, tresc + dol, jednostki="rzędne w m względem ±0")
    if miejsca.pominiete:
        print("bez opisu (brak miejsca): %s" % ", ".join(miejsca.pominiete))
    return dok, W


def main():
    ap = argparse.ArgumentParser(description="Plansza rozpoznania modelu zamierzenia (arkusz R-01).")
    ap.add_argument("model")
    ap.add_argument("--orto", help="ortofotomapa PNG z plikiem .pgw (EPSG:2180); wymaga meta.georef")
    ap.add_argument("--uzbrojenie", help="mapa uzbrojenia terenu PNG z plikiem .pgw (EPSG:2180); wymaga meta.georef")
    ap.add_argument("--numer", default="R-01", help="numer arkusza (domyslnie R-01)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    blad = rysuj.komunikat_rodzaju(M, "otoczenie lokalu pobiera narzedzia/geoportal.py")
    if blad:
        print(blad)
        return 2
    try:
        dok, _ = rysunek(M, a.orto, a.uzbrojenie, a.numer)
    except BladPodkladu as e:
        print(e)
        return 1
    for p in svg.zapisz(dok, model.sciezka_wyniku(M, "%s_rozpoznanie" % a.numer, a.wyjscie), pdf=True):
        print("zapisano", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
