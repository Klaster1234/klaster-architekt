"""Rysowanie modelu zamierzenia na arkuszu (arkusz.Widok): kadr, dzialka, sasiedztwo, warstwice,
obiekty wedlug legendy, moduly wnetrz, rzedne, wymiary i pozycje legendy.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model, rysuj
    M = model.wczytaj("przyklad/ogrod/model/projekt.json")
    W, skala_txt = rysuj.widok(M)
    miejsca = rysuj.Miejsca()
    tresc = rysuj.dzialka(W, M, miejsca=miejsca) + rysuj.obiekty(W, M, miejsca=miejsca) + rysuj.wymiary(W, M, miejsca=miejsca)

Kazda funkcja zwraca napis SVG. Wymiary i rzedne sa w metrach z dwoma miejscami ("4,25",
"+0,45", "−0,20", "±0,00"), ze znakiem "≈" przy danych niepewnych (model.niepewny). Opisy
(id obiektow, rzedne, wysokosci sasiedztwa, opisy warstwic, wymiary) omijaja sie nawzajem przez
wspolna liste zajetych miejsc (Miejsca - wspolne.opisy.Opisy z lista pominietych opisow, parametr
miejsca - jedna na arkusz); opis bez miejsca obok obiektu dostaje odnosnik albo jest pomijany;
czesci=True zwraca pare (rysunek, opisy), zeby opisy trafily na wierzch calego rysunku.
Obiekt rysuje styl z legendy (model.styl): wypelnienie, kreskowanie (jawne linie, wspolne.wzory),
linia (null - bez linii), grubosc, symbol punktu; dach - obrys okapu linia przerywana z kalenica
i narozami. tryb obiektow pokazuje roznice stanow: "usuniete" (przerywany obrys, punkt
przekreslony), "nowe" (pogrubione), "zmienione" (obrys i kreskowanie), "bez_zmian" (szare).
"""
import math
import re

from shapely.geometry import LineString, MultiPoint, Polygon, box
from shapely.ops import unary_union

from wspolne import arkusz, svg, wzory
from wspolne.opisy import Opisy, blok_tekstu, rect_tekstu
from zamierzenie import bryly, model, moduly as _moduly, teren

KOLOR_WYMIARU = "#7A4B16"            # jak wymiary rzutu lokalu
KOLOR_WARSTWIC = "#9A7B4F"
KOLOR_OPISU = "#333333"
DZIALKA = ("#222222", 1.6, "14 4 2 4")   # kolor, grubosc, kreski granicy dzialki
SASIEDZTWO = ("#F2F2F2", "#8C8C8C", "#B5B5B5")   # wypelnienie, obrys, kreskowanie
SCIANA_MODULU, POMIESZCZENIE_MODULU = "#1C2B52", "#666666"
KRESKOWANIA = {"ukos": [(45, 1.0)], "ukos_gesty": [(45, 0.5)], "poziome": [(0, 1.0)], "krzyz": [(45, 1.0), (135, 1.0)]}
KROK_PX = 7.0
GRUPY = {"powierzchnia": 0, "bryla": 1, "dach": 2, "linia": 3, "punkt": 4}
# roznica stanow: kolor linii (None - z legendy), kreski, kolor opisu
TRYBY = {"usuniete": ("#A8860B", "5 3", "#7A6207"), "nowe": ("#B03A2E", None, "#7A1D12"),
         "zmienione": ("#2F6FB4", None, "#1F4F86"), "bez_zmian": ("#9EA3A9", None, "#7A7F86")}
KRESKI_DACHU = "8 3"
OBWIEDNIA = "#333333"     # ciemna obwodka linii grubszych niz 2 (np. zywoplot na trawniku w tym samym kolorze)


def metry(cm):
    """Dlugosc w metrach z dwoma miejscami: 425 -> "4,25"."""
    return ("%.2f" % (cm / 100.0)).replace(".", ",")


def rzedna_txt(z_cm, niepewna=False):
    """Rzedna w metrach wzgledem +-0: "+0,45", "−0,20", "±0,00"; "≈" przed wartoscia niepewna."""
    v = round(z_cm / 100.0, 2)
    t = "±0,00" if v == 0 else ("+" if v > 0 else "−") + ("%.2f" % abs(v)).replace(".", ",")
    return ("≈" if niepewna else "") + t


def liczba(v, dokl=2):
    """Liczba z przecinkiem i spacja co trzy cyfry: 1234.5 -> "1 234,50"."""
    t = "%.*f" % (dokl, v)
    znak, t = ("-", t[1:]) if t.startswith("-") else ("", t)
    cz, _, ul = t.partition(".")
    grupy = []
    while len(cz) > 3:
        grupy.insert(0, cz[-3:])
        cz = cz[:-3]
    return znak + " ".join([cz] + grupy) + ("," + ul if ul else "")


