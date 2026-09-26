"""Lokalny serwer planera 3D: strona planera i dane modelu, tylko 127.0.0.1, bez cache.

    python planer3d/serwer.py przyklad/mieszkanie/model/lokal_projekt.json
    python planer3d/serwer.py przyklad/mieszkanie/model/lokal_projekt.json --port 8056 --wyjscie robocze/
    python planer3d/serwer.py przyklad/ogrod/model/projekt.json przyklad/ogrod/model/istniejacy.json

Pod adresem / jest planer: planer3d/index.html dla modelu lokalu, planer3d/zamierzenie.html,
gdy pierwszy z podanych modeli jest modelem zamierzenia. Pod /dane.json sa dane pierwszego
modelu, pod /dane.json?model=<nazwa> dane innego z podanych (nazwa pliku bez rozszerzenia,
tylko z tej listy), a pod /modele.json lista modeli z rodzajem - planer zamierzenia
przelacza nia warianty (np. stan istniejacy i projekt); model, ktorego nie da sie odczytac
(np. bledny JSON), ma tam rodzaj "blad" i komunikat. Dane odtwarza eksport_web.py
(w osobnym procesie), gdy model, pliki jego modulow wnetrz, eksporter albo biblioteki sa
nowsze od pliku <wyjscie>/<id>_planer.json, albo gdy plik danych nosi zrodlo innego modelu
(np. po przelaczeniu serwera na inny plik z tym samym --wyjscie), wiec po zmianie modelu
wystarczy odswiezyc strone. Serwer podaje wylacznie pliki strony z katalogu planer3d/ oraz
/dane.json i /modele.json, zawsze z naglowkiem Cache-Control: no-store, przyjmuje tylko
zapytania z naglowkiem Host 127.0.0.1:<port> albo localhost:<port> (ochrona przed DNS
rebinding) i nigdy nie zapisuje modelu.
"""
import argparse
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

KATALOG = Path(__file__).resolve().parent
BAZA = KATALOG.parent
EKSPORT = KATALOG / "eksport_web.py"
ZALEZNOSCI = [EKSPORT, BAZA / "lokal" / "model.py", BAZA / "lokal" / "geometria.py", BAZA / "wspolne" / "pliki.py",
              BAZA / "rysunki" / "glb.py", *sorted((BAZA / "zamierzenie").glob("*.py"))]
TYPY = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}

sys.path.insert(0, str(BAZA))
from lokal import model
from zamierzenie import model as zmodel


