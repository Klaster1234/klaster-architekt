"""Model zamierzenia: odczyty wspolne dla narzedzi (legenda, obiekty, poziomy, rzedne, dzialka).

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model
    M = model.wczytaj("przyklad/ogrod/model/projekt.json")
    for o in model.obiekty(M, "drzewo"):
        print(o["id"], model.styl(M, o["kategoria"])["nazwa"], model.zakres_z(M, o))

Model to jeden plik JSON na stan zamierzenia (cm, z wzgledem +-0), opisany w
zamierzenie/SCHEMAT.md. Narzedzia go czytaja; zapis tylko przez zapisz().
"""
import math

from shapely.geometry import GeometryCollection, LineString, Point, Polygon
from shapely.ops import unary_union

from wspolne.pliki import wczytaj, zapisz, json_zwarty, projekt, katalog_wyjscia, sciezka_wyniku
from zamierzenie import teren

RODZAJE_ZAMIERZEN = ("wnetrze", "ogrod", "budynek", "inne")
KSZTALTY = ("powierzchnia", "linia", "punkt", "bryla", "dach")
BILANS = ("zabudowa", "pbc", "utwardzona", "woda", "inne")
DOMYSLNE_POLOZENIE = {"lat": 52.1, "lon": 19.5, "strefa": "Europe/Warsaw"}
TYPY_DACHU = ("plaski", "jednospadowy", "dwuspadowy", "czterospadowy")
STRONY = {"N": (0.0, 1.0), "E": (1.0, 0.0), "S": (0.0, -1.0), "W": (-1.0, 0.0)}   # dach.nizej: kierunek w osiach modelu
# kategorie obiektow z modulow wnetrz (nie musza byc w legendzie): nazwa, ksztalt
KATEGORIE_MODULOW = {"_sciana": ("ściana", "bryla"), "_pomieszczenie": ("pomieszczenie", "powierzchnia"),
                     "_wyposazenie": ("wyposażenie", "bryla")}


def rodzaj_pliku(M):
    if "sciany" in M:
        return "lokal"
    if M.get("meta", {}).get("rodzaj") and any(k in M for k in ("obiekty", "moduly", "miejsce")):
        return "zamierzenie"
    return None


def legenda(M):
    return M.get("legenda") or {}


def styl(M, kategoria):
    """Wpis legendy uzupelniony wartosciami domyslnymi (nowy slownik, legenda modelu bez zmian)."""
    w = legenda(M).get(kategoria)
    if w is None:
        nazwa, ks = KATEGORIE_MODULOW.get(kategoria, (kategoria, None))
        w = {"nazwa": nazwa, "ksztalt": ks}
    ks = w.get("ksztalt")
    plan = {"wypelnienie": "#F2F2F2" if ks == "powierzchnia" else "#E0E0E0" if ks in ("bryla", "dach") else None,
            "kreskowanie": "brak", "linia": "#444444", "grubosc": 0.8, "symbol": "kolo" if ks == "punkt" else None}
    plan.update(w.get("plan") or {})
    roslina = plan["symbol"] in ("drzewo", "krzew") or w.get("bilans") == "pbc"
    bryla = w.get("bryla") or {}
    return {**w, "nazwa": w.get("nazwa", kategoria), "ksztalt": ks, "plan": plan,
            "bryla": {**bryla, "kolor": bryla.get("kolor") or ("#8FA27F" if roslina else "#C8C8C8")},   # null: domyslny
            "zestawienie": list(w.get("zestawienie") or []), "bilans": w.get("bilans"),
            "kolizja": w.get("kolizja", ks == "bryla")}


def obiekty(M, kategoria=None):
    return [o for o in M.get("obiekty") or [] if kategoria is None or o.get("kategoria") == kategoria]


def obiekt(M, ident):
    for o in M.get("obiekty") or []:
        if o.get("id") == ident:
            return o
    raise KeyError("brak obiektu %s" % ident)


