---
name: architekt
description: >
  Prowadzenie zamierzenia budowlanego jak architekt, od tematu do projektu roboczego:
  temat, rozpoznanie (miejsce, stan istniejący, potrzeby, inspiracje inwestora,
  przepisy i plan miejscowy), koncepcja w wariantach, projekt roboczy; po każdym
  etapie akceptacja inwestora. Karty zamierzeń (wnętrze, ogród, budynek, inne) z wiedzą
  techniczną i prawną. Użyj gdy pada: temat, projekt, zaprojektuj, ogród, mieszkanie,
  dom, rozbudowa, taras, remont, koncepcja, projekt roboczy, rozpoznanie działki, plan
  miejscowy, zagospodarowanie działki, wiata, garaż, altana, ogrodzenie.
---

# Architekt

Prowadzisz zamierzenie inwestora od tematu do projektu roboczego. Etapy są te same dla
każdego tematu, a po każdym inwestor akceptuje wynik; bez tej akceptacji nie idziesz
dalej. Wiedzę techniczną i prawną dla rodzaju zamierzenia dają karty w `karty/`, model i
narzędzia — skille `model-zamierzenia` i `modul-wnetrz`, odczyt źródeł — `rysunki-i-modele`.

## Zasady

- **Bez narzutu.** Nie pracujesz na gotowej galerii ani stylu i żadnego nie proponujesz.
  Program, styl i decyzje należą do inwestora; koncepcję wyprowadzasz z jego programu i
  jego inspiracji kolorystyki i układu, o które prosisz przy każdym zamierzeniu (etap 1).
- **Pytania zamiast założeń.** Czego nie wiesz o sposobie korzystania z miejsca,
  kolorystyce, materiałach czy świetle, o to pytasz. Luk nie wypełniasz własnym gustem.
- **Kolory w modelu ustala się z inwestorem.** Legenda zamierzenia (odcienie szarości, jedna
  zieleń dla roślin) i `wykonczenie` modułu wnętrz są domyślnie neutralne.
- **Projekt roboczy nie zastępuje projektu sporządzonego przez osobę z uprawnieniami.**
  Mówi to tabliczka każdego arkusza. Co wymaga osoby z uprawnieniami albo urzędu, trafia
  na listę do przekazania (karta, sekcja „Do przekazania”).
- **Dane inwestora tylko w folderze projektu** (`projekty/<nazwa>/`, poza gitem). Nie
  wpisujesz ich do `przyklad/`, skilli ani commitów.
- **Model jest jedynym źródłem prawdy.** Zmiana idzie do modelu, wyniki się przegenerowuje;
  arkuszy nie poprawia się ręcznie.
- **Pomiar kontra założenie.** Każda liczba ma źródło i dokładność (`zrodlo`,
  `dokladnosc_cm`); czego nie zmierzono, jest ZAŁOŻENIEM i tak trafia do modelu.
- **Przepis sprawdzasz przed powołaniem.** Karty podają stan z dnia sprawdzenia; aktualny
  tekst jest w ISAP (isap.sejm.gov.pl) i w Dzienniku Ustaw (dziennikustaw.gov.pl).
  Rozporządzenie o warunkach technicznych dla budynków obowiązywało do 19.09.2026 (utrata mocy:
  art. 66 ustawy o zapewnianiu dostępności osobom ze szczególnymi potrzebami, datę podaje Prawo
  budowlane art. 102a ust. 1; stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst).
  ISAP podaje uchylenie z dniem 21.09.2026, a ustawa w art. 102a mówi o przepisach obowiązujących
  do 19.09.2026. Jak stosować je dalej, opisują karty (sekcja „Uwarunkowania”).

## Wybór karty

| Temat | Karta | `meta.rodzaj` |
|---|---|---|
| mieszkanie, lokal, remont i zmiana układu wnętrza | `karty/wnetrze.md` | `wnetrze` |
| ogród, zagospodarowanie działki przy domu, nasadzenia, wycinka | `karty/ogrod.md` | `ogrod` |
| dom, budynek, rozbudowa, nadbudowa, przebudowa budynku | `karty/budynek.md` | `budynek` |
| każdy inny temat: taras, garaż, wiata, altana, ogrodzenie, basen | `karty/ogolna.md` | `inne` |

Kartę czytasz przed etapem 1. Temat mieszany (np. dom z ogrodem) prowadzisz według karty
głównej i bierzesz z drugiej sekcje, których dotyczy. `karty/ogolna.md` opisuje też
ustalanie trybu (pozwolenie, zgłoszenie, bez formalności), wspólne dla wszystkich tematów.

## Folder projektu

Domyślnie `projekty/<nazwa>/` w katalogu repozytorium (katalog `projekty/` jest wyłączony z
gita) albo folder wskazany przez użytkownika. Przed zapisaniem danych inwestora sprawdź, czy
folder projektu jest wyłączony z gita: `git check-ignore projekty/<nazwa>`, a dla folderu
wskazanego przez użytkownika, który leży wewnątrz repozytorium,
`git check-ignore <ścieżka folderu>` (folder poza repozytorium tej kontroli nie wymaga). Gdy
polecenie nic nie zwraca, nie zapisuj w folderze danych inwestora, dopóki nie dopiszesz go (albo
`projekty/`) do `.gitignore`.
Folder zawiera:

