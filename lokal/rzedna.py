"""Synchronizuje gorna krawedz zabudowy "do sufitu" z rzedna sufitu (RS).

    python lokal/rzedna.py przyklad/mieszkanie/model/lokal_projekt.json
    python lokal/rzedna.py kopia.json --zapisz

Dla elementow aranzacji z do_sufitu=true, ktorych wys[1] rozni sie od
biezacej rzednej sufitu (meta.rzedna_sufitu), wypisuje liste zmian. Bez
--zapisz to tylko przeglad "na sucho"; z --zapisz zapisuje model przez
model.zapisz (kopia .bak obok pliku) z uaktualnionymi wysokosciami. Kod
wyjscia w trybie na sucho: 1, gdy sa zmiany do wprowadzenia.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lokal import model
from zamierzenie import model as zmodel


def zmiany(M):
    """(pomieszczenie, id, rodzaj, stara_wartosc, nowa_wartosc) dla elementow niezgodnych z RS."""
    rs = model.rzedna_sufitu(M)
    wynik = []
    for e in model.elementy(M):
        if not e.get("do_sufitu"):
            continue
        w = e.get("wys")
        if w and w[1] != rs:
            wynik.append((e["_pom"], e["id"], e.get("rodzaj", ""), w[1], rs))
    return wynik


def zastosuj(M, zm, rs):
    """Ustawia wys[1] = rs na oryginalnej strukturze M (nie na kopiach z model.elementy)."""
    rs = int(rs) if float(rs) == int(rs) else rs  # 258, nie 258.0, gdy RS jest liczba calkowita
    do_zmiany = {(pom, eid) for pom, eid, _, _, _ in zm}
    for nr, ar in M.get("aranzacja", {}).items():
        for e in ar.get("elementy", []):
            if (nr, e["id"]) in do_zmiany and e.get("do_sufitu"):
                e["wys"][1] = rs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--zapisz", action="store_true", help="zapisuje model (kopia .bak); bez tego tylko przeglad")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj tego skryptu na pliku lokalu (modul wnetrz z sekcji moduly)."
              % Path(a.model).name)
        return 2
    rs = model.rzedna_sufitu(M)
    zm = zmiany(M)
    print("RZEDNA SUFITU: %s cm" % rs)
    if not zm:
        print("brak zmian - wszystkie elementy do_sufitu maja juz wys[1] == RS")
        return 0
    print("ZMIANY (%d):" % len(zm))
    for pom, eid, rodzaj, stara, nowa in zm:
        print("  %s %s (%s): gora %s -> %s" % (pom, eid, rodzaj, stara, nowa))
    if not a.zapisz:
        print("\n(przeglad na sucho, uzyj --zapisz aby zapisac)")
        return 1
    zastosuj(M, zm, rs)
    sciezka = model.zapisz(M)
    print("\nzapisano %s (kopia %s.bak)" % (sciezka, sciezka.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
