"""Cienie obiektow modelu zamierzenia: arkusz P-03 (SVG, PNG, PDF) - siatka malych planow, wiersze
to daty, kolumny godziny.

    python rysunki/cienie.py przyklad/ogrod/model/projekt.json
    python rysunki/cienie.py przyklad/ogrod/model/projekt.json --daty 03-21,06-21,09-21,12-21 --godziny 8,10:30,13,16 --rok 2027 --numer P-04

Polozenie slonca z wspolne/slonce.py (na_utc, pozycja, wektor_modelu) dla lokalizacji modelu
(meta.lokalizacja; bez niej srodek Polski), czasu lokalnego jej strefy (z czasem letnim) i azymutu
osi +Y z meta.polnoc; rok domyslnie biezacy (--rok). Cien siatki 3D z zamierzenie/bryly.py (bryly,
dachy, rosliny, ogrodzenia i inne linie z wysokoscia, sasiedztwo; bez terenu, plaskich powierzchni
i modulow wnetrz, ktore leza w bryle budynku) to rzut wzdluz kierunku slonca na pozioma
plaszczyzne terenu w srodku podstawy: czesc wypukla (pien, korona, dom, dach) - otoczka wypukla
rzutu wierzcholkow na plaszczyzne terenu w srodku jej podstawy; czesc niewypukla (np. ogrodzenie
drapowane po terenie) - unia rzutow trojkatow, kazdy na plaszczyzne terenu w srodku swojej
podstawy. Uproszczenia: teren w obrebie cienia plaski, bez cieni na scianach i dachach. Na kazdym
malym planie: obiekty szare, cienie, granica dzialki i kierunek slonca; slonce pod horyzontem
(wysokosc <= 0) - opis zamiast cieni. Model lokalu: komunikat i kod 2. Wynik: <id>_<numer>_cienie.
"""
import argparse
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import shapely
from shapely.geometry import MultiPoint, Polygon, box
from shapely.ops import unary_union

from wspolne import arkusz, slonce, svg, wzory
from wspolne.opisy import rect_tekstu
from zamierzenie import bryly, model, rysuj, teren

CIEN = ("#3E526B", 0.42)          # kolor i krycie cienia
SLONCE = "#D08A1E"
ODSTEP_X, ODSTEP_Y, PODPIS = 16, 14, 28   # odstepy malych planow i wysokosc podpisu


def slonce_modelu(M, chwila):
    """(azymut, wysokosc, wektor do slonca w ukladzie modelu) dla chwili "RRRR-MM-DDTHH:MM" czasu
    lokalnego strefy z lokalizacji modelu."""
    lok = model.lokalizacja(M)
    az, wys = slonce.pozycja(slonce.na_utc(chwila, lok["strefa"]), lok["lat"], lok["lon"])
    return az, wys, slonce.wektor_modelu(az, wys, model.azymut_polnocy(M))


def cien(siatka, wektor, s=None):
    """Cien siatki (shapely, uklad modelu) przy kierunku do slonca wektor; None, gdy slonce jest pod
    horyzontem. Czesc wypukla - otoczka wypukla rzutu wierzcholkow na plaszczyzne terenu w srodku jej
    podstawy (srodek obrysu w rzucie); czesc niewypukla - unia rzutow trojkatow, kazdy na plaszczyzne
    terenu w srodku swojej podstawy. Wierzcholek pod plaszczyzna zostaje na miejscu. s = teren.siatka."""
    vx, vy, vz = wektor
    if vz <= 1e-9 or len(siatka.faces) == 0:
        return None
    kierunek = np.array([vx, vy]) / vz
    wynik = []
    for m in (siatka.split(only_watertight=False) if siatka.body_count > 1 else [siatka]):
        V = np.asarray(m.vertices)
        if m.is_convex:
            (x0, y0), (x1, y1) = V[:, :2].min(axis=0), V[:, :2].max(axis=0)
            zt = teren.rzedna(s, (x0 + x1) / 2, (y0 + y1) / 2)
            xy = V[:, :2] - np.outer(np.maximum(V[:, 2] - zt, 0), kierunek)
            wynik.append(MultiPoint(xy).convex_hull)
        else:
            T = V[m.faces]
            zt = np.array([teren.rzedna(s, x, y) for x, y in T[:, :, :2].mean(axis=1)])
            xy = T[:, :, :2] - np.maximum(T[:, :, 2] - zt[:, None], 0)[:, :, None] * kierunek
            tr = shapely.polygons(xy)
            wynik.append(shapely.union_all(tr[shapely.area(tr) > 1e-6], grid_size=0.01))
    g = unary_union(wynik)
    return g if not g.is_empty else None


