"""Sprawdza model zamierzenia: spojnosc, geometrie i nakladanie obiektow.

    python zamierzenie/waliduj.py przyklad/ogrod/model/projekt.json

Bledy (kod wyjscia 1): brak albo powtorzone id, znak ":" w id dzialki, sasiedztwa, obiektu
albo modulu (zarezerwowany dla elementow modulow), brak albo niepoprawne meta.projekt.id
(przedrostek nazw plikow: litery A-Z, cyfry, _ . -), meta.rodzaj, ksztalt albo bilans w
legendzie spoza listy, kolor w legendzie inny niz #RRGGBB albo null, kategoria spoza
legendy (poza "_*"), ksztalt niezgodny z legenda, niepoprawna geometria, dach na
obrysie innym niz prostokat, dach czterospadowy z kalenica "krotszy", dach.nizej spoza
N/E/S/W, przy innym dachu niz jednospadowy albo na boku prostopadlym do kalenicy,
nieznany poziom albo modul bez pola poziom, brak pliku modulu, modul, ktorego nie
przyjmuje lokal/waliduj.py (z liniami jego bledow - najwyzej 15 - i poleceniem do sprawdzenia
lokalu), meta.projekt.id lokalu modulu rowne id zamierzenia albo innego
modulu (pliki wynikow by sie nadpisaly). WARTOSCI: liczby (nie tekst) w dopuszczalnym
zakresie - z [z0 < z1], wys > 0, srednica > 0, atrybuty.rozstaw_cm > 0, dach.kat w (0, 90)
dla dachow spadzistych (plaski: 0 albo brak), dach.z0, dach.okap >= 0, poziomy[].z,
miejsce.teren.punkty [x, y, z], sasiedztwo wys > 0, przekroje glebokosc >= 0,
moduly przesuniecie [x, y] i obrot_stopnie, meta.lokalizacja (lat, lon, strefa znana
zoneinfo). Ostrzezenia (kod 0): obiekt poza dzialka, nakladanie obiektow z kolizja (w planie
i w pionie), nakladanie powierzchni roznych klas bilansu, obiekty na terenie bez
siatki terenu; obiekty z blednymi wartosciami sa pomijane, a przy blednych poziomach albo
punktach terenu ostrzezen sie nie liczy. Model lokalu albo plik nierozpoznany: komunikat i kod 2.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import explain_validity

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import pliki
from zamierzenie import model, teren

GEOMETRIA = {"powierzchnia": "wielokat", "bryla": "wielokat", "dach": "wielokat", "linia": "linia", "punkt": "punkt"}
KOLEJNOSC_BILANSU = ("zabudowa", "utwardzona", "woda", "pbc", "inne")   # czesc wspolna idzie do wyzszej klasy
TOL = 1.0   # cm i cm2: mniejsza czesc wspolna to styk, nie nakladanie
WALIDUJ_LOKAL = Path(__file__).resolve().parents[1] / "lokal" / "waliduj.py"
LINII_LOKALU = 15   # linii bledow walidatora lokalu w komunikacie o odrzuconym module


def _liczba(v):
    """Liczba JSON (int albo float, skonczona) - nie tekst i nie true/false."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _pokaz(v):
    return json.dumps(v, ensure_ascii=False)[:80]


def _bledy_lokalu(wydruk):
    """Linie bledow z wydruku lokal/waliduj.py: spojnosc ("  - ...") i pola poza tolerancja albo bez wielokata;
    bez nich ostatnia linia wydruku. Najwyzej LINII_LOKALU linii, dalej "…"."""
    linie = [l[4:] if l.startswith("  - ") else l.strip() for l in wydruk.splitlines()
             if l.startswith("  - ") or "POZA TOLERANCJA" in l or "BRAK WIELOKATA" in l] or wydruk.strip().splitlines()[-1:]
    return linie[:LINII_LOKALU] + (["…"] if len(linie) > LINII_LOKALU else [])


