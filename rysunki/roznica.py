"""Roznica dwoch stanow modelu zamierzenia (np. istniejacy -> projekt): arkusz P-02 (SVG, PNG,
PDF) i lista zmian w konsoli.

    python rysunki/roznica.py przyklad/ogrod/model/istniejacy.json przyklad/ogrod/model/projekt.json
    python rysunki/roznica.py istniejacy.json koncepcja_A.json --numer P-02 --wyjscie robocze/

Obiekty porownane po id (zamierzenie/stany.py): usuniete - przerywany obrys, punkt przekreslony;
nowe - pogrubione; zmienione - obrys i kreskowanie; bez zmian - szare. Pod planem lista zmian
z kategoria, atrybutami z legendy i polem albo dlugoscia (najwyzej 40 pozycji na sekcje, reszta jako
"...i N dalszych" - pelna lista w konsoli i w Z-01). Dzialka, sasiedztwo, tabliczka i nazwa
pliku pochodza z drugiego modelu (projektu). W ogrodzie to wycinka i nasadzenia; roznice scian
modulu wnetrz pokazuje rysunki/wyburzenia.py. Model lokalu: komunikat i kod 2.
Wynik: <id projektu>_<numer>_roznica.
"""
import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon

from wspolne import arkusz, svg, wzory
from zamierzenie import model, rysuj, stany

SEKCJE = (("usuniete", "Usunięte", "USUNIETE"), ("nowe", "Nowe", "NOWE"), ("zmienione", "Zmienione", "ZMIENIONE"),
          ("bez_zmian", "Bez zmian", "BEZ ZMIAN"))
POLA_ZMIANY = {"ksztalt": "kształt", "kategoria": "kategoria", "z": "z", "wys": "wysokość", "srednica": "średnica",
               "dach": "dach", "poziom": "poziom", "na_terenie": "na terenie", "atrybuty": "atrybuty"}
LIMIT_LISTY = 40   # pozycji sekcji na arkuszu; pelna lista w konsoli i w zestawieniu Z-01


def opis_obiektu(M, o):
    """"D3 — drzewo: brzoza brodawkowata, obwod_cm 95" albo z polem / dlugoscia."""
    st = model.styl(M, o.get("kategoria"))
    at = o.get("atrybuty") or {}
    cechy = [str(at[k]) if isinstance(at[k], str) else "%s %s" % (k, svg.fmt(at[k], 2)) for k in st["zestawienie"] if k in at]
    g = model.ksztalt(o)
    ilosc = "%s m²" % rysuj.liczba(g.area / 1e4) if g.geom_type == "Polygon" else \
        "%s m" % rysuj.metry(g.length) if g.geom_type == "LineString" else ""
    t = "%s — %s" % (o["id"], st["nazwa"])
    if cechy:
        t += ": " + ", ".join(cechy)
    return t + (", " + ilosc if ilosc else "")


def lista_zmian(M_a, M_b, r, limit=LIMIT_LISTY):
    """[(tytul sekcji, tekst, kolor)] do listy pod planem; w sekcji najwyzej limit pozycji i dopisek o dalszych."""
    wynik = []
    for klucz, nazwa, _ in SEKCJE:
        el = r[klucz]
        if klucz == "usuniete":
            teksty = [opis_obiektu(M_a, o) for o in el]
        elif klucz == "zmienione":
            teksty = ["%s (%s)" % (opis_obiektu(M_b, b), ", ".join(POLA_ZMIANY[k] for k in stany.POLA
                                                              if (a.get(k) or None) != (b.get(k) or None))) for a, b in el]
        elif klucz == "nowe":
            teksty = [opis_obiektu(M_b, o) for o in el]
        else:
            teksty = [o["id"] for o in el]
        if len(teksty) > limit:
            n = len(teksty) - limit
            forma = "dalszy" if n == 1 else "dalsze" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "dalszych"
            teksty = teksty[:limit] + ["…i %d %s — pełna lista w konsoli / Z-01" % (n, forma)]
        wynik.append(("%s (%d): " % (nazwa, len(el)), ("; " if klucz != "bez_zmian" else ", ").join(teksty) or "—",
                      rysuj.TRYBY[klucz][2]))
    return wynik