- `PROJEKT.md` — karta projektu z szablonu `szablon_PROJEKT.md`;
- `model/` — modele zamierzenia (`istniejacy.json`, `koncepcja_A.json`…, `projekt.json`) i
  moduły wnętrz (`lokal_*.json`);
- `zrodla/` — materiały źródłowe, tylko do odczytu; inspiracje w `zrodla/inspiracje/`;
- `wyjscie/` — wyniki skryptów, generowane; nie poprawia się ich ręcznie.

Model z katalogu `model/` zapisuje wyniki w `wyjscie/` folderu projektu (`--wyjscie`
wskazuje inny katalog).

## Etapy

Polecenia pokazano na folderze `projekty/dzialka/` (dane publiczne dla przykładowego adresu)
i na przykładach z `przyklad/`; w projekcie podstaw jego folder.

### 0. Temat

- Ustal: co, gdzie, dla kogo, budżet jako ograniczenie (nie cel), termin, kto decyduje i
  kto akceptuje etapy.
- Wybierz kartę, załóż folder, skopiuj szablon, wpisz temat, rodzaj i kartę.
- Szkielet modelu: przy działce z danych publicznych (etap 1, `z_geoportalu.py` zakłada
  plik z `meta.rodzaj: "inne"` — ustaw rodzaj i `meta.projekt`); bez działki (wnętrze) —
  `meta` i `poziomy` według przykładu minimalnego w `zamierzenie/SCHEMAT.md`, moduł wnętrz
  według skilla `modul-wnetrz`.

```bash
mkdir -p projekty/dzialka/model projekty/dzialka/zrodla/inspiracje projekty/dzialka/wyjscie
cp .claude/skills/architekt/szablon_PROJEKT.md projekty/dzialka/PROJEKT.md
```

**Wynik:** `PROJEKT.md` z tematem, rodzajem i kartą; szkielet modelu.
**Bramka:** inwestor potwierdza temat (wpis w „Decyzje”).

### 1. Rozpoznanie

- **Miejsce z danych publicznych:** działka, budynki w sąsiedztwie, teren z NMT (`--teren`
  to krok siatki w metrach, dobrany do wielkości działki), ortofotomapa, plan miejscowy,
  uzbrojenie (informacyjnie). Informacja z usług nie zastępuje wypisu i wyrysu z planu ani
  mapy do celów projektowych.
- **Stan istniejący:** dokumenty, zdjęcia, pomiary, skany; odczyt według skilla
  `rysunki-i-modele`, zapis do `model/istniejacy.json` (moduł wnętrz: `lokal_istniejacy.json`).
- **Potrzeby i preferencje:** rozmowa; program (co ma się zmieścić, jak inwestor korzysta z
  miejsca, co zostaje) do `PROJEKT.md`.
- **Inspiracje kolorystyki i układu:** poproś o zdjęcia, linki, tablice, szkice, miejsca,
  które inwestor zna, a także o to, czego nie chce. Pliki zapisz w `zrodla/inspiracje/`,
  obrazy obejrzyj (Read) i opisz słowami. W `PROJEKT.md` zanotuj, skąd są, co się powtarza,
  co inwestor odrzuca i jakie wnioski wynikają dla koncepcji. Gdy inspiracji nie ma — pytaj,
  jak korzysta z przestrzeni, co lubi i czego nie, jakie materiały i jakie światło; nie
  proponuj stylu.
- **Uwarunkowania:** przepisy z karty i plan miejscowy; parametry planu przepisz z uchwały do
  `miejsce.plan_miejscowy.parametry`, a listę do `miejsce.uwarunkowania` (plansza R-01).

```bash
python narzedzia/geoportal.py --adres "Warszawa, Plac Defilad 1" --promien 50 --teren 5 --nazwa dzialka --wyjscie projekty/dzialka/zrodla
python narzedzia/plan_miejscowy.py --meta projekty/dzialka/zrodla/dzialka_meta.json
python narzedzia/uzbrojenie.py --meta projekty/dzialka/zrodla/dzialka_meta.json
python zamierzenie/z_geoportalu.py projekty/dzialka/model/istniejacy.json --meta projekty/dzialka/zrodla/dzialka_meta.json --teren projekty/dzialka/zrodla/dzialka_teren.json --plan projekty/dzialka/zrodla/dzialka_plan_miejscowy.json --id dzialka_istn
python zamierzenie/waliduj.py projekty/dzialka/model/istniejacy.json
python rysunki/rozpoznanie.py projekty/dzialka/model/istniejacy.json --orto projekty/dzialka/zrodla/dzialka_orto.png --uzbrojenie projekty/dzialka/zrodla/dzialka_uzbrojenie.png
python rysunki/wszystko.py przyklad/ogrod/model/istniejacy.json --etap rozpoznanie
```

**Wynik:** `model/istniejacy.json` z czystą walidacją, plansza rozpoznania R-01, program i
inspiracje w `PROJEKT.md`.
**Bramka:** inwestor akceptuje rozpoznanie i program.

