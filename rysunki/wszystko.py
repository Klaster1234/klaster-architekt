"""Przegenerowanie wszystkich wynikow z modelu (lokalu albo zamierzenia) jednym poleceniem.

    python rysunki/wszystko.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/wszystko.py przyklad/mieszkanie/model/lokal_projekt.json --istniejacy przyklad/mieszkanie/model/lokal_istniejacy.json
    python rysunki/wszystko.py przyklad/ogrod/model/projekt.json --istniejacy przyklad/ogrod/model/istniejacy.json
    python rysunki/wszystko.py przyklad/ogrod/model/istniejacy.json --etap rozpoznanie
    python rysunki/wszystko.py przyklad/ogrod/model/koncepcja_A.json przyklad/ogrod/model/koncepcja_B.json --etap koncepcja

Model lokalu (modul wnetrz): jak dotad - walidacja modelu (lokal/waliduj.py), kontrola punktow
(lokal/punkty.py), rzut A-01, karty pomieszczen z aranzacja, izometria, klady scian z zestawieniem
K-00, plan wyburzen A-02 (tylko z --istniejacy), DXF i makieta GLB. Etapy dotycza modelu
zamierzenia: na modelu lokalu --etap inny niz "projekt" (domyslny) nic nie zmienia w liscie krokow,
tylko dopisuje uwage w konsoli. Bez --etap wynik dla modelu lokalu jest identyczny jak zawsze.

Model zamierzenia (zamierzenie/SCHEMAT.md), wedlug --etap:
- rozpoznanie: walidacja, plansza rozpoznania R-01, plan roboczy P-01, cienie P-03;
- koncepcja (kazdy podany plik MODEL osobno): walidacja, P-01, przekroje (kazdy z sekcji
  przekroje modelu), bilans Z-02, makieta GLB, dane planera 3D;
- projekt (domyslny): jak koncepcja, plus roznica P-02 (tylko z --istniejacy), cienie P-03,
  zestawienie Z-01, DXF, a dla kazdego modulu wnetrz (sekcja moduly) komplet krokow modelu lokalu
  na jego pliku - stanem istniejacym modulu jest modul o tym samym id w modelu --istniejacy, jesli
  taki tam jest (arkusze modulu maja przedrostek id lokalu, wiec nazwy plikow wynikowych sie nie
  zderzaja z arkuszami zamierzenia).
Arkusz bez tresci nie powstaje: R-01, P-03 i Z-02 tylko przy modelu z miejsce.dzialki albo punktami
miejsce.teren, Z-01 tylko przy modelu z obiektami, P-02 - gdy obiekty ma ktorykolwiek z dwoch stanow
(np. mieszkanie jako model zamierzenia ma tylko modul wnetrz). Taki krok jest w tabeli z kodem 0
i adnotacja "pominiety - brak danych (...)", bez uruchamiania skryptu. Moduly bez pliku pomija
zamierzenie/moduly.py (uwaga w konsoli), a blad zglasza krok walidacji.

Kazdy krok to osobny proces tego samego Pythona (sys.executable), uruchamiany z katalogu
repozytorium; --wyjscie trafia do wszystkich rysunkow. Podanie kilku plikow MODEL (etap koncepcja)
daje wspolna tabele krokow; kroki kazdego modelu maja wtedy przedrostek "<id projektu>: ". Na
koncu tabela: krok, skrypt, kod wyjscia, czas. Brakujacy skrypt jest pomijany z adnotacja. Kod
wyjscia 1, gdy ktorykolwiek krok sie nie powiodl (bilans konczy sie zawsze kodem 0). Gdy walidacja
modelu zamierzenia (zamierzenie/waliduj.py) sie nie powiedzie, pozostale kroki tego modelu nie sa
uruchamiane (w tabeli "pominiety - walidacja nie przeszla", kod wyjscia 1) - arkusze nie powstaja
z blednych danych; przy kilku plikach MODEL pozostale modele ida dalej. Model lokalu jak dotad.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN))
from lokal import model
from zamierzenie import model as zmodel
from zamierzenie import moduly as zmoduly

ETAPY = ("rozpoznanie", "koncepcja", "projekt")
WALIDACJA_ZAMIERZENIA = "zamierzenie/waliduj.py"
PO_WALIDACJI = "pominiety - walidacja nie przeszla"


def kroki_lokalu(sciezka, istniejacy, wyjscie):
    """Lista (nazwa, skrypt wzgledem repozytorium, argumenty) dla modelu lokalu - jak dotad."""
    M = model.wczytaj(sciezka)
    m = str(sciezka)
    w = ["--wyjscie", str(wyjscie)] if wyjscie else []
    lista = [("walidacja modelu", "lokal/waliduj.py", [m]),
             ("kontrola punktow", "lokal/punkty.py", [m]),
             ("rzut A-01", "rysunki/rzut.py", [m] + w)]
    aranzacja = M.get("aranzacja", {})
    for p in M.get("pomieszczenia", []):
        if (aranzacja.get(p["nr"]) or {}).get("elementy"):
            lista.append(("karta %s" % p["nr"], "rysunki/karta_pomieszczenia.py", [m, p["nr"]] + w))
    lista += [("izometria", "rysunki/izometria.py", [m] + w),
              ("klady + zestawienie K-00", "rysunki/klady.py", [m, "--zestawienie"] + w)]
    if istniejacy:
        lista.append(("wyburzenia A-02", "rysunki/wyburzenia.py", [str(istniejacy), m] + w))
    lista += [("DXF", "rysunki/dxf.py", [m] + w),
              ("makieta GLB", "rysunki/glb.py", [m] + w)]
    return lista


def kroki_modulu(sciezka_zam, mod, M_ist, istniejacy_zam, wyjscie):
    """(lista krokow, uwaga albo None) dla modulu mod: kroki_lokalu na jego pliku, nazwy z
    przedrostkiem "modul <id>: "; plik modulu jest wzgledem katalogu pliku modelu zamierzenia
    (zamierzenie/moduly.py). Moduly bez pliku odsiewa juz zamierzenie/moduly.py: moduly() (uwaga
    na stderr, blad zglasza krok walidacji); sprawdzenia pliku nizej to tylko zabezpieczenie (krok
    bledu "modul <id>: brak pliku <sciezka>" albo uwaga o pominietych wyburzeniach A-02). Brak w
    modelu --istniejacy (M_ist, wczytany raz w kroki_zamierzenia) modulu o tym samym id to nie blad
    modulu projektu: pomija tylko wyburzenia A-02."""
    plik = (Path(sciezka_zam).parent / str(mod.get("plik") or "")).resolve()
    if not mod.get("plik") or not plik.is_file():
        return [("modul %s: brak pliku %s" % (mod.get("id"), krotko(str(plik))), None, None)], None
    plik_ist, uwaga = None, None
    if M_ist is not None:
        for m2 in zmoduly.moduly(M_ist):
            if m2.get("id") == mod.get("id"):
                kandydat = (Path(istniejacy_zam).parent / str(m2.get("plik") or "")).resolve()
                if m2.get("plik") and kandydat.is_file():
                    plik_ist = kandydat
                else:
                    uwaga = ("modul %s: brak pliku stanu istniejacego %s - pomijam wyburzenia A-02"
                             % (mod.get("id"), krotko(str(kandydat))))
                break
    kroki = kroki_lokalu(plik, plik_ist, wyjscie)
    return [("modul %s: %s" % (mod["id"], nazwa), skrypt, argumenty) for nazwa, skrypt, argumenty in kroki], uwaga


def ma_miejsce(M):
    """Czy model ma dzialke albo punkty terenu - tresc R-01, P-03 i Z-02."""
    miejsce = M.get("miejsce") or {}
    return bool(miejsce.get("dzialki") or (miejsce.get("teren") or {}).get("punkty"))


def krok(nazwa, skrypt, argumenty, jest, brak):
    """Krok albo krok pominiety (argumenty = tekst adnotacji: bez uruchamiania skryptu, kod 0), gdy jest == False."""
    return (nazwa, skrypt, argumenty if jest else "pominiety - brak danych (%s)" % brak)


def kroki_zamierzenia(sciezka, istniejacy, wyjscie, etap):
    """(lista krokow, lista uwag) dla modelu zamierzenia wedlug etapu (rozpoznanie | koncepcja |
    projekt); uwagi - komunikaty modulow do wypisania w konsoli (brak pliku modulu w
    --istniejacy, patrz kroki_modulu). Arkusze bez tresci sa krokami pominietymi (krok())."""
    M = model.wczytaj(sciezka)
    m = str(sciezka)
    w = ["--wyjscie", str(wyjscie)] if wyjscie else []
    lista, uwagi = [("walidacja modelu", "zamierzenie/waliduj.py", [m])], []
    miejsce, bez_miejsca = ma_miejsce(M), "model bez dzialki i punktow terenu"
    M_ist = model.wczytaj(istniejacy) if etap == "projekt" and istniejacy else None   # raz: P-02 i moduly
    if etap == "rozpoznanie":
        lista += [krok("rozpoznanie R-01", "rysunki/rozpoznanie.py", [m] + w, miejsce, bez_miejsca),
                  ("plan P-01", "rysunki/plan.py", [m] + w),
                  krok("cienie P-03", "rysunki/cienie.py", [m] + w, miejsce, bez_miejsca)]
        return lista, uwagi
    lista.append(("plan P-01", "rysunki/plan.py", [m] + w))
    if etap == "projekt" and istniejacy:
        obiekty = bool(M.get("obiekty") or M_ist.get("obiekty"))
        lista.append(krok("roznica P-02", "rysunki/roznica.py", [str(istniejacy), m] + w, obiekty, "oba stany bez obiektow"))
    if etap == "projekt":
        lista.append(krok("cienie P-03", "rysunki/cienie.py", [m] + w, miejsce, bez_miejsca))
    for p in M.get("przekroje") or []:
        lista.append(("przekroj %s" % p["id"], "rysunki/przekroj.py", [m, "--przekroj", str(p["id"])] + w))
    if etap == "projekt":
        i = ["--istniejacy", str(istniejacy)] if istniejacy else []
        lista.append(krok("zestawienie Z-01", "rysunki/zestawienie.py", [m] + i + w, bool(M.get("obiekty")), "model bez obiektow"))
    lista.append(krok("bilans Z-02", "rysunki/bilans.py", [m] + w, miejsce, bez_miejsca))
    if etap == "projekt":
        lista.append(("DXF", "rysunki/dxf.py", [m] + w))
    lista.append(("makieta GLB", "rysunki/glb.py", [m] + w))
    lista.append(("dane planera", "planer3d/eksport_web.py", [m] + w))
    if etap == "projekt":
        for mod in zmoduly.moduly(M):
            kroki_mod, uwaga = kroki_modulu(sciezka, mod, M_ist, istniejacy, wyjscie)
            lista += kroki_mod
            if uwaga:
                uwagi.append(uwaga)
    return lista, uwagi


def kroki_modelu(sciezka, istniejacy, wyjscie, etap):
    """(rodzaj, id projektu, lista krokow, lista uwag) dla jednego pliku MODEL. rodzaj None (lista
    pusta), gdy plik nie jest ani modelem lokalu, ani modelem zamierzenia. uwagi - komunikaty do
    wypisania w konsoli: model lokalu z --etap innym niz "projekt", albo (model zamierzenia) moduly
    bez pliku stanu istniejacego (kroki_zamierzenia)."""
    M = model.wczytaj(sciezka)
    rodzaj = zmodel.rodzaj_pliku(M)
    projekt_id = model.projekt(M)["id"]
    if rodzaj == "lokal":
        uwagi = []
        if etap != "projekt":
            uwagi.append("model lokalu nie zna etapow (dotycza modelu zamierzenia) - ignoruje --etap %s, generuje komplet jak zawsze" % etap)
        return rodzaj, projekt_id, kroki_lokalu(sciezka, istniejacy, wyjscie), uwagi
    if rodzaj == "zamierzenie":
        lista, uwagi = kroki_zamierzenia(sciezka, istniejacy, wyjscie, etap)
        return rodzaj, projekt_id, lista, uwagi
    return None, projekt_id, [], []


def krotko(arg):
    """Sciezka wzgledem biezacego katalogu (do wypisania), gdy to mozliwe."""
    if not os.path.isabs(arg):
        return arg
    try:
        return os.path.relpath(arg)
    except ValueError:      # Windows: inny dysk
        return arg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="+", help="model lokalu albo zamierzenia (jeden albo wiecej)")
    ap.add_argument("--etap", choices=ETAPY, default="projekt",
                    help="etap modelu zamierzenia: rozpoznanie | koncepcja | projekt (domyslny); model lokalu go ignoruje")
    ap.add_argument("--istniejacy", help="model stanu istniejacego (lokalu albo zamierzenia)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <folder projektu>/wyjscie)")
    a = ap.parse_args()
    # sciezki uzytkownika wzgledem jego katalogu, bo kroki startuja z katalogu repozytorium
    sciezki = [Path(x).resolve() for x in a.model]
    istniejacy = Path(a.istniejacy).resolve() if a.istniejacy else None
    wyjscie = Path(a.wyjscie).resolve() if a.wyjscie else None
    for p in sciezki + ([istniejacy] if istniejacy else []):
        if not p.is_file():
            raise SystemExit("brak pliku modelu: %s" % p)
    wiele = len(sciezki) > 1
    lista = []    # (numer modelu, rodzaj modelu, krok, skrypt, argumenty)
    for n, sciezka in enumerate(sciezki):
        rodzaj, projekt_id, kroki_pliku, uwagi = kroki_modelu(sciezka, istniejacy, wyjscie, a.etap)
        if rodzaj is None:
            print("nie rozpoznano modelu %s: potrzebne sciany (lokal) albo meta.rodzaj i obiekty/moduly/miejsce "
                  "(zamierzenie/SCHEMAT.md)" % krotko(str(sciezka)))
            return 2
        for uwaga in uwagi:
            print("UWAGA (%s): %s" % (krotko(str(sciezka)), uwaga))
        if wiele:
            kroki_pliku = [("%s: %s" % (projekt_id, nazwa), skrypt, argumenty) for nazwa, skrypt, argumenty in kroki_pliku]
        lista += [(n, rodzaj, nazwa, skrypt, argumenty) for nazwa, skrypt, argumenty in kroki_pliku]
    wyniki = []    # (krok, skrypt, kod, czas, adnotacja)
    niezwalidowane = set()   # numery modeli zamierzenia, ktorych walidacja sie nie powiodla
    for i, (n, rodzaj, nazwa, skrypt, argumenty) in enumerate(lista, 1):
        if n in niezwalidowane:    # model zamierzenia z bledami walidacji: bez arkuszy z blednych danych
            print("\n=== [%d/%d] %s: %s - %s" % (i, len(lista), nazwa, skrypt or "-", PO_WALIDACJI), flush=True)
            wyniki.append((nazwa, skrypt or "-", None, None, PO_WALIDACJI))
            continue
        if skrypt is None:    # krok bledu zbudowany juz przy liczeniu listy (np. brak pliku modulu) - bez procesu
            print("\n=== [%d/%d] %s" % (i, len(lista), nazwa), flush=True)
            wyniki.append((nazwa, "-", 1, 0.0, ""))
            continue
        if isinstance(argumenty, str):    # krok pominiety (brak danych w modelu) - bez procesu, kod 0
            print("\n=== [%d/%d] %s: %s - %s" % (i, len(lista), nazwa, skrypt, argumenty), flush=True)
            wyniki.append((nazwa, skrypt, 0, None, argumenty))
            continue
        plik = KORZEN / skrypt
        print("\n=== [%d/%d] %s: %s %s" % (i, len(lista), nazwa, skrypt, " ".join(krotko(x) for x in argumenty)),
              flush=True)
        if not plik.is_file():
            print("pominiety: brak pliku %s" % skrypt)
            wyniki.append((nazwa, skrypt, None, 0.0, ""))
            continue
        t0 = time.perf_counter()
        kod = subprocess.run([sys.executable, str(plik)] + argumenty, cwd=str(KORZEN)).returncode
        wyniki.append((nazwa, skrypt, kod, time.perf_counter() - t0, ""))
        if kod and rodzaj == "zamierzenie" and skrypt == WALIDACJA_ZAMIERZENIA:
            niezwalidowane.add(n)
            print("walidacja modelu nie przeszla - pozostale kroki tego modelu pominiete (popraw model i uruchom ponownie)", flush=True)
    print("\n%-26s %-34s %6s %9s" % ("KROK", "SKRYPT", "KOD", "CZAS [s]"))
    for nazwa, skrypt, kod, czas, adnotacja in wyniki:
        if adnotacja:
            print("%-26s %-34s %6s %9s  %s" % (nazwa, skrypt, "-" if kod is None else kod, "-", adnotacja))
        elif kod is None:
            print("%-26s %-34s %6s %9s  pominiety: brak pliku" % (nazwa, skrypt, "-", "-"))
        else:
            print("%-26s %-34s %6d %9.1f%s" % (nazwa, skrypt, kod, czas, "  BLAD" if kod else ""))
    bledy = [n for n, _, kod, _, _ in wyniki if kod]
    if wyjscie:
        gdzie = str(wyjscie)
    else:
        gdzie = ", ".join(sorted({str(model.katalog_wyjscia(model.wczytaj(s), None)) for s in sciezki}))
    print("\nWYNIK: %s; wyniki w %s" % ("OK" if not bledy else "bledy w krokach: %d (%s)" % (len(bledy), ", ".join(bledy)), gdzie))
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
