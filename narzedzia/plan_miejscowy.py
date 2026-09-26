"""Plan miejscowy dla dzialki albo punktu z uslugi GUGiK Krajowa Integracja Miejscowych Planow
Zagospodarowania Przestrzennego (WMS GetFeatureInfo): symbol i przeznaczenie terenu, nazwa planu, odnosnik.

    python narzedzia/plan_miejscowy.py --meta wyjscie/geoportal_meta.json
    python narzedzia/plan_miejscowy.py --dzialka 146510_8.0309.24/35 --wyjscie wyjscie
    python narzedzia/plan_miejscowy.py --xy 21.0063,52.2318 --model model/istniejacy.json

Zapytania w srodku dzialki i w 4 punktach 1 m od jej granicy (skrajnych w kierunkach NE, NW, SE, SW);
bez dzialki - w punkcie. Dzialka z --meta (wynik narzedzia/geoportal.py), z --dzialka (ULDK:
identyfikator albo "obreb numer") albo z ULDK w punkcie --xy (dlugosc,szerokosc WGS84).
Usluga zbiorcza przekazuje odpowiedzi uslug gmin w roznej postaci (XML, GML, tabele HTML, tekst),
oddzielone znacznikiem <hr/>. Skrypt prosi o format najbardziej strukturalny z GetCapabilities
(GML/XML przed HTML), a gdy usluga gminy odpowiada na niego wyjatkiem - o text/html. Pola czyta po
nazwach: symbol albo oznaczenie, przeznaczenie albo funkcja, nazwa planu, pierwszy odnosnik;
tabele HTML po naglowkach albo parach pole | wartosc; kazdy rekord i tekst bez pol trafia do "surowe".
Wynik <nazwa>_plan_miejscowy.json: {zrodlo, data, nazwa, odnosnik, tereny: [{symbol, przeznaczenie}],
surowe: [tekst], brak_w_usludze}. Odnosnik wzgledny (serwis planow gminy) zapisany doslownie
z dopiskiem. brak_w_usludze nie znaczy, ze planu nie ma: nie kazda gmina jest wlaczona do integracji,
a plan rastrowy ma w usludze tylko nazwe i odnosnik. --model: wpis do miejsce.plan_miejscowy modelu
zamierzenia (nazwa, symbol, przeznaczenie, odnosnik, zrodlo; parametry bez zmian). Informacja
z uslugi nie zastepuje wypisu i wyrysu z planu.
"""
import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wspolne.pliki import json_zwarty
from zamierzenie import model, z_geoportalu
from geoportal import PL1992, do_tm, pobierz, uldk, usluga