def klucz_id(ident):
    """Porzadek naturalny: D2 przed D10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(ident))]


def komunikat_rodzaju(M, dla_lokalu=None):
    """None dla modelu zamierzenia, inaczej komunikat do konsoli (skrypt konczy sie kodem 2)."""
    r = model.rodzaj_pliku(M)
    if r == "zamierzenie":
        return None
    if r == "lokal":
        return ("To model lokalu (modul wnetrz)%s. Ten skrypt przyjmuje model zamierzenia (zamierzenie/SCHEMAT.md)."
                % (" - " + dla_lokalu if dla_lokalu else ""))
    return "Nie rozpoznano modelu zamierzenia: potrzebne meta.rodzaj i sekcja obiekty, moduly albo miejsce (zamierzenie/SCHEMAT.md)."


class Miejsca(Opisy):
    """Zajete miejsca arkusza (wspolne.opisy.Opisy) i lista opisow pominietych z braku miejsca."""

    def __init__(self):
        super().__init__()
        self.pominiete = []


def napis(miejsca, kandydaci, linie, kolor=KOLOR_OPISU, tlo=True, kotwica=None, pomin=False):
    """Blok linii [(tekst, rozmiar)] w pierwszym wolnym miejscu z kandydatow [(cx, cy)]. Gdy
    wolnego nie ma, a jest kotwica (X, Y): dalej od niej, z cienkim odnosnikiem; gdy i tam brak
    miejsca albo pomin=True - opis pominiety (pierwsza linia trafia do Miejsca.pominiete). Bez
    kotwicy i pomin opis trafia w pierwszego kandydata. Pod tekstem polprzezroczyste biale tlo."""
    r = next((q for q in (rect_tekstu(cx, cy, linie) for cx, cy in kandydaci) if miejsca.wolne(q)), None)
    odnosnik = ""
    if r is None and pomin:
        if hasattr(miejsca, "pominiete"):
            miejsca.pominiete.append(linie[0][0])
        return ""
    if r is None and kotwica is not None:
        X, Y = kotwica
        r = next((q for d in (16, 28, 42) for q in (rect_tekstu(cx, cy, linie) for cx, cy in wokol(X, Y, linie, d))
                  if miejsca.wolne(q)), None)
        if r is None:
            if hasattr(miejsca, "pominiete"):
                miejsca.pominiete.append(linie[0][0])
            return ""
        odnosnik = svg.linia(X, Y, min(max(X, r[0]), r[2]), min(max(Y, r[1]), r[3]), "#777777", 0.5)
    r = r or rect_tekstu(kandydaci[0][0], kandydaci[0][1], linie)
    miejsca.zajmij(r)
    t = svg.prostokat(r[0] - 1.5, r[1] - 0.5, r[2] + 1.5, r[3] + 0.5, "#FFFFFF", None, przezr=0.8) if tlo else ""
    return odnosnik + t + blok_tekstu(r, linie, kolory=[kolor])


def wokol(X, Y, linie, d=3.0, kierunek=None):
    """Srodki bloku opisu przylegajacego do punktu (X, Y) z odstepem d, w 8 kierunkach;
    kierunek (arkusz) ustawia najpierw strony najblizsze temu kierunkowi."""
    x0, y0, x1, y1 = rect_tekstu(0, 0, linie)
    w, h = x1 - x0, y1 - y0
    kier = [(1, -1), (-1, -1), (1, 1), (-1, 1), (1, 0), (-1, 0), (0, -1), (0, 1)]
    if kierunek:
        kier.sort(key=lambda k: -(k[0] * kierunek[0] + k[1] * kierunek[1]) / math.hypot(*k))
    return [(X + kx * (d + w / 2), Y + ky * (d + h / 2)) for kx, ky in kier]


def miejsca_arkusza(pole, metrow, px_na_m):
    """Miejsca z zajetym obszarem poza polem rysunku, strzalka polnocy (prawy gorny rog pola),
    podzialka i pasem notki o pominietych opisach (dol pola)."""
    x0, y0, x1, y1 = pole
    m = Miejsca()
    for r in ((0, 0, arkusz.SZER, y0), (0, y1, arkusz.SZER, arkusz.WYS), (0, 0, x0, arkusz.WYS), (x1, 0, arkusz.SZER, arkusz.WYS),
              (x1 - 72, y0 + 8, x1 - 8, y0 + 72), (x0, y1 - 32, x0 + 20 + metrow * px_na_m, y1 - 4),
              (x0 + 40 + metrow * px_na_m, y1 - 18, x1, y1 - 4)):
        m.zajmij(r)
    return m


def zajmij_granice(miejsca, W, M):
    """Granice dzialek jako zajete miejsca - opisy obiektow ich nie przykrywaja."""
    for d in (M.get("miejsce") or {}).get("dzialki") or []:
        pk = [W.p(x, y) for x, y in d["granica"]]
        for p0, p1 in zip(pk, pk[1:] + pk[:1]):
            _zajmij_linie(miejsca, p0, p1, 1.5)


def notka_pominietych(miejsca, pole, metrow, px_na_m):
    """Linia tekstu na dole pola: opisy pominiete z braku miejsca (pelna lista obiektow - Z-01)."""
    p = getattr(miejsca, "pominiete", [])
    if not p:
        return ""
    lista = ", ".join(p[:15]) + (" … (razem %d)" % len(p) if len(p) > 15 else "")
    return svg.tekst(pole[0] + 40 + metrow * px_na_m, pole[3] - 8, "Z braku miejsca bez opisu: %s — pełna lista obiektów "
                     "w zestawieniu (Z-01)." % lista, 8, kolor="#555555")


def stopka(pozycje, uwagi_linie, y=1800, dol=2076, szer=640):
    """(svg, y_gorne): legenda w 1-3 kolumnach i uwagi w lewym dolnym rogu arkusza, obok tabliczki;
    gdy nie mieszcza sie od y w dol, blok zaczyna sie wyzej (pole rysunku konczy sie nad y_gorne)."""
    def uklad(k):
        n = -(-len(pozycje) // k) if pozycje else 0
        kol = [pozycje[i * n:(i + 1) * n] for i in range(k)] if n else []
        h = max([arkusz.legenda(c, 0, 0, szer / k - 10)[1] for c in kol if c] or [0])
        hu = arkusz.uwagi(uwagi_linie, 0, 0, szer)[1] if uwagi_linie else 0
        return kol, h, hu
    for k in (1, 2, 3):
        kol, h, hu = uklad(k)
        if y + h + 8 + hu <= dol:
            break
    y0 = min(y, dol - h - 8 - hu)
    s = [arkusz.legenda(c, 50 + i * szer / len(kol), y0, szer / len(kol) - 10, "LEGENDA" if i == 0 else "")[0]
         for i, c in enumerate(kol) if c]
    if uwagi_linie:
        s.append(arkusz.uwagi(uwagi_linie, 50, y0 + (h + 8 if kol else 0), szer)[0])
    return "".join(s), y0


def tabela(x, y, naglowki, wiersze, szer=1380, r=9.0, wyrownanie=None, kolory=None):
    """(svg, wysokosc): tabela z naglowkiem na arkuszu; szerokosci kolumn wedlug tresci (razem
    najwyzej szer, przy wiekszej tresci mniejsze pismo); wyrownanie - napis z "l" albo "p" na
    kolumne; kolory - kolor tekstu na wiersz (None - domyslny)."""
    n = len(naglowki)
    wyrownanie = wyrownanie or "l" * n
    dl = [max([len(str(h))] + [len(str(w[i])) for w in wiersze]) for i, h in enumerate(naglowki)]
    k = min(1.0, szer / sum(d * r * 0.55 + 12 for d in dl))
    r = r * k
    szerokosci = [d * r * 0.55 + 12 * k for d in dl]
    h = r * 1.85
    xs = [x]
    for s_ in szerokosci:
        xs.append(xs[-1] + s_)
    s = [svg.prostokat(x, y, xs[-1], y + h, "#EDEDED", None)]

    def wiersz(yy, komorki, waga=None, kolor=KOLOR_OPISU):
        for i, c in enumerate(komorki):
            if wyrownanie[i] == "p":
                s.append(svg.tekst(xs[i + 1] - 6 * k, yy + h * 0.68, str(c), r, "end", kolor=kolor, waga=waga))
            else:
                s.append(svg.tekst(xs[i] + 6 * k, yy + h * 0.68, str(c), r, kolor=kolor, waga=waga))

    wiersz(y, naglowki, "bold")
    for j, w in enumerate(wiersze):
        yy = y + (j + 1) * h
        if j % 2:
            s.append(svg.prostokat(x, yy, xs[-1], yy + h, "#F6F6F6", None))
        wiersz(yy, w, kolor=(kolory[j] if kolory and kolory[j] else KOLOR_OPISU))
    dol = y + (len(wiersze) + 1) * h
    s += [svg.linia(x, y, xs[-1], y, "#555555", 0.9), svg.linia(x, y + h, xs[-1], y + h, "#555555", 0.7),
          svg.linia(x, dol, xs[-1], dol, "#555555", 0.9)]
    return "".join(s), dol - y


def widok(M, pole=arkusz.POLE, margines=300):
    """(Widok, skala_txt) na model.zakres(M) powiekszony o margines (cm)."""
    x0, y0, x1, y1 = model.zakres(M) or (0.0, 0.0, 1000.0, 1000.0)
    zakres = (x0 - margines, y0 - margines, x1 + margines, y1 + margines)
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    return arkusz.Widok(zakres, pole, sk), skala_txt


def grupa(M, o):
    """Kolejnosc rysowania: 0 powierzchnie, 1 bryly, 2 dachy, 3 linie, 4 punkty."""
    ks = model.styl(M, o.get("kategoria"))["ksztalt"]
    if ks not in GRUPY:
        ks = {"Polygon": "powierzchnia", "LineString": "linia"}.get(model.ksztalt(o).geom_type, "punkt")
    return GRUPY["dach" if o.get("dach") else ks]


def _zakres_z(M, o, s=None):
    try:
        return model.zakres_z(M, o, s)
    except KeyError:    # nieznany poziom zglasza walidator
        return (0.0, 0.0)


def plaskie(M):
    """Id obiektow bez wysokosci: powierzchnie i bryly o zerowym zakresie z (bez dachu) - w 3D plyta
    2 cm albo arkusz na terenie (zamierzenie/bryly.py). Przekroj rysuje je pasem na terenie,
    cienie je pomijaja."""
    s = teren.siatka(M)
    wynik = set()
    for o in model.obiekty(M):
        ks = model.styl(M, o.get("kategoria"))["ksztalt"] or \
            {"Polygon": "powierzchnia", "LineString": "linia"}.get(model.ksztalt(o).geom_type, "punkt")
        z0, z1 = _zakres_z(M, o, s)
        if not o.get("dach") and (ks == "powierzchnia" or ks not in ("punkt", "linia") and z1 <= z0):
            wynik.add(o["id"])
    return wynik


def _zajmij_linie(miejsca, p0, p1, zapas=2.0):
    """Linia arkusza jako ciag malych prostokatow zajetych (opisy jej nie przykrywaja)."""
    dl = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = max(1, int(dl / 8))
    for i in range(n + 1):
        x, y = p0[0] + (p1[0] - p0[0]) * i / n, p0[1] + (p1[1] - p0[1]) * i / n
        miejsca.zajmij((x - zapas, y - zapas, x + zapas, y + zapas))


def _obrys(g, P, kolor, gr, kreski=None):
    """Obrys geometrii ciagly albo przerywany (jawne odcinki - PyMuPDF pomija stroke-dasharray)."""
    if not kolor:
        return ""
    return svg.sciezka(g, P, "none", kolor, gr, kreski)


def _wynik(rys, op, czesci):
    return ("".join(rys), "".join(op)) if czesci else "".join(rys) + "".join(op)


def dzialka(W, M, miejsca=None, czesci=False):
    """Granice dzialek (linia punktowa) z numerem albo id i polem."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    kol, gr, kreski = DZIALKA
    rys, op = [], []
    for d in (M.get("miejsce") or {}).get("dzialki") or []:
        g = Polygon(d["granica"])
        rys.append(_obrys(g, W.p, kol, gr, kreski))
        linie = [("dz. %s" % (d.get("numer") or d["id"]), 9.5), ("%s m²" % liczba(g.area / 1e4), 8.5)]
        cx, cy = W.p(g.centroid.x, g.centroid.y)
        kand = []
        for x, y in g.exterior.coords[:-1]:
            X, Y = W.p(x, y)
            k = math.hypot(X - cx, Y - cy) or 1.0
            kand += wokol(X, Y, linie, 22, ((X - cx) / k, (Y - cy) / k))[:1]
        rp = W.p(*g.representative_point().coords[0])
        op.append(napis(miejsca, kand + [rp], linie, kotwica=rp))
    return _wynik(rys, op, czesci)


