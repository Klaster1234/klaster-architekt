---
name: model-zamierzenia
description: >
  Model zamierzenia w JSON (działka, teren, sąsiedztwo, plan miejscowy, poziomy, legenda
  projektu, obiekty, moduły wnętrz, przekroje) jako jedyne źródło arkuszy, zestawień, DXF,
  GLB i danych planera 3D; stan istniejący, koncepcje i projekt w osobnych plikach. Użyj
  gdy pada: model zamierzenia, dopisz obiekt, legenda, kategoria, teren, warstwice,
  rzędne, działka, sąsiedztwo, dach, przekrój, elewacja, cienie, zestawienie roślin,
  bilans powierzchni, powierzchnia biologicznie czynna, różnica stanów, wycinka i
  nasadzenia, warianty, koncepcja A i B, dane z geoportalu, plan miejscowy do modelu,
  planer 3D ogrodu, wszystko.py --etap.
---

# Model zamierzenia

## Zasada, od której się nie odchodzi

**Model jest jedynym źródłem prawdy.** Jeden plik JSON na stan zamierzenia, w centymetrach,
opisany w `zamierzenie/SCHEMAT.md` (przykłady: `przyklad/ogrod/model/` i
`przyklad/mieszkanie/model/`). Arkusze, zestawienia, DXF, GLB i dane planera powstają z niego
skryptami; wyników nikt nie poprawia ręcznie. Zmienia się model i przegenerowuje wyniki.
Materiały źródłowe są tylko do odczytu.

## Jak opisać zamierzenie

- **Rodzaj pliku.** Model zamierzenia ma `meta.rodzaj` (`wnetrze`, `ogrod`, `budynek`, `inne`)
  i co najmniej jedną z sekcji `obiekty`, `moduly`, `miejsce`; model lokalu (moduł wnętrz) ma
  `sciany`. Skrypty zamierzenia na modelu lokalu kończą się komunikatem i kodem 2.
- **`meta.projekt`** — `id` (bez spacji, przedrostek nazw wyników, inny w każdym stanie),
  `obiekt`, `inwestor`, `autor`, `faza` (trafia na tabliczkę dosłownie, np. `STAN ISTNIEJĄCY`,
  `KONCEPCJA`, `PROJEKT ROBOCZY`). Obok: `polnoc.azymut_osi_Y_stopnie`, `lokalizacja` (słońce),
  opcjonalnie `georef` i `zero_npm_m`.
- **Jednostki i rzędne.** Centymetry w planie i w pionie; `z` względem ±0. Wysokości obiektu
  (`z`, `wys`, `dach.z0`) liczy się od podstawy: rzędnej poziomu (`poziom`), terenu w środku
  obrysu (`na_terenie: true`) albo ±0.
- **Obiekty** — `{id, kategoria, ksztalt, …}`: wielokąt (powierzchnia, bryła, dach), linia albo
  punkt, zgodnie z kształtem kategorii w legendzie. Bryła ma `z: [z0, z1]` albo `wys`; linia z
  `wys` (ogrodzenie, murek) ma bryłę; punkt rośliny ma `srednica` korony i `wys`.
- **Dach** — obiekt z obrysem ścian (prostokąt) i polem `dach` (`plaski`, `jednospadowy`,
  `dwuspadowy`, `czterospadowy`; `kat`, `z0`, `okap`, `kalenica`, `nizej`); dach złożony to
  kilka obiektów.
- **Rośliny w grupie** — powierzchnia albo linia z `atrybuty.rozstaw_cm`; zestawienie liczy
  sztuki z rozstawu.
- **Źródło i dokładność** — `zrodlo` i `dokladnosc_cm` przy działkach, terenie, sąsiedztwie i
  obiektach; wartości niepewne (dokładność powyżej 5 cm albo `zrodlo: "ZALOZENIE"`) arkusze
  oznaczają „≈”.
- **Przekroje** — `{id, linia, glebokosc, tytul}`; widok sięga w lewo od linii (patrząc od
  pierwszego punktu do drugiego), linia obok budynku daje elewację.

## Legenda projektu

Kategorie obiektów definiuje legenda modelu, nie kod: `{nazwa, ksztalt, plan, bryla,
zestawienie, bilans, kolizja}`. Obiekt z kategorią spoza legendy to błąd walidacji (poza
kategoriami `_sciana`, `_pomieszczenie`, `_wyposazenie`, które biblioteka tworzy z modułów).

- **Kolory ustala się z inwestorem.** Bez nich obowiązują neutralne domyślne (szarości; rośliny
  `#8FA27F`), przykłady mają legendę neutralną. Kategorie rozróżnia też kreskowanie
  (`plan.kreskowanie`) i symbol punktu (`plan.symbol`).
