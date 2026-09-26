"""Rzut roboczy lokalu z pelnym wymiarowaniem: arkusz A-01 (SVG, PNG, PDF).

    python rysunki/rzut.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/rzut.py przyklad/mieszkanie/model/lokal_projekt.json --bez-mebli --wyjscie robocze/

Rysuje sciany (nosne ciemniej), otwory z lukami, szachty, grzejniki, meble, numery
i pola pomieszczen, wymiar kazdego lica z podzialem na oscieza, grubosci scian,
lancuchy zewnetrzne, strzalke polnocy i podzialke. Kadr i skala wynikaja z obrysu
lokalu, nic nie jest wpisane na sztywno. Wymiary scian z niepewnych zrodel maja "≈".
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import svg, arkusz
from lokal import model, geometria, plan
from zamierzenie import model as zmodel

MARGINES_CM = 110  # miejsce na lancuchy zewnetrzne


def widok(M, pole=arkusz.POLE):
    x0, y0, x1, y1 = geometria.obrys(M).bounds
    zakres = (x0 - MARGINES_CM, y0 - MARGINES_CM, x1 + MARGINES_CM, y1 + MARGINES_CM)
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    return arkusz.Widok(zakres, pole, sk), skala_txt


def rysuj_rzut(M, W, meble=True):
    """Tresc rzutu (bez arkusza) — uzywana tez przez galerie i inne rysunki."""
    czesci = [plan.kontekst(W, M), plan.pomieszczenia(W, M), plan.grzejniki(W, M)]
    if meble:
        czesci.append(plan.meble(W, M))
    czesci += [plan.sciany(W, M), plan.szachty(W, M), plan.otwory(W, M, opisy=False), plan.grubosci_scian(W, M),
               plan.wymiary_pomieszczen(W, M), plan.lancuchy_zewnetrzne(W, M), plan.opisy_otworow(W, M),
               plan.etykiety(W, M)]
    return "".join(czesci)


def legenda():
    return [
        (svg.prostokat(0, 3, 24, 13, plan.KOLOR["nosna"], None), "ściana nośna"),
        (svg.prostokat(0, 3, 24, 13, plan.KOLOR["dzialowa"], None), "ściana działowa"),
        (svg.prostokat(0, 3, 24, 13, plan.KOLOR["niska"], None), "balustrada, murek (niepełna wysokość)"),
        (svg.linia(0, 8, 24, 8, plan.KOLOR["okno"], 1.4) + svg.linia(0, 4, 24, 4, plan.KOLOR["okno"], 1),
         "okno"),
        (svg.linia(0, 14, 0, 2, plan.KOLOR["drzwi"], 1.6) + svg.polilinia([(0, 2), (8, 4), (13, 8), (14, 14)],
         plan.KOLOR["drzwi"], 0.7, "3 2"), "drzwi z łukiem otwierania"),
        (svg.prostokat(2, 1, 22, 15, plan.KOLOR["szacht"][0], plan.KOLOR["szacht"][1], 1.1), "szacht instalacyjny"),
        (svg.prostokat(0, 5, 24, 11, plan.KOLOR["grzejnik"][0], plan.KOLOR["grzejnik"][1], 1.1), "grzejnik"),
        (svg.prostokat(0, 2, 24, 14, "none", "#3B5B8C", 1, "5 3"),
         "element powyżej płaszczyzny cięcia (%d cm), np. szafka wisząca" % plan.CIECIE),
        (svg.tekst(12, 12, "≈", 12, "middle", kolor=plan.KOLOR["wymiar"], waga="bold"),
         "wymiar ze źródła o niepełnej dokładności — sprawdzić pomiarem"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    ap.add_argument("--bez-mebli", action="store_true")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj rysunki/plan.py (plan P-01); "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        sys.exit(2)
    W, skala_txt = widok(M)
    x1, y0 = arkusz.POLE[2], arkusz.POLE[1]
    tresc = (rysuj_rzut(M, W, not a.bez_mebli)
             + svg.strzalka_polnocy(x1 - 40, y0 + 40, M.get("meta", {}).get("polnoc", {}).get("azymut_osi_Y_stopnie", 0))
             + svg.podzialka(arkusz.POLE[0] + 10, arkusz.POLE[3] - 20, W.px_na_m))
    uwagi = [
        "Wymiary w centymetrach, w świetle ścian (do lic surowych). Pola pomieszczeń liczone z modelu.",
        "Opisy otworów: szerokość otworu / górna krawędź otworu od podłogi wykończonej.",
        "Rysunek generowany z modelu lokalu — zmiany wprowadza się w modelu, nie na rysunku.",
    ]
    dok = arkusz.arkusz(M, "A-01", "Rzut roboczy", skala_txt, tresc, legenda(), uwagi)
    for p in svg.zapisz(dok, model.sciezka_wyniku(M, "A-01_rzut", a.wyjscie), pdf=True):
        print("zapisano", p)


if __name__ == "__main__":
    main()
