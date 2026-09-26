"""Plan roboczy modelu zamierzenia: arkusz P-01 (SVG, PNG, PDF).

    python rysunki/plan.py przyklad/ogrod/model/projekt.json
    python rysunki/plan.py przyklad/ogrod/model/projekt.json --poziom P0 --bez-warstwic --numer P-04 --wyjscie robocze/

Rysuje dzialke z numerem i polem, sasiedztwo z wysokosciami, warstwice terenu co 25 cm, obiekty
wedlug legendy modelu, moduly wnetrz (sciany i obrysy pomieszczen), wymiary bryl i dachow
z odleglosciami od granic dzialki, rzedne terenu w naroznikach dzialki i bryl, strzalke polnocy,
podzialke, legende kategorii obecnych na arkuszu i uwagi o jednostkach. Wymiary i rzedne
w metrach (rzedne wzgledem +-0), "≈" przy danych niepewnych. --poziom ID rysuje tylko obiekty
i moduly tego poziomu; dzialka, sasiedztwo i warstwice zostaja jako tlo. Kadr i skala wynikaja
z zakresu modelu. Model lokalu: komunikat i kod 2 (rzut lokalu rysuje rysunki/rzut.py).
Wynik: <id>_<numer>_plan.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon

from wspolne import arkusz, svg, wzory
from zamierzenie import model, moduly, rysuj, teren

WARSTWICE_CO = 25   # cm


def punkty_rzednych(M, lista):
    """Narozniki dzialek i bryl z kierunkiem opisu na zewnatrz (od srodka dzialki albo bryly)."""
    wynik = []
    wielokaty = [Polygon(d["granica"]) for d in (M.get("miejsce") or {}).get("dzialki") or []]
    wielokaty += [model.ksztalt(o) for o in lista if rysuj.grupa(M, o) == 1 and model.ksztalt(o).geom_type == "Polygon"]
    for g in wielokaty:
        c = g.centroid
        for x, y in g.exterior.coords[:-1]:
            wynik.append((x, y, (x - c.x, y - c.y)))
    return wynik


def legenda_planu(M, lista, mods, warstwice, rzedne, wymiary=True, niepewne=True):
    """Pozycje legendy; wymiar (z odlegloscia od granicy, gdy jest dzialka) i "≈" tylko, gdy sa na arkuszu."""
    kategorie = {o.get("kategoria") for o in lista} | ({"_sciana", "_pomieszczenie"} if mods else set())
    poz = rysuj.legenda(M, kategorie)
    miejsce = M.get("miejsce") or {}
    kol, gr, kreski = rysuj.DZIALKA
    if miejsce.get("dzialki"):
        poz.append((svg.linia(0, 8, 24, 8, kol, gr, kreski), "granica działki (numer, pole)"))
    if miejsce.get("sasiedztwo"):
        wyp, obr, kr = rysuj.SASIEDZTWO
        g = Polygon([(1, 3), (23, 3), (23, 13), (1, 13)])
        poz.append((svg.prostokat(1, 3, 23, 13, wyp, None) + wzory.kreskowanie(g, lambda x, y: (x, y), 6.0, 45, kr, 0.5)
                    + svg.prostokat(1, 3, 23, 13, "none", obr, 1.0), "obiekt sąsiedni; h — wysokość nad terenem"))
    if warstwice:
        poz.append((svg.polilinia([(0, 11), (8, 8), (16, 7), (24, 4)], rysuj.KOLOR_WARSTWIC, 0.8),
                    "warstwica co %s m z rzędną (co 1 m grubsza)" % rysuj.metry(WARSTWICE_CO)))
    if rzedne:
        poz.append((wzory.symbol("krzyz", 12, 8, 3.4, "#222222", 0.9), "rzędna terenu"))
    if wymiary:
        poz.append((svg.linia(0, 12, 24, 12, rysuj.KOLOR_WYMIARU, 0.7) + svg.linia(-1, 15, 3, 9, rysuj.KOLOR_WYMIARU, 0.9)
                    + svg.linia(21, 15, 25, 9, rysuj.KOLOR_WYMIARU, 0.9) + svg.tekst(12, 9, "4,25", 7, "middle", kolor=rysuj.KOLOR_WYMIARU),
                    "wymiar, odległość od granicy działki [m]" if miejsce.get("dzialki") else "wymiar [m]"))
    if niepewne:
        poz.append((svg.tekst(12, 12, "≈", 12, "middle", kolor=rysuj.KOLOR_WYMIARU, waga="bold"),
                    "wartość ze źródła o niepełnej dokładności — sprawdzić pomiarem"))
    return poz


def main():
    ap = argparse.ArgumentParser(description="Plan roboczy modelu zamierzenia (arkusz P-01).")
    ap.add_argument("model")
    ap.add_argument("--poziom", help="tylko obiekty i moduly tego poziomu (id z sekcji poziomy)")
    ap.add_argument("--bez-warstwic", action="store_true", help="bez warstwic terenu")
    ap.add_argument("--numer", default="P-01", help="numer arkusza (domyslnie P-01)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    blad = rysuj.komunikat_rodzaju(M, "rzut lokalu rysuje rysunki/rzut.py")
    if blad:
        print(blad)
        return 2
    lista, mods, tytul = model.obiekty(M), moduly.moduly(M), "Plan roboczy"
    if a.poziom:
        try:
            poz = model.poziom(M, a.poziom)
        except KeyError:
            print("Nieznany poziom %s (poziomy: %s)." % (a.poziom, ", ".join(x["id"] for x in model.poziomy(M)) or "brak"))
            return 1
        lista = [o for o in lista if o.get("poziom") == a.poziom]
        mods = [m for m in mods if m.get("poziom") == a.poziom]
        tytul += ", poziom %s%s (%s)" % (a.poziom, " — " + poz["nazwa"] if poz.get("nazwa") else "", rysuj.rzedna_txt(poz.get("z", 0)))
    teren_jest = teren.siatka(M) is not None
    warstwice = teren_jest and not a.bez_warstwic
    # co faktycznie bedzie na arkuszu: wymiary bryl i dachow (i odleglosci od granic przy dzialce), dane niepewne ("≈")
    miejsce = M.get("miejsce") or {}
    bryly = [o for o in lista if rysuj.grupa(M, o) in (1, 2) and model.ksztalt(o).geom_type == "Polygon"]
    pkt_rzednych = punkty_rzednych(M, lista) if teren_jest else []
    niepewne = (model.niepewny(miejsce.get("teren") or {}) and (warstwice or bool(pkt_rzednych))) \
        or any(s.get("wys") is not None and model.niepewny(s) for s in miejsce.get("sasiedztwo") or []) \
        or any(model.niepewny(o) for o in bryly) or bool(bryly) and any(model.niepewny(d) for d in miejsce.get("dzialki") or [])
    uwagi = ["Wymiary i odległości w metrach; rzędne w metrach względem ±0 projektu. Przy bryłach i dachach "
             "rzędne dołu i góry (dach: okap … kalenica).",
             "Rysunek generowany z modelu zamierzenia — zmiany wprowadza się w modelu, nie na rysunku."]
    if bryly and miejsce.get("dzialki"):
        uwagi.insert(1, "Odległości od granic działki mierzone od obrysu brył (bez okapu), prostopadle do boku działki.")
    if not teren_jest:
        uwagi.insert(1, "Model bez punktów terenu (teren płaski na ±0): bez warstwic i rzędnych terenu.")
    if a.poziom:
        uwagi.insert(1, "Tylko obiekty i moduły poziomu %s; działka, sąsiedztwo i teren jako tło." % a.poziom)
    dol, y_stopki = rysuj.stopka(legenda_planu(M, lista, mods, warstwice, teren_jest, bool(bryly), niepewne), uwagi)
    pole = (arkusz.POLE[0], arkusz.POLE[1], arkusz.POLE[2], min(arkusz.POLE[3], y_stopki - 25))
    W, skala_txt = rysuj.widok(M, pole)
    x0, y0, x1, y1 = pole
    metrow = 5 if W.px_na_m >= 16 else 10
    miejsca = rysuj.miejsca_arkusza(pole, metrow, W.px_na_m)
    rysuj.zajmij_granice(miejsca, W, M)
    # opisy rozmieszczane od najwazniejszych: wymiary, rzedne, obiekty, moduly, sasiedztwo, dzialka, warstwice
    wym = rysuj.wymiary(W, M, lista, miejsca, czesci=True, przeszkody=[moduly.obrys_modulu(M, m) for m in mods])
    rz = rysuj.rzedne(W, M, pkt_rzednych, miejsca, czesci=True) if teren_jest else ("", "")
    reszta = rysuj.obiekty(W, M, [o for o in lista if rysuj.grupa(M, o) > 0], miejsca=miejsca, czesci=True)
    pow_ = rysuj.obiekty(W, M, [o for o in lista if rysuj.grupa(M, o) == 0], miejsca=miejsca, czesci=True)
    mod = rysuj.moduly(W, M, miejsca, czesci=True, lista=mods)
    sas = rysuj.sasiedztwo(W, M, True, miejsca, czesci=True)
    dz = rysuj.dzialka(W, M, miejsca, czesci=True)
    war = rysuj.warstwice(W, M, WARSTWICE_CO, miejsca, czesci=True) if warstwice else ("", "")
    tresc = "".join(c[0] for c in (sas, pow_, war, reszta, mod, dz, wym, rz))
    tresc += "".join(c[1] for c in (war, sas, pow_, reszta, mod, dz, rz, wym))
    tresc += svg.strzalka_polnocy(x1 - 40, y0 + 40, model.azymut_polnocy(M))
    tresc += svg.podzialka(x0 + 10, y1 - 20, W.px_na_m, metrow)
    tresc += rysuj.notka_pominietych(miejsca, pole, metrow, W.px_na_m)
    dok = arkusz.arkusz(M, a.numer, tytul, skala_txt, tresc + dol, jednostki="wymiary i rzędne w m, rzędne względem ±0")
    for p in svg.zapisz(dok, model.sciezka_wyniku(M, "%s_plan" % a.numer, a.wyjscie), pdf=True):
        print("zapisano", p)
    if miejsca.pominiete:
        print("bez opisu (brak miejsca): %s" % ", ".join(miejsca.pominiete))
    return 0


if __name__ == "__main__":
    sys.exit(main())
