"""Plan wyburzen i nowych scian: roznica stanu istniejacego i projektowanego, arkusz A-02
(SVG, PNG, PDF).

    python rysunki/wyburzenia.py przyklad/mieszkanie/model/lokal_istniejacy.json przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/wyburzenia.py istniejacy.json projekt.json --wyjscie robocze/

Bryly scian (pasy minus otwory) stanu istniejacego minus projektowanego to rozbiorki
(zolte, kreskowane), projektowanego minus istniejacego to nowe sciany i zamurowania
(czerwone), czesc wspolna jest szara. Liczy sie geometria, nie ID: sciana przesunieta
z tym samym ID to rozbiorka starej i nowa w nowym miejscu. Otwory istniejace, ktore
znikaja, maja przerywany zolty obrys (demontaz stolarki). Etykiety z zmiany[] modelu
projektowanego (xy, opis), pod rysunkiem zestawienie zmian z dlugosciami i orientacyjna
powierzchnia scian, legenda i tabliczka z meta projektu. Wynik: <id>_A-02_wyburzenia.
"""
import argparse
import sys
import textwrap
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import svg, arkusz
from lokal import model, geometria, plan
from zamierzenie import model as zmodel

ZOLTY, ZOLTY_OBR, ZOLTY_TXT = "#F2C94C", "#A8860B", "#7A6207"
CZERWONY, CZERWONY_OBR, CZERWONY_TXT = "#D64545", "#7A1D12", "#7A1D12"
SZARY, SZARY_OBR = "#C9CCD2", "#8A8F96"
POLE_PLANU = (50, 110, 1430, 1480)      # pod planem zestawienie zmian
MARGINES_CM = 70


def czesci(g):
    if g is None or g.is_empty:
        return []
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def czysc(g, min_pole=20.0):
    """Usuwa drzazgi po odejmowaniu (paski wezsze niz ok. 1 cm i skrawki)."""
    g = g.buffer(-0.4, join_style=2).buffer(0.4, join_style=2)
    wynik = [p for p in czesci(g) if p.geom_type == "Polygon" and p.area >= min_pole]
    return unary_union(wynik) if wynik else Polygon()


def bryly(M):
    return unary_union(list(geometria.bryly_scian(M).values()))


def kreskowanie(g, W, krok_px=7.0, kolor=ZOLTY_OBR, gr=0.7):
    """Ukosne kreskowanie wielokata (MuPDF nie obsluguje wzorow SVG, wiec linie sa jawne)."""
    s = []
    krok = krok_px / W.sk
    for p in czesci(g):
        x0, y0, x1, y1 = p.bounds
        c = x0 - y1
        while c < x1 - y0:
            linia = LineString([(x0 - 1, x0 - 1 - c), (x1 + 1, x1 + 1 - c)]).intersection(p)
            for odc in czesci(linia):
                if odc.geom_type == "LineString" and odc.length > 0.1:
                    (ax, ay), (bx, by) = odc.coords[0], odc.coords[-1]
                    s.append(svg.linia(*W.p(ax, ay), *W.p(bx, by), kolor, gr))
            c += krok * 1.4142
    return "".join(s)


def widok(M_i, M_p, pole):
    x0, y0, x1, y1 = unary_union([geometria.obrys(M_i), geometria.obrys(M_p)]).bounds
    zakres = (x0 - MARGINES_CM, y0 - MARGINES_CM, x1 + MARGINES_CM, y1 + MARGINES_CM)
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    return arkusz.Widok(zakres, pole, sk), skala_txt


def opis_otworu(o, M):
    x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
    sc = next(s for s in M["sciany"] if s["id"] == o["sciana"])
    szer = o.get("szer_otw") or ((x1 - x0) if geometria.wzdluz_x(sc["pas"]) else (y1 - y0))
    return "%s %s/%s" % (o["id"], svg.fmt(szer), svg.fmt(o.get("wys_otw", 205)))