class Dane:
    """Plik danych planera odtwarzany z modelu, gdy jest nieaktualny."""

    blokada = threading.Lock()   # wspolna: modele o tym samym id pisalyby ten sam plik danych

    def __init__(self, sciezka_modelu, wyjscie=None):
        self.model = Path(sciezka_modelu).resolve()
        self.wyjscie = wyjscie
        self.nazwa = self.model.stem   # w /dane.json?model=<nazwa> i /modele.json
        self._rodzaj = "lokal"
        self.blad = None   # komunikat, gdy modelu nie da sie odczytac (w /modele.json rodzaj "blad")

    def rodzaj(self):
        """"zamierzenie" albo "lokal"; gdy modelu chwilowo nie da sie odczytac - ostatni rozpoznany (komunikat w blad)."""
        try:
            M = model.wczytaj(self.model)
        except (OSError, ValueError, SystemExit) as e:   # SystemExit: bledny JSON (wspolne/pliki.py)
            self.blad = str(e)
            return self._rodzaj
        self.blad = None
        self._rodzaj = "zamierzenie" if zmodel.rodzaj_pliku(M) == "zamierzenie" else "lokal"
        return self._rodzaj

    def plik(self, M=None):
        if M is None:
            M = model.wczytaj(self.model)  # tylko odczyt: id projektu wyznacza nazwe pliku
        p = model.sciezka_wyniku(M, "planer", self.wyjscie)
        return p.with_name(p.name + ".json")

    def zrodla(self, M):
        """Pliki, z ktorych powstaja dane: model, pliki modulow wnetrz (wzgledem katalogu modelu) i ZALEZNOSCI."""
        moduly = [self.model.parent / m["plik"] for m in M.get("moduly") or [] if isinstance(m, dict) and m.get("plik")]
        return [self.model, *moduly, *ZALEZNOSCI]

    def _zrodlo_zgodne(self, plik):
        """Czy pole "zrodlo" zapisane przez eksport_web.py wskazuje na aktualnie serwowany model.

        Odczyt jest bezpieczny: uszkodzony albo nie-JSON-owy plik danych liczy sie jako niezgodny,
        wiec zostanie po prostu odtworzony od nowa.
        """
        try:
            with open(plik, encoding="utf-8") as f:
                zrodlo = json.load(f).get("zrodlo", "")
        except (OSError, ValueError):
            return False
        return zrodlo.startswith(self.model.name + " ")

    def pobierz(self):
        """(kod HTTP, tresc) - dane aktualne wzgledem modelu, jego modulow, eksportera i wlasnego zrodla."""
        with self.blokada:
            try:
                M = model.wczytaj(self.model)
                plik = self.plik(M)
            except (OSError, ValueError, SystemExit) as e:   # SystemExit: bledny JSON albo id (wspolne/pliki.py)
                return 500, ("nie mozna wczytac modelu %s: %s\n" % (self.model.name, e)).encode("utf-8")
            zrodla = max(p.stat().st_mtime for p in self.zrodla(M) if p.exists())
            nieaktualne = not plik.exists() or plik.stat().st_mtime < zrodla or not self._zrodlo_zgodne(plik)
            if nieaktualne:
                polecenie = [sys.executable, str(EKSPORT), str(self.model)]
                if self.wyjscie:
                    polecenie += ["--wyjscie", str(self.wyjscie)]
                w = subprocess.run(polecenie, capture_output=True, text=True, encoding="utf-8", errors="replace")
                print("dane planera:", ((w.stdout or "") + (w.stderr or "")).strip()[-600:], flush=True)
                if w.returncode != 0 or not plik.exists():
                    return 500, ("eksport_web.py zakonczyl sie bledem:\n%s\n" % (w.stderr or w.stdout)[-3000:]).encode("utf-8")
            return 200, plik.read_bytes()


def strona(modele):
    """Strona planera dla pierwszego modelu: zamierzenie.html albo index.html."""
    return "zamierzenie.html" if modele[0].rodzaj() == "zamierzenie" else "index.html"


def wybrany(modele, zapytanie):
    """Model z parametru ?model=<nazwa> - tylko nazwa z listy, bez sciezek; bez parametru pierwszy, nieznany None."""
    nazwy = parse_qs(zapytanie, keep_blank_values=True).get("model")
    if nazwy is None:
        return modele[0]
    return next((d for d in modele if d.nazwa == nazwy[0]), None) if len(nazwy) == 1 else None


