"""Sprawdza spojnosc modelu lokalu i porownuje pola pomieszczen z dokumentacja.

    python lokal/waliduj.py przyklad/mieszkanie/model/lokal_projekt.json

Spojnosc: meta.projekt.id zgodne z regula nazw plikow wynikowych (wspolne/pliki.py: poprawne_id),
unikalne id, odwolania (otwor -> sciana, element / punkt / grzejnik -> pomieszczenie, trasa -> punkt,
wariant -> cel, kolor -> token, rekord -> zrodlo).
Pola: kazde pomieszczenie musi dac wielokat, a pole z modelu zgadzac sie z pow_m2
z tolerancja max(0,5%, 0,02 m2). Pomieszczenia z "wydzielone_z" sumuja sie do
bazowego; pole "zmiana" oznacza roznice zamierzona. Kod wyjscia 1 przy bledach.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import pliki
from lokal import model, geometria
from zamierzenie import model as zmodel


def spojnosc(M):
    bledy, ident = [], model.projekt(M)["id"]   # id - przedrostek nazw plikow wynikowych (sciezka_wyniku)
    if not pliki.poprawne_id(ident):
        bledy.append("meta.projekt.id %s: dozwolone litery A-Z i a-z, cyfry, _ . - (bez spacji, nie samo ..) - to przedrostek "
                     "nazw plikow wynikowych" % json.dumps(ident, ensure_ascii=False))
    try:
        idx = model.indeks_id(M)
    except ValueError as e:
        return bledy + [str(e)]
    pomieszczenia = [p["nr"] for p in M["pomieszczenia"]]
    nr_pom = set(pomieszczenia)
    if len(nr_pom) != len(pomieszczenia):
        bledy.append("powtorzony numer pomieszczenia")
    sciany = {s["id"] for s in M["sciany"]}
    zrodla = {z["id"] for z in M.get("meta", {}).get("zrodla", [])}
    tokeny = model.tokeny(M)

    def pom(opis, nr):
        if nr not in nr_pom:
            bledy.append("%s: nieznane pomieszczenie %s" % (opis, nr))

    def token(opis, t):
        if t and not (t.startswith("#") and len(t) == 7) and t not in tokeny:
            bledy.append("%s: nieznany token %s" % (opis, t))

    def zrodlo(opis, r):
        if r.get("zrodlo") and r["zrodlo"] not in zrodla:
            bledy.append("%s: nieznane zrodlo %s" % (opis, r["zrodlo"]))

    for s in M["sciany"]:
        zrodlo("sciana " + s["id"], s)
    for p in M["pomieszczenia"]:
        if "stamp" not in p:
            bledy.append("pomieszczenie %s: brak stamp" % p["nr"])
        if p.get("wydzielone_z"):
            pom("pomieszczenie %s wydzielone_z" % p["nr"], p["wydzielone_z"])
        token("pomieszczenie %s sciany_kolor" % p["nr"], p.get("sciany_kolor"))
    for o in M.get("otwory", []):
        if o["sciana"] not in sciany:
            bledy.append("otwor %s: nieznana sciana %s" % (o["id"], o["sciana"]))
        if o.get("do"):
            pom("otwor " + o["id"], o["do"])
        zrodlo("otwor " + o["id"], o)
    for g in M.get("grzejniki", []):
        pom("grzejnik " + g["id"], g["pomieszczenie"])
    for nr, ar in M.get("aranzacja", {}).items():
        pom("aranzacja", nr)
        for e in ar.get("elementy", []):
            token("element " + e["id"], e.get("kolor"))
            zrodlo("element " + e["id"], e)
            if e.get("front") and e["front"] not in ("N", "E", "S", "W"):
                bledy.append("element %s: front spoza N/E/S/W: %s" % (e["id"], e["front"]))
    for e in M.get("elektryka", []):
        pom("punkt " + e["id"], e.get("pomieszczenie"))
        if e.get("typ") not in model.TYPY_E:
            bledy.append("punkt %s: typ spoza slownika: %s" % (e["id"], e.get("typ")))
        if not e.get("xy"):
            bledy.append("punkt %s: brak xy" % e["id"])
    wk = M.get("wod_kan") or {}
    for p in wk.get("punkty", []):
        pom("punkt " + p["id"], p.get("pomieszczenie"))
        if p.get("medium") not in model.MEDIA:
            bledy.append("punkt %s: medium spoza slownika: %s" % (p["id"], p.get("medium")))
        if not p.get("xy") and not p.get("linia"):
            bledy.append("punkt %s: brak xy i linia" % p["id"])
    kl = M.get("klimatyzacja") or {}
    for j in kl.get("jednostki", []):
        pom("jednostka " + j["id"], j.get("pomieszczenie"))
    for t in wk.get("trasy", []) + kl.get("trasy", []):
        if t.get("od") and t["od"] not in idx:
            bledy.append("trasa %s: nieznany poczatek %s" % (t["id"], t["od"]))
    for p in kl.get("przekucia", []):
        if p.get("sciana") and p["sciana"] not in sciany:
            bledy.append("przekucie %s: nieznana sciana %s" % (p["id"], p["sciana"]))
    for s in (M.get("sufity") or {}).get("strefy", []):
        pom("strefa sufitu", s.get("pomieszczenie"))
    szachty = {s["id"] for s in M.get("szachty", [])}
    for k in M.get("klady", []):
        pom("klad " + k["id"], k.get("pomieszczenie"))
        if k.get("sciana") not in sciany | szachty:
            bledy.append("klad %s: nieznana sciana ani szacht %s" % (k["id"], k.get("sciana")))
    wy = M.get("wykonczenie") or {}
    for o in wy.get("okladziny", []):
        pom("okladzina " + o["id"], o.get("pomieszczenie"))
        token("okladzina " + o["id"], o.get("token"))
    for w in wy.get("warianty", []):
        for c in w.get("cel", []):
            if "element" in c and not idx.get(c["element"], ("",))[0].startswith("aranzacja"):
                bledy.append("wariant %s: nieznany element %s" % (w["id"], c["element"]))
            if "okladzina" in c and c["okladzina"] not in idx:
                bledy.append("wariant %s: nieznana okladzina %s" % (w["id"], c["okladzina"]))
            if "pomieszczenie" in c:
                pom("wariant " + w["id"], c["pomieszczenie"])
        for op in w.get("opcje", []):
            token("wariant %s opcja %s" % (w["id"], op.get("nazwa")), op.get("token"))
        if not 0 <= int(w.get("domyslna", 0)) < len(w.get("opcje", [])):
            bledy.append("wariant %s: domyslna poza lista opcji" % w["id"])
    return bledy


def porownaj_pola(M, tolerancja):
    """Wiersze tabeli i liczba bledow pola."""
    pola = geometria.pola(M)
    definicje = {p["nr"]: p for p in M["pomieszczenia"]}
    dzieci = {}
    for p in M["pomieszczenia"]:
        if p.get("wydzielone_z"):
            dzieci.setdefault(p["wydzielone_z"], []).append(p["nr"])
    wiersze, bledy = [], 0
    for nr, p in definicje.items():
        a = pola[nr]
        if a is None:
            wiersze.append((nr, p["nazwa"], None, p.get("pow_m2"), None, "BRAK WIELOKATA — sprawdz stamp i domkniecia"))
            bledy += 1
            continue
        if p.get("wydzielone_z"):
            wiersze.append((nr, p["nazwa"], a, None, None, "czesc " + p["wydzielone_z"]))
            continue
        razem = a + sum(pola[d] or 0 for d in dzieci.get(nr, []))
        doc = p.get("pow_m2")
        if doc is None:
            wiersze.append((nr, p["nazwa"], razem, None, None, "brak pola w dokumentacji"))
            continue
        d = razem - doc
        if p.get("zmiana"):
            uwaga = "zmiana zamierzona: " + p["zmiana"]
        elif abs(d) <= max(tolerancja * doc, 0.02):
            uwaga = ""
        else:
            uwaga = "POZA TOLERANCJA"
            bledy += 1
        wiersze.append((nr, p["nazwa"], razem, doc, d, uwaga))
    return wiersze, bledy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--tolerancja", type=float, default=0.005, help="wzgledna tolerancja pola (0.005 = 0,5%%)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj zamierzenie/waliduj.py; "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        return 2
    bledy = spojnosc(M)
    print("SPOJNOSC:", "OK" if not bledy else "%d bledow" % len(bledy))
    for b in bledy:
        print("  -", b)
    if bledy:
        print("\nPola pominiete: geometria wymaga spojnych odwolan. Popraw bledy i uruchom ponownie.")
        return 1
    wiersze, zle = porownaj_pola(M, a.tolerancja)
    print("\n%-5s %-28s %8s %8s %8s" % ("nr", "nazwa", "model", "dokum.", "roznica"))
    suma = 0.0
    for nr, nazwa, m2, doc, d, uwaga in wiersze:
        f = lambda v, z="%8.2f": (z % v) if v is not None else "%8s" % "—"
        print("%-5s %-28s %s %s %s  %s" % (nr, nazwa[:28], f(m2), f(doc), f(d, "%+8.2f"), uwaga))
        zewn = model.pomieszczenie(M, nr).get("zewnetrzne")
        if m2 is not None and not zewn and not model.pomieszczenie(M, nr).get("wydzielone_z"):
            suma += m2
    print("%-5s %-28s %8.2f" % ("", "SUMA (bez zewnetrznych)", suma))
    print("\nWYNIK:", "OK" if not zle else "%d problemow" % zle)
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