def sasiedztwo(W, M, opisy=True, miejsca=None, czesci=False):
    """Obiekty sasiednie: obrys z kreskowaniem i opis "h≈7,50 m" (wysokosc nad terenem)."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    wyp, obr, kr = SASIEDZTWO
    rys, op = [], []
    for s in (M.get("miejsce") or {}).get("sasiedztwo") or []:
        g = Polygon(s["obrys"])
        rys += [svg.sciezka(g, W.p, wyp, None), wzory.kreskowanie(g, W.p, 6.0, 45, kr, 0.5),
                svg.sciezka(g, W.p, "none", obr, 1.0)]
        if opisy:
            linie = [(s["id"], 8.5)]
            if s.get("wys") is not None:
                linie.append(("h%s%s m" % ("≈" if model.niepewny(s) else "=", metry(s["wys"])), 8))
            X, Y = W.p(*g.representative_point().coords[0])
            op.append(napis(miejsca, [(X, Y)] + wokol(X, Y, linie, 4), linie, "#555555", kotwica=(X, Y)))
    return _wynik(rys, op, czesci)


def warstwice(W, M, co=50, miejsca=None, czesci=False):
    """Warstwice terenu co `co` cm (co metr grubsze) z rzedna w metrach; opisy omijaja bryly."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    s = teren.siatka(M)
    if s is None:
        return _wynik([], [], czesci)
    nie = model.niepewny((M.get("miejsce") or {}).get("teren") or {})
    kadr = box(*W.zakres)
    bryly_ = []
    for o in model.obiekty(M):
        if grupa(M, o) in (1, 2):
            x0, y0, x1, y1 = model.ksztalt(o).bounds
            (X0, Y0), (X1, Y1) = W.p(x0, y1), W.p(x1, y0)
            bryly_.append((X0, Y0, X1, Y1))
    rys, op = [], []
    for z, linie in teren.warstwice(s, co):
        gr = 1.0 if abs(z % 100) < 1e-6 else 0.55
        for l in linie:
            x = LineString(l).intersection(kadr)
            for c in getattr(x, "geoms", [x]):
                if c.geom_type != "LineString" or c.length <= 0:
                    continue
                pkt = [W.p(x, y) for x, y in c.coords]
                rys.append(svg.polilinia(pkt, KOLOR_WARSTWIC, gr))
                if W.d(c.length) < 80:
                    continue
                t = [(rzedna_txt(z, nie), 7.5)]
                kand = [W.p(*c.interpolate(f, normalized=True).coords[0]) for f in (0.5, 0.3, 0.7, 0.15, 0.85)]
                r = next((q for q in (rect_tekstu(x, y, t) for x, y in kand) if miejsca.wolne(q, dodatkowe=bryly_)), None)
                if r is not None:
                    miejsca.zajmij(r)
                    op.append(svg.prostokat(r[0] - 1, r[1] - 0.5, r[2] + 1, r[3] + 0.5, "#FFFFFF", None, przezr=0.85)
                              + blok_tekstu(r, t, kolory=[KOLOR_WARSTWIC]))
    return _wynik(rys, op, czesci)


