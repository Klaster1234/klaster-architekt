"""Dane publiczne do modelu zamierzenia: wyniki narzedzia/geoportal.py (meta, teren) i narzedzia/plan_miejscowy.py.

    python zamierzenie/z_geoportalu.py model/istniejacy.json --meta zrodla/dz_meta.json
    python zamierzenie/z_geoportalu.py model/istniejacy.json --meta dz_meta.json --teren dz_teren.json --plan dz_plan_miejscowy.json --id dom
    python zamierzenie/z_geoportalu.py model/istniejacy.json --meta dz_meta.json --teren dz_teren.json --nadpisz-teren

Uklad modelu: poczatek w punkcie bazowym z _meta.json, osie jak siatka PL-1992, centymetry
(meta.georef = {epsg: 2180, x0: E, y0: N, obrot_stopnie: 0}). Model z innym meta.georef zostaje bez
zmian (kod 1), bo jego obiekty leza w innym ukladzie. Bez pliku MODEL powstaje szkielet: meta.rodzaj
"inne", projekt.id z --id albo z nazwy pliku.
Z meta: miejsce.dzialki (id = identyfikator dzialki z ULDK, granica = obrys_m x 100), miejsce.sasiedztwo
(budynki sasiednie: id XGn, obrys_m x 100, wys = wys_m x 100 - bez wys, gdy wysokosc nieznana; zrodlo
i dokladnosc z meta; budynek w punkcie nie trafia do modelu - to obiekt albo modul zamierzenia),
meta.georef, meta.polnoc, meta.lokalizacja i meta.zero_npm_m (tylko gdy model go nie ma: teren
w punkcie bazowym). --teren: miejsce.teren, z w cm wzgledem +-0 = round((z_m_npm - zero_npm_m) * 100, 1)
(bez zero_npm_m w modelu i w meta: rzedna punktu terenu najblizszego punktowi bazowemu). --plan:
miejsce.plan_miejscowy (nazwa, symbol, przeznaczenie, odnosnik, zrodlo; parametry bez zmian; brak
w usludze - bez zmian).
Dane reczne zostaja. Rekordy zapisane przez ten skrypt (dzialka, budynki sasiednie, teren) maja pole
"z_geoportalu": true. Ponowny import zastepuje tylko rekordy z tym polem: dzialke o tym samym id
i budynki w sasiedztwie (budynek, ktorego nie ma juz w meta, usuwa). Rekordy bez pola - wpisane albo
poprawione recznie - zostaja, takze rekord o id dzialki albo budynku z geoportalu (reczna poprawka
wygrywa, rekord z geoportalu nie jest dopisywany; w wydruku "zostawiono (reczny)"). Teren bez
pola (np. z pomiaru) zostaje - --nadpisz-teren zastepuje go terenem z NMT. Na koncu wydruk: co dodano,
zastapiono, usunieto i zostawiono; poprzedni model zostaje w kopii .bak. Plik terenu albo planu
nieczytelny: komunikat, reszta dalej; kod 0, gdy model zapisano. Model lokalu: komunikat i kod 2.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zamierzenie import model

ZNACZNIK = "z_geoportalu"   # pole rekordow zapisanych przez ten skrypt: ponowny import zastepuje tylko je


def szkielet(ident):
    return {"meta": {"rodzaj": "inne", "projekt": {"id": ident}}, "miejsce": {}, "legenda": {}, "obiekty": []}


def liczba(v):
    v = round(float(v), 1)
    return int(v) if v == int(v) else v


def obrys_cm(obrys_m):
    """(obrys w cm co 0,1 cm, czy naprawiony): niepoprawny wielokat -> buffer(0), najwiekszy fragment."""
    p = [[liczba(x * 100), liczba(y * 100)] for x, y in obrys_m]
    g = Polygon(p)
    if g.is_valid:
        return p, False
    g = g.buffer(0)
    g = max(getattr(g, "geoms", [g]), key=lambda c: c.area)
    return [[liczba(x), liczba(y)] for x, y in g.exterior.coords[:-1]], True


def inny_georef(g, meta):
    """Czy meta.georef modelu (g) rozni sie od punktu bazowego z meta (albo meta nie ma georeferencji)."""
    gm = meta.get("georef")
    if not g:
        return False
    try:
        return gm is None or int(g.get("epsg", 2180)) != 2180 or abs(float(g["x0"]) - float(gm["x0"])) > 0.005 or \
            abs(float(g["y0"]) - float(gm["y0"])) > 0.005 or abs(float(g.get("obrot_stopnie") or 0)) > 1e-9
    except (KeyError, TypeError, ValueError):
        return True


def zmiana(raport, rodzaj, sekcja, co=None):
    """Wpis do raportu {rodzaj: {sekcja: [co, ...]}}; rodzaj: dodano, zastapiono, usunieto, zostawiono,
    zostawiono (reczny)."""
    lista = raport.setdefault(rodzaj, {}).setdefault(sekcja, [])
    if co is not None:
        lista.append(str(co))


def wypisz(raport):
    for rodzaj in ("dodano", "zastapiono", "usunieto", "zostawiono", "zostawiono (reczny)"):
        if raport.get(rodzaj):
            print("%s: %s" % (rodzaj, "; ".join(s + (" " + ", ".join(x) if x else "") for s, x in raport[rodzaj].items())))


def ustaw(mt, klucz, wartosc, raport):
    """meta.<klucz> = wartosc; w raporcie dodano albo zastapiono (bez wpisu, gdy wartosc sie nie zmienia)."""
    if mt.get(klucz) != wartosc:
        zmiana(raport, "zastapiono" if klucz in mt else "dodano", "meta." + klucz)
        mt[klucz] = wartosc


def scal(stare, nowe, zastap, raport, sekcja):
    """Rekordy sekcji po imporcie, w dotychczasowej kolejnosci: rekordy, dla ktorych zastap(r) jest falszem, zostaja
    (nowy o ich id jest pomijany - w raporcie "zostawiono (reczny)"); pozostale sa zastapione nowym o tym samym id
    albo usuniete, gdy nowego nie ma; nowe bez odpowiednika na koncu."""
    reczne, ids_nowych = {r.get("id") for r in stare if not zastap(r)}, {r["id"] for r in nowe}
    nowe_id = {r["id"]: r for r in nowe if r["id"] not in reczne}
    wynik, uzyte = [], set()
    for r in stare:
        i = r.get("id")
        if not zastap(r):
            wynik.append(r)
            zmiana(raport, "zostawiono (reczny)" if i in ids_nowych else "zostawiono", sekcja, i)
        elif i in nowe_id and i not in uzyte:
            wynik.append(nowe_id[i])
            uzyte.add(i)
            zmiana(raport, "zastapiono", sekcja, i)
        else:
            zmiana(raport, "usunieto", sekcja, i)
    for i, r in nowe_id.items():
        if i not in uzyte:
            wynik.append(r)
            zmiana(raport, "dodano", sekcja, i)
    return wynik


def wpisz_meta(M, meta, raport=None):
    """Dzialka, sasiedztwo, georef, polnoc, lokalizacja i zero_npm_m z <nazwa>_meta.json (dane reczne zostaja);
    zwraca linie opisu, zmiany dopisuje do raportu."""
    raport = {} if raport is None else raport
    mt = M.setdefault("meta", {})
    mj = M["miejsce"] = M.get("miejsce") or {}
    data, dokl, linie = meta.get("data"), meta.get("dokladnosc_cm"), []
    polnoc = meta.get("polnoc") or {}
    if polnoc.get("azymut_osi_Y_stopnie") is not None:
        ustaw(mt, "polnoc", {**(mt.get("polnoc") or {}), "azymut_osi_Y_stopnie": polnoc["azymut_osi_Y_stopnie"]}, raport)
        linie.append("meta.polnoc: azymut osi +Y %s st. (polnoc siatki PL-1992)" % polnoc["azymut_osi_Y_stopnie"])
    lok = {k: v for k, v in (polnoc.get("lokalizacja") or {}).items() if v is not None}
    if lok:
        ustaw(mt, "lokalizacja", {**(mt.get("lokalizacja") or {}), **lok}, raport)
    g = meta.get("georef")
    if g:
        ustaw(mt, "georef", {"epsg": 2180, "x0": g["x0"], "y0": g["y0"], "obrot_stopnie": 0}, raport)
        linie.append("meta.georef: EPSG:2180 E %s N %s = punkt (0, 0) modelu, osie siatki" % (g["x0"], g["y0"]))
    if mt.get("zero_npm_m") is not None:
        zmiana(raport, "zostawiono", "meta.zero_npm_m", mt["zero_npm_m"])
    elif meta.get("teren_m_npm") is not None:
        ustaw(mt, "zero_npm_m", round(float(meta["teren_m_npm"]), 2), raport)
        linie.append("meta.zero_npm_m: %.2f m n.p.m. (teren w punkcie bazowym)" % mt["zero_npm_m"])
    d = meta.get("dzialka")
    if d:
        granica, naprawiona = obrys_cm(d["obrys_m"])
        rek = {"id": d.get("id") or "DZ1", "granica": granica, "zrodlo": "EGiB (GUGiK ULDK), %s" % data, "dokladnosc_cm": dokl,
               ZNACZNIK: True}
        rek = {k: v for k, v in rek.items() if v is not None}
        # jak sasiedztwo: zastepowana tylko dzialka ze znacznikiem; reczna o tym samym id zostaje, bez duplikatu id
        mj["dzialki"] = scal(mj.get("dzialki") or [], [rek], lambda r: r.get("id") == rek["id"] and r.get(ZNACZNIK) is True,
                             raport, "miejsce.dzialki")
        reczna = any(r.get("id") == rek["id"] and r.get(ZNACZNIK) is not True for r in mj["dzialki"])
        linie.append("dzialka %s z geoportalu: %.0f m2%s%s" % (rek["id"], Polygon(granica).area / 1e4,
                                                              " (obrys niepoprawny - naprawiony)" if naprawiona else "",
                                                              " - w modelu zostaje dzialka reczna o tym id (bez pola z_geoportalu)"
                                                              if reczna else ""))
    if meta.get("sasiednie") is not None:
        nowe = []
        for b in meta["sasiednie"]:
            obrys, naprawiony = obrys_cm(b["obrys_m"])
            s = {"id": b.get("kontekst") or b["id"], "rodzaj": "budynek", "obrys": obrys}
            if len(obrys) < 3:
                linie.append("  obrys %s bez pola - pominiety" % s["id"])
                continue
            if b.get("wys_m") is not None:
                s["wys"] = int(round(b["wys_m"] * 100))
                s["zrodlo"] = "%s %s; wysokość: %s%s; %s" % (
                    b.get("zrodlo"), b["id"], b.get("wys_zrodlo"),
                    "; niski obiekt: budynek podziemny, wiata albo stan sprzed budowy - sprawdzić" if b["wys_m"] < 2 else "", data)
            else:
                s["zrodlo"] = "%s %s; wysokość nieznana - do uzupełnienia; %s" % (b.get("zrodlo"), b["id"], data)
            s["dokladnosc_cm"] = dokl
            s[ZNACZNIK] = True
            nowe.append(s)
            if naprawiony:
                linie.append("  obrys %s niepoprawny - naprawiony" % s["id"])
        mj["sasiedztwo"] = scal(mj.get("sasiedztwo") or [], nowe, lambda r: r.get(ZNACZNIK) is True, raport, "miejsce.sasiedztwo")
        linie.append("sasiedztwo z geoportalu: %d budynkow (z wysokoscia: %d)" % (len(nowe), sum("wys" in s for s in nowe)))
    if meta.get("budynek"):
        linie.append("budynek w punkcie (%s) nie trafia do modelu - opisz go jako obiekt albo modul (obrys w meta.budynek)"
                     % meta["budynek"].get("id"))
    return linie


def wpisz_teren(M, teren, raport=None, nadpisz=False):
    """miejsce.teren z <nazwa>_teren.json (z w cm wzgledem +-0); teren bez znacznika z_geoportalu (np. z pomiaru)
    zostaje, chyba ze nadpisz=True. Zwraca linie opisu, zmiany dopisuje do raportu."""
    raport = {} if raport is None else raport
    pkt = [p for p in teren.get("punkty") or [] if isinstance(p, list) and len(p) == 3]
    if not pkt:
        return ["teren: plik bez punktow - miejsce.teren bez zmian"]
    M["miejsce"] = M.get("miejsce") or {}
    stary = M["miejsce"].get("teren") or {}
    if stary.get("punkty") and not stary.get(ZNACZNIK) and not nadpisz:
        opis = "%s, %d punktow" % (stary.get("zrodlo") or "bez zrodla", len(stary["punkty"]))
        zmiana(raport, "zostawiono", "miejsce.teren", "%s - teren z NMT pominiety (--nadpisz-teren)" % opis)
        return ["teren: istniejacy teren nie pochodzi z geoportalu (%s) - teren z NMT pominieto; --nadpisz-teren go wymusza" % opis]
    mt, linie = M.setdefault("meta", {}), []
    if mt.get("zero_npm_m") is None:
        ustaw(mt, "zero_npm_m", round(float(min(pkt, key=lambda p: p[0] ** 2 + p[1] ** 2)[2]), 2), raport)
        linie.append("meta.zero_npm_m: %.2f m n.p.m. (punkt terenu najblizszy punktowi bazowemu)" % mt["zero_npm_m"])
    z0 = float(mt["zero_npm_m"])
    M["miejsce"]["teren"] = {"punkty": [[p[0], p[1], round((p[2] - z0) * 100, 1)] for p in pkt],
                             "zrodlo": "%s, krok %s m, %s" % (teren.get("zrodlo"), teren.get("krok_m"), teren.get("data")),
                             "dokladnosc_cm": teren.get("dokladnosc_cm"), ZNACZNIK: True}
    zmiana(raport, "zastapiono" if stary.get("punkty") else "dodano", "miejsce.teren", "%d punktow" % len(pkt))
    z = [p[2] for p in M["miejsce"]["teren"]["punkty"]]
    linie.append("teren z NMT: %d punktow, z od %+.1f do %+.1f cm wzgledem +-0 (= %.2f m n.p.m.)" % (len(pkt), min(z), max(z), z0))
    dz = model.dzialka(M)
    x, y = [p[0] for p in pkt], [p[1] for p in pkt]
    if dz is not None and not (min(x) <= dz.centroid.x <= max(x) and min(y) <= dz.centroid.y <= max(y)):
        linie.append("uwaga: punkty terenu nie obejmuja dzialki - czy plik terenu pochodzi z tego samego wywolania geoportal.py?")
    return linie


def wpisz_plan(M, plan, raport=None):
    """miejsce.plan_miejscowy z wyniku narzedzia/plan_miejscowy.py: nazwa, symbol, przeznaczenie, odnosnik i zrodlo;
    parametry i pola bez nowej wartosci zostaja. Zwraca opis albo None (brak planu w usludze - model bez zmian)."""
    raport = {} if raport is None else raport
    tereny = plan.get("tereny") or []
    if plan.get("brak_w_usludze") or not (tereny or plan.get("nazwa") or plan.get("odnosnik")):
        zmiana(raport, "zostawiono", "miejsce.plan_miejscowy", "brak planu w usludze")
        return None
    symbole = [t["symbol"] for t in tereny if t.get("symbol")]
    przezn = [(t.get("symbol"), t["przeznaczenie"]) for t in tereny if t.get("przeznaczenie")]
    nowe = {"nazwa": plan.get("nazwa"), "symbol": ", ".join(symbole),
            "przeznaczenie": przezn[0][1] if len(tereny) == 1 and przezn else
            "; ".join("%s: %s" % (s, p) if s else p for s, p in przezn),
            "odnosnik": plan.get("odnosnik"), "zrodlo": ", ".join(str(x) for x in (plan.get("zrodlo"), plan.get("data")) if x)}
    nowe = {k: v for k, v in nowe.items() if v}
    M["miejsce"] = M.get("miejsce") or {}
    stary = M["miejsce"].get("plan_miejscowy") or {}
    pm = {**stary, **nowe}
    if pm != stary:
        zmiana(raport, "zastapiono" if any(k in stary for k in nowe) else "dodano", "miejsce.plan_miejscowy", ", ".join(nowe))
    if "parametry" in stary:
        zmiana(raport, "zostawiono", "miejsce.plan_miejscowy.parametry")
    M["miejsce"]["plan_miejscowy"] = pm
    return "miejsce.plan_miejscowy: %s%s" % (nowe.get("symbol") or "bez symbolu terenu", ", " + nowe["nazwa"] if nowe.get("nazwa") else "")


def czytaj(sciezka, opis):
    try:
        with open(sciezka, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print("plik %s (%s) nieczytelny: %s - pominieto" % (sciezka, opis, e))
        return None


def main():
    ap = argparse.ArgumentParser(description="Dane z narzedzia/geoportal.py i plan_miejscowy.py do modelu zamierzenia.")
    ap.add_argument("model", help="plik modelu zamierzenia (bez pliku - nowy szkielet)")
    ap.add_argument("--meta", required=True, help="<nazwa>_meta.json z narzedzia/geoportal.py")
    ap.add_argument("--teren", help="<nazwa>_teren.json z narzedzia/geoportal.py --teren")
    ap.add_argument("--nadpisz-teren", action="store_true", help="teren z NMT zastepuje takze teren spoza geoportalu (np. z pomiaru)")
    ap.add_argument("--plan", help="<nazwa>_plan_miejscowy.json z narzedzia/plan_miejscowy.py")
    ap.add_argument("--id", help="projekt.id nowego modelu (domyslnie nazwa pliku)")
    a = ap.parse_args()
    meta = czytaj(a.meta, "meta")
    if not isinstance(meta, dict):
        return 1
    sciezka = Path(a.model)
    if sciezka.is_file():
        M = model.wczytaj(sciezka)
        rodzaj = model.rodzaj_pliku(M)
        if rodzaj != "zamierzenie":
            print("To %s. z_geoportalu.py uzupelnia model zamierzenia (zamierzenie/SCHEMAT.md)." % (
                "model lokalu (modul wnetrz) - otoczenie lokalu daje narzedzia/geoportal.py (_kontekst.json)"
                if rodzaj == "lokal" else "nie jest model zamierzenia"))
            return 2
        g = (M.get("meta") or {}).get("georef")
        if inny_georef(g, meta):
            print("model ma meta.georef %s, a punkt bazowy z %s to %s: obiekty modelu leza w innym ukladzie niz dane "
                  "geoportalu - model bez zmian (uzyj meta z tym samym punktem bazowym albo nowego pliku modelu)"
                  % (json.dumps(g), a.meta, json.dumps(meta.get("georef"))))
            return 1
        if not g and (M.get("obiekty") or M.get("moduly")):
            print("uwaga: model mial obiekty bez meta.georef - przyjeto, ze leza w ukladzie punktu bazowego (sprawdz na R-01 z --orto)")
        if a.id and a.id != model.projekt(M)["id"]:
            print("model istnieje: --id pominiete (projekt.id = %s)" % model.projekt(M)["id"])
    else:
        M = szkielet(re.sub(r"\s+", "_", a.id or sciezka.stem))
        print("nowy model %s (projekt.id = %s)" % (sciezka, M["meta"]["projekt"]["id"]))
    raport = {}
    for linia in wpisz_meta(M, meta, raport):
        print(linia)
    teren = czytaj(a.teren, "teren") if a.teren else None
    if isinstance(teren, dict):
        for linia in wpisz_teren(M, teren, raport, a.nadpisz_teren):
            print(linia)
    plan = czytaj(a.plan, "plan miejscowy") if a.plan else None
    if isinstance(plan, dict):
        print(wpisz_plan(M, plan, raport) or "plan miejscowy: brak planu w usludze - miejsce.plan_miejscowy bez zmian (sprawdz w gminie)")
    wypisz(raport)
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    print("zapisano", model.zapisz(M, sciezka))
    return 0


if __name__ == "__main__":
    sys.exit(main())