def ksztalt(o):
    """Geometria shapely obiektu: Polygon (wielokat), LineString (linia) albo Point (punkt)."""
    k = o["ksztalt"]
    if "wielokat" in k:
        return Polygon(k["wielokat"])
    if "linia" in k:
        return LineString(k["linia"])
    return Point(k["punkt"])


def poziomy(M):
    return M.get("poziomy") or []


def poziom(M, ident):
    for p in poziomy(M):
        if p.get("id") == ident:
            return p
    raise KeyError("brak poziomu %s" % ident)


def baza_z(M, o, siatka=None):
    """Podstawa wysokosci obiektu wzgledem +-0: rzedna poziomu, rzedna terenu w srodku
    ciezkosci ksztaltu (na_terenie) albo 0. siatka = gotowa teren.siatka(M)."""
    if o.get("poziom") is not None:
        return float(poziom(M, o["poziom"]).get("z", 0))
    if o.get("na_terenie"):
        c = ksztalt(o).centroid
        return teren.rzedna(siatka if siatka is not None else teren.siatka(M), c.x, c.y)
    return 0.0


def zakres_z(M, o, siatka=None):
    """(z0, z1) wzgledem +-0: podstawa + z, podstawa..podstawa + wys albo (podstawa, podstawa).
    Dach: od okapu (z0 - okap * tg kata, plaski z0) do kalenicy (plaski z0 + 30, jednospadowy
    z0 + b * tg, dwu- i czterospadowy z0 + b / 2 * tg; b = bok obrysu scian prostopadly do kalenicy)."""
    b = baza_z(M, o, siatka)
    d = o.get("dach")
    if d:
        z0, tg = b + d.get("z0", 0), math.tan(math.radians(d.get("kat", 0)))
        if d.get("typ") == "plaski":
            return (z0, z0 + 30)
        g = ksztalt(o)
        s = g.length / 2                        # boki prostokata z obwodu i pola: a + c = s, a * c = pole
        r = math.sqrt(max(s * s - 4 * g.area, 0))
        szer = (s + r) / 2 if d.get("kalenica") == "krotszy" else (s - r) / 2
        return (z0 - d.get("okap", 0) * tg, z0 + szer * tg * (1 if d.get("typ") == "jednospadowy" else 0.5))
    if o.get("z"):
        return (b + o["z"][0], b + o["z"][1])
    if o.get("wys") is not None:
        return (b, b + o["wys"])
    return (b, b)


