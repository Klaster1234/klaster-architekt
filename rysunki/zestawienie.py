"""Zestawienie obiektow modelu zamierzenia wedlug legendy: MD, CSV i arkusz Z-01 (SVG, PNG, PDF).

    python rysunki/zestawienie.py przyklad/ogrod/model/projekt.json
    python rysunki/zestawienie.py przyklad/ogrod/model/projekt.json --istniejacy przyklad/ogrod/model/istniejacy.json

Wiersz na obiekt, w kolejnosci legendy i id: kategoria, id, atrybuty wybrane w legendzie (pole
zestawienie kategorii), pole w m2 (powierzchnia, bryla, dach - rzut wielokata), dlugosc w m
(linia) i sztuki: punkt - 1, rosliny w grupie z atrybuty.rozstaw_cm - pole / rozstaw^2 albo
dlugosc / rozstaw, zaokraglone w gore. --istniejacy dodaje kolumne stan: obiekt istniejacy (to samo
id w stanie istniejacym) albo nowy. Pod tabela sumy kategorii. CSV: srednik, przecinek dziesietny,
UTF-8 z BOM (utf-8-sig, zeby Excel od razu rozpoznal kodowanie), kategoria jako klucz legendy.
Model lokalu: komunikat i kod 2.
Wynik: <id>_<numer>_zestawienie.{md,csv,svg,png,pdf}.
"""
import argparse
import csv
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import arkusz, svg
from zamierzenie import model, rysuj

ILOSCI = ("pole_m2", "dlugosc_m", "sztuki")
NAGLOWKI_ILOSCI = ("pole [m²]", "długość [m]", "sztuki")
RYSUNEK_R = 10.0     # rozmiar pisma tabeli na arkuszu


def wiersze(M, M_ist=None):
    """(nazwy atrybutow, [wiersz]); wiersz: kategoria, nazwa, id, atrybuty, pole_m2, dlugosc_m,
    sztuki (liczby albo None) i stan (przy M_ist)."""
    kolejnosc = {k: i for i, k in enumerate(model.legenda(M))}
    obiekty = sorted(model.obiekty(M), key=lambda o: (kolejnosc.get(o.get("kategoria"), len(kolejnosc)),
                                                       str(o.get("kategoria")), rysuj.klucz_id(o["id"])))
    atrybuty = []
    for o in obiekty:
        for k in model.styl(M, o.get("kategoria"))["zestawienie"]:
            if k not in atrybuty:
                atrybuty.append(k)
    istniejace = {o["id"] for o in model.obiekty(M_ist)} if M_ist is not None else None
    wynik = []
    for o in obiekty:
        st, g = model.styl(M, o.get("kategoria")), model.ksztalt(o)
        at = o.get("atrybuty") or {}
        w = {"kategoria": o.get("kategoria"), "nazwa": st["nazwa"], "id": o["id"], "pole_m2": None, "dlugosc_m": None,
             "sztuki": None}
        for k in atrybuty:
            w[k] = at.get(k) if k in st["zestawienie"] else None
        rozstaw = at.get("rozstaw_cm")
        if g.geom_type == "Polygon":
            w["pole_m2"] = g.area / 1e4
            if rozstaw:
                w["sztuki"] = math.ceil(g.area / rozstaw ** 2 - 1e-9)
        elif g.geom_type == "LineString":
            w["dlugosc_m"] = g.length / 100
            if rozstaw:
                w["sztuki"] = math.ceil(g.length / rozstaw - 1e-9)
        else:
            w["sztuki"] = 1
        if istniejace is not None:
            w["stan"] = "istniejący" if o["id"] in istniejace else "nowy"
        wynik.append(w)
    return atrybuty, wynik


def sumy(wiersze_):
    """[(kategoria, nazwa, liczba obiektow, pole, dlugosc, sztuki)] w kolejnosci wierszy."""
    s = {}
    for w in wiersze_:
        k = s.setdefault(w["kategoria"], [w["nazwa"], 0, None, None, None])
        k[1] += 1
        for i, pole in enumerate(ILOSCI, 2):
            if w[pole] is not None:
                k[i] = (k[i] or 0) + w[pole]
    return [(k, *v) for k, v in s.items()]