def _wyglad(st, tryb):
    """Styl obiektu z legendy (model.styl) zmieniony przez tryb roznicy stanow."""
    p = st["plan"]
    w = {"wyp": p["wypelnienie"] or "none", "lin": p["linia"], "gr": float(p["grubosc"] or 0.8), "kreski": None,
         "wzor": p["kreskowanie"] or "brak", "kol_wzoru": p["linia"] or "#555555", "przezr": None}
    if tryb in TRYBY:
        kol, kreski, _ = TRYBY[tryb]
        if tryb == "bez_zmian":
            w.update(wyp="#EEEFF1" if w["wyp"] != "none" else "none", lin=kol, gr=min(w["gr"], 0.9), wzor="brak")
        elif tryb == "nowe":
            w.update(lin=kol, gr=max(1.6, 1.6 * w["gr"]), przezr=0.6 if w["wyp"] != "none" else None)
        elif tryb == "zmienione":
            w.update(wyp="none", lin=kol, gr=max(1.2, w["gr"]), wzor="ukos", kol_wzoru=kol)
        else:
            w.update(wyp="none", lin=kol, gr=max(1.2, min(w["gr"], 2.0)), kreski=kreski, wzor="brak")
    return w


def _wzor(g, P, w):
    """Kreskowanie albo kropki z legendy (P mapuje model na arkusz)."""
    if w["wzor"] == "kropki":
        return wzory.kropki(g, P, 8.0, 0.9, w["kol_wzoru"])
    return "".join(wzory.kreskowanie(g, P, KROK_PX * k, kat, w["kol_wzoru"], 0.6) for kat, k in KRESKOWANIA.get(w["wzor"], []))