- **`zestawienie`** — atrybuty pokazywane w zestawieniu Z-01 (np. `gatunek`, `rozstaw_cm`,
  `obwod_cm`, `wielkosc`).
- **`bilans`** — klasa w bilansie Z-02: `zabudowa`, `pbc`, `utwardzona`, `woda`, `inne`;
  część wspólna klas liczy się w wyższej (zabudowa > utwardzona > woda > pbc > inne), a walidator
  ostrzega o nakładaniu.
- **`kolizja`** — czy walidator i planer kontrolują nakładanie (domyślnie tylko bryły).

## Teren

`miejsce.teren.punkty` to `[x, y, z]` w cm względem ±0 ze `zrodlo` i `dokladnosc_cm`: z NMT
(`narzedzia/geoportal.py --teren KROK_M` i `zamierzenie/z_geoportalu.py`) albo z pomiaru.
Biblioteka buduje z nich siatkę trójkątów; poza siatką rzędna najbliższego punktu, a mniej niż
3 punkty to teren płaski na ±0. Arkusze rysują warstwice co 25 cm i rzędne; powierzchnie i
linie `na_terenie` przylegają do terenu w 3D. Teren z pomiaru ma pierwszeństwo przed NMT
(import go nie nadpisuje bez `--nadpisz-teren`).

Zmiana ±0 po imporcie: ±0 wyznacza `meta.zero_npm_m` (rzędna w m n.p.m.); import wpisuje tę rzędną
tylko wtedy, gdy model jej nie ma (teren w punkcie bazowym). Inne ±0 (np. poziom parteru) wpisuje
się w `meta.zero_npm_m` i ponawia import terenu (`z_geoportalu.py … --teren <nazwa>_teren.json`) —
teren z NMT (ze znacznikiem `z_geoportalu`) przelicza się wtedy względem nowego ±0. Teren z
pomiaru (bez znacznika) import zostawia: jego `z` przesuwa się ręcznie o różnicę (stare ±0 − nowe
±0) × 100 cm. O tę samą różnicę trzeba przesunąć `z` poziomów i obiektów opisanych względem
starego ±0.

## Moduły wnętrz

`moduly: [{id, rodzaj: "wnetrze", plik, poziom, przesuniecie, obrot_stopnie}]` wpina model lokalu
(`lokal/SCHEMAT.md`) na poziomie zamierzenia: obrót przeciwnie do ruchu wskazówek zegara wokół
punktu (0, 0) lokalu, potem przesunięcie. Arkusze zamierzenia rysują ściany i pomieszczenia
modułu, `rysunki/wszystko.py` robi dla modułu komplet rysunków lokalu. Szczegóły: skill
`modul-wnetrz`.

## Stany i warianty

- Stan istniejący, koncepcje i projekt to osobne pliki (`istniejacy.json`, `koncepcja_A.json`,
  `koncepcja_B.json`, `projekt.json`) z własnym `meta.projekt.id` i fazą.
- Obiekt, który się nie zmienia, ma we wszystkich plikach to samo `id` i te same dane.
  `zamierzenie/stany.py` porównuje pliki po `id`: usunięte, nowe, zmienione (kształt,
  kategoria, wysokości, średnica, dach, poziom, położenie na terenie, atrybuty).
- `rysunki/roznica.py` rysuje różnicę (P-02: w ogrodzie wycinka i nasadzenia); różnicę ścian
  lokalu pokazuje plan wyburzeń A-02 (`modul-wnetrz`).
- Warianty ogląda się razem: `rysunki/wszystko.py … --etap koncepcja` i planer z kilkoma plikami.

## Polecenia i wyniki

Wyniki trafiają do `wyjscie/` folderu projektu (model w katalogu `model/`), inaczej do
`wyjscie/` obok modelu; `--wyjscie` wskazuje inny katalog. Nazwy: `<meta.projekt.id>_<numer>_…`;
arkusze jako SVG, PNG i PDF. Numer arkusza zmienia `--numer`.