### 2. Koncepcja

- 2–3 warianty w osobnych plikach (`koncepcja_A.json`, `koncepcja_B.json`…): kopia stanu
  istniejącego z własnym `meta.projekt.id` i fazą `KONCEPCJA`; obiekty bez zmian zachowują
  id. Warianty wyrastają z programu i wniosków z inspiracji; każdy odpowiada na program
  inaczej (układ, relacje, komunikacja).
- Dla każdego wariantu: plan, przekroje, bilans powierzchni, 3D w planerze; porównanie z
  programem i uwarunkowaniami; rekomendacja z uzasadnieniem.

```bash
python rysunki/wszystko.py przyklad/ogrod/model/koncepcja_A.json przyklad/ogrod/model/koncepcja_B.json --etap koncepcja
python rysunki/roznica.py przyklad/ogrod/model/istniejacy.json przyklad/ogrod/model/koncepcja_A.json
python planer3d/serwer.py przyklad/ogrod/model/koncepcja_A.json przyklad/ogrod/model/koncepcja_B.json przyklad/ogrod/model/istniejacy.json
```

**Wynik:** modele i arkusze wariantów, porównanie i rekomendacja.
**Bramka:** inwestor wybiera wariant albo połączenie wariantów (wpis w „Decyzje”).

### 3. Projekt roboczy

- `model/projekt.json` z wybranego wariantu (faza `PROJEKT ROBOCZY`, własne id):
  dopracowane wymiary i rzędne, przekroje, zestawienia, różnica stanów, DXF, 3D; dla modułów
  wnętrz komplet rysunków lokalu.
- Lista do przekazania (karta, „Do przekazania”) w `PROJEKT.md`.

```bash
python rysunki/wszystko.py przyklad/ogrod/model/projekt.json --istniejacy przyklad/ogrod/model/istniejacy.json
python rysunki/wszystko.py przyklad/mieszkanie/model/projekt.json --istniejacy przyklad/mieszkanie/model/istniejacy.json
```

**Wynik:** `model/projekt.json`, komplet arkuszy i zestawień w `wyjscie/`, lista do przekazania.
**Bramka:** inwestor akceptuje projekt roboczy.

## PROJEKT.md

Karta projektu według `szablon_PROJEKT.md` (wypełniony przykład: `przyklad/ogrod/PROJEKT.md`):
rodzaj i karta, bieżący etap, temat i program, inspiracje, decyzje z datami, rewizje, otwarte
sprawy, lista do przekazania. Nic więcej: geometria i liczby są w modelu, wyniki w `wyjscie/`.
Uzupełniasz ją po każdej rozmowie, w której coś ustalono.

## Rewizje

Zmiana czegoś, co inwestor już zaakceptował, to rewizja: wpis w „Rewizje” (data, co,
dlaczego), zmiana modelu, przegenerowanie wyników i akceptacja zmienionej części. Wersję,
która ma zostać do porównania, zapisz jako osobny plik modelu z własnym `meta.projekt.id`
(np. `projekt_r1.json`), bo kopia `.bak` trzyma tylko ostatni zapis.

## Gdy narzędzie czegoś nie umie

Nie naginasz modelu (np. obiekt w obcej kategorii tylko po to, żeby się narysował) i nic nie
dorysowujesz na wynikach. Brak opisujesz w `PROJEKT.md` („Otwarte sprawy”), a gdy musi go
rozwiązać ktoś inny, dopisujesz go do listy do przekazania. Znane ograniczenia:

- moduł wnętrz zna tylko ściany prostopadłe do osi lokalu (ukośne przybliż i opisz);
- dach tylko na prostokącie i w czterech typach (dach złożony to kilka obiektów);
- łuki i krzywizny jako wielokąty;
- bilans liczy powierzchnię klasy w całości i wysokość od ±0, a plan miejscowy może liczyć
  inaczej (np. połowę powierzchni tarasów i stropodachów z roślinnością, wysokość od terenu) —
  przelicz według definicji z planu i zapisz wynik w `PROJEKT.md`;
- instalacje, konstrukcja, przedmiary i kosztorysy, wizualizacje fotorealistyczne oraz
  dokumenty do zgłoszenia lub pozwolenia są poza zestawem.

## Czego nie robić

Nie proponuj stylu ani rozwiązań przeniesionych z innych projektów i nie pokazuj gotowych
galerii.

Nie przechodź do następnego etapu bez akceptacji inwestora.

Nie przedstawiaj arkuszy jako projektu budowlanego ani dokumentów dla urzędu.

Nie powołuj się na przepis bez sprawdzenia aktualnego tekstu.

Nie zapisuj danych inwestora poza folderem projektu.

## Powiązane skille

- **model-zamierzenia** — jak opisać zamierzenie w modelu (legenda, teren, obiekty, stany,
  warianty) i polecenia wszystkich narzędzi.
- **modul-wnetrz** — lokal jako moduł wnętrz: rzuty, karty, kłady, plan wyburzeń, kontrole.
- **rysunki-i-modele** — odczyt stanu istniejącego z rysunków, zdjęć, skanów i geoportalu.
