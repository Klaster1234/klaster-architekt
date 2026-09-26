"""Wczytanie i zapis modelu (JSON) oraz sciezki wynikow - wspolne dla modulu lokalu
i modulu zamierzenia.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from wspolne import pliki
    M = pliki.wczytaj("przyklad/mieszkanie/model/lokal_projekt.json")
    pliki.zapisz(M, "wyjscie/projekt.json")

Model to jeden plik JSON w centymetrach. Klucze zaczynajace sie od "_" (sciezka,
cache) istnieja tylko w pamieci i nie trafiaja do zapisu. katalog_wyjscia i
sciezka_wyniku ustalaja, gdzie narzedzia zapisuja wyniki. Brak pliku modelu, bledny JSON i id
projektu, ktore nie nadaje sie na przedrostek nazwy pliku (poprawne_id), koncza narzedzie
komunikatem (SystemExit) zamiast tracebacku.
"""
import json
import re
import shutil
from pathlib import Path

DOMYSLNY_PROJEKT = {"id": "lokal", "obiekt": "", "inwestor": "", "autor": "", "faza": "WSTĘPNA"}
WZOR_ID = re.compile(r"[A-Za-z0-9_.-]+")   # meta.projekt.id: przedrostek nazw plikow wynikowych


def poprawne_id(ident):
    """Czy id projektu nadaje sie na przedrostek nazwy pliku: litery A-Z, cyfry, _ . - (i nie samo "..")."""
    return isinstance(ident, str) and WZOR_ID.fullmatch(ident) is not None and ident != ".."


def wczytaj(sciezka):
    sciezka = Path(sciezka).resolve()
    try:
        f = open(sciezka, encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit("brak pliku modelu: %s" % sciezka)
    with f:
        try:
            M = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit("%s: bledny JSON w linii %d, kolumnie %d: %s" % (sciezka, e.lineno, e.colno, e.msg))
    M["_sciezka"] = sciezka
    M["_cache"] = {}
    return M


def json_zwarty(o, wciecie=0, szer=150):
    """JSON z wcieciami, w ktorym krotkie rekordy i listy liczb zostaja w jednej linii."""
    jedna = json.dumps(o, ensure_ascii=False, separators=(", ", ": "))
    if wciecie > 0 and len(jedna) + 2 * wciecie <= szer or not isinstance(o, (dict, list)) or not o:
        return jedna
    sp = "  " * wciecie
    if isinstance(o, dict):
        czesci = ["%s  %s: %s" % (sp, json.dumps(k, ensure_ascii=False), json_zwarty(v, wciecie + 1, szer))
                  for k, v in o.items()]
        return "{\n" + ",\n".join(czesci) + "\n" + sp + "}"
    czesci = ["%s  %s" % (sp, json_zwarty(v, wciecie + 1, szer)) for v in o]
    return "[\n" + ",\n".join(czesci) + "\n" + sp + "]"


def zapisz(M, sciezka=None, kopia=True):
    """Zapisuje model bez kluczy "_"; przy kopia=True zostawia obok plik .bak."""
    sciezka = Path(sciezka or M["_sciezka"])
    if kopia and sciezka.exists():
        shutil.copy2(sciezka, sciezka.with_name(sciezka.name + ".bak"))
    czysty = {k: v for k, v in M.items() if not k.startswith("_")}
    with open(sciezka, "w", encoding="utf-8", newline="\n") as f:
        f.write(json_zwarty(czysty) + "\n")
    M["_cache"] = {}
    return sciezka


def katalog_wyjscia(M, podany=None):
    if podany:
        k = Path(podany)
    else:
        baza = Path(M["_sciezka"]).parent
        if baza.name == "model":
            baza = baza.parent
        k = baza / "wyjscie"
    k.mkdir(parents=True, exist_ok=True)
    return k


def projekt(M):
    return {**DOMYSLNY_PROJEKT, **M.get("meta", {}).get("projekt", {})}


def sciezka_wyniku(M, nazwa, podany=None):
    """Sciezka bez rozszerzenia: <wyjscie>/<id projektu>_<nazwa>; id spoza WZOR_ID - SystemExit
    z komunikatem (plik nie trafi poza katalog wynikow)."""
    ident = projekt(M)["id"]
    if not poprawne_id(ident):
        raise SystemExit("%s: meta.projekt.id %s nie nadaje sie na przedrostek nazw plikow wynikowych - dozwolone "
                         "litery A-Z i a-z, cyfry, _ . - (bez spacji, nie samo ..); popraw model"
                         % (Path(M.get("_sciezka") or "model").name, json.dumps(ident, ensure_ascii=False)))
    return katalog_wyjscia(M, podany) / ("%s_%s" % (ident, nazwa))