def cienie(M, wektor, siatki=None):
    """{nazwa siatki: cien} dla siatek z bryly.siatki bez terenu, plaskich powierzchni (rysuj.plaskie)
    i siatek modulow wnetrz (wyglad (hex, alfa, szorstkosc) - leza w bryle budynku); {} przy sloncu
    pod horyzontem."""
    if wektor[2] <= 1e-9:
        return {}
    siatki = bryly.siatki(M) if siatki is None else siatki
    plaskie = rysuj.plaskie(M)
    s = teren.siatka(M)
    wynik = {}
    for nazwa, m, wyglad in siatki:
        if nazwa == "teren" or nazwa in plaskie or isinstance(wyglad, tuple):
            continue
        g = cien(m, wektor, s)
        if g is not None:
            wynik[nazwa] = g
    return wynik


def _kierunek_slonca(X, Y, v):
    """Znak slonca: kolko, slonce na obwodzie w kierunku (w rzucie) do slonca i strzalka biegu swiatla."""
    h = math.hypot(v[0], v[1]) or 1.0
    dx, dy = v[0] / h, -v[1] / h
    s = [svg.okrag(X, Y, 12, "#FFFFFF", "#AAAAAA", 0.6)]
    sx, sy, kx, ky = X + dx * 12, Y + dy * 12, X - dx * 9, Y - dy * 9
    s.append(svg.linia(sx, sy, kx, ky, "#555555", 0.9))
    s.append(svg.polilinia([(kx, ky), (kx + dx * 5 - dy * 2.5, ky + dy * 5 + dx * 2.5), (kx + dx * 5 + dy * 2.5, ky + dy * 5 - dx * 2.5)],
                           "#555555", 0.6, wyp="#555555", zamknij=True))
    s.append(svg.okrag(sx, sy, 3.2, SLONCE, "#8A5A10", 0.6))
    return "".join(s)


def maly_plan(M, W, ramka, siatki, v, wys):
    """Maly plan w ramce (X0, Y0, X1, Y1) arkusza: powierzchnie, cienie (przyciete do ramki),
    obiekty, sasiedztwo i dzialka szare, znak slonca albo opis o sloncu pod horyzontem."""
    X0, Y0, X1, Y1 = ramka
    zx0, zy0, zx1, zy1 = W.zakres
    okno = box(zx0 - (W.X0 - X0) / W.sk, zy1 - (Y1 - W.Y0) / W.sk, zx0 + (X1 - W.X0) / W.sk, zy1 + (W.Y0 - Y0) / W.sk)
    lista = model.obiekty(M)
    s = [svg.prostokat(X0, Y0, X1, Y1, "#FFFFFF", "#BBBBBB", 0.6),
         rysuj.obiekty(W, M, [o for o in lista if rysuj.grupa(M, o) == 0], "bez_zmian", opisy=False)]
    if wys > 0:
        g = unary_union(list(cienie(M, v, siatki).values()))
        if not g.is_empty:
            s.append(svg.sciezka(g.intersection(okno), W.p, CIEN[0], None, przezr=CIEN[1]))
    s += [rysuj.sasiedztwo(W, M, opisy=False), rysuj.obiekty(W, M, [o for o in lista if rysuj.grupa(M, o) > 0], "bez_zmian", opisy=False),
          rysuj.moduly(W, M, czesci=True)[0], rysuj.dzialka(W, M, czesci=True)[0]]
    if wys > 0:
        s.append(_kierunek_slonca(X1 - 20, Y0 + 20, v))
    else:
        linie = [("słońce pod horyzontem", 10)]
        r = rect_tekstu((X0 + X1) / 2, (Y0 + Y1) / 2, linie)
        s.append(svg.prostokat(r[0] - 6, r[1] - 4, r[2] + 6, r[3] + 4, "#FFFFFF", "#888888", 0.6)
                 + svg.tekst((X0 + X1) / 2, r[3] - 3.5, linie[0][0], 10, "middle", kolor="#333333", waga="bold"))
    return "".join(s)