KIMPZP = "https://mapy.geoportal.gov.pl/wss/ext/KrajowaIntegracjaMiejscowychPlanowZagospodarowaniaPrzestrzennego"
WARSTWY = "plany,plany_granice,raster,wektor-str,wektor-lzb,wektor-pow"   # gdy GetCapabilities nie odpowiada
ZRODLO = "GUGiK Krajowa Integracja MPZP (WMS GetFeatureInfo)"
DOPISEK = " (odnośnik względny — dotyczy serwisu planów gminy)"
PUSTE = {"br", "hr", "img", "meta", "link", "input", "col", "area", "base", "wbr", "param", "source"}
POMIJANE = {"style", "script", "head"}
INLINE = {"a", "b", "i", "u", "strong", "em", "font", "span", "br", "sup", "sub", "small"}
HTML = INLINE | {"html", "body", "div", "p", "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "center",
                 "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "pre", "code", "label"}
ZAMYKA = {"td": ("td", "th"), "th": ("td", "th"), "tr": ("tr", "td", "th")}           # HTML bez znacznikow koncowych
GRANICE = {"td": ("tr", "table"), "th": ("tr", "table"), "tr": ("table", "tbody", "thead", "tfoot")}
# nazwy pol (male litery bez ogonkow, "_" zamiast innych znakow), od najpewniejszego wzorca
POLA = {"symbol": (r"symb", r"^oznaczenie(_terenu)?$", r"^ozn(_ter(enu)?)?$"),
        "przeznaczenie": (r"przezn", r"^fun_?nazw", r"^funkcj", r"opis_?ozn"),
        "nazwa": (r"nazwa_?plan", r"nazwa_?mpzp", r"^tytul$", r"title$", r"^nazwa$", r"^name$")}
LINK = re.compile(r"(?:https?://|\.{1,2}/|www\.)[^\s<>\"']+")


class Drzewo(HTMLParser):
    """Tolerancyjne drzewo znacznikow HTML i XML: wezel = {"tag", "nazwa", "atr", "tresc": [tekst | wezel]};
    tag malymi literami, nazwa jak w zrodle."""

    def __init__(self, tekst):
        super().__init__(convert_charrefs=True)
        self.korzen = {"tag": "", "nazwa": "", "atr": {}, "tresc": []}
        self.stos = [self.korzen]
        self.feed(tekst)
        self.close()

    def _wezel(self, tag, atr):
        m = re.match(r"<\s*([^\s/>]+)", self.get_starttag_text() or "")
        w = {"tag": tag, "nazwa": m.group(1) if m else tag, "atr": dict(atr), "tresc": []}
        self.stos[-1]["tresc"].append(w)
        return w

    def handle_starttag(self, tag, atr):
        if tag in ZAMYKA:        # nowa komorka albo wiersz zamyka poprzednie (do granicy wiersza albo tabeli)
            j = None
            for i in range(len(self.stos) - 1, 0, -1):
                if self.stos[i]["tag"] in GRANICE[tag]:
                    break
                if self.stos[i]["tag"] in ZAMYKA[tag]:
                    j = i
            if j is not None:
                del self.stos[j:]
        w = self._wezel(tag, atr)
        if tag not in PUSTE:
            self.stos.append(w)

    def handle_startendtag(self, tag, atr):
        self._wezel(tag, atr)

    def handle_endtag(self, tag):
        for i in range(len(self.stos) - 1, 0, -1):
            if self.stos[i]["tag"] == tag:
                del self.stos[i:]
                return

    def handle_data(self, dane):
        self.stos[-1]["tresc"].append(dane)

    def unknown_decl(self, dane):
        if dane.startswith("CDATA["):
            self.stos[-1]["tresc"].append(dane[6:])


def dzieci(w):
    return [x for x in w["tresc"] if isinstance(x, dict)]


def tekst(w):
    if isinstance(w, str):
        return w
    return "" if w["tag"] in POMIJANE else " ".join(tekst(x) for x in w["tresc"])


def czysty(t):
    t = re.sub(r"\s+", " ", t).strip()
    return "" if t.lower() in ("null", "none") else t


def komorka(w):
    """Tekst pola albo komorki; odnosnik <a href> dopisany, gdy tekst go nie zawiera."""
    t = czysty(tekst(w))
    stos, href = [w], None
    while stos and href is None:
        x = stos.pop()
        href = x["atr"].get("href") if x["tag"] == "a" and x["atr"].get("href") else None
        stos += dzieci(x)
    return ("%s %s" % (t, href)).strip() if href and href not in t else t


def lisc(w):
    return all(d["tag"] in INLINE for d in dzieci(w))


def wiersze_tabeli(t):
    for d in dzieci(t):
        if d["tag"] == "tr":
            yield d
        elif d["tag"] != "table":
            yield from wiersze_tabeli(d)


def rekordy(w, wynik):
    """Rekordy [(pole, wartosc)]: tabela HTML z wierszem naglowkow th (rekord na wiersz) albo z parami
    pole | wartosc (jeden rekord), element XML z co najmniej dwoma polami (liscmi)."""
    if w["tag"] == "table":
        wiersze = [r for r in ([k for k in dzieci(tr) if k["tag"] in ("td", "th")] for tr in wiersze_tabeli(w)) if r]
        if len(wiersze) >= 2 and len(wiersze[0]) >= 2 and all(k["tag"] == "th" for k in wiersze[0]):
            naglowki = [komorka(k) for k in wiersze[0]]
            wynik += [list(zip(naglowki, map(komorka, r))) for r in wiersze[1:]]
        elif wiersze and all(len(r) == 2 for r in wiersze):
            wynik.append([(komorka(r[0]), komorka(r[1])) for r in wiersze])
        return
    liscie = [d for d in dzieci(w) if d["tag"] not in HTML and lisc(d)]
    if len(liscie) >= 2:
        wynik.append([(d["nazwa"], komorka(d)) for d in liscie])
    for d in dzieci(w):
        rekordy(d, wynik)


def klucz(nazwa):
    n = unicodedata.normalize("NFKD", nazwa.split(":")[-1].lower().replace("ł", "l"))
    return re.sub(r"[^a-z0-9]+", "_", n.encode("ascii", "ignore").decode()).strip("_")


def pole(rekord, rodzaj):
    for wzor in POLA[rodzaj]:
        for k, v in rekord:
            if v and re.search(wzor, klucz(k)):
                return v
    return None


def dodaj(lista, x):
    if x not in lista:
        lista.append(x)


def rozbierz(odpowiedz):
    """Odpowiedz GetFeatureInfo uslugi zbiorczej -> {"tereny", "nazwa", "odnosnik", "surowe", "bledy"}.
    Czesci oddzielone <hr/>: wyjatek uslugi (bledy), rekordy z polami (tereny z symbolem albo
    przeznaczeniem, nazwa, pierwszy odnosnik; surowe "pole: wartosc; ...") albo sam tekst (surowe)."""
    w = {"tereny": [], "nazwa": None, "odnosnik": None, "surowe": [], "bledy": []}
    for czesc in re.split(r"<hr\s*/?>", odpowiedz, flags=re.I):
        if not czesc.strip():
            continue
        drzewo = Drzewo(czesc).korzen
        if "ServiceException" in czesc:
            kod = re.search(r'code\s*=\s*["\']([^"\']+)', czesc)
            w["bledy"].append(("%s: " % kod.group(1) if kod else "") + (czysty(tekst(drzewo)) or "ServiceException"))
            continue
        lista = []
        rekordy(drzewo, lista)
        lista = [r for r in ([(czysty(k), v) for k, v in r if v] for r in lista) if r]
        if not lista:
            t = czysty(tekst(drzewo))
            if t and not czesc.lstrip().startswith("<?xml"):       # pusta kolekcja GML - bez tekstu
                dodaj(w["surowe"], t)
            continue
        for r in lista:
            dodaj(w["surowe"], "; ".join("%s: %s" % kv for kv in r))
            s, p = pole(r, "symbol"), pole(r, "przeznaczenie")
            if s or p:
                dodaj(w["tereny"], {"symbol": s, "przeznaczenie": p})
            w["nazwa"] = w["nazwa"] or pole(r, "nazwa")
            link = next((m.group(0) for m in (LINK.search(v) for _, v in r) if m), None)
            w["odnosnik"] = w["odnosnik"] or link
    return w


def zbierz(czesciowe, fmt):
    """Wynik z odpowiedzi w kilku punktach (kolejnosc punktow; bez powtorzen)."""
    W = {"zrodlo": "%s, format %s" % (ZRODLO, fmt), "data": date.today().isoformat(), "nazwa": None, "odnosnik": None,
         "tereny": [], "surowe": [], "brak_w_usludze": True}
    for c in czesciowe:
        for t in c["tereny"]:
            dodaj(W["tereny"], t)
        for s in c["surowe"] + ["wyjątek usługi WMS: " + b for b in c["bledy"]]:
            dodaj(W["surowe"], s)
        W["nazwa"] = W["nazwa"] or c["nazwa"]
        W["odnosnik"] = W["odnosnik"] or c["odnosnik"]
    if W["odnosnik"] and re.match(r"\.{0,2}/", W["odnosnik"]):
        W["odnosnik"] += DOPISEK
    W["brak_w_usludze"] = not (W["tereny"] or W["nazwa"] or W["odnosnik"])
    return W


def format_i_warstwy(cap):
    """(format GetFeatureInfo: GML/XML przed HTML przed reszta, warstwy odpytywalne) z GetCapabilities WMS 1.3.0."""
    ns = "{http://www.opengis.net/wms}"
    k = ET.fromstring(cap)
    formaty = [f.text.strip() for f in k.iterfind(".//%sGetFeatureInfo/%sFormat" % (ns, ns)) if f.text]
    warstwy = [w.findtext(ns + "Name") for w in k.iter(ns + "Layer") if w.get("queryable") == "1" and w.findtext(ns + "Name")]
    ranga = lambda f: 0 if "gml" in f or "xml" in f else 1 if "html" in f else 2
    return (min(formaty, key=ranga) if formaty else "text/html"), warstwy


def punkty_zapytan(dzialka, punkt):
    """[(E, N)]: srodek dzialki i 4 punkty 1 m od granicy (skrajne w kierunkach NE, NW, SE, SW);
    bez dzialki - punkt, dzialka wezsza niz 2 m - sam srodek."""
    if dzialka is None:
        return [tuple(punkt)]
    c = dzialka.centroid if dzialka.contains(dzialka.centroid) else dzialka.representative_point()
    wynik = [(c.x, c.y)]
    wew = dzialka.buffer(-1)
    if not wew.is_empty:
        wsp = [p for g in getattr(wew, "geoms", [wew]) for p in g.exterior.coords[:-1]]
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            dodaj(wynik, max(wsp, key=lambda q: sx * q[0] + sy * q[1]))
    return wynik


def zapytanie(E, N, fmt, warstwy, d=5.0):
    """Tekst odpowiedzi GetFeatureInfo w punkcie (WMS 1.3.0, EPSG:2180: BBOX w kolejnosci osi N, E)."""
    t = pobierz(KIMPZP, {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetFeatureInfo", "LAYERS": warstwy,
                         "QUERY_LAYERS": warstwy, "STYLES": "", "CRS": "EPSG:2180",
                         "BBOX": "%.2f,%.2f,%.2f,%.2f" % (N - d, E - d, N + d, E + d), "WIDTH": 101, "HEIGHT": 101,
                         "I": 50, "J": 50, "INFO_FORMAT": fmt, "FEATURE_COUNT": 10}, czas=60)[0]
    return t.decode("utf-8", "replace")


def opis(w):
    if w["tereny"]:
        return "; ".join(" ".join(x for x in (t["symbol"], t["przeznaczenie"]) if x) for t in w["tereny"])
    if w["nazwa"] or w["odnosnik"]:
        return "plan bez symbolu terenu w usludze: %s" % (w["nazwa"] or w["odnosnik"])
    return "brak: %s" % ("; ".join(w["bledy"] + w["surowe"])[:150] or "pusta odpowiedz")


def main():
    ap = argparse.ArgumentParser(description="Plan miejscowy z uslugi GUGiK Krajowa Integracja MPZP (WMS GetFeatureInfo).")
    grupa = ap.add_mutually_exclusive_group(required=True)
    grupa.add_argument("--xy", help="dlugosc,szerokosc geograficzna (WGS84), np. 21.0063,52.2318")
    grupa.add_argument("--dzialka", help='identyfikator dzialki (np. 146510_8.0309.24/35) albo "obreb numer"')
    grupa.add_argument("--meta", help="<nazwa>_meta.json z narzedzia/geoportal.py (dzialka i punkt bazowy)")
    ap.add_argument("--model", help="model zamierzenia: wpis do miejsce.plan_miejscowy (parametry bez zmian)")
    ap.add_argument("--wyjscie", help="katalog wyniku (domyslnie katalog pliku --meta albo ./wyjscie)")
    ap.add_argument("--nazwa", help="przedrostek pliku wyniku (domyslnie z nazwy pliku --meta albo geoportal)")
    a = ap.parse_args()

    M = None
    if a.model:
        if not Path(a.model).is_file():
            print("brak pliku modelu %s - utworz go przez zamierzenie/z_geoportalu.py" % a.model)
            return 1
        M = model.wczytaj(a.model)
        if model.rodzaj_pliku(M) != "zamierzenie":
            print("--model: to nie jest model zamierzenia (zamierzenie/SCHEMAT.md)%s" % (
                " - to model lokalu" if model.rodzaj_pliku(M) == "lokal" else ""))
            return 2

    # dzialka (EPSG:2180) i punkt zapytania
    dzialka = None
    if a.meta:
        try:
            with open(a.meta, encoding="utf-8") as f:
                meta = json.load(f)
            pb = meta["punkt_bazowy"]
            if pb.get("epsg") != 2180:
                print("%s: punkt bazowy poza Polska - usluga obejmuje tylko Polske" % a.meta)
                return 1
            punkt = (float(pb["E"]), float(pb["N"]))
            if meta.get("dzialka"):
                dzialka = Polygon([(punkt[0] + x, punkt[1] + y) for x, y in meta["dzialka"]["obrys_m"]])
                print("dzialka %s z %s" % (meta["dzialka"].get("id"), a.meta))
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("plik %s nieczytelny albo bez punktu bazowego: %s" % (a.meta, e))
            return 1
    elif a.dzialka:
        r = usluga("ULDK", uldk, "GetParcelByIdOrNr", id=a.dzialka, result="id,geom_wkt")
        if not r:
            print("nie znaleziono dzialki \"%s\"" % a.dzialka if r is not None else "usluga ULDK nie odpowiada")
            return 1
        dzialka = r[0][1]
        punkt = dzialka.representative_point().coords[0]
        print("dzialka %s (ULDK)" % r[0][0])
    else:
        try:
            lon, lat = (float(v) for v in a.xy.split(","))
        except ValueError:
            ap.error("--xy: dlugosc,szerokosc, np. 21.0063,52.2318")
        if not (49.0 <= lat <= 54.9 and 14.1 <= lon <= 24.2):
            print("punkt poza Polska - usluga obejmuje tylko Polske")
            return 1
        punkt = do_tm(lat, lon, **PL1992)
        r = usluga("ULDK", uldk, "GetParcelByXY", xy="%.2f,%.2f" % punkt, result="id,geom_wkt")
        if r:
            dzialka = r[0][1]
            print("dzialka %s (ULDK) w punkcie" % r[0][0])
        else:
            print("bez dzialki: zapytanie tylko w punkcie")

    # format i warstwy z GetCapabilities, zapytania w punktach (po wyjatku uslugi text/html)
    cap = usluga("KIMPZP GetCapabilities", lambda: format_i_warstwy(
        pobierz(KIMPZP, {"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"}, czas=60)[0]))
    fmt, warstwy = cap or ("text/html", [])
    warstwy = ",".join(warstwy) or WARSTWY
    print("usluga KIMPZP: format %s, warstwy %s" % (fmt, warstwy))
    czesciowe = []
    for i, (E, N) in enumerate(punkty_zapytan(dzialka, punkt), 1):
        t = usluga("KIMPZP GetFeatureInfo", zapytanie, E, N, fmt, warstwy)
        w = rozbierz(t) if t is not None else None
        if w and w["bledy"] and fmt != "text/html":
            print("wyjatek uslugi na format %s (%s) - dalej text/html" % (fmt, w["bledy"][0][:100]))
            fmt = "text/html"
            t = usluga("KIMPZP GetFeatureInfo", zapytanie, E, N, fmt, warstwy)
            w = rozbierz(t) if t is not None else None
        if w is not None:
            czesciowe.append(w)
            print("  punkt %d (E %.2f, N %.2f): %s" % (i, E, N, opis(w)))
    if not czesciowe:
        print("usluga KIMPZP nie odpowiedziala - nic nie zapisano")
        return 1
    W = zbierz(czesciowe, fmt)

    nazwa = a.nazwa or (re.sub(r"_meta$", "", Path(a.meta).stem) if a.meta else "geoportal")
    kat = Path(a.wyjscie or (Path(a.meta).parent if a.meta else "wyjscie"))
    kat.mkdir(parents=True, exist_ok=True)
    plik = kat / ("%s_plan_miejscowy.json" % nazwa)
    with open(plik, "w", encoding="utf-8") as f:
        f.write(json_zwarty(W) + "\n")
    if W["brak_w_usludze"]:
        print("brak planu w usludze: gmina moze nie byc wlaczona do integracji albo planu nie ma - sprawdz w gminie")
    else:
        print("nazwa planu: %s" % (W["nazwa"] or "-"))
        for t in W["tereny"] or [{"symbol": "-", "przeznaczenie": "brak symbolu w usludze (plan rastrowy?) - odczytaj z rysunku planu"}]:
            print("teren: %s - %s" % (t["symbol"] or "-", t["przeznaczenie"] or "-"))
        print("odnosnik: %s" % (W["odnosnik"] or "-"))
    print("zapisano", plik)
    if M is not None:
        wpis = z_geoportalu.wpisz_plan(M, W)
        if wpis:
            model.zapisz(M)
            print("%s -> %s" % (wpis, M["_sciezka"]))
        else:
            print("model bez zmian (brak planu w usludze)")
    print("informacja z uslugi nie zastepuje wypisu i wyrysu z planu miejscowego")
    return 0


if __name__ == "__main__":
    sys.exit(main())
