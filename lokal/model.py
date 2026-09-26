"""Wczytanie modelu lokalu i odczyty wspolne dla wszystkich narzedzi.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lokal import model
    M = model.wczytaj("przyklad/mieszkanie/model/lokal_projekt.json")

Model to jeden plik JSON w centymetrach, opisany w lokal/SCHEMAT.md. Narzedzia
go czytaja i nie zapisuja; wyjatek to zapisz(), z ktorego korzysta rzedna.py.
Klucze zaczynajace sie od "_" (sciezka, cache) istnieja tylko w pamieci.
"""
from wspolne.pliki import DOMYSLNY_PROJEKT, wczytaj, json_zwarty, zapisz, projekt, katalog_wyjscia, sciezka_wyniku

# rodzaj elementu aranzacji -> kategoria, z ktorej korzystaja rysunki, planer i kontrole
RODZAJE = {
    "krzesło": "siedzisko", "hoker": "siedzisko", "fotel": "siedzisko", "fotel biurowy": "siedzisko",
    "fotel rozkładany": "siedzisko", "pufa": "siedzisko", "stołek": "siedzisko", "ławka": "siedzisko",
    "stół": "stol", "biurko": "stol", "toaletka": "stol",
    "stolik kawowy": "stolik", "stolik": "stolik",
    "łóżko": "lozko",
    "sofa": "sofa", "narożnik": "sofa", "kanapa": "sofa",
    "ciąg kuchenny": "zabudowa_niska", "wyspa": "zabudowa_niska", "komoda": "zabudowa_niska",
    "szafka RTV": "zabudowa_niska", "szafka nocna": "zabudowa_niska", "szafka": "zabudowa_niska",
    "szafka z umywalką": "zabudowa_niska",
    "szafa": "zabudowa_wysoka", "szafa w zabudowie": "zabudowa_wysoka", "regał": "zabudowa_wysoka",
    "witryna": "zabudowa_wysoka", "słupek": "zabudowa_wysoka", "słupek lodówki": "zabudowa_wysoka",
    "zabudowa": "zabudowa_wysoka",
    "szafka wisząca": "wiszaca", "półka": "wiszaca", "front wiszący": "wiszaca", "blenda": "wiszaca",
    "toaleta": "sanitariat", "umywalka": "sanitariat", "bidet": "sanitariat", "wanna": "sanitariat",
    "prysznic": "prysznic",
    "lodówka": "urzadzenie", "pralka": "urzadzenie", "pralko-suszarka": "urzadzenie",
    "zmywarka": "urzadzenie", "zamrażarka": "urzadzenie", "piekarnik": "urzadzenie",
    "murek": "murek", "drzwi szklane": "szklo", "lustro": "lustro",
}

KATEGORIE = ("siedzisko", "stol", "stolik", "lozko", "sofa", "zabudowa_niska", "zabudowa_wysoka",
             "wiszaca", "sanitariat", "prysznic", "urzadzenie", "murek", "szklo", "lustro", "inne")

TYPY_E = ("gniazdo", "łącznik", "punkt świetlny", "kinkiet", "wypust", "rozdzielnica", "zasilanie", "rezerwa")
MEDIA = ("kanalizacja", "woda zimna", "woda ciepła")


def wysokosc(M):
    return float(M.get("meta", {}).get("wysokosc_kondygnacji", 270))


def rzedna_sufitu(M):
    rs = M.get("meta", {}).get("rzedna_sufitu") or {}
    return float(rs.get("wartosc", wysokosc(M)))


def pomieszczenie(M, nr):
    for p in M["pomieszczenia"]:
        if p["nr"] == nr:
            return p
    raise KeyError("brak pomieszczenia %s" % nr)


def elementy(M, nr=None):
    """Kopie elementow aranzacji z dodanym kluczem "_pom" (numer pomieszczenia)."""
    wynik = []
    for pom, ar in M.get("aranzacja", {}).items():
        if nr is not None and pom != nr:
            continue
        wynik += [dict(e, _pom=pom) for e in ar.get("elementy", [])]
    return wynik