def tekst(v, dokl=2, tysiace=True):
    """Liczba po polsku (przecinek; spacja co trzy cyfry, gdy tysiace), napis bez zmian, None - ""."""
    if v is None:
        return ""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, int):
        return rysuj.liczba(v, 0) if tysiace else str(v)
    return rysuj.liczba(v, dokl) if tysiace else ("%.*f" % (dokl, v)).replace(".", ",")


def liczbowe(atrybuty, wiersze_):
    """Atrybuty, ktore we wszystkich wierszach sa liczbami albo sa puste (wyrownanie do prawej)."""
    return {a for a in atrybuty if all(w[a] is None or (isinstance(w[a], (int, float)) and not isinstance(w[a], bool))
                                       for w in wiersze_)}


def komorki(w, atrybuty, stan):
    k = [w["nazwa"], w["id"]] + [tekst(w[a]) for a in atrybuty] + [tekst(w[p]) for p in ILOSCI]
    return k + ([w["stan"]] if stan else [])


def markdown(M, atrybuty, wiersze_, stan, numer, zrodlo):
    pr = model.projekt(M)
    nag = ["kategoria", "id"] + atrybuty + list(NAGLOWKI_ILOSCI) + (["stan"] if stan else [])
    liczby = liczbowe(atrybuty, wiersze_)
    wyr = ["---", "---"] + ["---:" if a in liczby else "---" for a in atrybuty] + ["---:"] * 3 + (["---"] if stan else [])
    linie = ["# %s — Zestawienie obiektów" % numer, "",
             "%s · %s · %s · %s" % (pr.get("obiekt") or "—", pr["id"], pr.get("faza") or "—", date.today().strftime("%d.%m.%Y")),
             "Wygenerowano z modelu `%s` (`python rysunki/zestawienie.py`)%s." % (
                 Path(M["_sciezka"]).name, "; stan według `%s`" % zrodlo if stan else ""), "",
             "| " + " | ".join(nag) + " |", "|" + "|".join(wyr) + "|"]
    linie += ["| " + " | ".join(komorki(w, atrybuty, stan)) + " |" for w in wiersze_]
    linie += ["", "## Sumy kategorii", "", "| kategoria | obiekty | pole [m²] | długość [m] | sztuki |",
              "|---|---:|---:|---:|---:|"]
    linie += ["| %s | %d | %s | %s | %s |" % (n, ile, tekst(p), tekst(d), tekst(s)) for _, n, ile, p, d, s in sumy(wiersze_)]
    linie += ["", "Pole — rzut wielokąta obiektu (dach: obrys ścian). Sztuki roślin w grupie: pole / rozstaw² "
              "(powierzchnia) albo długość / rozstaw (linia), zaokrąglone w górę."]
    return "\n".join(linie) + "\n"


def zapisz_csv(sciezka, atrybuty, wiersze_, stan):
    with open(sciezka, "w", encoding="utf-8-sig", newline="") as f:
        z = csv.writer(f, delimiter=";", lineterminator="\n")
        z.writerow(["kategoria", "id"] + atrybuty + list(ILOSCI) + (["stan"] if stan else []))
        for w in wiersze_:
            z.writerow([w["kategoria"], w["id"]] + [tekst(w[a], tysiace=False) for a in atrybuty]
                       + [tekst(w[p], tysiace=False) for p in ILOSCI] + ([w["stan"]] if stan else []))