def zakres_robot(M_i, M_p):
    """Pasy rozbiorek i nowych scian (z dlugoscia i orientacyjna powierzchnia) oraz zmiany otworow."""
    pasy_i = unary_union([geometria.prostokat(s["pas"]) for s in M_i["sciany"]])
    pasy_p = unary_union([geometria.prostokat(s["pas"]) for s in M_p["sciany"]])

    def sciany(M, inne, rodzaj):
        wynik = []
        for s in M["sciany"]:
            g = czysc(geometria.prostokat(s["pas"]).difference(inne))
            if g.is_empty:
                continue
            x0, y0, x1, y1 = geometria.prostokat(s["pas"]).bounds
            grub = min(x1 - x0, y1 - y0)
            dl = g.area / grub
            z0, z1 = s.get("wys", [0, model.wysokosc(M)])
            pole = dl * (z1 - z0)
            for o in M.get("otwory", []):
                if o["sciana"] == s["id"]:
                    r = geometria.prostokat(geometria.prostokat_otworu(M, o)).intersection(g)
                    if not r.is_empty:
                        pole -= r.area / grub * (min(o.get("wys_otw", 205), z1) - max(o.get("parapet") or 0, z0))
            wynik.append({"sciana": s, "geom": g, "dl": dl, "grub": grub, "m2": max(pole, 0) / 1e4, "rodzaj": rodzaj})
        return wynik

    otw_i = [(o, geometria.prostokat(geometria.prostokat_otworu(M_i, o))) for o in M_i.get("otwory", [])]
    otw_p = [(o, geometria.prostokat(geometria.prostokat_otworu(M_p, o))) for o in M_p.get("otwory", [])]
    unia_i = unary_union([r for _, r in otw_i]) if otw_i else Polygon()
    unia_p = unary_union([r for _, r in otw_p]) if otw_p else Polygon()
    likwidowane = [(o, r) for o, r in otw_i if r.intersection(unia_p).area < 0.5 * r.area]
    zamurowania = [(o, r) for o, r in likwidowane if r.intersection(pasy_p).area >= 0.5 * r.area]
    wykucia = [(o, r) for o, r in otw_p if r.intersection(unia_i).area < 0.5 * r.area
               and r.intersection(pasy_i).area >= 0.5 * r.area]
    return {"rozbiorki": sciany(M_i, pasy_p, "rozbiorka"), "nowe": sciany(M_p, pasy_i, "nowa"),
            "likwidowane": likwidowane, "zamurowania": zamurowania, "wykucia": wykucia}


def kolor_zmiany(rodzaj):
    r = (rodzaj or "").lower()
    if "wybur" in r or "rozbi" in r or "wyku" in r or "demont" in r:
        return ZOLTY_TXT
    if "now" in r or "przesun" in r or "muro" in r or "zamur" in r:
        return CZERWONY_TXT
    return "#444"


def rysuj_plan(M_i, M_p, W, zakres):
    wsp_i, wsp_p = bryly(M_i), bryly(M_p)
    wspolne = czysc(wsp_i.intersection(wsp_p), 1.0)
    rozbiorki = czysc(wsp_i.difference(wsp_p))
    nowe = czysc(wsp_p.difference(wsp_i))
    s = [plan.kontekst(W, M_p), plan.pomieszczenia(W, M_p), plan.szachty(W, M_p, opisy=False)]
    s.append(svg.sciezka(wspolne, W.p, SZARY, SZARY_OBR, 0.8))
    s.append(svg.sciezka(rozbiorki, W.p, ZOLTY, None))
    s.append(kreskowanie(rozbiorki, W))
    s.append(svg.sciezka(rozbiorki, W.p, "none", ZOLTY_OBR, 1.4))
    s.append(svg.sciezka(nowe, W.p, CZERWONY, CZERWONY_OBR, 1.4))
    for o, r in zakres["likwidowane"]:
        s.append(svg.sciezka(r, W.p, "none", ZOLTY_OBR, 1.3, "5 3"))
    for o in M_p.get("otwory", []):
        s.append(plan.luk_drzwi(W, M_p, o, "#B3B3B3"))
    s.append(plan.etykiety(W, M_p, pole=False))
    for z in M_p.get("zmiany", []):
        if not z.get("xy"):
            continue
        X, Y = W.p(*z["xy"])
        kol = kolor_zmiany(z.get("rodzaj"))
        r = 7 + 2.6 * len(z["id"])
        s.append(svg.okrag(X, Y, r, "#FFFFFF", kol, 1.6))
        s.append(svg.tekst(X, Y + 4, z["id"], 10.5, "middle", kolor=kol, waga="bold"))
    return "".join(s)