def dach_w_planie(M, o):
    """(obrys okapu, [odcinki kalenicy i narozy], strzalka spadku albo None) w ukladzie modelu;
    None, gdy dachu nie da sie zbudowac (bledy zglasza walidator)."""
    d = o.get("dach") or {}
    try:
        m = bryly.dach(model.ksztalt(o), d.get("typ"), d.get("kat", 0), 0.0, d.get("kalenica", "dluzszy"),
                       d.get("okap", 0), d.get("nizej"))
    except ValueError:    # bryly.dach zglasza ValueError dla zlych danych dachu
        return None
    v = [tuple(p) for p in m.vertices[:, :2]]
    obrys = MultiPoint(v).convex_hull
    typ, linie, spadek = d.get("typ"), [], None
    if typ == "dwuspadowy":
        linie = [(v[4], v[5])]
    elif typ == "czterospadowy":
        linie = [(v[i], v[4]) for i in range(4)] if len(v) == 5 else \
            [(v[4], v[5]), (v[0], v[4]), (v[3], v[4]), (v[1], v[5]), (v[2], v[5])]
    elif typ == "jednospadowy":
        gora = ((v[4][0] + v[5][0]) / 2, (v[4][1] + v[5][1]) / 2)
        dol = ((v[0][0] + v[1][0]) / 2, (v[0][1] + v[1][1]) / 2)
        spadek = (gora, dol)
    return obrys, linie, spadek


def _strzalka(W, a, b, kolor, gr):
    """Strzalka spadku od a do b (model) - srodkowe 60 % odcinka."""
    (ax, ay), (bx, by) = W.p(*a), W.p(*b)
    ax, ay, bx, by = ax + (bx - ax) * 0.2, ay + (by - ay) * 0.2, ax + (bx - ax) * 0.8, ay + (by - ay) * 0.8
    dl = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / dl, (by - ay) / dl
    grot = [(bx, by), (bx - 8 * ux - 3.5 * uy, by - 8 * uy + 3.5 * ux), (bx - 8 * ux + 3.5 * uy, by - 8 * uy - 3.5 * ux)]
    return svg.linia(ax, ay, bx, by, kolor, gr) + svg.polilinia(grot, kolor, gr, wyp=kolor, zamknij=True)


def _etykieta(M, o, s, gr_):
    """Linie opisu obiektu: id, a przy bryle i dachu zakres wysokosci (dach: okap ... kalenica)."""
    linie = [(o["id"], 8.5)]
    if gr_ in (1, 2):
        z0, z1 = _zakres_z(M, o, s)
        linie.append(("%s … %s" % (rzedna_txt(z0), rzedna_txt(z1)), 7.5))
    return linie