def arkusze(M, atrybuty, wiersze_, stan, numer):
    """Dokumenty SVG: tabela obiektow dzielona na arkusze wedlug wysokosci, sumy kategorii na ostatnim."""
    nag = ["kategoria", "id"] + atrybuty + list(NAGLOWKI_ILOSCI) + (["stan"] if stan else [])
    liczby = liczbowe(atrybuty, wiersze_)
    wyr = "ll" + "".join("p" if a in liczby else "l" for a in atrybuty) + "ppp" + ("l" if stan else "")
    uwagi = ["Pole — rzut wielokąta obiektu (dach: obrys ścian); długość linii w m; sztuki: punkt — 1, rośliny "
             "w grupie z atrybutem rozstaw_cm — pole / rozstaw² albo długość / rozstaw, w górę.",
             "Atrybuty według pola „zestawienie” w legendzie modelu. Te same dane w plikach MD i CSV.",
             "Zestawienie generowane z modelu zamierzenia — zmiany wprowadza się w modelu, nie w zestawieniu."]
    if stan:
        uwagi.insert(2, "Stan: istniejący — obiekt o tym samym id jest w stanie istniejącym; nowy — tylko w projekcie.")
    dol, y_stopki = rysuj.stopka([], uwagi)
    wiersz = RYSUNEK_R * 1.85
    na_arkusz = max(1, int((y_stopki - 30 - 140) / wiersz) - 1)
    s_sumy = sumy(wiersze_)
    h_sum = 40 + (len(s_sumy) + 1) * wiersz
    paczki = [wiersze_[i:i + na_arkusz] for i in range(0, len(wiersze_), na_arkusz)] or [[]]
    if 140 + (len(paczki[-1]) + 1) * wiersz + h_sum > y_stopki - 30:
        paczki.append(None)          # sumy na osobnym arkuszu
    dok = []
    for i, paczka in enumerate(paczki):
        s, y = [], 140
        if paczka is not None:
            s.append(svg.tekst(50, 128, "OBIEKTY (%d)%s" % (len(wiersze_), " — część %d z %d" % (
                i + 1, len([x for x in paczki if x is not None])) if len(paczki) > 1 else ""), 11, waga="bold"))
            t, h = rysuj.tabela(50, 140, nag, [komorki(w, atrybuty, stan) for w in paczka], 1380, RYSUNEK_R, wyr)
            s.append(t)
            y = 140 + h + 40
        if i == len(paczki) - 1:
            s.append(svg.tekst(50, y - 12, "SUMY KATEGORII", 11, waga="bold"))
            t, _ = rysuj.tabela(50, y, ["kategoria", "obiekty", "pole [m²]", "długość [m]", "sztuki"],
                                [[n, str(ile), tekst(p), tekst(d), tekst(sz)] for _, n, ile, p, d, sz in s_sumy],
                                760, RYSUNEK_R, "lpppp")
            s.append(t)
        dok.append(arkusz.arkusz(M, numer, "Zestawienie obiektów", "bez skali (tabela)", "".join(s) + dol,
                                 jednostki="pola w m², długości w m"))
    return dok


def main():
    ap = argparse.ArgumentParser(description="Zestawienie obiektow modelu zamierzenia (arkusz Z-01, MD, CSV).")
    ap.add_argument("model")
    ap.add_argument("--istniejacy", help="model stanu istniejacego: kolumna stan (istniejacy albo nowy)")
    ap.add_argument("--numer", default="Z-01", help="numer arkusza (domyslnie Z-01)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    M_ist = model.wczytaj(a.istniejacy) if a.istniejacy else None
    for x in (M, M_ist):
        blad = rysuj.komunikat_rodzaju(x) if x is not None else None
        if blad:
            print("%s: %s" % (Path(x["_sciezka"]).name, blad))
            return 2
    atrybuty, w = wiersze(M, M_ist)
    stan = M_ist is not None
    baza = model.sciezka_wyniku(M, "%s_zestawienie" % a.numer, a.wyjscie)
    md = baza.with_name(baza.name + ".md")
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown(M, atrybuty, w, stan, a.numer, Path(a.istniejacy).name if stan else None))
    print("zapisano", md)
    plik_csv = baza.with_name(baza.name + ".csv")
    zapisz_csv(plik_csv, atrybuty, w, stan)
    print("zapisano", plik_csv)
    for i, dok in enumerate(arkusze(M, atrybuty, w, stan, a.numer)):
        for p in svg.zapisz(dok, baza.with_name(baza.name + ("_%d" % (i + 1) if i else "")), pdf=True):
            print("zapisano", p)
    print("obiektow %d, kategorii %d%s" % (len(w), len(sumy(w)), ", nowych %d" % sum(x["stan"] == "nowy" for x in w) if stan else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
