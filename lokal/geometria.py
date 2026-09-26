"""Geometria pochodna z modelu: bryly scian, kawalki wokol otworow, wielokaty pomieszczen.

    from lokal import model, geometria
    M = model.wczytaj("przyklad/mieszkanie/model/lokal_projekt.json")
    print(geometria.pola(M))

Pomieszczen nie rysuje sie w modelu. Wielokat to najmniejsza sciana poligonizacji
lic scian, szacht, stref wirtualnych i domkniec otworow, ktora zawiera punkt stamp.
Wyniki licza sie raz na model (M["_cache"]).
"""
import math
from shapely.geometry import box, LineString, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polygonize

from lokal import model as _model


def prostokat(b):
    x0, y0, x1, y1 = b
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def wzdluz_x(pas):
    x0, y0, x1, y1 = pas
    return abs(x1 - x0) >= abs(y1 - y0)


def _cache(M, klucz, licz):
    c = M.setdefault("_cache", {})
    if klucz not in c:
        c[klucz] = licz()
    return c[klucz]


def _sciany(M):
    return {s["id"]: s for s in M["sciany"]}


def prostokat_otworu(M, otwor):
    """(x0, y0, x1, y1) otworu przez cala grubosc sciany."""
    s = _sciany(M)[otwor["sciana"]]
    x0, y0, x1, y1 = prostokat(s["pas"]).bounds
    a, b = sorted(otwor["zakres"])
    return (a, y0, b, y1) if wzdluz_x(s["pas"]) else (x0, a, x1, b)


def bryly_scian(M):
    """id sciany -> wielokat pasa z wycietymi otworami (rzut)."""
    def licz():
        wynik = {s["id"]: prostokat(s["pas"]) for s in M["sciany"]}
        sc = _sciany(M)
        for o in M.get("otwory", []):
            x0, y0, x1, y1 = prostokat_otworu(M, o)
            if wzdluz_x(sc[o["sciana"]]["pas"]):
                wyciecie = box(x0, y0 - 1, x1, y1 + 1)
            else:
                wyciecie = box(x0 - 1, y0, x1 + 1, y1)
            wynik[o["sciana"]] = wynik[o["sciana"]].difference(wyciecie)
        return wynik
    return _cache(M, "bryly_scian", licz)


def kawalki_sciany(M, sciana):
    """Pas sciany pociety wzdluz osi: (x0, y0, x1, y1, z0, z1, rodzaj).

    rodzaj: pelny | niski (sciana z polem wys, np. balustrada) | podokiennik | nadproze.
    """
    H = _model.wysokosc(M)
    x0, y0, x1, y1 = prostokat(sciana["pas"]).bounds
    poziomo = wzdluz_x(sciana["pas"])
    z_dol, z_gora = sciana.get("wys", [0, H])
    pelny = "niski" if "wys" in sciana else "pelny"
    a0, a1 = (x0, x1) if poziomo else (y0, y1)
    otwory = sorted((min(o["zakres"]), max(o["zakres"]), o)
                    for o in M.get("otwory", []) if o["sciana"] == sciana["id"])
    kawalki, kursor = [], a0
    for oa, ob, o in otwory:
        if oa > kursor:
            kawalki.append((kursor, oa, z_dol, z_gora, pelny))
        parapet = o.get("parapet") or 0
        if parapet > z_dol:
            kawalki.append((oa, ob, z_dol, min(parapet, z_gora), "podokiennik"))
        gora = o.get("wys_otw", 205)
        if gora < z_gora:
            kawalki.append((oa, ob, max(gora, z_dol), z_gora, "nadproze"))
        kursor = max(kursor, ob)
    if kursor < a1:
        kawalki.append((kursor, a1, z_dol, z_gora, pelny))
    wynik = []
    for ka, kb, z0, z1, rodzaj in kawalki:
        if poziomo:
            wynik.append((ka, y0, kb, y1, z0, z1, rodzaj))
        else:
            wynik.append((x0, ka, x1, kb, z0, z1, rodzaj))
    return wynik


def linie_graniczne(M):
    """Krawedzie bryl scian i szacht, strefy wirtualne i domkniecia otworow w obu licach."""
    linie = [g.boundary for g in bryly_scian(M).values()]
    linie += [prostokat(s["box"]).boundary for s in M.get("szachty", [])]
    linie += [LineString(sv["polilinia"]) for sv in M.get("strefy_wirtualne", [])]
    sc = _sciany(M)
    for o in M.get("otwory", []):
        x0, y0, x1, y1 = prostokat(sc[o["sciana"]]["pas"]).bounds
        a, b = sorted(o["zakres"])
        if wzdluz_x(sc[o["sciana"]]["pas"]):
            linie += [LineString([(a, y0), (b, y0)]), LineString([(a, y1), (b, y1)])]
        else:
            linie += [LineString([(x0, a), (x0, b)]), LineString([(x1, a), (x1, b)])]
    return linie