def osie_dachu(g, kalenica="dluzszy", nizej=None):
    """Osie prostokata obrysu dachu i strona nizsza polaci jednospadowej (bryly.dach, walidator).

    (srodek, u, v, a, b, zgodne): u - kierunek kalenicy (wzdluz dluzszego boku, przy
    kalenica="krotszy" krotszego), v - u obrocone o 90 st. przeciwnie do zegara, a i b - boki
    wzdluz u i v; strona nizsza lezy po stronie -v. Osie wyznacza najdluzsza krawedz i rzuty
    wierzcholkow, wiec prostokat z pomiaru (bok 1000,4 zamiast 1000, wspolrzedne co 1 cm) i
    pierscien zaczety na boku daja ten sam uklad. Boki rownolegle do kalenicy (na kwadracie,
    gdy boki roznia sie o mniej niz 1 cm - wszystkie) rozpoznaje po kierunku normalnej. Z nizej
    (N, E, S, W) strona nizsza to ten z nich, ktorego normalna zewnetrzna jest najblizsza
    kierunkowi; bez nizej (i przy remisie w granicach 0,01) ten z normalna najblizsza -X (W), gdy
    normalne wszystkich kandydatow odchylaja sie od osi X o najwyzej 10 st. (boki rownolegle do
    kalenicy blisko osi Y), a w pozostalych przypadkach najblizsza -Y (S; przy remisie, np. na
    kwadracie obroconym o 45 st., blizsza -X). zgodne = False, gdy nizej wskazuje bok prostopadly
    do kalenicy (strona nizsza to wtedy najblizszy bok rownolegly).
    """
    p = [c[:2] for c in g.exterior.coords[:-1]]
    ex, ey = max(((q[0] - r[0], q[1] - r[1]) for r, q in zip(p, p[1:] + p[:1])), key=lambda e: math.hypot(*e))
    u = (ex / math.hypot(ex, ey), ey / math.hypot(ex, ey))
    v = (-u[1], u[0])
    su, sv = [x * u[0] + y * u[1] for x, y in p], [x * v[0] + y * v[1] for x, y in p]
    a, b = max(su) - min(su), max(sv) - min(sv)
    cu, cv = (max(su) + min(su)) / 2, (max(sv) + min(sv)) / 2
    c = (cu * u[0] + cv * v[0], cu * u[1] + cv * v[1])
    if (a < b) != (kalenica == "krotszy"):
        u, v, a, b = v, (-u[0], -u[1]), b, a
    # boki: (normalna zewnetrzna, odleglosc do boku przeciwleglego, dlugosc boku)
    boki = [((-v[0], -v[1]), b, a), (v, b, a)] + ([((-u[0], -u[1]), a, b), (u, a, b)] if abs(a - b) < 1.0 else [])

    def najblizszy(lista, k):
        """Bok z normalna najblizsza kierunkowi k; remis (0,01) rozstrzyga regula domyslna."""
        naj = max(s[0][0] * k[0] + s[0][1] * k[1] for s in lista)
        return [s for s in lista if s[0][0] * k[0] + s[0][1] * k[1] > naj - 0.01], naj

    def domyslny(lista):
        blisko_x = all(abs(s[0][0]) >= math.cos(math.radians(10)) - 1e-12 for s in lista)
        remis = najblizszy(lista, (-1.0, 0.0) if blisko_x else (0.0, -1.0))[0]
        return max(remis, key=lambda s: -s[0][0])   # przy remisie blizszy -X

    zgodne = True
    if nizej is None:
        n, gl, dl = domyslny(boki)
    else:
        k = STRONY[nizej]
        remis, naj = najblizszy(boki, k)
        n, gl, dl = domyslny(remis)
        zgodne = naj > max(abs(u[0] * k[0] + u[1] * k[1]), abs(v[0] * k[0] + v[1] * k[1])) - 0.01
    return c, (-n[1], n[0]), (-n[0], -n[1]), dl, gl, zgodne


def dzialka(M):
    """Unia granic dzialek albo None."""
    g = [Polygon(d["granica"]) for d in (M.get("miejsce") or {}).get("dzialki") or []]
    return unary_union(g) if g else None


def lokalizacja(M):
    return {**DOMYSLNE_POLOZENIE, **((M.get("meta") or {}).get("lokalizacja") or {})}


def azymut_polnocy(M):
    return float(((M.get("meta") or {}).get("polnoc") or {}).get("azymut_osi_Y_stopnie", 0.0))


def zakres(M):
    """(x0, y0, x1, y1) dzialek, obiektow (drzewa z korona), sasiedztwa i obrysow modulow;
    None, gdy nic nie ma."""
    from zamierzenie import moduly   # tu, bo moduly importuje ten plik
    g = [ksztalt(o).buffer(o["srednica"] / 2) if o.get("srednica") else ksztalt(o) for o in obiekty(M)]
    g += [Polygon(s["obrys"]) for s in (M.get("miejsce") or {}).get("sasiedztwo") or []]
    g += [moduly.obrys_modulu(M, m) for m in moduly.moduly(M)]
    d = dzialka(M)
    if d is not None:
        g.append(d)
    return tuple(float(v) for v in GeometryCollection(g).bounds) if g else None


def niepewny(rekord, prog=5):
    """Wartosc z zalozenia albo z dokladnoscia gorsza niz prog cm (na rysunkach znak "≈")."""
    return (rekord.get("dokladnosc_cm") or 0) > prog or rekord.get("zrodlo") == "ZALOZENIE"