| Polecenie | Wynik |
|---|---|
| `python zamierzenie/waliduj.py przyklad/ogrod/model/projekt.json` | spójność, geometria, dachy, poziomy, moduły; ostrzeżenia o kolizjach, obiektach poza działką i nakładaniu klas bilansu |
| `python rysunki/rozpoznanie.py przyklad/ogrod/model/istniejacy.json` | R-01, plansza rozpoznania: działka, sąsiedztwo, warstwice, plan miejscowy, uwarunkowania; `--orto` i `--uzbrojenie` dają podkład (model z `meta.georef`) |
| `python rysunki/plan.py przyklad/ogrod/model/projekt.json` | P-01, plan: obiekty według legendy, moduły, wymiary, odległości od granic, rzędne |
| `python rysunki/plan.py przyklad/mieszkanie/model/projekt.json --poziom L3` | P-01 jednego poziomu (obiekty i moduły tego poziomu na tle działki) |
| `python rysunki/plan.py przyklad/ogrod/model/projekt.json --bez-warstwic --numer P-04` | plan bez warstwic terenu, pod innym numerem arkusza |
| `python rysunki/roznica.py przyklad/ogrod/model/istniejacy.json przyklad/ogrod/model/projekt.json` | P-02, obiekty usunięte, nowe i zmienione; lista zmian w konsoli |
| `python rysunki/cienie.py przyklad/ogrod/model/projekt.json` | P-03, cienie brył, dachów, roślin i sąsiedztwa (domyślnie 21.03, 21.06, 21.12, godz. 9, 12, 15) |
| `python rysunki/cienie.py przyklad/ogrod/model/projekt.json --daty 03-21,09-21 --godziny 8,10:30,13,16 --rok 2027 --numer P-05` | cienie dla wybranych dat (`MM-DD`), godzin (`HH` albo `HH:MM`, czas lokalny strefy modelu) i roku |
| `python rysunki/przekroj.py przyklad/ogrod/model/projekt.json` | P-11, P-12…, przekroje i elewacje z sekcji `przekroje` |
| `python rysunki/przekroj.py przyklad/ogrod/model/projekt.json --przekroj B` | jeden przekrój |
| `python rysunki/zestawienie.py przyklad/ogrod/model/projekt.json --istniejacy przyklad/ogrod/model/istniejacy.json` | Z-01, zestawienie według legendy (MD, CSV, arkusz), kolumna stanu |
| `python rysunki/bilans.py przyklad/ogrod/model/projekt.json` | Z-02, bilans powierzchni i porównanie z `plan_miejscowy.parametry` |
| `python rysunki/dxf.py przyklad/ogrod/model/projekt.json` | `<id>_plan.dxf` w milimetrach, warstwa na kategorię |
| `python rysunki/glb.py przyklad/ogrod/model/projekt.json` | `<id>_makieta.glb`: teren, obiekty, sąsiedztwo, moduły |
| `python planer3d/eksport_web.py przyklad/ogrod/model/projekt.json` | `<id>_planer.json` (serwer planera robi to sam) |

Komplet dla etapu (`rysunki/wszystko.py`, kroki według `--etap`):
- `rozpoznanie`: walidacja, plansza R-01, plan P-01, cienie P-03;
- `koncepcja` (każdy podany plik osobno): walidacja, P-01, przekroje, bilans Z-02, makieta GLB i
  dane planera;
- `projekt` (domyślny): jak koncepcja, a do tego różnica P-02 (z `--istniejacy`), cienie P-03,
  zestawienie Z-01, DXF i komplet rysunków każdego modułu wnętrz.

Arkusza bez treści `wszystko.py` nie rysuje, tylko wpisuje do tabeli jako pominięty (kod 0): R-01, P-03 i
Z-02 bez działki i punktów terenu, Z-01 bez obiektów, P-02, gdy żaden z dwóch stanów nie ma obiektów.

Po nieudanej walidacji zamierzenia — także gdy `lokal/waliduj.py` odrzuca moduł wnętrz — arkusze tego
modelu nie powstają: `wszystko.py` wpisuje pozostałe kroki jako „pominiety - walidacja nie przeszla” i
kończy się kodem 1. Rozbieżność pola pomieszczenia z dokumentacją (`POZA TOLERANCJA`) poprawia się w
`pow_m2` albo oznacza polem `zmiana` pomieszczenia (opis zamierzonej zmiany, `lokal/SCHEMAT.md`).

```bash
python rysunki/wszystko.py przyklad/ogrod/model/istniejacy.json --etap rozpoznanie
python rysunki/wszystko.py przyklad/ogrod/model/koncepcja_A.json przyklad/ogrod/model/koncepcja_B.json --etap koncepcja
python rysunki/wszystko.py przyklad/ogrod/model/projekt.json --istniejacy przyklad/ogrod/model/istniejacy.json
```

`waliduj.py` i `wszystko.py` kończą się kodem 1 przy błędach; bilans przekroczony względem planu
to informacja (kod 0).

## Dane publiczne

Działka, budynki w sąsiedztwie, teren z NMT i ortofotomapa (`geoportal.py`), plan miejscowy z
Krajowej Integracji MPZP (`plan_miejscowy.py`), podkład uzbrojenia (`uzbrojenie.py`); import do
modelu `z_geoportalu.py`. Bez pliku modelu import zakłada szkielet (`meta.rodzaj: "inne"`).
Rekordy z geoportalu mają `z_geoportalu: true`. Ponowny import:
- działkę zastępuje po `id` (identyfikator z ULDK) tylko wtedy, gdy rekord ma znacznik; działka
  poprawiona ręcznie (np. granica z pomiaru geodety) traci znacznik i zostaje, a działka z
  geoportalu o tym samym `id` nie jest dopisywana (raport importu: „zostawiono (reczny)”);
