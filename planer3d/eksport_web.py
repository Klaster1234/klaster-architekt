"""Dane planera 3D w przegladarce: geometria pochodna z modelu, meble z kolorami po
wariantach domyslnych, okladziny, punkty swietlne, tokeny i warianty wykonczenia.
Model zamierzenia: teren, dzialki, sasiedztwo, legenda, obiekty z siatkami 3D i moduly wnetrz.

    python planer3d/eksport_web.py przyklad/mieszkanie/model/lokal_projekt.json
    python planer3d/eksport_web.py przyklad/mieszkanie/model/lokal_projekt.json --wyjscie robocze/
    python planer3d/eksport_web.py przyklad/ogrod/model/projekt.json

Wynik: <wyjscie>/<id>_planer.json (domyslnie katalog wyjscie/ obok modelu). Serwer
planera (planer3d/serwer.py) uruchamia ten skrypt sam, gdy model albo eksporter sa
nowsze od pliku wynikowego. Wielokaty pomieszczen, kawalki scian wokol otworow i lica
licza sie tak samo jak w rysunkach (lokal/geometria.py), kolory tak samo jak w makiecie
GLB (lokal/model.py: warianty > pole kolor / sciany_kolor / token). Balkon to zwykle
pomieszczenie z "zewnetrzne": true, a balustrada to kawalek sciany o rodzaju "niski".
Pomieszczenie z dziura w wielokacie (szacht albo slup stojacy wolno) dostaje dodatkowe
pole "dziury". Planer przebarwia cele wariantow sam, dlatego plik niesie tez tokeny
i opcje wariantow.

Model zamierzenia (rozpoznany przez zamierzenie/model.py: rodzaj_pliku) daje dane ze
znacznikiem "rodzaj_modelu": "zamierzenie" dla strony planer3d/zamierzenie.html. Siatki
terenu i obiektow licza sie jak w makiecie GLB (zamierzenie/bryly.py: siatki), w cm
w ukladzie modelu z osia z w gore, wspolrzedne zaokraglone do 0,1 cm. Sasiedztwo to
obrys i zakres wysokosci od terenu w srodku obrysu (planer wyciaga obrys w pionie, jak
bryly.siatki). Modul wnetrz to dane planera lokalu (jak wyzej, w ukladzie lokalu),
jego przesuniecie, obrot i poziom oraz sciany i pomieszczenia w ukladzie zamierzenia.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from lokal import model, geometria
from zamierzenie import bryly, model as zmodel, moduly as zmoduly, teren as zteren

# gdy model nie podaje polozenia: geometryczny srodek Polski (slonce dziala, a planer pokazuje wspolrzedne)
DOMYSLNE_POLOZENIE = {"lat": 52.1, "lon": 19.5, "strefa": "Europe/Warsaw"}


def r1(v):
    return round(float(v), 1)


def prost(b):
    x0, y0, x1, y1 = geometria.prostokat(b).bounds
    return [r1(x0), r1(y0), r1(x1), r1(y1)]


def bez_minus_zera(v, dokl=3):
    return round(float(v), dokl) + 0.0


def polnoc(M):
    p = M.get("meta", {}).get("polnoc") or {}
    lok = p.get("lokalizacja") or {}
    if "lat" not in lok or "lon" not in lok:
        print("uwaga: brak meta.polnoc.lokalizacja (lat, lon) - slonce liczone dla srodka Polski")
    if "azymut_osi_Y_stopnie" not in p:
        print("uwaga: brak meta.polnoc.azymut_osi_Y_stopnie - przyjeto 0 (gora rzutu = polnoc)")
    return {"azymut_osi_Y_stopnie": float(p.get("azymut_osi_Y_stopnie", 0)),
            "lokalizacja": {"lat": float(lok.get("lat", DOMYSLNE_POLOZENIE["lat"])),
                            "lon": float(lok.get("lon", DOMYSLNE_POLOZENIE["lon"])),
                            "strefa": lok.get("strefa") or DOMYSLNE_POLOZENIE["strefa"]}}


def pomieszczenia(M):
    wynik = []
    pola = geometria.pola(M)
    wielokaty = geometria.wielokaty(M)
    for p in M["pomieszczenia"]:
        w = wielokaty.get(p["nr"])
        if w is None:
            print("pomieszczenie %s: stamp nie lezy w zamknietej przestrzeni - pominiete" % p["nr"])
            continue
        w = orient(w.simplify(0), 1.0)  # bez wierzcholkow wspolliniowych; obrys przeciwnie do zegara, dziury zgodnie
        ar = (M.get("aranzacja") or {}).get(p["nr"], {})
        rek = {
            "nr": p["nr"], "nazwa": p.get("nazwa") or p["nr"], "zewnetrzne": bool(p.get("zewnetrzne")),
            "m2": pola[p["nr"]], "pow_m2": p.get("pow_m2"), "stamp": [r1(v) for v in p["stamp"]],
            "poligon": pierscien(w.exterior),
            "podloga": p.get("podloga") or "", "kolor_scian": model.kolor(M, ("sciany", p["nr"])),
            "status": ar.get("status"), "kontrole": ar.get("kontrole", []),
            "wymiary_kontrolne": ar.get("wymiary_kontrolne", []),
        }
        if w.interiors:  # szacht albo slup stojacy wolno w pomieszczeniu (pole opcjonalne, tylko gdy wystepuje)
            rek["dziury"] = [pierscien(r) for r in w.interiors]
        wynik.append(rek)
    return wynik


def pierscien(r):
    return [[r1(x), r1(y)] for x, y in list(r.coords)[:-1]]


def sciany(M):
    wynik = []
    for s in M["sciany"]:
        for x0, y0, x1, y1, z0, z1, rodzaj in geometria.kawalki_sciany(M, s):
            wynik.append({"id": s["id"], "nosna": bool(s.get("nosna")), "box": [r1(x0), r1(y0), r1(x1), r1(y1)],
                          "z": [r1(z0), r1(z1)], "rodzaj": rodzaj})
    return wynik


def otwory(M):
    sc = {s["id"]: s for s in M["sciany"]}
    wynik = []
    for o in M.get("otwory", []):
        wynik.append({
            "id": o["id"], "rodzaj": o["rodzaj"], "sciana": o["sciana"],
            "box": [r1(v) for v in geometria.prostokat_otworu(M, o)],
            "poziomo": geometria.wzdluz_x(sc[o["sciana"]]["pas"]),
            "parapet": o.get("parapet") or 0, "wys_otw": o.get("wys_otw", 205),
            "skrzydlo": o.get("skrzydlo"), "luk": o.get("luk"), "do": o.get("do"),
            "wejscie": bool(o.get("wejscie")), "pokoje": geometria.pokoje_otworu(M, o),
        })
    return wynik


def meble(M):
    wynik = {}
    for nr, ar in (M.get("aranzacja") or {}).items():
        lista = []
        for e in ar.get("elementy", []):
            rek = {k: v for k, v in e.items() if not k.startswith("_")}
            rek.update(box=prost(e["box"]), wys=list(e.get("wys", [0, 75])),
                       kolor=model.kolor(M, ("element", e["id"])), kategoria=model.kategoria(e.get("rodzaj")))
            lista.append(rek)
        wynik[nr] = lista
    return wynik


def swiatla(M):
    return [{"id": e["id"], "pomieszczenie": e.get("pomieszczenie"), "xy": [r1(v) for v in e["xy"]], "h": e.get("h"),
             "typ": e.get("typ", ""), "wariant": e.get("wariant"), "opis": e.get("opis", "")}
            for e in M.get("elektryka", []) if e.get("xy") and model.jest_swiatlem(e)]


def lico_okladziny(M, okl):
    """Lico pomieszczenia, na ktorym lezy odcinek okladziny (jak w rysunki/glb.py)."""
    (ax, ay), (bx, by) = okl["odcinek"]
    for lico in geometria.lica(M, okl["pomieszczenie"]):
        (px, py), (qx, qy) = lico["a"], lico["b"]
        dl = lico["dl"]

        def odl(x, y):
            return abs((qx - px) * (y - py) - (qy - py) * (x - px)) / dl
        if odl(ax, ay) < 1 and odl(bx, by) < 1:
            return lico
    return None


def okladziny(M):
    wynik = []
    for o in (M.get("wykonczenie") or {}).get("okladziny", []):
        lico = lico_okladziny(M, o)
        if lico is None:
            print("okladzina %s: nie lezy na licu pomieszczenia %s - pominieta" % (o["id"], o.get("pomieszczenie")))
            continue
        (ax, ay), (bx, by) = o["odcinek"]
        wynik.append({
            "id": o["id"], "pomieszczenie": o["pomieszczenie"], "a": [r1(ax), r1(ay)], "b": [r1(bx), r1(by)],
            "normalna": [bez_minus_zera(lico["normalna"][0]), bez_minus_zera(lico["normalna"][1])],
            "z": [r1(v) for v in o["z"]], "token": model.token_celu(M, ("okladzina", o["id"])),
            "hex": model.kolor(M, ("okladzina", o["id"])), "wzor": o.get("wzor"),
        })
    return wynik


def tokeny(M):
    return {n: {"hex": model.hex_tokenu(M, n), "opis": t.get("opis", "")}
            for n, t in model.tokeny(M).items()}


def warianty(M):
    wynik = []
    for w in model.warianty(M):
        opcje = [{"nazwa": op.get("nazwa") or op.get("token"), "token": op.get("token"),
                  "hex": model.hex_tokenu(M, op.get("token"))} for op in w.get("opcje", [])]
        if not opcje:
            print("wariant %s: brak opcji - pominiety" % w["id"])
            continue
        wynik.append({"id": w["id"], "nazwa": w.get("nazwa") or w["id"], "cel": w.get("cel", []), "opcje": opcje,
                      "domyslna": min(max(int(w.get("domyslna", 0)), 0), len(opcje) - 1)})
    return wynik


def dane_planera(M):
    pr = model.projekt(M)
    return {
        "zrodlo": "%s (planer3d/eksport_web.py)" % Path(M["_sciezka"]).name,
        "meta": {"id": pr["id"], "nazwa": pr.get("obiekt") or pr["id"], "polnoc": polnoc(M),
                 "wysokosc": model.wysokosc(M), "rzedna_sufitu": model.rzedna_sufitu(M),
                 "sufit": model.hex_tokenu(M, (M.get("wykonczenie") or {}).get("sufit"), "#F7F6F3"),
                 "obrys": [r1(v) for v in geometria.obrys(M).bounds]},
        "pomieszczenia": pomieszczenia(M),
        "sciany": sciany(M),
        "otwory": otwory(M),
        "szachty": [{"id": s["id"], "box": prost(s["box"]), "opis": s.get("opis", "")} for s in M.get("szachty", [])],
        "grzejniki": [{"id": g["id"], "pomieszczenie": g.get("pomieszczenie"), "typ": g.get("typ", ""),
                       "box": prost(g["box"]), "z": list(g.get("wys", [15, 75]))} for g in M.get("grzejniki", [])],
        "kontekst": [{"id": k["id"], "rodzaj": k.get("rodzaj", ""), "box": prost(k["box"]),
                      "z": list(k.get("wys", [0, model.wysokosc(M)]))} for k in M.get("kontekst", [])],
        "meble": meble(M),
        "swiatla": swiatla(M),
        "tokeny": tokeny(M),
        "okladziny": okladziny(M),
        "warianty": warianty(M),
    }


def obrys2d(g):
    """Punkt [x, y], linia [[x, y], ...] albo pierscien wielokata bez powtorzonego pierwszego punktu (cm z 0,1)."""
    if g.geom_type == "Point":
        return [r1(g.x), r1(g.y)]
    if g.geom_type == "LineString":
        return [[r1(x), r1(y)] for x, y in g.coords]
    return pierscien(g.exterior)


def siatka_json(m):
    """{"pozycje": [x, y, z, ...], "trojkaty": [i, j, k, ...]} - cm z 0,1, uklad modelu (z w gore)."""
    return {"pozycje": (np.round(np.asarray(m.vertices, dtype=float), 1) + 0.0).ravel().tolist(),
            "trojkaty": np.asarray(m.faces, dtype=int).ravel().tolist()}


def meta_zamierzenia(M, obrys):
    meta = M.get("meta") or {}
    if "lat" not in (meta.get("lokalizacja") or {}) or "lon" not in (meta.get("lokalizacja") or {}):
        print("uwaga: brak meta.lokalizacja (lat, lon) - slonce liczone dla srodka Polski")
    if "azymut_osi_Y_stopnie" not in (meta.get("polnoc") or {}):
        print("uwaga: brak meta.polnoc.azymut_osi_Y_stopnie - przyjeto 0 (gora rzutu = polnoc)")
    pr, lok = zmodel.projekt(M), zmodel.lokalizacja(M)
    wynik = {"id": pr["id"], "nazwa": pr.get("obiekt") or pr["id"], "rodzaj": meta.get("rodzaj"),
             "polnoc": {"azymut_osi_Y_stopnie": zmodel.azymut_polnocy(M),
                        "lokalizacja": {"lat": float(lok["lat"]), "lon": float(lok["lon"]),
                                        "strefa": lok["strefa"] or zmodel.DOMYSLNE_POLOZENIE["strefa"]}},
             "obrys": [r1(v) for v in obrys]}
    if meta.get("zero_npm_m") is not None:
        wynik["zero_npm_m"] = float(meta["zero_npm_m"])
    return wynik


def legenda_zamierzenia(M):
    kategorie = list(zmodel.legenda(M)) + [o.get("kategoria") for o in zmodel.obiekty(M)]
    wynik = {}
    for k in kategorie:
        if k is not None and k not in wynik:
            st = zmodel.styl(M, k)
            wynik[k] = {"nazwa": st["nazwa"], "wypelnienie": st["plan"]["wypelnienie"], "linia": st["plan"]["linia"],
                        "kolor3d": st["bryla"]["kolor"]}
    return wynik


def obiekty_zamierzenia(M, s, siatki):
    wynik = []
    for o in zmodel.obiekty(M):
        st, g = zmodel.styl(M, o.get("kategoria")), zmodel.ksztalt(o)
        rek = {"id": o["id"], "kategoria": o.get("kategoria"),
               "ksztalt": st["ksztalt"] or {"Polygon": "powierzchnia", "LineString": "linia", "Point": "punkt"}[g.geom_type],
               "obrys2d": obrys2d(g)}
        if o.get("srednica"):
            rek["srednica"] = r1(o["srednica"])
        m = siatki.get(o["id"])
        rek.update(z=[r1(v) for v in zmodel.zakres_z(M, o, s)], kolizja=bool(st["kolizja"]),
                   siatka=siatka_json(m) if m is not None else None, atrybuty=o.get("atrybuty") or {})
        wynik.append(rek)
    return wynik


def sasiedztwo_zamierzenia(M, s):
    """Obrys i zakres wysokosci od terenu w srodku obrysu (bez wys - plaski, bez bryly), jak bryly.siatki."""
    wynik = []
    for x in (M.get("miejsce") or {}).get("sasiedztwo") or []:
        g = Polygon(x["obrys"])
        zt = zteren.rzedna(s, g.centroid.x, g.centroid.y)
        wynik.append({"id": x["id"], "obrys": obrys2d(g), "z": [r1(zt), r1(zt + (x.get("wys") or 0))]})
    return wynik


def moduly_zamierzenia(M):
    wynik = []
    for mod in zmoduly.moduly(M):
        T = zmoduly.transformacja(M, mod)
        ob = zmoduly.obiekty_modulu(M, mod)
        wynik.append({"id": mod["id"], "dx": r1(T["dx"]), "dy": r1(T["dy"]), "kat": T["kat"], "z0": r1(T["z0"]),
                      "sciany2d": [obrys2d(zmodel.ksztalt(o)) for o in ob if o["kategoria"] == "_sciana"],
                      "pomieszczenia2d": [obrys2d(zmodel.ksztalt(o)) for o in ob if o["kategoria"] == "_pomieszczenie"],
                      "dane": dane_planera(zmoduly.wczytaj_modul(M, mod))})
    return wynik


def dane_zamierzenia(M):
    s = zteren.siatka(M)
    # bez modulow (ida jako dane planera lokalu, planer buduje je jak lokal) i bez sasiedztwa (planer wyciaga obrys sam)
    siatki = bryly.siatki({**M, "moduly": [], "miejsce": {**(M.get("miejsce") or {}), "sasiedztwo": []}})
    i = next((k for k, (nazwa, _, _) in enumerate(siatki) if nazwa == "teren"), None) if s is not None else None
    siatka_terenu = siatki.pop(i)[1] if i is not None else None
    obrys = zmodel.zakres(M)
    if obrys is None and s is not None:
        obrys = (*s["pkt"][:, :2].min(axis=0), *s["pkt"][:, :2].max(axis=0))
    return {
        "zrodlo": "%s (planer3d/eksport_web.py)" % Path(M["_sciezka"]).name,
        "rodzaj_modelu": "zamierzenie",
        "meta": meta_zamierzenia(M, obrys or (0, 0, 0, 0)),
        "teren": siatka_json(siatka_terenu) if siatka_terenu is not None else None,
        "dzialki": [{"id": d.get("id"), "granica": obrys2d(Polygon(d["granica"]))} for d in (M.get("miejsce") or {}).get("dzialki") or []],
        "sasiedztwo": sasiedztwo_zamierzenia(M, s),
        "legenda": legenda_zamierzenia(M),
        "obiekty": obiekty_zamierzenia(M, s, {nazwa: m for nazwa, m, _ in siatki}),
        "moduly": moduly_zamierzenia(M),
    }


def main():
    ap = argparse.ArgumentParser(description="Dane planera 3D (<id>_planer.json) z modelu lokalu albo zamierzenia")
    ap.add_argument("model", help="plik modelu lokalu albo modelu zamierzenia (JSON)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    rodzaj = zmodel.rodzaj_pliku(M)
    if rodzaj is None:
        print("Nie rozpoznano modelu: lokal ma sekcje sciany, zamierzenie meta.rodzaj i obiekty, moduly albo miejsce.")
        return 2
    dane = dane_planera(M) if rodzaj == "lokal" else dane_zamierzenia(M)
    sciezka = model.sciezka_wyniku(M, "planer", a.wyjscie)
    sciezka = sciezka.with_name(sciezka.name + ".json")
    roboczy = sciezka.with_name(sciezka.name + ".tmp")
    with open(roboczy, "w", encoding="utf-8") as f:
        if rodzaj == "lokal":
            json.dump(dane, f, ensure_ascii=False)
        else:
            json.dump(dane, f, ensure_ascii=False, separators=(",", ":"))
    roboczy.replace(sciezka)  # serwer nigdy nie czyta pliku w polowie zapisu
    if rodzaj == "lokal":
        print("zapisano %s (%.0f kB): %d pomieszczen, %d kawalkow scian, %d otworow, %d elementow, "
              "%d punktow swiatla, %d okladzin, %d wariantow" % (
                  sciezka, sciezka.stat().st_size / 1024, len(dane["pomieszczenia"]), len(dane["sciany"]),
                  len(dane["otwory"]), sum(len(v) for v in dane["meble"].values()), len(dane["swiatla"]),
                  len(dane["okladziny"]), len(dane["warianty"])))
    else:
        trojkaty = sum(len(o["siatka"]["trojkaty"]) // 3 for o in dane["obiekty"] if o["siatka"])
        print("zapisano %s (%.0f kB): %d obiektow (%d trojkatow), teren %d trojkatow, %d dzialek, %d obiektow "
              "sasiedztwa, %d modulow" % (
                  sciezka, sciezka.stat().st_size / 1024, len(dane["obiekty"]), trojkaty,
                  len(dane["teren"]["trojkaty"]) // 3 if dane["teren"] else 0, len(dane["dzialki"]),
                  len(dane["sasiedztwo"]), len(dane["moduly"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