def spojnosc(M):
    bledy = []
    if M["meta"].get("rodzaj") not in model.RODZAJE_ZAMIERZEN:
        bledy.append("meta.rodzaj spoza listy (%s): %s" % (", ".join(model.RODZAJE_ZAMIERZEN), M["meta"].get("rodzaj")))
    pr = M["meta"].get("projekt")
    if pr is not None and not isinstance(pr, dict):
        bledy.append("meta.projekt musi byc obiektem {id, obiekt, inwestor, autor, faza}: %s" % _pokaz(pr))
    elif (pr or {}).get("id") is None:
        bledy.append("meta.projekt.id: brak pola (przedrostek nazw plikow wynikowych, np. \"ogrod\")")
    elif not pliki.poprawne_id(pr["id"]):
        bledy.append("meta.projekt.id %s: dozwolone litery A-Z i a-z, cyfry, _ . - (bez spacji, nie samo ..) - to przedrostek "
                     "nazw plikow wynikowych" % _pokaz(pr["id"]))
    miejsce = M.get("miejsce") or {}
    widziane = set()
    for sekcja, lista in (("dzialki", miejsce.get("dzialki")), ("sasiedztwo", miejsce.get("sasiedztwo")),
                          ("poziomy", M.get("poziomy")), ("obiekty", M.get("obiekty")),
                          ("moduly", M.get("moduly")), ("przekroje", M.get("przekroje"))):
        for r in lista or []:
            if not r.get("id"):
                bledy.append("%s: rekord bez id" % sekcja)
            elif r["id"] in widziane:
                bledy.append("powtorzone id: %s" % r["id"])
            elif sekcja in ("dzialki", "sasiedztwo", "obiekty", "moduly") and ":" in str(r["id"]):
                bledy.append("%s %s: znak \":\" w id jest zarezerwowany dla elementow modulow wnetrz (<modul>:<id>)"
                             % (sekcja, r["id"]))
            widziane.add(r.get("id"))
    legenda, poziomy = model.legenda(M), {p.get("id") for p in model.poziomy(M)}
    for k, wpis in legenda.items():
        if wpis.get("ksztalt") not in model.KSZTALTY:
            bledy.append("legenda %s: ksztalt spoza listy (%s): %s" % (k, ", ".join(model.KSZTALTY), wpis.get("ksztalt")))
        if wpis.get("bilans") not in model.BILANS + (None,):
            bledy.append("legenda %s: bilans spoza listy (%s): %s" % (k, ", ".join(model.BILANS), wpis.get("bilans")))
        plan, bryla = wpis.get("plan") or {}, wpis.get("bryla") or {}
        for pole, kolor in (("plan.wypelnienie", plan.get("wypelnienie")), ("plan.linia", plan.get("linia")),
                            ("bryla.kolor", bryla.get("kolor"))):
            if kolor is not None and not (isinstance(kolor, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", kolor)):
                bledy.append("legenda %s: %s musi miec postac #RRGGBB albo null: %s" % (k, pole, kolor))
    for o in model.obiekty(M):
        k = o.get("kategoria")
        if k not in legenda and not str(k).startswith("_"):
            bledy.append("obiekt %s: kategoria spoza legendy: %s" % (o.get("id"), k))
        if o.get("poziom") is not None and o["poziom"] not in poziomy:
            bledy.append("obiekt %s: nieznany poziom %s" % (o.get("id"), o["poziom"]))
    id_zamierzenia = pliki.projekt(M)["id"] if pr is None or isinstance(pr, dict) else None   # id nazw plikow wynikow
    lokale = {}   # meta.projekt.id lokalu -> id modulu
    for m in M.get("moduly") or []:
        if m.get("poziom") is None:
            bledy.append("modul %s: brak pola poziom" % m.get("id"))
        elif m["poziom"] not in poziomy:
            bledy.append("modul %s: nieznany poziom %s" % (m.get("id"), m["poziom"]))
        plik = Path(M["_sciezka"]).parent / str(m.get("plik") or "")
        if not m.get("plik") or not plik.is_file():
            bledy.append("modul %s: brak pliku %s" % (m.get("id"), m.get("plik")))
            continue
        try:
            id_lokalu = pliki.projekt(pliki.wczytaj(plik))["id"]
        except (SystemExit, OSError, ValueError) as e:   # SystemExit: bledny JSON (wspolne/pliki.py)
            bledy.append("modul %s: plik %s nieczytelny: %s" % (m.get("id"), m["plik"], e))
            continue
        if id_lokalu == id_zamierzenia:
            bledy.append("modul %s: meta.projekt.id lokalu %s (plik %s) jest takie samo jak id zamierzenia - pliki wynikow "
                         "by sie nadpisaly; nadaj lokalowi inne id" % (m.get("id"), _pokaz(id_lokalu), m["plik"]))
        elif id_lokalu in lokale:
            bledy.append("modul %s: meta.projekt.id lokalu %s (plik %s) jest takie samo jak w module %s - pliki wynikow "
                         "by sie nadpisaly" % (m.get("id"), _pokaz(id_lokalu), m["plik"], lokale[id_lokalu]))
        lokale.setdefault(id_lokalu, m.get("id"))
        w = subprocess.run([sys.executable, str(WALIDUJ_LOKAL), str(plik)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if w.returncode != 0:
            sciezka = plik.resolve()
            try:
                sciezka = sciezka.relative_to(Path.cwd())   # polecenie do wklejenia z biezacego katalogu
            except ValueError:
                pass
            bledy.append("modul %s: lokal/waliduj.py odrzuca plik %s (kod %d):\n%s\n      sprawdz: python lokal/waliduj.py %s"
                         % (m.get("id"), m["plik"], w.returncode, "\n".join("      " + l for l in _bledy_lokalu(w.stdout + w.stderr)),
                            '"%s"' % sciezka if " " in str(sciezka) else sciezka))
    return bledy


def wartosci(M):
    """(bledy, zle, zalezne): pola liczbowe (liczba, nie tekst, w dopuszczalnym zakresie) i meta.lokalizacja;
    zle - id(obiekt) obiektow z bledna wartoscia (ostrzezenia ich nie licza), zalezne - bledny poziom albo punkt
    terenu, od ktorych zaleza wysokosci obiektow (ostrzezen wtedy sie nie liczy)."""
    bledy, zle, zalezne = [], set(), False

    def liczba(opis, v, warunek=lambda x: True, zakres=""):
        if _liczba(v) and warunek(v):
            return True
        bledy.append("%s musi byc liczba%s: %s" % (opis, zakres, _pokaz(v)))
        return False

    lok = M["meta"].get("lokalizacja")
    if lok is not None and not isinstance(lok, dict):
        bledy.append("meta.lokalizacja musi byc obiektem {lat, lon, strefa}: %s" % _pokaz(lok))
    elif lok:
        if "lat" in lok:
            liczba("meta.lokalizacja.lat", lok["lat"], lambda x: -90 <= x <= 90, " w przedziale [-90, 90] st.")
        if "lon" in lok:
            liczba("meta.lokalizacja.lon", lok["lon"], lambda x: -180 <= x <= 180, " w przedziale [-180, 180] st.")
        if "strefa" in lok:
            try:
                ZoneInfo(lok["strefa"])
            except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
                bledy.append("meta.lokalizacja.strefa: nieznana strefa czasowa %s (nazwa IANA, np. \"Europe/Warsaw\")"
                             % _pokaz(lok["strefa"]))
    for p in M.get("poziomy") or []:
        if "z" in p and not liczba("poziom %s: z" % p.get("id"), p["z"], zakres=" (cm wzgledem +-0)"):
            zalezne = True
    miejsce = M.get("miejsce") or {}
    punkty = (miejsce.get("teren") or {}).get("punkty") or []
    zle_pkt = [i for i, q in enumerate(punkty) if not (isinstance(q, list) and len(q) == 3 and all(_liczba(v) for v in q))]
    if zle_pkt:
        zalezne = True
        bledy.append("miejsce.teren.punkty: %d z %d punktow nie ma postaci [x, y, z] z trzema liczbami (cm); pierwszy: "
                     "punkty[%d] = %s" % (len(zle_pkt), len(punkty), zle_pkt[0], _pokaz(punkty[zle_pkt[0]])))
    for s in miejsce.get("sasiedztwo") or []:
        if s.get("wys") is not None:
            liczba("sasiedztwo %s: wys" % s.get("id"), s["wys"], lambda x: x > 0, " dodatnia (cm)")
    for p in M.get("przekroje") or []:
        if p.get("glebokosc") is not None:
            liczba("przekroj %s: glebokosc" % p.get("id"), p["glebokosc"], lambda x: x >= 0, " nieujemna (cm)")
    for m in M.get("moduly") or []:
        v = m.get("przesuniecie")
        if v is not None and not (isinstance(v, list) and len(v) == 2 and all(_liczba(x) for x in v)):
            bledy.append("modul %s: przesuniecie ma postac [x, y] - dwie liczby (cm): %s" % (m.get("id"), _pokaz(v)))
        if m.get("obrot_stopnie") is not None:
            liczba("modul %s: obrot_stopnie" % m.get("id"), m["obrot_stopnie"], zakres=" (stopnie)")
    for o in model.obiekty(M):
        opis, n = "obiekt %s: " % o.get("id"), len(bledy)
        if "z" in o:
            v = o["z"]
            if not (isinstance(v, list) and len(v) == 2 and all(_liczba(x) for x in v) and v[0] < v[1]):
                bledy.append("%sz ma postac [z0, z1] - dwie liczby, z0 < z1 (cm): %s" % (opis, _pokaz(v)))
        for pole in ("wys", "srednica"):
            if o.get(pole) is not None:
                liczba(opis + pole, o[pole], lambda x: x > 0, " dodatnia (cm)")
        at = o.get("atrybuty")
        if isinstance(at, dict) and at.get("rozstaw_cm") is not None:
            liczba(opis + "atrybuty.rozstaw_cm", at["rozstaw_cm"], lambda x: x > 0, " dodatnia (cm)")
        d = o.get("dach")
        if d is not None and not isinstance(d, dict):
            bledy.append("%sdach musi byc obiektem {typ, kat, z0, okap, ...}: %s" % (opis, _pokaz(d)))
        elif d:
            if d.get("typ") == "plaski":
                if "kat" in d and not (_liczba(d["kat"]) and d["kat"] == 0):
                    bledy.append("%sdach.kat dachu plaskiego: 0 albo brak pola: %s" % (opis, _pokaz(d["kat"])))
            elif d.get("typ") in model.TYPY_DACHU:
                if "kat" not in d:
                    bledy.append("%sdach.kat: brak pola (nachylenie polaci w stopniach, w przedziale (0, 90))" % opis)
                else:
                    liczba(opis + "dach.kat", d["kat"], lambda x: 0 < x < 90, " w przedziale (0, 90) st.")
            if "z0" in d:
                liczba(opis + "dach.z0", d["z0"], zakres=" (cm)")
            if "okap" in d:
                liczba(opis + "dach.okap", d["okap"], lambda x: x >= 0, " nieujemna (cm)")
        if len(bledy) > n:
            zle.add(id(o))
    return bledy, zle, zalezne


def _geometria(opis, rodzaj, wsp, bledy):
    """Geometria shapely ze wspolrzednych albo None (z bledem dopisanym do listy)."""
    try:
        if rodzaj == "wielokat" and len({tuple(p) for p in wsp}) < 3:
            bledy.append("%s: wielokat ma mniej niz 3 wierzcholki" % opis)
            return None
        g = {"wielokat": Polygon, "linia": LineString, "punkt": Point}[rodzaj](wsp)
    except Exception as e:   # zle wspolrzedne: shapely i Python zglaszaja rozne wyjatki
        bledy.append("%s: niepoprawna geometria (%s)" % (opis, str(e).strip()))
        return None
    if g.is_empty or not g.is_valid or rodzaj != "punkt" and g.length == 0:
        powod = "pusta" if g.is_empty else explain_validity(g) if not g.is_valid else "zerowa dlugosc"
        bledy.append("%s: niepoprawna geometria (%s)" % (opis, powod))
        return None
    return g


def _prostokat(g):
    """Czy wielokat to prostokat (takze obrocony); katy proste z dokladnoscia ok. 0,5 st."""
    p = [c[:2] for c in g.simplify(0).exterior.coords[:-1]]
    if len(p) != 4:
        return False
    for i in range(4):
        (ax, ay), (bx, by), (cx, cy) = p[i - 1], p[i], p[(i + 1) % 4]
        if abs((bx - ax) * (cx - bx) + (by - ay) * (cy - by)) > 0.01 * math.hypot(bx - ax, by - ay) * math.hypot(cx - bx, cy - by):
            return False
    return True


def _nizej(opis, g, d, prostokat):
    """Bledy dach.nizej: strona spoza listy, dach inny niz jednospadowy albo strona wskazujaca bok
    prostopadly do kalenicy (bok wskazany i kalenica jak w bryle: model.osie_dachu)."""
    if not isinstance(d["nizej"], str) or d["nizej"] not in model.STRONY:
        return ["%s: dach.nizej spoza listy (%s): %s" % (opis, ", ".join(model.STRONY), d["nizej"])]
    if d.get("typ") != "jednospadowy":
        return ["%s: dach.nizej dotyczy tylko dachu jednospadowego (typ %s)" % (opis, d.get("typ"))]
    if not prostokat or model.osie_dachu(g, d.get("kalenica", "dluzszy"), d["nizej"])[5]:
        return []
    krotszy = d.get("kalenica") == "krotszy"
    return ["%s: dach.nizej %s wskazuje %s bok obrysu; nizsza moze byc tylko strona %s boku (rownoleglego do kalenicy)"
            % (opis, d["nizej"], "dluzszy" if krotszy else "krotszy", "krotszego" if krotszy else "dluzszego")]


def geometria(M):
    """(bledy, {id(obiekt): geometria}, unia dzialek albo None)."""
    bledy, geom = [], {}
    miejsce = M.get("miejsce") or {}
    dzialki = [_geometria("dzialka %s" % d.get("id"), "wielokat", d.get("granica"), bledy) for d in miejsce.get("dzialki") or []]
    for s in miejsce.get("sasiedztwo") or []:
        _geometria("sasiedztwo %s" % s.get("id"), "wielokat", s.get("obrys"), bledy)
    for p in M.get("przekroje") or []:
        _geometria("przekroj %s" % p.get("id"), "linia", p.get("linia"), bledy)
    for o in model.obiekty(M):
        opis, st, k = "obiekt %s" % o.get("id"), model.styl(M, o.get("kategoria")), o.get("ksztalt") or {}
        rodzaj = next((r for r in ("wielokat", "linia", "punkt") if r in k), None)
        if st["ksztalt"] in GEOMETRIA and rodzaj != GEOMETRIA[st["ksztalt"]]:
            bledy.append("%s: ksztalt niezgodny z legenda (%s wymaga pola %s)" % (opis, st["ksztalt"], GEOMETRIA[st["ksztalt"]]))
            continue
        if rodzaj is None:
            bledy.append("%s: brak ksztaltu (wielokat, linia albo punkt)" % opis)
            continue
        g = _geometria(opis, rodzaj, k[rodzaj], bledy)
        if g is None:
            continue
        if st["ksztalt"] == "dach" or o.get("dach"):
            d = o["dach"] if isinstance(o.get("dach"), dict) else {}   # dach nie-obiekt zglasza wartosci()
            typ = d.get("typ")
            if typ not in model.TYPY_DACHU:
                bledy.append("%s: typ dachu spoza listy (%s): %s" % (opis, ", ".join(model.TYPY_DACHU), typ))
            prostokat = g.geom_type == "Polygon" and _prostokat(g)
            if not prostokat:
                bledy.append("%s: dach na obrysie innym niz prostokat" % opis)
            if typ == "czterospadowy" and d.get("kalenica") == "krotszy":
                bledy.append("%s: dach czterospadowy z kalenica \"krotszy\" (przy rownych polaciach kalenica biegnie "
                             "wzdluz dluzszego boku)" % opis)
            if "nizej" in d:
                bledy += _nizej(opis, g, d, prostokat)
        geom[id(o)] = g
    return bledy, geom, (unary_union(dzialki) if dzialki and None not in dzialki else None)


def ostrzezenia(M, geom, dz, s):
    w, poziomy = [], {p.get("id") for p in model.poziomy(M)}
    lista = [(o, geom[id(o)], model.styl(M, o.get("kategoria"))) for o in model.obiekty(M)
             if id(o) in geom and (o.get("poziom") is None or o["poziom"] in poziomy)]
    strefa = dz.buffer(TOL) if dz is not None else None
    for o, g, st in lista:
        if strefa is not None and not strefa.covers(g):
            w.append("obiekt %s lezy poza dzialka" % o["id"])
    na_terenie = [o for o in model.obiekty(M) if o.get("na_terenie")]
    if na_terenie and s is None:
        w.append("teren: brak siatki (mniej niz 3 punkty albo punkty na jednej linii), a %d obiektow lezy na terenie "
                 "- ich podstawa to +-0" % len(na_terenie))
    # kolizja: czesc wspolna w planie (punkt i linia jako pas 20 cm) i w pionie (zakres_z)
    kolizje = [(o, g if g.geom_type == "Polygon" else g.buffer(10)) for o, g, st in lista if st["kolizja"]]
    for (a, ga), (b, gb) in combinations(kolizje, 2):
        czesc = ga.intersection(gb).area if ga.intersects(gb) else 0
        if czesc <= TOL:
            continue
        (a0, a1), (b0, b1) = model.zakres_z(M, a, s), model.zakres_z(M, b, s)
        if min(a1, b1) > max(a0, b0):
            w.append("kolizja: %s i %s (czesc wspolna w planie %.2f m2, w pionie %.0f cm)"
                     % (a["id"], b["id"], czesc / 1e4, min(a1, b1) - max(a0, b0)))
    bilans = [(o, g, st["bilans"]) for o, g, st in lista if st["bilans"] in KOLEJNOSC_BILANSU and g.geom_type == "Polygon"]
    for (a, ga, ka), (b, gb, kb) in combinations(bilans, 2):
        czesc = ga.intersection(gb).area if ka != kb and ga.intersects(gb) else 0
        if czesc > TOL:
            w.append("klasy bilansu: %s (%s) i %s (%s) nakladaja sie na %.2f m2 - czesc wspolna liczona jako %s"
                     % (a["id"], ka, b["id"], kb, czesc / 1e4, min(ka, kb, key=KOLEJNOSC_BILANSU.index)))
    return w


def main():
    ap = argparse.ArgumentParser(description="Walidacja modelu zamierzenia (zamierzenie/SCHEMAT.md).")
    ap.add_argument("model")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    rodzaj = model.rodzaj_pliku(M)
    if rodzaj != "zamierzenie":
        print("To %s. Ten walidator sprawdza model zamierzenia (meta.rodzaj i sekcja obiekty, moduly albo miejsce)."
              % ("model lokalu - sprawdz go przez lokal/waliduj.py" if rodzaj == "lokal" else "nie jest model zamierzenia"))
        return 2
    print("MODEL: %s (rodzaj: %s, obiekty: %d, moduly: %d)"
          % (Path(a.model).name, M["meta"]["rodzaj"], len(model.obiekty(M)), len(M.get("moduly") or [])))
    b_spoj = spojnosc(M)
    b_wart, zle, zalezne = wartosci(M)
    b_geom, geom, dz = geometria(M)
    for k in zle:
        geom.pop(k, None)
    w = None if zalezne else ostrzezenia(M, geom, dz, teren.siatka(M))
    for nazwa, lista in (("SPOJNOSC", b_spoj), ("WARTOSCI", b_wart), ("GEOMETRIA", b_geom)):
        print("%s: %s" % (nazwa, "BLEDY (%d)" % len(lista) if lista else "OK"))
        for b in lista:
            print("  -", b)
    if w is None:
        print("OSTRZEZENIA: pominiete - najpierw popraw bledne poziomy albo punkty terenu (od nich zaleza wysokosci obiektow)")
    else:
        print("OSTRZEZENIA: %s" % (len(w) or "brak"))
        for x in w:
            print("  -", x)
    n = len(b_spoj) + len(b_wart) + len(b_geom)
    print("\nWYNIK:", "BLEDY (%d)" % n if n else "OK")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