def blok_listy(pozycje, x, y, szer, r=9.5):
    """(svg, wysokosc) listy zmian: tytul sekcji pogrubiony w osobnej linii, pod nim tekst zawijany."""
    s = [svg.tekst(x, y + 12, "ZMIANY", 11, waga="bold")]
    yy = y + 30
    znakow = int((szer - 16) / (r * 0.52))
    for tytul, tekst, kolor in pozycje:
        s.append(svg.tekst(x, yy, tytul.strip().rstrip(":"), r, kolor=kolor, waga="bold"))
        yy += r * 1.4
        for lin in textwrap.wrap(tekst, znakow) or [""]:
            s.append(svg.tekst(x + 16, yy, lin, r, kolor=kolor))
            yy += r * 1.4
        yy += 3
    return "".join(s), yy - y


def legenda_roznicy(M):
    I = lambda x, y: (x, y)
    kw = Polygon([(1, 3), (23, 3), (23, 13), (1, 13)])
    kol_u, kreski_u, _ = rysuj.TRYBY["usuniete"]
    kol_n, kol_z, kol_b = rysuj.TRYBY["nowe"][0], rysuj.TRYBY["zmienione"][0], rysuj.TRYBY["bez_zmian"][0]
    poz = [(wzory.kreski(kw, I, kreski_u, kol_u, 1.2) + wzory.symbol("krzyz", 12, 8, 6, kol_u, 1.2),
            "usunięte (punkt — przekreślony)"),
           (svg.prostokat(1, 3, 23, 13, "#DCE3D5", kol_n, 1.8), "nowe (pogrubione, wypełnienie z legendy)"),
           (wzory.kreskowanie(kw, I, 7.0, 45, kol_z, 0.6) + svg.prostokat(1, 3, 23, 13, "none", kol_z, 1.3),
            "zmienione (obrys i kreskowanie)"),
           (svg.prostokat(1, 3, 23, 13, "#EEEFF1", kol_b, 0.9), "bez zmian")]
    miejsce = M.get("miejsce") or {}
    if miejsce.get("dzialki"):
        kol, gr, kreski = rysuj.DZIALKA
        poz.append((svg.linia(0, 8, 24, 8, kol, gr, kreski), "granica działki"))
    if miejsce.get("sasiedztwo"):
        wyp, obr, kr = rysuj.SASIEDZTWO
        poz.append((svg.prostokat(1, 3, 23, 13, wyp, None) + wzory.kreskowanie(kw, I, 6.0, 45, kr, 0.5)
                    + svg.prostokat(1, 3, 23, 13, "none", obr, 1.0), "obiekt sąsiedni; h — wysokość nad terenem"))
    return poz


def widok(M_a, M_b, pole, margines=300):
    """Kadr obejmujacy oba stany."""
    z = [x for x in (model.zakres(M_a), model.zakres(M_b)) if x]
    x0, y0 = min(a[0] for a in z) if z else 0.0, min(a[1] for a in z) if z else 0.0
    x1, y1 = max(a[2] for a in z) if z else 1000.0, max(a[3] for a in z) if z else 1000.0
    zakres = (x0 - margines, y0 - margines, x1 + margines, y1 + margines)
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    return arkusz.Widok(zakres, pole, sk), skala_txt