def wielokaty(M):
    """nr -> wielokat pomieszczenia (None, gdy stamp nie trafia w zamknieta sciane)."""
    def licz():
        twarze = list(polygonize(unary_union(linie_graniczne(M))))
        wynik = {}
        for p in M["pomieszczenia"]:
            pt = Point(*p["stamp"])
            kand = [f for f in twarze if f.contains(pt)]
            wynik[p["nr"]] = orient(min(kand, key=lambda f: f.area), 1.0) if kand else None
        return wynik
    return _cache(M, "wielokaty", licz)


def pola(M):
    return {nr: (round(w.area / 1e4, 2) if w is not None else None) for nr, w in wielokaty(M).items()}


def pomieszczenie_punktu(M, xy, tol=1.0):
    """Numer pomieszczenia zawierajacego punkt (albo lezacego najblizej w granicy tol)."""
    pt = Point(*xy)
    najblizsze = None
    for nr, w in wielokaty(M).items():
        if w is None:
            continue
        d = w.distance(pt)
        if d == 0:
            return nr
        if d <= tol and (najblizsze is None or d < najblizsze[0]):
            najblizsze = (d, nr)
    return najblizsze[1] if najblizsze else None


def pokoje_otworu(M, otwor):
    prost = box(*prostokat_otworu(M, otwor))
    return [nr for nr, w in wielokaty(M).items() if w is not None and w.distance(prost) < 1.0]


def obrys(M):
    """Unia wszystkich scian (z balustradami), szacht i wielokatow pomieszczen."""
    def licz():
        czesci = [prostokat(s["pas"]) for s in M["sciany"]]
        czesci += [prostokat(s["box"]) for s in M.get("szachty", [])]
        czesci += [w for w in wielokaty(M).values() if w is not None]
        return unary_union(czesci)
    return _cache(M, "obrys", licz)


def _na_obrysie(prost, a, b):
    r = prost.exterior
    return r.distance(Point(*a)) < 0.5 and r.distance(Point(*b)) < 0.5 \
        and r.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < 0.5


def _wlasciciel_krawedzi(M, a, b):
    """(id sciany albo None, id szachtu albo None) dla odcinka a-b obrysu pomieszczenia."""
    for s in M["sciany"]:
        if _na_obrysie(prostokat(s["pas"]), a, b):
            return s["id"], None
    for s in M.get("szachty", []):
        if _na_obrysie(prostokat(s["box"]), a, b):
            return None, s["id"]
    return None, None


def lica(M, nr):
    """Krawedzie wielokata pomieszczenia z przypisana sciana albo szachtem.

    Kazde lico: {"a": (x, y), "b": (x, y), "sciana": id | None, "szacht": id | None,
    "normalna": (nx, ny) do wnetrza, "dl": cm}. Oba None oznaczaja strefe wirtualna.
    Obejmuje obrys zewnetrzny i dziury (np. szacht albo slup stojacy w pomieszczeniu);
    kazdy pierscien ma wnetrze pomieszczenia po lewej stronie. Wspolliniowe odcinki tej
    samej sciany (np. przerwane otworem) sa laczone w jedno lico.
    """
    def licz():
        w = wielokaty(M).get(nr)
        if w is None:
            return []
        wynik = []
        for ring in [w.exterior] + list(w.interiors):
            wynik += _lica_pierscienia(M, list(ring.coords)[:-1])
        return wynik
    return _cache(M, "lica:" + nr, licz)


def _lica_pierscienia(M, pkt):
    surowe = []
    for i, a in enumerate(pkt):
        b = pkt[(i + 1) % len(pkt)]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
            continue
        surowe.append([a, b, _wlasciciel_krawedzi(M, a, b)])
    scalone = []
    for a, b, s in surowe:
        if scalone:
            pa, pb, ps = scalone[-1]
            if ps == s and _wspolliniowe(pa, pb, b):
                scalone[-1][1] = b
                continue
        scalone.append([a, b, s])
    if len(scalone) > 1:
        a, b, s = scalone[0]
        pa, pb, ps = scalone[-1]
        if ps == s and _wspolliniowe(pa, pb, b):
            scalone[0] = [pa, b, s]
            scalone.pop()
    wynik = []
    for a, b, s in scalone:
        dl = math.hypot(b[0] - a[0], b[1] - a[1])
        wynik.append({"a": (a[0], a[1]), "b": (b[0], b[1]), "sciana": s[0], "szacht": s[1],
                      "normalna": (-(b[1] - a[1]) / dl, (b[0] - a[0]) / dl), "dl": dl})
    return wynik


def _wspolliniowe(a, b, c, tol=0.05):
    """Czy c lezy na prostej a-b (odleglosc w cm)."""
    dl = math.hypot(b[0] - a[0], b[1] - a[1])
    return dl > 0 and abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / dl < tol