def obsluga(modele):
    class Obsluga(BaseHTTPRequestHandler):
        def do_GET(self):
            self.odpowiedz(True)

        def do_HEAD(self):
            self.odpowiedz(False)

        def odpowiedz(self, z_trescia):
            port = self.server.server_port
            host = (self.headers.get("Host") or "").strip().lower()
            if host not in ("127.0.0.1:%d" % port, "localhost:%d" % port):
                # ochrona przed DNS rebinding: strona z innej domeny przekierowana na 127.0.0.1
                # przez DNS wysyla naglowek Host tej domeny, nie 127.0.0.1/localhost
                kod, tresc, typ = 403, b"niedozwolony naglowek Host\n", "text/plain; charset=utf-8"
            else:
                adres = urlsplit(self.path)
                sciezka = unquote(adres.path)
                if sciezka == "/dane.json":
                    dane = wybrany(modele, adres.query)
                    if dane is None:
                        kod, tresc = 404, b"nie ma takiego modelu\n"
                    else:
                        kod, tresc = dane.pobierz()
                    typ = "application/json; charset=utf-8" if kod == 200 else "text/plain; charset=utf-8"
                elif sciezka == "/modele.json":
                    kod, typ = 200, "application/json; charset=utf-8"
                    lista = [(d, d.rodzaj()) for d in modele]   # rodzaj() ustawia blad
                    tresc = json.dumps([{"nazwa": d.nazwa, "rodzaj": "blad", "blad": d.blad} if d.blad else {"nazwa": d.nazwa, "rodzaj": r}
                                        for d, r in lista], ensure_ascii=False).encode("utf-8")
                else:
                    nazwa = strona(modele) if sciezka == "/" else sciezka.lstrip("/")
                    try:
                        plik = (KATALOG / nazwa).resolve()
                    except (OSError, ValueError):  # np. bajt NUL w adresie
                        plik = KATALOG
                    if plik.parent != KATALOG or plik.suffix not in TYPY or not plik.is_file():
                        kod, tresc, typ = 404, b"nie ma takiego pliku\n", "text/plain; charset=utf-8"
                    else:
                        kod, tresc, typ = 200, plik.read_bytes(), TYPY[plik.suffix]
            self.send_response(kod)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(tresc)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if z_trescia:
                self.wfile.write(tresc)

        def log_request(self, code="-", size="-"):
            try:
                if int(code) < 400:
                    return
            except (TypeError, ValueError):
                pass
            super().log_request(code, size)

    return Obsluga


def main():
    ap = argparse.ArgumentParser(description="Serwer planera 3D (tylko 127.0.0.1)")
    ap.add_argument("model", nargs="+", help="plik modelu lokalu albo modelu zamierzenia (JSON); kilka plikow "
                                             "to warianty do przelaczania w planerze, pierwszy jest domyslny")
    ap.add_argument("--port", type=int, default=8055)
    ap.add_argument("--wyjscie", help="katalog na dane planera (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    for p in a.model:
        if not Path(p).is_file():
            sys.exit("brak pliku modelu: %s" % p)
    nazwy = [Path(p).stem for p in a.model]
    powtorzone = sorted({n for n in nazwy if nazwy.count(n) > 1})
    if powtorzone:
        sys.exit("modele musza miec rozne nazwy plikow (planer wybiera je po nazwie): %s" % ", ".join(powtorzone))
    modele = [Dane(p, a.wyjscie) for p in a.model]
    for dane in modele:
        kod, tresc = dane.pobierz()
        if kod != 200:
            print(tresc.decode("utf-8", "replace"), flush=True)
    try:
        serwer = ThreadingHTTPServer(("127.0.0.1", a.port), obsluga(modele))
    except OSError as e:
        sys.exit("nie mozna uruchomic serwera na porcie %d (%s) - wybierz inny: --port" % (a.port, e))
    adres = "http://127.0.0.1:%d/" % a.port
    if len(modele) == 1:
        print("Planer 3D: %s  (model: %s, Ctrl+C konczy)" % (adres, Path(a.model[0]).name), flush=True)
    else:
        print("Planer 3D (Ctrl+C konczy):", flush=True)
        pierwszy = modele[0].rodzaj()
        for i, dane in enumerate(modele):
            rodzaj = dane.rodzaj()
            if i == 0:
                print("  %s  - %s (%s)" % (adres, dane.model.name, rodzaj), flush=True)
            elif rodzaj == "zamierzenie":
                print("  %s  - %s (%s)" % (adres + ("?model=" if pierwszy == "zamierzenie" else "zamierzenie.html?model=")
                                            + dane.nazwa, dane.model.name, rodzaj), flush=True)
            else:
                print("  %s (%s) - planer lokalu pokazuje tylko pierwszy model: uruchom dla niego osobny serwer"
                      % (dane.model.name, rodzaj), flush=True)
    try:
        serwer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serwer.server_close()


if __name__ == "__main__":
    main()