def legenda_cieni(M):
    I = lambda x, y: (x, y)
    kw = Polygon([(1, 3), (23, 3), (23, 13), (1, 13)])
    poz = [(svg.prostokat(1, 3, 23, 13, CIEN[0], None, przezr=CIEN[1]), "cień rzucony na teren"),
           (svg.prostokat(1, 3, 23, 13, "#EEEFF1", rysuj.TRYBY["bez_zmian"][0], 0.9), "obiekty modelu (bez opisów, pełny opis — plan P-01)")]
    if (M.get("miejsce") or {}).get("sasiedztwo"):
        wyp, obr, kr = rysuj.SASIEDZTWO
        poz.append((svg.prostokat(1, 3, 23, 13, wyp, None) + wzory.kreskowanie(kw, I, 6.0, 45, kr, 0.5)
                    + svg.prostokat(1, 3, 23, 13, "none", obr, 1.0), "obiekt sąsiedni"))
    if (M.get("miejsce") or {}).get("dzialki"):
        kol, gr, kreski = rysuj.DZIALKA
        poz.append((svg.linia(0, 8, 24, 8, kol, gr, kreski), "granica działki"))
    poz.append(('<g transform="translate(12 8) scale(0.55) translate(-12 -8)">%s</g>' % _kierunek_slonca(12, 8, (0.7, 0.5, 0.5)),
                "słońce w rzucie (kierunek do słońca) i bieg promieni"))
    return poz


def daty_i_godziny(daty, godziny, rok):
    """([(etykieta, "MM-DD")], [(etykieta, "HH:MM")]); ValueError przy blednej dacie albo godzinie."""
    d, g = [], []
    for t in [x.strip() for x in daty.split(",") if x.strip()]:
        mm, dd = (int(v) for v in t.split("-"))
        date(rok, mm, dd)                      # ValueError przy dacie spoza kalendarza
        d.append(("%02d.%02d" % (dd, mm), "%02d-%02d" % (mm, dd)))
    for t in [x.strip() for x in godziny.split(",") if x.strip()]:
        hh, _, mi = t.partition(":")
        hh, mi = int(hh), int(mi or 0)
        if not (0 <= hh <= 23 and 0 <= mi <= 59):
            raise ValueError(t)
        g.append(("%d:%02d" % (hh, mi), "%02d:%02d" % (hh, mi)))
    if not d or not g:
        raise ValueError("pusta lista")
    return d, g


