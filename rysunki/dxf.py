"""Rzut lokalu do DXF (R2018, milimetry) z warstwami, do dalszej pracy w CAD.
Model zamierzenia: plan (<id>_plan.dxf) z dzialkami, terenem, sasiedztwem, obiektami i modulami.

    python rysunki/dxf.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/dxf.py przyklad/ogrod/model/projekt.json

Warstwy maja prefiks z meta.projekt.id: _SCIANY_NOSNE, _SCIANY, _OTWORY, _SZACHTY,
_GRZEJNIKI, _MEBLE, _POMIESZCZENIA, _OPISY, _WYMIARY, _ELEKTRYKA. Wymiary lic
pomieszczen sa prawdziwymi wymiarami DXF (edytowalne). Na koncu audyt ezdxf.
Plan zamierzenia: _DZIALKA, _WARSTWICE (polilinie na swojej rzednej), _SASIEDZTWO,
warstwa na kazda kategorie legendy i _OPISY (id obiektow); punkty to okregi (korona
roslin, 20 cm dla innych); moduly wnetrz jak rzut lokalu, na warstwach z id lokalu.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ezdxf
from shapely.geometry import LineString, Polygon

from lokal import model, geometria
from zamierzenie import model as zmodel, moduly, teren

MM = 10.0  # cm -> mm
WARSTWY = {"SCIANY_NOSNE": 5, "SCIANY": 8, "OTWORY": 30, "SZACHTY": 6, "GRZEJNIKI": 1, "MEBLE": 3,
           "POMIESZCZENIA": 9, "OPISY": 7, "WYMIARY": 2, "ELEKTRYKA": 4}
TEKST = 200  # mm: wysokosc opisow na planie zamierzenia
SRODEK = ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER


def _mm(pkt, T=None):
    """Punkty cm -> mm; z T (zamierzenie/moduly.transformacja) najpierw obrot i przesuniecie."""
    if T is not None:
        pkt = [moduly.punkt(T, x, y) for x, y in pkt]
    return [(x * MM, y * MM) for x, y in pkt]


def _obrysy(geom):
    czesci = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    for g in czesci:
        if g.geom_type == "Polygon" and not g.is_empty:
            yield list(g.exterior.coords)
            for h in g.interiors:
                yield list(h.coords)


def zbuduj(M, doc=None, T=None):
    """Rzut lokalu w nowym dokumencie albo w podanym (doc). Z T (zamierzenie/moduly.transformacja)
    punkty, katy lukow i wymiary sa w ukladzie modelu zamierzenia; teksty zostaja poziome."""
    pref = re.sub(r"[^A-Z0-9_]", "_", model.projekt(M)["id"].upper())
    if doc is None:
        doc = ezdxf.new("R2018", setup=True)
        doc.header["$INSUNITS"] = 4
        doc.header["$MEASUREMENT"] = 1
    for nazwa, kolor in WARSTWY.items():
        if "%s_%s" % (pref, nazwa) not in doc.layers:
            doc.layers.add("%s_%s" % (pref, nazwa), color=kolor)
    L = lambda n: "%s_%s" % (pref, n)
    P = lambda x, y: _mm([(x, y)], T)[0]

    def PT(x, y, dx=0, dy=0):
        """Punkt tekstu: (x, y) z modelu, przesuniecie (dx, dy) cm w ukladzie arkusza."""
        if T is None:
            return ((x + dx) * MM, (y + dy) * MM)
        X, Y = P(x, y)
        return (X + dx * MM, Y + dy * MM)
    msp = doc.modelspace()

    typy = {s["id"]: s for s in M["sciany"]}
    for sid, g in geometria.bryly_scian(M).items():
        warstwa = L("SCIANY_NOSNE" if typy[sid].get("nosna") else "SCIANY")
        for ring in _obrysy(g):
            msp.add_lwpolyline(_mm(ring, T), close=True, dxfattribs={"layer": warstwa})
    for o in M.get("otwory", []):
        x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
        msp.add_lwpolyline(_mm([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], T), close=True, dxfattribs={"layer": L("OTWORY")})
        l = o.get("luk")
        if l:
            od, do = l["od"], l["do"]
            if T is not None:
                od, do = od + T["kat"], do + T["kat"]
            msp.add_arc(P(l["c"][0], l["c"][1]), l["r"] * MM, od, do, dxfattribs={"layer": L("OTWORY")})
        msp.add_text(o["id"], height=60, dxfattribs={"layer": L("OPISY")}).set_placement(
            PT((x0 + x1) / 2, (y0 + y1) / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for sz in M.get("szachty", []):
        x0, y0, x1, y1 = geometria.prostokat(sz["box"]).bounds
        msp.add_lwpolyline(_mm([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], T), close=True, dxfattribs={"layer": L("SZACHTY")})
        msp.add_line(P(x0, y0), P(x1, y1), dxfattribs={"layer": L("SZACHTY")})
        msp.add_line(P(x0, y1), P(x1, y0), dxfattribs={"layer": L("SZACHTY")})
    for gz in M.get("grzejniki", []):
        x0, y0, x1, y1 = geometria.prostokat(gz["box"]).bounds
        msp.add_lwpolyline(_mm([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], T), close=True, dxfattribs={"layer": L("GRZEJNIKI")})
    for e in model.elementy(M):
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        if e.get("ksztalt") == "kolo":
            msp.add_circle(P((x0 + x1) / 2, (y0 + y1) / 2), (x1 - x0) / 2 * MM, dxfattribs={"layer": L("MEBLE")})
        else:
            msp.add_lwpolyline(_mm([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], T), close=True, dxfattribs={"layer": L("MEBLE")})
        msp.add_text(e["id"], height=50, dxfattribs={"layer": L("OPISY")}).set_placement(
            PT((x0 + x1) / 2, (y0 + y1) / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    pola = geometria.pola(M)
    for nr, w in geometria.wielokaty(M).items():
        if w is None:
            continue
        for ring in _obrysy(w):
            msp.add_lwpolyline(_mm(ring, T), close=True, dxfattribs={"layer": L("POMIESZCZENIA")})
        p = model.pomieszczenie(M, nr)
        x, y = p["stamp"]
        for i, t in enumerate((nr, p["nazwa"], "%.2f m2" % pola[nr])):
            msp.add_text(t, height=90 if i == 0 else 60, dxfattribs={"layer": L("OPISY")}).set_placement(
                PT(x, y, 0, -i * 14), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        for lico in geometria.lica(M, nr):
            if lico["dl"] < 12:
                continue
            (ax, ay), (bx, by) = lico["a"], lico["b"]
            # lica biegna przeciwnie do zegara, wiec dodatnia odleglosc kladzie wymiar do wnetrza
            wym = msp.add_aligned_dim(p1=P(ax, ay), p2=P(bx, by), distance=18 * MM,
                                      dimstyle="EZDXF", override={"dimtxt": 60, "dimasz": 40, "dimdec": 0},
                                      dxfattribs={"layer": L("WYMIARY")})
            wym.render()
    for e in M.get("elektryka", []):
        x, y = e["xy"]
        msp.add_circle(P(x, y), 40, dxfattribs={"layer": L("ELEKTRYKA")})
        msp.add_text("%s h%s" % (e["id"], e.get("h", "")), height=40, dxfattribs={"layer": L("ELEKTRYKA")}).set_placement(
            PT(x, y, 6, 6))
    return doc


def zbuduj_zamierzenie(M):
    """Plan modelu zamierzenia: dzialki, warstwice, sasiedztwo, obiekty na warstwach kategorii
    z opisem id, moduly wnetrz przez zbuduj(lokal, doc, T)."""
    pref = re.sub(r"[^A-Z0-9_]", "_", model.projekt(M)["id"].upper())
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    msp = doc.modelspace()

    def L(nazwa, kolor=7, hex_=None):
        n = "%s_%s" % (pref, re.sub(r"[^A-Z0-9_]", "_", nazwa.upper()))
        if n not in doc.layers:
            w = doc.layers.add(n, color=kolor)
            if hex_:
                w.rgb = tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))
        return n

    zajete = {}

    def opis(t, x, y):
        """Id obiektu; kolejne opisy w tym samym miejscu (np. budynek i dach) jeden pod drugim."""
        k = (round(x), round(y))
        n = zajete[k] = zajete.get(k, -1) + 1
        msp.add_text(t, height=TEKST, dxfattribs={"layer": L("OPISY")}).set_placement(
            (x * MM, y * MM - n * 1.5 * TEKST), align=SRODEK)

    for nazwa, kolor in (("DZIALKA", 1), ("WARSTWICE", 8), ("SASIEDZTWO", 9)):
        L(nazwa, kolor)
    for k in zmodel.legenda(M):
        L(k, 7, zmodel.styl(M, k)["plan"]["linia"])
    L("OPISY")
    for d in (M.get("miejsce") or {}).get("dzialki") or []:
        msp.add_lwpolyline(_mm(d["granica"]), close=True, dxfattribs={"layer": L("DZIALKA")})
    for z, linie in teren.warstwice(teren.siatka(M)):
        for l in linie:
            msp.add_lwpolyline(_mm(l), dxfattribs={"layer": L("WARSTWICE"), "elevation": z * MM})
            x, y = LineString(l).interpolate(0.5, normalized=True).coords[0]
            msp.add_text(("%+.2f" % (z / 100)).replace(".", ","), height=0.75 * TEKST,
                         dxfattribs={"layer": L("WARSTWICE")}).set_placement((x * MM, y * MM), align=SRODEK)
    for s in (M.get("miejsce") or {}).get("sasiedztwo") or []:
        msp.add_lwpolyline(_mm(s["obrys"]), close=True, dxfattribs={"layer": L("SASIEDZTWO")})
        opis(s["id"], *Polygon(s["obrys"]).representative_point().coords[0])
    for o in zmodel.obiekty(M):
        st, g = zmodel.styl(M, o.get("kategoria")), zmodel.ksztalt(o)
        w = L(o.get("kategoria") or "inne", 7, st["plan"]["linia"])
        if g.geom_type == "Point":
            roslina = st["plan"]["symbol"] in ("drzewo", "krzew") and o.get("srednica")
            msp.add_circle((g.x * MM, g.y * MM), (o["srednica"] / 2 if roslina else 10) * MM, dxfattribs={"layer": w})
            p = (g.x, g.y)
        elif g.geom_type == "LineString":
            msp.add_lwpolyline(_mm(g.coords), dxfattribs={"layer": w})
            p = g.interpolate(0.5, normalized=True).coords[0]
        else:
            msp.add_lwpolyline(_mm(g.exterior.coords[:-1]), close=True, dxfattribs={"layer": w})
            p = g.representative_point().coords[0]
        opis(o["id"], *p)
    for mod in moduly.moduly(M):
        zbuduj(moduly.wczytaj_modul(M, mod), doc, moduly.transformacja(M, mod))
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--wyjscie")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    rodzaj = zmodel.rodzaj_pliku(M)
    if rodzaj is None:
        print("Nie rozpoznano modelu: lokal ma sekcje sciany, zamierzenie meta.rodzaj i obiekty, moduly albo miejsce.")
        return 2
    doc = zbuduj(M) if rodzaj == "lokal" else zbuduj_zamierzenie(M)
    baza = model.sciezka_wyniku(M, "rzut" if rodzaj == "lokal" else "plan", a.wyjscie)
    sciezka = baza.with_name(baza.name + ".dxf")
    doc.saveas(sciezka)
    audyt = ezdxf.readfile(sciezka).audit()
    warstw = sum(1 for w in doc.layers if w.dxf.name not in ("0", "Defpoints"))
    print("zapisano %s, warstw %d, bledow audytu %d" % (sciezka, warstw, len(audyt.errors)))
    return 1 if audyt.errors else 0


if __name__ == "__main__":
    sys.exit(main())
