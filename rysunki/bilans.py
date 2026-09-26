"""Bilans powierzchni modelu zamierzenia i porownanie z planem miejscowym: MD i arkusz Z-02 (SVG,
PNG, PDF).

    python rysunki/bilans.py przyklad/ogrod/model/projekt.json
    python rysunki/bilans.py przyklad/ogrod/model/projekt.json --numer Z-02 --wyjscie robocze/

Klasa bilansu pochodzi z legendy (zabudowa, utwardzona, woda, pbc, inne). Powierzchnia klasy to
suma wielokatow jej obiektow przycieta do dzialki; czesc wspolna roznych klas liczy sie w klasie
wyzszej (zabudowa > utwardzona > woda > pbc > inne) z ostrzezeniem, a reszta dzialki to
"pozostala". Porownanie z miejsce.plan_miejscowy.parametry: zabudowa_max_proc, pbc_min_proc
i wys_max (cm) z najwyzsza rzedna bryl i dachow (model.zakres_z; dach - kalenica) liczona od +-0 -
uproszczenie (plan miejscowy mierzy wysokosc zwykle od terenu). Arkusz: schemat klas na dzialce,
tabela bilansu i porownanie. Przekroczenie to informacja (kod 0). Model lokalu: komunikat i kod 2.
Wynik: <id>_<numer>_bilans.{md,svg,png,pdf}.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon
from shapely.ops import unary_union

from wspolne import arkusz, svg
from zamierzenie import model, rysuj, teren

KOLEJNOSC = ("zabudowa", "utwardzona", "woda", "pbc", "inne")   # czesc wspolna idzie do wyzszej klasy
NAZWY = {"zabudowa": "zabudowa", "utwardzona": "utwardzona", "woda": "woda", "pbc": "pbc — biologicznie czynna",
         "inne": "inne", "pozostala": "pozostała (bez klasy bilansu)"}
KOLORY = {"zabudowa": "#8C8C8C", "utwardzona": "#D2D2D2", "woda": "#A9CBE3", "pbc": "#B7C8A6", "inne": "#E8DDBF"}
UPROSZCZENIE = "od ±0 — uproszczenie"
TOL = 1.0   # cm2: mniejsza czesc wspolna to styk


def policz(M):
    """Bilans: {"dzialka": m2 albo None, "dzialki": [id], "klasy": {klasa: {"m2", "obiekty", "geom"}},
    "pozostala": m2 albo None, "nakladanie": [(klasa, m2)], "wys": (z_cm, id) albo None, "parametry": {...}}."""
    dz = model.dzialka(M)
    grupy = {k: [] for k in KOLEJNOSC}
    for o in model.obiekty(M):
        k, g = model.styl(M, o.get("kategoria"))["bilans"], model.ksztalt(o)
        if k in grupy and g.geom_type == "Polygon" and (dz is None or g.intersection(dz).area > TOL):
            grupy[k].append((o, g))
    wynik = {"dzialka": dz.area / 1e4 if dz is not None else None,
             "dzialki": [d["id"] for d in (M.get("miejsce") or {}).get("dzialki") or []],
             "klasy": {}, "nakladanie": []}
    zajete = Polygon()
    for k in KOLEJNOSC:
        g = unary_union([x for _, x in grupy[k]]) if grupy[k] else Polygon()
        if dz is not None:
            g = g.intersection(dz)
        wspolna = g.intersection(zajete).area
        if wspolna > TOL:
            wynik["nakladanie"].append((k, wspolna / 1e4))
        czesc = g.difference(zajete)
        wynik["klasy"][k] = {"m2": czesc.area / 1e4, "obiekty": sorted((o["id"] for o, _ in grupy[k]), key=rysuj.klucz_id),
                             "geom": czesc}
        zajete = unary_union([zajete, g])
    wynik["pozostala"] = max(0.0, (dz.area - zajete.area) / 1e4) if dz is not None else None
    s = teren.siatka(M)
    wys = [(model.zakres_z(M, o, s)[1], o["id"]) for o in model.obiekty(M) if rysuj.grupa(M, o) in (1, 2)]
    wynik["wys"] = max(wys) if wys else None
    wynik["parametry"] = ((M.get("miejsce") or {}).get("plan_miejscowy") or {}).get("parametry") or {}
    return wynik


def porownanie(b):
    """[(parametr, wartosc, wymaganie, wynik, zgodny albo None, tekst do konsoli)] dla parametrow
    planu miejscowego (arkusz i MD z polskimi znakami, konsola bez nich)."""
    p, dz, w = b["parametry"], b["dzialka"], []
    udzial = lambda k: 100 * b["klasy"][k]["m2"] / dz if dz else None
    konsola = lambda nazwa, wart, wym, ok: "%s %s (%s) %s" % (nazwa, wart, wym, "brak danych" if ok is None else "OK" if ok else
                                                              "PONIZEJ MINIMUM" if nazwa == "PBC" else "PRZEKROCZENIE")
    if "zabudowa_max_proc" in p:
        u, gr = udzial("zabudowa"), svg.fmt(p["zabudowa_max_proc"], 2)
        ok = None if u is None else u <= p["zabudowa_max_proc"] + 1e-9
        wart = "—" if u is None else "%s %%" % rysuj.liczba(u)
        w.append(("udział powierzchni zabudowy", wart, "≤ %s %%" % gr, "brak działki" if ok is None else "spełnia" if ok else "przekracza",
                  ok, konsola("zabudowa", "-" if u is None else "%s %%" % rysuj.liczba(u), "max %s %%" % gr, ok)))
    if "pbc_min_proc" in p:
        u, gr = udzial("pbc"), svg.fmt(p["pbc_min_proc"], 2)
        ok = None if u is None else u >= p["pbc_min_proc"] - 1e-9
        wart = "—" if u is None else "%s %%" % rysuj.liczba(u)
        w.append(("udział powierzchni biologicznie czynnej", wart, "≥ %s %%" % gr, "brak działki" if ok is None else "spełnia" if ok else "za mało",
                  ok, konsola("PBC", "-" if u is None else "%s %%" % rysuj.liczba(u), "min %s %%" % gr, ok)))
    if "wys_max" in p:
        gr = svg.fmt(p["wys_max"])
        if b["wys"] is None:
            w.append(("wysokość (najwyższa rzędna brył i dachów)", "brak brył", "≤ %s cm" % gr, "—", None,
                      konsola("wysokosc", "bez bryl", "max %s cm" % gr, None)))
        else:
            z, ident = b["wys"]
            ok = z <= p["wys_max"] + 1e-9
            w.append(("wysokość: najwyższa rzędna brył i dachów (%s)" % ident, "%s cm" % svg.fmt(z), "≤ %s cm" % gr,
                      "%s (%s)" % ("spełnia" if ok else "przekracza", UPROSZCZENIE), ok,
                      konsola("wysokosc", "%s cm" % svg.fmt(z), "max %s cm" % gr, ok) + ", od +-0 - uproszczenie"))
    return w


def wiersze_bilansu(b):
    """[(klasa, pole, udzial, obiekty)] - dzialka, klasy i pozostala."""
    dz = b["dzialka"]
    proc = lambda m2: rysuj.liczba(100 * m2 / dz) if dz else "—"
    w = [("działka", rysuj.liczba(dz) if dz is not None else "—", "100,00" if dz else "—", ", ".join(b["dzialki"]) or "—")]
    for k in KOLEJNOSC:
        m2 = b["klasy"][k]["m2"]
        w.append((NAZWY[k], rysuj.liczba(m2), proc(m2), ", ".join(b["klasy"][k]["obiekty"]) or "—"))
    if b["pozostala"] is not None:
        w.append((NAZWY["pozostala"], rysuj.liczba(b["pozostala"]), proc(b["pozostala"]), "—"))
    return w


def markdown(M, b, numer):
    pr, pm = model.projekt(M), (M.get("miejsce") or {}).get("plan_miejscowy") or {}
    linie = ["# %s — Bilans powierzchni" % numer, "",
             "%s · %s · %s · %s" % (pr.get("obiekt") or "—", pr["id"], pr.get("faza") or "—", date.today().strftime("%d.%m.%Y")),
             "Wygenerowano z modelu `%s` (`python rysunki/bilans.py`)." % Path(M["_sciezka"]).name, "",
             "| klasa | pole [m²] | udział [%] | obiekty |", "|---|---:|---:|---|"]
    linie += ["| %s | %s | %s | %s |" % w for w in wiersze_bilansu(b)]
    if b["dzialka"] is None:
        linie += ["", "Model bez działki: pola klas bez przycięcia, bez udziałów."]
    for k, m2 in b["nakladanie"]:
        linie += ["", "Uwaga: klasa %s nakłada się na klasy wyższe na %s m² — część wspólna policzona w klasie wyższej."
                  % (k, rysuj.liczba(m2))]
    nazwa = " ".join(x for x in (pm.get("nazwa"), pm.get("symbol")) if x)
    linie += ["", "## Porównanie z planem miejscowym%s" % (" (%s)" % nazwa if nazwa else ""), ""]
    por = porownanie(b)
    if por:
        linie += ["| parametr | wartość | wymaganie | wynik |", "|---|---:|---:|---|"]
        linie += ["| %s | %s | %s | %s |" % w[:4] for w in por]
    else:
        linie.append("Model bez parametrów planu miejscowego (miejsce.plan_miejscowy.parametry).")
    linie += ["", "Wysokość liczona %s: plan miejscowy mierzy ją zwykle od terenu, więc przed decyzją sprawdź ją "
              "według definicji planu." % UPROSZCZENIE]
    return "\n".join(linie) + "\n"


def schemat(M, b, pole):
    """Schemat klas bilansu na dzialce (bez skali tekstowej na arkuszu - skala w tabliczce)."""
    dz = model.dzialka(M)
    geom = [x["geom"] for x in b["klasy"].values() if not x["geom"].is_empty]
    x0, y0, x1, y1 = (dz if dz is not None else unary_union(geom)).bounds if (dz is not None or geom) else (0, 0, 1000, 1000)
    zakres = (x0 - 200, y0 - 200, x1 + 200, y1 + 200)
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    W = arkusz.Widok(zakres, pole, sk)
    miejsca, s, op = rysuj.Miejsca(), [], []
    for k in KOLEJNOSC:
        g = b["klasy"][k]["geom"]
        if g.is_empty:
            continue
        s.append(svg.sciezka(g, W.p, KOLORY[k], "#555555", 0.6))
        naj = max(getattr(g, "geoms", [g]), key=lambda c: c.area)
        if W.d(naj.bounds[2] - naj.bounds[0]) > 40 and W.d(naj.bounds[3] - naj.bounds[1]) > 18:
            X, Y = W.p(*naj.representative_point().coords[0])
            udz = " %s %%" % rysuj.liczba(100 * b["klasy"][k]["m2"] / b["dzialka"]) if b["dzialka"] else ""
            linie = [(k, 9), ("%s m²%s" % (rysuj.liczba(b["klasy"][k]["m2"]), udz), 8)]
            op.append(rysuj.napis(miejsca, [(X, Y)] + rysuj.wokol(X, Y, linie, 4), linie))
    s.append(rysuj.dzialka(W, M, miejsca))
    return "".join(s + op), skala_txt, W


def main():
    ap = argparse.ArgumentParser(description="Bilans powierzchni modelu zamierzenia (arkusz Z-02, MD).")
    ap.add_argument("model")
    ap.add_argument("--numer", default="Z-02", help="numer arkusza (domyslnie Z-02)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    blad = rysuj.komunikat_rodzaju(M)
    if blad:
        print(blad)
        return 2
    b = policz(M)
    baza = model.sciezka_wyniku(M, "%s_bilans" % a.numer, a.wyjscie)
    md = baza.with_name(baza.name + ".md")
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown(M, b, a.numer))
    # arkusz: schemat klas, tabela bilansu, porownanie z planem miejscowym
    wb = wiersze_bilansu(b)
    por = porownanie(b)
    tab, h_tab = rysuj.tabela(50, 0, ["klasa", "pole [m²]", "udział [%]", "obiekty"], [list(w) for w in wb], 1380, 10, "lppl")
    tab_p, h_p = rysuj.tabela(50, 0, ["parametr", "wartość", "wymaganie", "wynik"], [list(w[:4]) for w in por], 1380, 10, "lppl",
                              [("#7A1D12" if w[4] is False else None) for w in por]) if por else ("", 0)
    pm = (M.get("miejsce") or {}).get("plan_miejscowy") or {}
    uwagi = ["Powierzchnia klasy: suma wielokątów obiektów tej klasy (legenda modelu) przycięta do działki; część wspólna "
             "różnych klas liczona w klasie wyższej (zabudowa > utwardzona > woda > pbc > inne).",
             "Wysokość: najwyższa rzędna brył i dachów (dach — kalenica) liczona %s; plan miejscowy mierzy ją zwykle "
             "od terenu — sprawdzić według definicji planu." % UPROSZCZENIE,
             "Bilans generowany z modelu zamierzenia — zmiany wprowadza się w modelu, nie na arkuszu."]
    uwagi += ["Klasa %s nakłada się na klasy wyższe na %s m² — część wspólna policzona w klasie wyższej."
              % (k, rysuj.liczba(m2)) for k, m2 in b["nakladanie"]]
    legenda = [(svg.prostokat(1, 3, 23, 13, KOLORY[k], "#555555", 0.6), NAZWY[k]) for k in KOLEJNOSC]
    dol, y_stopki = rysuj.stopka(legenda, uwagi)
    y_por = y_stopki - 30 - h_p if por else y_stopki
    y_tab = (y_por - 50 if por else y_stopki - 30) - h_tab
    pole = (arkusz.POLE[0], arkusz.POLE[1], arkusz.POLE[2], y_tab - 40)
    rys, skala_txt, W = schemat(M, b, pole)
    tresc = rys + svg.strzalka_polnocy(pole[2] - 40, pole[1] + 40, model.azymut_polnocy(M))
    tresc += svg.tekst(50, y_tab - 12, "BILANS POWIERZCHNI", 11, waga="bold")
    tresc += '<g transform="translate(0 %.1f)">%s</g>' % (y_tab, tab)
    if por:
        nazwa = " ".join(x for x in (pm.get("nazwa"), pm.get("symbol")) if x)
        tresc += svg.tekst(50, y_por - 12, "PORÓWNANIE Z PLANEM MIEJSCOWYM%s" % (" — %s" % nazwa if nazwa else ""), 11, waga="bold")
        tresc += '<g transform="translate(0 %.1f)">%s</g>' % (y_por, tab_p)
    dok = arkusz.arkusz(M, a.numer, "Bilans powierzchni", skala_txt, tresc + dol,
                        jednostki="pola w m², wysokości w cm %s" % UPROSZCZENIE)
    print("zapisano", md)
    for p in svg.zapisz(dok, baza, pdf=True):
        print("zapisano", p)
    dz = b["dzialka"]
    for k in KOLEJNOSC:
        x = b["klasy"][k]
        print("%s: %s m2%s%s" % (k, rysuj.liczba(x["m2"]), " (%s %%)" % rysuj.liczba(100 * x["m2"] / dz) if dz else "",
                                 " - " + ", ".join(x["obiekty"]) if x["obiekty"] else ""))
    for k, m2 in b["nakladanie"]:
        print("UWAGA: klasa %s naklada sie na klasy wyzsze na %s m2 (liczona w wyzszej)" % (k, rysuj.liczba(m2)))
    print("dzialka %s m2; %s" % (rysuj.liczba(dz) if dz is not None else "-",
                                 "; ".join(w[5] for w in por) or "bez parametrow planu miejscowego"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