- w sąsiedztwie zastępuje albo usuwa tylko rekordy ze znacznikiem; rekordy wpisane ręcznie
  zostają (poprawiony rekord z geoportalu traci znacznik), także rekord o `id` budynku z
  geoportalu;
- teren bez znacznika (np. z pomiaru) zostawia, chyba że podano `--nadpisz-teren`.

Parametry planu (`pbc_min_proc`, `zabudowa_max_proc`, `wys_max` w cm) przepisujesz z uchwały.
Informacja z usług nie zastępuje wypisu i wyrysu z planu ani mapy do celów projektowych.

```bash
python narzedzia/geoportal.py --adres "Warszawa, Plac Defilad 1" --promien 50 --teren 5 --nazwa dzialka --wyjscie projekty/dzialka/zrodla
python narzedzia/plan_miejscowy.py --meta projekty/dzialka/zrodla/dzialka_meta.json
python narzedzia/uzbrojenie.py --meta projekty/dzialka/zrodla/dzialka_meta.json
python zamierzenie/z_geoportalu.py projekty/dzialka/model/istniejacy.json --meta projekty/dzialka/zrodla/dzialka_meta.json --teren projekty/dzialka/zrodla/dzialka_teren.json --plan projekty/dzialka/zrodla/dzialka_plan_miejscowy.json --id dzialka_istn
python rysunki/rozpoznanie.py projekty/dzialka/model/istniejacy.json --orto projekty/dzialka/zrodla/dzialka_orto.png --uzbrojenie projekty/dzialka/zrodla/dzialka_uzbrojenie.png
```

## Planer 3D

`python planer3d/serwer.py przyklad/ogrod/model/projekt.json przyklad/ogrod/model/koncepcja_A.json przyklad/ogrod/model/koncepcja_B.json`
uruchamia planer w przeglądarce (adres wypisuje serwer, domyślnie `http://127.0.0.1:8055/`).
Pierwszy plik decyduje o stronie (model zamierzenia: `zamierzenie.html`), pozostałe są
wariantami do przełączania w tym samym kadrze i o tej samej porze. Planer pokazuje rzut i 3D z
terenem, obiekty według legendy, moduły wnętrz, zegar słoneczny z cieniami i kontrole
(odległość wybranego obiektu od granicy działki i od obiektu odniesienia, który wskazuje się
Shift+klikiem na rzucie albo w 3D, z wymiarem na rzucie; Esc usuwa odniesienie; kolizje według
legendy). Obiekt można przesunąć; „kopiuj zmiany dla Claude” daje JSON `{"model",
"przesuniete": [{"id", "dx", "dy"}]}` w cm, który nanosi się na model, a potem przegenerowuje
wyniki. Planer nigdy nie zapisuje modelu; po zmianie pliku modelu wystarczy odświeżyć stronę —
przesunięcia zapisane w przeglądarce dla innego położenia obiektu w modelu (np. już naniesione)
planer pomija i o tym informuje.

## Po zmianie sprawdź

| Zmiana w modelu | Sprawdź |
|---|---|
| działka albo plan miejscowy | bilans Z-02, odległości od granic (P-01), obiekty poza działką (walidacja) |
| teren | rzędne i warstwice (P-01, R-01), przekroje, podstawy obiektów `na_terenie` |
| bryła albo dach | przekroje, cienie P-03, bilans (wysokość i zabudowa), kolizje (walidacja) |
| obiekty roślin | zestawienie Z-01 (sztuki z rozstawu), bilans (pbc), cienie |
| legenda | wszystkie arkusze (kolory, kreskowanie, klasy bilansu, zestawienie) |
| `id` obiektu | różnica stanów: zmiana `id` to usunięcie i nowy obiekt |
| moduł wnętrz | walidacja zamierzenia i lokalu, rysunki modułu (`modul-wnetrz`) |

## Czego nie robić

Nie poprawiaj ręcznie wyników wygenerowanych z modelu: zmień model i przegeneruj.

Nie nadawaj dwóm stanom tego samego `meta.projekt.id`.

Nie wymyślaj kolorów legendy: ustal je z inwestorem albo zostaw neutralne.

Nie zamykaj zmiany bez czystej walidacji i obejrzenia zmienionych arkuszy.

## Powiązane skille

- **architekt** — prowadzenie zamierzenia etapami (temat, rozpoznanie, koncepcja, projekt
  roboczy) z kartami zamierzeń; ten skill opisuje model i narzędzia, z których korzysta.
- **modul-wnetrz** — lokal jako moduł wnętrz: format, rysunki, kontrole i planer lokalu.
- **rysunki-i-modele** — odczyt stanu istniejącego z rysunków, zdjęć, skanów i geoportalu.