def obiekty(W, M, lista=None, tryb=None, miejsca=None, czesci=False, opisy=True):
    """Obiekty (domyslnie wszystkie) wedlug legendy: powierzchnie, bryly, dachy, linie, punkty
    (korony drzew od najwiekszej); tryb - styl roznicy stanow (TRYBY), opisy - id obiektow."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    lista = model.obiekty(M) if lista is None else lista
    s = teren.siatka(M)
    kol_opisu = TRYBY[tryb][2] if tryb in TRYBY else KOLOR_OPISU
    rys, op = [], []
    for o in sorted(lista, key=lambda o: (grupa(M, o), -(o.get("srednica") or 0), _zakres_z(M, o, s)[1])):
        st, g, gr_ = model.styl(M, o.get("kategoria")), model.ksztalt(o), grupa(M, o)
        w = _wyglad(st, tryb)
        if gr_ == 2:
            d = dach_w_planie(M, o)
            obrys, linie, spadek = d if d else (g, [], None)
            if w["wyp"] != "none":
                rys.append(svg.sciezka(obrys, W.p, w["wyp"], None, przezr=w["przezr"]))
            rys.append(_wzor(obrys, W.p, w))
            if w["lin"]:
                rys.append(_obrys(obrys, W.p, w["lin"], w["gr"], w["kreski"] or KRESKI_DACHU))
                rys += [_obrys(LineString([a, b]), W.p, w["lin"], 0.8 * w["gr"], w["kreski"]) for a, b in linie]
                if spadek:
                    rys.append(_strzalka(W, spadek[0], spadek[1], w["lin"], 0.8 * w["gr"]))
            X, Y = W.p(*g.representative_point().coords[0])
            kand, kotwica = [(X, Y + 18), (X, Y - 18)] + wokol(X, Y, _etykieta(M, o, s, gr_), 12), (X, Y)
        elif g.geom_type == "Polygon":
            if w["wyp"] != "none":
                rys.append(svg.sciezka(g, W.p, w["wyp"], None, przezr=w["przezr"]))
            rys.append(_wzor(g, W.p, w))
            rys.append(_obrys(g, W.p, w["lin"], w["gr"], w["kreski"]))
            X, Y = W.p(*g.representative_point().coords[0])
            kand, kotwica = [(X, Y)] + wokol(X, Y, _etykieta(M, o, s, gr_), 8), (X, Y)
        elif g.geom_type == "LineString":
            if w["lin"] and w["gr"] >= 2 and not w["kreski"]:
                rys.append(svg.sciezka(g, W.p, "none", OBWIEDNIA, w["gr"] + 1.4))
            rys.append(_obrys(g, W.p, w["lin"], w["gr"], w["kreski"]))
            kand = []
            for f in (0.5, 0.3, 0.7):
                X, Y = W.p(*g.interpolate(f, normalized=True).coords[0])
                kand += wokol(X, Y, _etykieta(M, o, s, gr_), 4 + w["gr"] / 2)[:4]
            kotwica = W.p(*g.interpolate(0.5, normalized=True).coords[0])
        else:
            X, Y = W.p(g.x, g.y)
            r = max(3.0, W.d(o["srednica"] / 2)) if o.get("srednica") else 4.0
            sym = st["plan"]["symbol"] or "kolo"
            rys.append(wzory.symbol(sym, X, Y, r, w["lin"], min(w["gr"], 2.5), w["wyp"], w["kreski"]))
            if tryb == "usuniete":
                rys.append(wzory.symbol("krzyz", X, Y, max(r, 6.0), w["lin"], 1.2))
            t = rect_tekstu(0, 0, [(o["id"], 8.5)])
            half = (t[2] - t[0]) / 2
            kand = [(X + 4 + half, Y - 8), (X - 4 - half, Y - 8), (X + 4 + half, Y + 9), (X - 4 - half, Y + 9)] + \
                wokol(X, Y, [(o["id"], 8.5)], r + 2)
            kotwica = None       # punkty w gestej grupie: opis pominiety zamiast plataniny odnosnikow
        if opisy:
            op.append(napis(miejsca, kand, _etykieta(M, o, s, gr_), kol_opisu, kotwica=kotwica, pomin=gr_ == 4))
    return _wynik(rys, op, czesci)


def moduly(W, M, miejsca=None, czesci=False, lista=None):
    """Moduly wnetrz (domyslnie wszystkie): sciany ciemne, pomieszczenia samym obrysem, opis id
    modulu; wnetrze (wyposazenie, otwory) pokazuja rysunki modulu (rysunki/rzut.py)."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    rys, sciany, op = [], [], []
    for mod in _moduly.moduly(M) if lista is None else lista:
        for o in _moduly.obiekty_modulu(M, mod):
            if o["kategoria"] == "_pomieszczenie":
                rys.append(svg.sciezka(model.ksztalt(o), W.p, "none", POMIESZCZENIE_MODULU, 0.6))
            elif o["kategoria"] == "_sciana":
                sciany.append(svg.sciezka(model.ksztalt(o), W.p, SCIANA_MODULU, None))
        X, Y = W.p(*_moduly.obrys_modulu(M, mod).representative_point().coords[0])
        linie = [(mod["id"], 9), ("moduł wnętrz", 7.5)]
        op.append(napis(miejsca, [(X, Y)] + wokol(X, Y, linie, 6), linie, kotwica=(X, Y)))
    return _wynik(rys + sciany, op, czesci)