def zestawienie(M_i, M_p, zakres, x, y, szer):
    """Lista zmian (z modelu), rozbiorek, nowych scian i zmian otworow; zwraca svg."""
    linie = []
    for z in M_p.get("zmiany", []):
        linie.append(("%s (%s): %s" % (z["id"], z.get("rodzaj", "zmiana"), z.get("opis", "")),
                      kolor_zmiany(z.get("rodzaj"))))
    for klucz, naglowek, kol in (("rozbiorki", "Rozbiórki", ZOLTY_TXT), ("nowe", "Nowe ściany", CZERWONY_TXT)):
        for w in zakres[klucz]:
            sc = w["sciana"]
            t = "%s: %s%s — dł. %s cm, gr. %s cm, ok. %s m² ściany" % (
                naglowek, sc["id"], " (%s)" % sc["typ"] if sc.get("typ") else "", svg.fmt(w["dl"]),
                svg.fmt(w["grub"]), svg.fmt(w["m2"], 2))
            if sc.get("nosna"):
                t += " — ŚCIANA NOŚNA: wymaga projektu konstrukcji"
            linie.append((t, kol))
    if zakres["likwidowane"]:
        linie.append(("Demontaż stolarki / likwidowane otwory: " + ", ".join(
            "%s (ściana %s)" % (opis_otworu(o, M_i), o["sciana"]) for o, _ in zakres["likwidowane"]), ZOLTY_TXT))
    if zakres["zamurowania"]:
        linie.append(("Zamurowania otworów: " + ", ".join(opis_otworu(o, M_i) for o, _ in zakres["zamurowania"]),
                      CZERWONY_TXT))
    if zakres["wykucia"]:
        linie.append(("Wykucia nowych otworów w ścianach istniejących: " + ", ".join(
            "%s (ściana %s)" % (opis_otworu(o, M_p), o["sciana"]) for o, _ in zakres["wykucia"]), ZOLTY_TXT))
    nosne = [w["sciana"]["id"] for k in ("rozbiorki", "nowe") for w in zakres[k] if w["sciana"].get("nosna")]
    if not nosne:
        linie.append(("Ściany nośne bez zmian.", "#444"))
    if not any(zakres[k] for k in zakres):
        linie.append(("Brak różnic w ścianach między stanem istniejącym a projektowanym.", "#444"))
    s = [svg.tekst(x, y + 12, "ZAKRES ZMIAN", 11, waga="bold")]
    yy = y + 30
    znakow = int(szer / (9.5 * 0.5))
    for t, kol in linie:
        for j, lin in enumerate(textwrap.wrap(t, znakow) or [""]):
            s.append(svg.tekst(x + (0 if j == 0 else 16), yy, lin, 9.5, kolor=kol))
            yy += 13
        yy += 3
    s.append(svg.tekst(x, yy + 8, "Powierzchnie ścian orientacyjne: długość × wysokość minus otwory; "
                                 "wiążący zakres robót ustala projekt wykonawczy.", 8.5, kolor="#777"))
    return "".join(s)


def legenda():
    return [
        (svg.prostokat(0, 3, 24, 13, SZARY, SZARY_OBR, 0.8), "ściana bez zmian"),
        (svg.prostokat(0, 3, 24, 13, ZOLTY, ZOLTY_OBR, 1.2) + "".join(
            svg.linia(i, 13, i + 10, 3, ZOLTY_OBR, 0.7) for i in (0, 7, 14)), "rozbiórka, wykucie otworu"),
        (svg.prostokat(0, 3, 24, 13, CZERWONY, CZERWONY_OBR, 1.2), "nowa ściana, zamurowanie"),
        (svg.prostokat(2, 2, 22, 14, "none", ZOLTY_OBR, 1.2, "5 3"), "demontaż stolarki, likwidowany otwór"),
        (svg.okrag(12, 8, 8, "#FFFFFF", "#444", 1.4) + svg.tekst(12, 11, "Z", 8, "middle", kolor="#444", waga="bold"),
         "oznaczenie zmiany (opis w zakresie zmian)"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("istniejacy", help="model stanu istniejacego")
    ap.add_argument("projekt", help="model stanu projektowanego")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu projektu>/wyjscie)")
    a = ap.parse_args()
    M_i, M_p = model.wczytaj(a.istniejacy), model.wczytaj(a.projekt)
    for M, sciezka in ((M_i, a.istniejacy), (M_p, a.projekt)):
        if zmodel.rodzaj_pliku(M) == "zamierzenie":
            print("%s: to model zamierzenia - uzyj rysunki/roznica.py (roznica stanow P-02); "
                  "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(sciezka).name)
            sys.exit(2)
    W, skala_txt = widok(M_i, M_p, POLE_PLANU)
    zakres = zakres_robot(M_i, M_p)
    tresc = rysuj_plan(M_i, M_p, W, zakres)
    x1, y0 = POLE_PLANU[2], POLE_PLANU[1]
    tresc += svg.strzalka_polnocy(x1 - 40, y0 + 40, M_p.get("meta", {}).get("polnoc", {}).get("azymut_osi_Y_stopnie", 0))
    tresc += svg.podzialka(POLE_PLANU[0] + 10, POLE_PLANU[3] - 12, W.px_na_m)
    tresc += zestawienie(M_i, M_p, zakres, 50, 1500, 1380)
    dok = arkusz.arkusz(M_p, "A-02", "Plan wyburzeń i nowych ścian", skala_txt, tresc, legenda())
    for p in svg.zapisz(dok, model.sciezka_wyniku(M_p, "A-02_wyburzenia", a.wyjscie), pdf=True):
        print("zapisano", p)


if __name__ == "__main__":
    main()
