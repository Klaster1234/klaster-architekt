"""Zbiera zalozenia i niepewne dane modelu do jednej rundy potwierdzen.

    python lokal/zalozenia.py przyklad/mieszkanie/model/lokal_projekt.json
    python lokal/zalozenia.py przyklad/mieszkanie/model/lokal_projekt.json --prog-dokladnosci 5 --wyjscie robocze/

Trzy grupy pozycji: (1) elementy aranzacji i grzejniki, ktorych wys_zrodlo
zaczyna sie od "ZALOZENIE"; (2) rzedna sufitu (meta.rzedna_sufitu), gdy jej
status zawiera "ZALOZENIE"; (3) sciany/otwory/elementy, ktorych dokladnosc_cm
przekracza prog albo ktorych zrodlo wskazuje na wpis w meta.zrodla z
wiazace:false. Wynik to <id>_zalozenia.md z kolumna "Odpowiedz" do
wypelnienia ("OK" albo nowa wartosc) — ten sam tekst trafia tez na konsole.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lokal import model
from zamierzenie import model as zmodel

# konwencja pol wys_zrodlo / rzedna_sufitu.status w modelu, patrz SCHEMAT.md
PREFIKS_ZALOZENIA = "ZAŁOŻENIE"


def _wysokosci(M):
    """(pomieszczenie, id, rodzaj, wys, wys_zrodlo) dla elementow/grzejnikow z ZALOZENIEM."""
    wiersze = []
    for e in model.elementy(M):
        z = e.get("wys_zrodlo") or ""
        if z.startswith(PREFIKS_ZALOZENIA):
            wiersze.append((e["_pom"], e["id"], e.get("rodzaj", ""), e.get("wys"), z))
    for g in M.get("grzejniki", []):
        z = g.get("wys_zrodlo") or ""
        if z.startswith(PREFIKS_ZALOZENIA):
            wiersze.append((g.get("pomieszczenie", ""), g["id"], "grzejnik (%s)" % g.get("typ", ""),
                            g.get("wys"), z))
    wiersze.sort()
    return wiersze


def _rzedna_sufitu(M):
    """[(wartosc, widelki, status)] — jeden wiersz, jesli status jest zalozeniem."""
    rs = (M.get("meta") or {}).get("rzedna_sufitu") or {}
    status = rs.get("status") or ""
    if PREFIKS_ZALOZENIA not in status:
        return []
    return [(rs.get("wartosc"), rs.get("widelki"), status)]


def _niepewny(rekord, zrodla, prog):
    """Czy rekord ma dokladnosc gorsza niz prog cm albo zrodlo niewiazace."""
    if (rekord.get("dokladnosc_cm") or 0) > prog:
        return True
    z = zrodla.get(rekord.get("zrodlo"))
    return bool(z and not z.get("wiazace", True))


def _niepewne_zrodla(M, prog):
    """(rodzaj, id, zrodlo, dokladnosc_cm, opis) dla scian/otworow/elementow niepewnych."""
    zrodla = {z["id"]: z for z in (M.get("meta") or {}).get("zrodla", [])}
    wiersze = []
    for rodzaj, lista in (("sciana", M.get("sciany", [])), ("otwor", M.get("otwory", []))):
        for r in lista:
            if _niepewny(r, zrodla, prog):
                wiersze.append((rodzaj, r["id"], r.get("zrodlo", ""), r.get("dokladnosc_cm", ""), r.get("opis", "")))
    for e in model.elementy(M):
        if _niepewny(e, zrodla, prog):
            wiersze.append(("element", e["id"], e.get("zrodlo", ""), e.get("dokladnosc_cm", ""), e.get("opis", "")))
    wiersze.sort()
    return wiersze


def raport(M, prog):
    """(tekst markdown, liczba pozycji lacznie)."""
    wys = _wysokosci(M)
    rs = _rzedna_sufitu(M)
    zrd = _niepewne_zrodla(M, prog)
    dzis = datetime.now().strftime("%d.%m.%Y")
    linie = [
        "# Zalozenia i niepewne dane — %s" % model.projekt(M)["id"],
        "",
        "Wygenerowano: %s · `python lokal/zalozenia.py` · pozycji: %d" % (dzis, len(wys) + len(rs) + len(zrd)),
        "Kolumna \"Odpowiedz\": wpisz \"OK\" (zalozenie sie potwierdza) albo nowa wartosc; "
        "potem wpisz do modelu i przestaw zrodlo/wys_zrodlo na potwierdzone.",
        "",
        "## Zalozenia wysokosci (%d)" % len(wys),
        "",
        "| Pom. | ID | Rodzaj | wys [cm] | Zalozenie | Odpowiedz |",
        "|---|---|---|---|---|---|",
    ]
    for pom, eid, rodzaj, w, z in wys:
        wtxt = "%s–%s" % (w[0], w[1]) if w else "?"
        linie.append("| %s | %s | %s | %s | %s | |" % (pom, eid, rodzaj, wtxt, z))
    linie += ["", "## Rzedna sufitu (%d)" % len(rs), "",
              "| Wartosc | Widelki | Status | Odpowiedz |", "|---|---|---|---|"]
    for wartosc, widelki, status in rs:
        wtxt = "%s–%s" % (widelki[0], widelki[1]) if widelki else "?"
        linie.append("| %s | %s | %s | |" % (wartosc, wtxt, status))
    linie += ["", "## Niepewne zrodla (%d)" % len(zrd), "",
              "| Rodzaj | ID | Zrodlo | Dokladnosc [cm] | Opis | Odpowiedz |", "|---|---|---|---|---|---|"]
    for rodzaj, eid, zrodlo, dokl, opis in zrd:
        linie.append("| %s | %s | %s | %s | %s | |" % (rodzaj, eid, zrodlo, dokl, opis))
    return "\n".join(linie) + "\n", len(wys) + len(rs) + len(zrd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--prog-dokladnosci", type=float, default=2.0, help="prog dokladnosci w cm (domyslnie 2)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj tego skryptu na pliku lokalu (modul wnetrz z sekcji moduly)."
              % Path(a.model).name)
        return 2
    tekst, n = raport(M, a.prog_dokladnosci)
    baza = model.sciezka_wyniku(M, "zalozenia", a.wyjscie)
    sciezka = baza.with_name(baza.name + ".md")
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(tekst)
    print("zapisano %s (%d pozycji)\n" % (sciezka, n))
    print(tekst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