def rzedne(W, M, punkty, miejsca=None, czesci=False):
    """Rzedne terenu w punktach [(x, y)] albo [(x, y, (kx, ky))] - kierunek (model), w ktorym
    najpierw szukac miejsca na opis; znak x i rzedna w m wzgledem +-0, "≈" przy terenie niepewnym."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    s = teren.siatka(M)
    nie = model.niepewny((M.get("miejsce") or {}).get("teren") or {})
    rys, op, gotowe = [], [], []
    for p in punkty:
        x, y = p[0], p[1]
        if any(math.hypot(x - a, y - b) < 1 for a, b in gotowe):
            continue
        gotowe.append((x, y))
        X, Y = W.p(x, y)
        rys.append(wzory.symbol("krzyz", X, Y, 3.4, "#222222", 0.9))
        miejsca.zajmij((X - 3, Y - 3, X + 3, Y + 3))
        linie = [(rzedna_txt(teren.rzedna(s, x, y), nie), 8)]
        k = p[2] if len(p) > 2 else None
        op.append(napis(miejsca, wokol(X, Y, linie, 5, (k[0], -k[1]) if k else None), linie, "#222222", kotwica=(X, Y)))
    return _wynik(rys, op, czesci)


def _osie(g):
    """(u, v, (u0, u1), (v0, v1)): osie wzdluz najdluzszej krawedzi obrysu i jego zakresy."""
    p = list(g.exterior.coords[:-1])
    ex, ey = max(((q[0] - r[0], q[1] - r[1]) for r, q in zip(p, p[1:] + p[:1])), key=lambda e: math.hypot(*e))
    dl = math.hypot(ex, ey)
    u, v = (ex / dl, ey / dl), (-ey / dl, ex / dl)
    su, sv = [x * u[0] + y * u[1] for x, y in p], [x * v[0] + y * v[1] for x, y in p]
    return u, v, (min(su), max(su)), (min(sv), max(sv))


def _rect_wymiaru(p0, p1, tekst, r=9, strona=1):
    """Prostokat opisu linii wymiarowej svg.wymiar (te same wzory polozenia i rozmiaru)."""
    (x0, y0), (x1, y1) = p0, p1
    dl = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / dl, (y1 - y0) / dl
    nx, ny = uy * strona, -ux * strona
    kat = math.degrees(math.atan2(uy, ux))
    if kat > 90 or kat <= -90:
        kat += 180
    rozmiar = r if dl >= 3.2 * r else r * 0.78
    kr = math.radians(kat)
    odl = 3.5 if nx * math.sin(kr) - ny * math.cos(kr) > 0 else rozmiar + 1
    mx, my = (x0 + x1) / 2 + nx * odl, (y0 + y1) / 2 + ny * odl
    w = len(tekst) * rozmiar * 0.56 + 3
    c, s_ = math.cos(kr), math.sin(kr)
    naroza = [(mx + a * c - b * s_, my + a * s_ + b * c) for a in (-w / 2, w / 2) for b in (-0.82 * rozmiar, 0.23 * rozmiar)]
    return (min(q[0] for q in naroza), min(q[1] for q in naroza), max(q[0] for q in naroza), max(q[1] for q in naroza))


def _strona(p0, p1, ku=None):
    """strona svg.wymiar: opis w strone punktu ku (arkusz), bez niego nad linia albo na lewo od niej."""
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    nx, ny = uy, -ux             # lewa strona kierunku p0 -> p1 na arkuszu (strona=1)
    if ku is not None:
        return 1 if nx * (ku[0] - p0[0]) + ny * (ku[1] - p0[1]) > 0 else -1
    return (1 if ny < 0 else -1) if abs(ux) >= abs(uy) else (1 if nx < 0 else -1)


def wymiary(W, M, lista=None, miejsca=None, czesci=False, od_krawedzi_px=12.0, przeszkody=None):
    """Wymiary bryl i dachow (dwa boki obrysu, wewnatrz obrysu, gdy sie miesci; obrys wspolny
    kilku obiektow - raz) oraz odleglosci grup stykajacych sie bryl od bokow dzialki, na ktore
    grupa patrzy (spodek prostopadlej w obrebie boku); odleglosc przechodzaca przez inna grupe,
    przez przeszkode (domyslnie obrysy modulow wnetrz) albo przez narysowany wymiar jest pomijana.
    Metry z dwoma miejscami, "≈" przy danych niepewnych."""
    miejsca = miejsca if miejsca is not None else Miejsca()
    lista = [o for o in (model.obiekty(M) if lista is None else lista)
             if grupa(M, o) in (1, 2) and model.ksztalt(o).geom_type == "Polygon"]
    lista.sort(key=lambda o: -model.ksztalt(o).area)
    linie_, opisy_, zrobione, obrysy, odcinki = [], [], [], [], []

    def wymiar(a, b, niepewny, ku=None):
        p0, p1 = W.p(*a), W.p(*b)
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 4:
            return
        dl = math.hypot(b[0] - a[0], b[1] - a[1])
        strona = _strona(p0, p1, ku)
        l, t = svg.wymiar(p0, p1, metry(dl), niepewny, 9, KOLOR_WYMIARU, strona, czesci=True)
        linie_.append(l)
        opisy_.append(t)
        odcinki.append(LineString([a, b]))
        _zajmij_linie(miejsca, p0, p1)
        miejsca.zajmij(_rect_wymiaru(p0, p1, ("≈ " if niepewny else "") + metry(dl), 9, strona))

    for o in lista:
        g = model.ksztalt(o)
        wsp = next((x for x in obrysy if x[0].symmetric_difference(g).area < 1.0), None)
        if wsp:
            wsp[1].append(o)
            continue
        obrysy.append((g, [o]))
    for g, obj in obrysy:
        nie = any(model.niepewny(o) for o in obj)
        u, v, (u0, u1), (v0, v1) = _osie(g)
        c = W.p(*(((u0 + u1) / 2) * u[0] + ((v0 + v1) / 2) * v[0], ((u0 + u1) / 2) * u[1] + ((v0 + v1) / 2) * v[1]))
        d = od_krawedzi_px / W.sk
        for wzdluz_u in (True, False):
            # a - wspolrzedna wzdluz mierzonego boku, b - w poprzek (os v albo u)
            (a0, a1), (b0, b1) = ((u0, u1), (v0, v1)) if wzdluz_u else ((v0, v1), (u0, u1))
            ea, eb = (u, v) if wzdluz_u else (v, u)
            Q = lambda a, b: (a * ea[0] + b * eb[0], a * ea[1] + b * eb[1])
            wew = W.d(b1 - b0) > 4 * od_krawedzi_px
            # bok nizej na arkuszu, przy rownych - blizszy lewej krawedzi arkusza
            b = min((b0, b1), key=lambda bb: (-round(W.p(*Q((a0 + a1) / 2, bb))[1], 1), round(W.p(*Q((a0 + a1) / 2, bb))[0], 1)))
            b += (d if b == b0 else -d) * (1 if wew else -1)
            pa, pb = Q(a0, b), Q(a1, b)
            k = (ea[0], ea[1]) if ea[0] > 1e-9 or (abs(ea[0]) <= 1e-9 and ea[1] > 0) else (-ea[0], -ea[1])
            przedzial = sorted((pa[0] * k[0] + pa[1] * k[1], pb[0] * k[0] + pb[1] * k[1]))
            if any(abs(k[0] * kk[0] + k[1] * kk[1]) > 1 - 1e-6 and abs(przedzial[0] - pp[0]) < 1 and abs(przedzial[1] - pp[1]) < 1
                   for kk, pp in zrobione):
                continue            # ten sam wymiar ma juz inny obrys (np. taras pod domem)
            zrobione.append((k, przedzial))
            m = W.p((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            wymiar(pa, pb, nie, c if wew else (2 * m[0] - c[0], 2 * m[1] - c[1]))
    if przeszkody is None:
        przeszkody = [_moduly.obrys_modulu(M, mod) for mod in _moduly.moduly(M)]
    dz = model.dzialka(M)
    if dz is not None and obrysy:
        rekordy = {d["id"]: d for d in (M.get("miejsce") or {}).get("dzialki") or []}
        nie_dz = any(model.niepewny(d) for d in rekordy.values())
        u_ = unary_union([g for g, _ in obrysy])
        grupy_ = sorted(getattr(u_, "geoms", [u_]), key=lambda h: -h.area)   # najpierw glowny budynek
        for gr_ in grupy_:
            nie = nie_dz or any(model.niepewny(o) for g, obj in obrysy if g.intersects(gr_) for o in obj)
            for pierscien in (p.exterior for p in getattr(dz, "geoms", [dz])):
                pk = list(pierscien.coords)
                for a, b in zip(pk, pk[1:]):
                    bok = LineString([a, b])
                    odl = gr_.distance(bok)
                    if odl < 1:
                        continue
                    czesc = gr_.boundary.intersection(bok.buffer(odl + 0.5))
                    czesc = max(getattr(czesc, "geoms", [czesc]), key=lambda c: c.length) if not czesc.is_empty else None
                    if czesc is None:
                        continue
                    q = czesc.interpolate(0.5, normalized=True) if czesc.geom_type == "LineString" else czesc.centroid
                    t = bok.project(q)
                    if not 1 < t < bok.length - 1:
                        continue
                    f = bok.interpolate(t)
                    przez = LineString([(q.x, q.y), (f.x, f.y)])
                    if any(przez.crosses(h) or przez.within(h) for h in grupy_ if h is not gr_) or \
                            any(przez.crosses(h) for h in odcinki) or any(przez.intersects(h) for h in przeszkody):
                        continue            # przez inna bryle albo przez narysowany wymiar
                    wymiar((q.x, q.y), (f.x, f.y), nie)
    return _wynik(linie_, opisy_, czesci)


def _symbol_legendy(st, kategoria):
    """Symbol kategorii w polu 24 x 16 jednostek arkusza, tym samym stylem co na rysunku."""
    w = _wyglad(st, None)
    ks = st["ksztalt"]
    if kategoria == "_sciana":
        return svg.prostokat(0, 4, 24, 12, SCIANA_MODULU, None)
    if kategoria == "_pomieszczenie":
        return svg.prostokat(1, 2, 23, 14, "none", POMIESZCZENIE_MODULU, 0.6)
    if ks == "linia":
        gr = min(w["gr"], 5.0)
        return ((svg.linia(0, 8, 24, 8, OBWIEDNIA, gr + 1.4) if gr >= 2 else "") + svg.linia(0, 8, 24, 8, w["lin"], gr)) \
            if w["lin"] else ""
    if ks == "punkt":
        return wzory.symbol(st["plan"]["symbol"] or "kolo", 12, 8, 7, w["lin"], min(w["gr"], 2.5), w["wyp"])
    s = [svg.prostokat(1, 3, 23, 13, w["wyp"], None) if w["wyp"] != "none" else "", _wzor(box(1, 3, 23, 13), lambda x, y: (x, y), w)]
    if ks == "dach":
        if w["lin"]:
            s += [svg.polilinia([(1, 3), (23, 3), (23, 13), (1, 13)], w["lin"], w["gr"], KRESKI_DACHU, zamknij=True),
                  svg.linia(1, 8, 23, 8, w["lin"], 0.8 * w["gr"])]
    elif w["lin"]:
        s.append(svg.prostokat(1, 3, 23, 13, "none", w["lin"], min(w["gr"], 2.0)))
    return "".join(s)


def legenda(M, kategorie):
    """[(symbol 24 x 16, opis)] dla kategorii obecnych na arkuszu, w kolejnosci legendy modelu
    (kategorie modulow "_*" na koncu, wyposazenie modulow pominiete - nie ma go na planie)."""
    kategorie = set(kategorie)
    kolejnosc = [k for k in model.legenda(M) if k in kategorie]
    kolejnosc += sorted(k for k in kategorie if k not in model.legenda(M) and k != "_wyposazenie")
    wynik = []
    for k in kolejnosc:
        st = model.styl(M, k)
        opis = st["nazwa"] + (" (moduł wnętrz)" if k.startswith("_") else "")
        wynik.append((_symbol_legendy(st, k), opis))
    return wynik