def _rekordy(M):
    """(sekcja, rekord) dla wszystkiego, co ma pole id."""
    listy = [("sciany", M.get("sciany", [])), ("otwory", M.get("otwory", [])),
             ("szachty", M.get("szachty", [])), ("grzejniki", M.get("grzejniki", [])),
             ("strefy_wirtualne", M.get("strefy_wirtualne", [])), ("kontekst", M.get("kontekst", [])),
             ("zmiany", M.get("zmiany", [])), ("elektryka", M.get("elektryka", [])),
             ("klady", M.get("klady", []))]
    wk, kl, su, wy = (M.get(k) or {} for k in ("wod_kan", "klimatyzacja", "sufity", "wykonczenie"))
    listy += [("wod_kan.punkty", wk.get("punkty", [])), ("wod_kan.trasy", wk.get("trasy", [])),
              ("klimatyzacja.jednostki", kl.get("jednostki", [])), ("klimatyzacja.trasy", kl.get("trasy", [])),
              ("klimatyzacja.przekucia", kl.get("przekucia", [])), ("sufity.klapy", su.get("klapy", [])),
              ("sufity.kratki", su.get("kratki", [])), ("wykonczenie.okladziny", wy.get("okladziny", [])),
              ("wykonczenie.warianty", wy.get("warianty", []))]
    for nr, ar in M.get("aranzacja", {}).items():
        listy.append(("aranzacja." + nr, ar.get("elementy", [])))
    for sekcja, lista in listy:
        for r in lista:
            if isinstance(r, dict) and "id" in r:
                yield sekcja, r


def indeks_id(M):
    """id -> (sekcja, rekord); ValueError przy powtorzonym id."""
    idx = {}
    for sekcja, r in _rekordy(M):
        if r["id"] in idx:
            raise ValueError("powtorzone id %s (%s i %s)" % (r["id"], idx[r["id"]][0], sekcja))
        idx[r["id"]] = (sekcja, r)
    return idx


def kategoria(rodzaj):
    """Kategoria rodzaju: dokladne dopasowanie albo najdluzszy pasujacy poczatek
    ("szafka wisząca górna" -> wiszaca); nieznany rodzaj -> "inne"."""
    if not rodzaj:
        return "inne"
    if rodzaj in RODZAJE:
        return RODZAJE[rodzaj]
    for klucz in sorted(RODZAJE, key=len, reverse=True):
        if rodzaj.startswith(klucz):
            return RODZAJE[klucz]
    return "inne"


def jest_swiatlem(punkt):
    typ = punkt.get("typ", "")
    if typ in ("punkt świetlny", "kinkiet"):
        return True
    wariant = punkt.get("wariant") or ""
    return typ == "wypust" and ("LED" in wariant or "oświetl" in wariant)


def tokeny(M):
    return (M.get("wykonczenie") or {}).get("tokeny", {})


def hex_tokenu(M, token, domyslny="#D9D6D0"):
    """Hex tokenu; napis w postaci #RRGGBB przechodzi bez zmian; brak -> domyslny."""
    if not token:
        return domyslny
    if isinstance(token, str) and token.startswith("#") and len(token) == 7:
        return token.upper()
    t = tokeny(M).get(token)
    return t["hex"].upper() if t else domyslny


def warianty(M):
    return (M.get("wykonczenie") or {}).get("warianty", [])


def wybory_domyslne(M):
    return {w["id"]: int(w.get("domyslna", 0)) for w in warianty(M)}


def wybory_z_tekstu(tekst):
    """'V1=1,V2=0' -> {'V1': 1, 'V2': 0}; pusty -> {}."""
    wynik = {}
    for kawalek in (tekst or "").split(","):
        if "=" in kawalek:
            k, v = kawalek.split("=", 1)
            wynik[k.strip()] = int(v)
    return wynik


def _trafia(cel, rodzaj, ident):
    if rodzaj == "element":
        return cel.get("element") == ident
    if rodzaj == "sciany":
        return cel.get("pomieszczenie") == ident and cel.get("sciany")
    if rodzaj == "okladzina":
        return cel.get("okladzina") == ident
    return False


def okladzina(M, ident):
    for o in (M.get("wykonczenie") or {}).get("okladziny", []):
        if o["id"] == ident:
            return o
    raise KeyError("brak okladziny %s" % ident)


def token_celu(M, cel, wybory=None):
    """Nazwa tokenu po wariantach: cel = ("element", id) | ("sciany", nr) | ("okladzina", id)."""
    rodzaj, ident = cel
    wyb = wybory_domyslne(M)
    wyb.update(wybory or {})
    for w in warianty(M):
        if any(_trafia(c, rodzaj, ident) for c in w.get("cel", [])):
            opcje = w["opcje"]
            i = min(max(int(wyb.get(w["id"], 0)), 0), len(opcje) - 1)
            return opcje[i]["token"]
    if rodzaj == "element":
        for e in elementy(M):
            if e["id"] == ident:
                return e.get("kolor")
        return None
    if rodzaj == "sciany":
        return pomieszczenie(M, ident).get("sciany_kolor")
    if rodzaj == "okladzina":
        return okladzina(M, ident).get("token")
    raise ValueError("nieznany rodzaj celu: %s" % rodzaj)


def kolor(M, cel, wybory=None):
    """Hex koloru celu po wariantach albo None, gdy model koloru nie okresla."""
    token = token_celu(M, cel, wybory)
    return hex_tokenu(M, token) if token else None