def main():
    ap = argparse.ArgumentParser(description="Roznica dwoch stanow modelu zamierzenia (arkusz P-02).")
    ap.add_argument("istniejacy", help="model stanu wyjsciowego (np. istniejacego)")
    ap.add_argument("projekt", help="model stanu porownywanego (np. projektu)")
    ap.add_argument("--numer", default="P-02", help="numer arkusza (domyslnie P-02)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M_a, M_b = model.wczytaj(a.istniejacy), model.wczytaj(a.projekt)
    for M in (M_a, M_b):
        blad = rysuj.komunikat_rodzaju(M, "roznice scian lokalu pokazuje rysunki/wyburzenia.py")
        if blad:
            print("%s: %s" % (Path(M["_sciezka"]).name, blad))
            return 2
    r = stany.roznica(M_a, M_b)
    for k in r:
        r[k].sort(key=lambda o: rysuj.klucz_id(o[1]["id"] if isinstance(o, tuple) else o["id"]))
    pr_a, pr_b = model.projekt(M_a), model.projekt(M_b)
    uwagi = ["Obiekty porównane po id: zmieniony ma inny kształt, kategorię, wysokości, średnicę, dach, poziom, "
             "położenie na terenie albo atrybuty (opis i źródło nie są zmianą).",
             "Stan wyjściowy: %s (%s); stan porównywany: %s (%s). Działka, sąsiedztwo i tabliczka ze stanu porównywanego."
             % (pr_a["faza"], Path(M_a["_sciezka"]).name, pr_b["faza"], Path(M_b["_sciezka"]).name),
             "Rysunek generowany z modeli zamierzenia — zmiany wprowadza się w modelach, nie na rysunku."]
    dol, y_stopki = rysuj.stopka(legenda_roznicy(M_b), uwagi)
    lista, h_listy = blok_listy(lista_zmian(M_a, M_b, r), 50, 0, 1380)
    y_listy = y_stopki - 18 - h_listy
    pole = (arkusz.POLE[0], arkusz.POLE[1], arkusz.POLE[2], min(arkusz.POLE[3], y_listy - 15))
    W, skala_txt = widok(M_a, M_b, pole)
    x0, y0, x1, y1 = pole
    metrow = 5 if W.px_na_m >= 16 else 10
    miejsca = rysuj.miejsca_arkusza(pole, metrow, W.px_na_m)
    rysuj.zajmij_granice(miejsca, W, M_b)
    rys, op = [], []
    # najpierw zmiany (ich opisy maja pierwszenstwo), potem bez zmian; rysunek grupami od powierzchni do punktow
    czesci = {}
    for tryb in ("usuniete", "nowe", "zmienione", "bez_zmian"):
        M = M_a if tryb == "usuniete" else M_b
        el = [o[1] for o in r[tryb]] if tryb == "zmienione" else r[tryb]
        for g in range(5):
            czesci[(tryb, g)] = rysuj.obiekty(W, M, [o for o in el if rysuj.grupa(M, o) == g], tryb, miejsca, czesci=True)
    sas = rysuj.sasiedztwo(W, M_b, True, miejsca, czesci=True)
    dz = rysuj.dzialka(W, M_b, miejsca, czesci=True)
    rys.append(sas[0])
    for g in range(5):
        rys += [czesci[(tryb, g)][0] for tryb in ("bez_zmian", "nowe", "zmienione")]
    rys += [czesci[("usuniete", g)][0] for g in range(5)] + [dz[0]]
    op = [sas[1], dz[1]] + [czesci[k][1] for k in czesci]
    tresc = "".join(rys + op)
    tresc += svg.strzalka_polnocy(x1 - 40, y0 + 40, model.azymut_polnocy(M_b))
    tresc += svg.podzialka(x0 + 10, y1 - 20, W.px_na_m, metrow)
    tresc += rysuj.notka_pominietych(miejsca, pole, metrow, W.px_na_m)
    tresc += '<g transform="translate(0 %.1f)">%s</g>' % (y_listy, lista)
    dok = arkusz.arkusz(M_b, a.numer, "Różnica stanów", skala_txt, tresc + dol, jednostki="pola w m², długości w m")
    for p in svg.zapisz(dok, model.sciezka_wyniku(M_b, "%s_roznica" % a.numer, a.wyjscie), pdf=True):
        print("zapisano", p)
    if miejsca.pominiete:
        print("bez opisu (brak miejsca): %s" % ", ".join(miejsca.pominiete))
    print("ROZNICA %s -> %s" % (pr_a["id"], pr_b["id"]))
    for klucz, _, naglowek in SEKCJE:
        ids = [(o[1] if isinstance(o, tuple) else o)["id"] for o in r[klucz]]
        print("%s (%d): %s" % (naglowek, len(ids), ", ".join(ids) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