def arkusz_cieni(M, daty, godziny, rok, numer, siatki=None):
    """Dokument SVG arkusza cieni i lista [(chwila, azymut, wysokosc)]."""
    siatki = bryly.siatki(M) if siatki is None else siatki
    lok = model.lokalizacja(M)
    zrodlo = "meta.lokalizacja" if (M.get("meta") or {}).get("lokalizacja") else "domyślnie środek Polski — uzupełnij meta.lokalizacja"
    uwagi = ["Położenie słońca dla %s° N, %s° E (%s), rok %d, czas lokalny strefy %s (z czasem letnim); azymut i wysokość "
             "słońca według wzorów SunCalc (dokładność ok. 0,1°)." % (svg.fmt(lok["lat"], 2), svg.fmt(lok["lon"], 2), zrodlo, rok,
                                                                      lok["strefa"]),
             "Cień to rzut bryły 3D modelu wzdłuż promieni słońca na poziomą płaszczyznę terenu na rzędnej w środku podstawy "
             "(ogrodzenia i inne bryły niewypukłe — każdy trójkąt osobno). Uproszczenie: teren w obrębie cienia płaski, "
             "bez cieni na ścianach i dachach.",
             "Bez cieni: teren i powierzchnie bez wysokości (trawnik, nawierzchnia…); drzewa jako pień i elipsoida korony.",
             "Rysunek generowany z modelu zamierzenia — zmiany wprowadza się w modelu, nie na rysunku."]
    dol, y_stopki = rysuj.stopka(legenda_cieni(M), uwagi)
    x0, y0, x1 = arkusz.POLE[0], arkusz.POLE[1], arkusz.POLE[2]
    y1 = min(arkusz.POLE[3], y_stopki - 25) - 34            # pod siatka podzialka
    nw, nk = len(daty), len(godziny)
    szer = (x1 - x0 - (nk - 1) * ODSTEP_X) / nk
    wys = (y1 - y0 - nw * PODPIS - (nw - 1) * ODSTEP_Y) / nw
    zx0, zy0, zx1, zy1 = model.zakres(M) or (0.0, 0.0, 1000.0, 1000.0)
    zakres = (zx0 - 50, zy0 - 50, zx1 + 50, zy1 + 50)
    sk, skala_txt = arkusz.skala_arkusza(zakres, (0, 0, szer, wys))
    tresc, wyniki = [], []
    for i, (d_txt, d) in enumerate(daty):
        for j, (g_txt, g) in enumerate(godziny):
            X0 = x0 + j * (szer + ODSTEP_X)
            Y0 = y0 + i * (wys + PODPIS + ODSTEP_Y) + PODPIS
            chwila = "%d-%sT%s" % (rok, d, g)
            az, h, v = slonce_modelu(M, chwila)
            wyniki.append((chwila, az, h))
            W = arkusz.Widok(zakres, (X0, Y0, X0 + szer, Y0 + wys), sk)
            tresc.append(svg.tekst(X0, Y0 - 15, "%s, %s" % (d_txt, g_txt), 10.5, kolor="#222222", waga="bold"))
            tresc.append(svg.tekst(X0, Y0 - 4, "słońce: azymut %s°, wysokość %s°" % (svg.fmt(az, 0), svg.fmt(h, 0)) if h > 0 else
                                   "słońce pod horyzontem (wysokość %s°)" % svg.fmt(h, 0).replace("-", "−"), 8, kolor="#555555"))
            tresc.append(maly_plan(M, W, (X0, Y0, X0 + szer, Y0 + wys), siatki, v, h))
    W = arkusz.Widok(zakres, (x0, y0, x0 + szer, y0 + wys), sk)
    tresc.append(svg.podzialka(x0 + 10, y1 + 22, W.px_na_m, 10 if W.px_na_m < 16 else 5))
    tresc.append(svg.strzalka_polnocy(x1 - 30, 64, model.azymut_polnocy(M), r=18))
    tytul = "Cienie"
    dok = arkusz.arkusz(M, numer, tytul, skala_txt, "".join(tresc) + dol, jednostki="czas lokalny, strefa %s" % lok["strefa"])
    return dok, wyniki


def main():
    ap = argparse.ArgumentParser(description="Cienie obiektow modelu zamierzenia (arkusz P-03: daty x godziny).")
    ap.add_argument("model")
    ap.add_argument("--daty", default="03-21,06-21,12-21", help="daty MM-DD po przecinku (domyslnie 03-21,06-21,12-21)")
    ap.add_argument("--godziny", default="9,12,15", help="godziny czasu lokalnego HH albo HH:MM (domyslnie 9,12,15)")
    ap.add_argument("--rok", type=int, default=date.today().year, help="rok (domyslnie biezacy)")
    ap.add_argument("--numer", default="P-03", help="numer arkusza (domyslnie P-03)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    blad = rysuj.komunikat_rodzaju(M, "slonce w lokalu pokazuje rysunki/izometria.py")
    if blad:
        print(blad)
        return 2
    try:
        daty, godziny = daty_i_godziny(a.daty, a.godziny, a.rok)
    except ValueError:
        print("Bledne --daty (MM-DD) albo --godziny (HH albo HH:MM): %s / %s" % (a.daty, a.godziny))
        return 1
    dok, wyniki = arkusz_cieni(M, daty, godziny, a.rok, a.numer)
    for chwila, az, h in wyniki:
        print("%s: azymut %s st., wysokosc %s st.%s" % (chwila, svg.fmt(az), svg.fmt(h), " - slonce pod horyzontem" if h <= 0 else ""))
    for p in svg.zapisz(dok, model.sciezka_wyniku(M, "%s_cienie" % a.numer, a.wyjscie), pdf=True):
        print("zapisano", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
