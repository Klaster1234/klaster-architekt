# Schemat modelu zamierzenia

Model zamierzenia to plik JSON, który opisuje zamierzenie budowlane dowolnego rodzaju — wnętrze, ogród, budynek
albo inny temat (taras, wiata, ogrodzenie…): działkę, teren, sąsiedztwo, plan miejscowy, poziomy, obiekty
opisane legendą projektu i moduły. Jeden plik to jeden stan (`istniejacy.json`, `koncepcja_A.json`,
`projekt.json`). Plik jest **jedynym źródłem prawdy**: wyniki powstają z niego skryptami i nikt ich nie
poprawia ręcznie. Moduł wnętrz to model lokalu opisany w `lokal/SCHEMAT.md`.

Pełny przykład: `przyklad/ogrod/model/istniejacy.json` i `przyklad/ogrod/model/projekt.json` (fikcyjny ogród
przy domu).

## Konwencje

- **Jednostki: centymetry** w planie i w pionie, układ lokalny. Oś +X w prawo, oś +Y w górę arkusza; strony
  świata wynikają z `meta.polnoc.azymut_osi_Y_stopnie`.
- **Rzędne `z` względem ±0 projektu.** `meta.zero_npm_m` (opcjonalnie) wiąże ±0 z rzędną nad poziomem morza.
- **ID są unikalne w całym modelu** (działki, sąsiedztwo, poziomy, obiekty, moduły, przekroje). Obiekt, który
  się nie zmienia, ma we wszystkich plikach stanów to samo id i te same dane. Znak `:` w id działki, sąsiedztwa,
  obiektu i modułu jest zarezerwowany dla elementów modułów wnętrz (`<moduł>:<id>`).
- **Rodzaj pliku:** model zamierzenia ma `meta.rodzaj` i co najmniej jedną z sekcji `obiekty`, `moduly`,
  `miejsce`; model lokalu (moduł wnętrz) ma `sciany`. Narzędzia przyjmujące oba rodzaje rozpoznają je po tej
  regule.
- **Pola zaczynające się od `_`** istnieją tylko w pamięci narzędzi; w pliku ich nie ma.
- Plik w UTF-8 z końcami linii LF; zapis przez bibliotekę (`model.zapisz`, z kopią `.bak`).

## meta

| Pole | Znaczenie |
|---|---|
| `rodzaj` | `wnetrze` \| `ogrod` \| `budynek` \| `inne` |
| `projekt` | `{id, obiekt, inwestor, autor, faza}` — dane tabliczki; `id` (litery A–Z i a–z, cyfry, `_`, `.`, `-`, bez spacji) jest przedrostkiem nazw plików wynikowych, więc każdy stan ma własne, a moduł wnętrz (lokal) — inne niż zamierzenie i pozostałe moduły; `faza` trafia na tabliczkę dosłownie |
| `polnoc` | `{azymut_osi_Y_stopnie}` — azymut kierunku +Y od północy zgodnie z ruchem wskazówek zegara (domyślnie 0) |
| `lokalizacja` | `{lat, lon, strefa}` — położenie do obliczeń słońca; bez tego pola środek Polski (52,1; 19,5; `Europe/Warsaw`) |
| `georef` | opcjonalnie `{epsg: 2180, x0, y0, obrot_stopnie}` — jak w module wnętrz |
| `zero_npm_m` | opcjonalnie — rzędna ±0 nad poziomem morza w metrach |

## miejsce

**`dzialki`** — `{id, numer?, granica: [[x, y], …], zrodlo?, dokladnosc_cm?, z_geoportalu?}`. Kilka działek tworzy
jedną całość (suma granic).

**`teren`** — `{punkty: [[x, y, z], …], zrodlo?, dokladnosc_cm?, z_geoportalu?}` — punkty wysokościowe. Biblioteka
(`zamierzenie/teren.py`) buduje z nich siatkę trójkątów (Delaunay): wewnątrz siatki rzędna jest interpolowana
liniowo, poza nią równa rzędnej najbliższego punktu; podaje też profil wzdłuż linii i warstwice. Mniej niż
3 punkty (albo punkty na jednej linii) oznaczają teren płaski na z = 0.

**`sasiedztwo`** — `{id, rodzaj, obrys: [[x, y], …], wys?, zrodlo?, dokladnosc_cm?, z_geoportalu?}` — budynki
i inne obiekty poza zamierzeniem; `wys` to wysokość nad terenem, podstawa leży na rzędnej terenu (bez `wys` —
wysokość nieznana, obiekt nie ma bryły w 3D).

**`plan_miejscowy`** — `{nazwa?, symbol?, przeznaczenie?, odnosnik?, zrodlo?, parametry?}`. W `parametry`:
`pbc_min_proc` (najmniejszy udział powierzchni biologicznie czynnej w %), `zabudowa_max_proc` (największy
udział powierzchni zabudowy w %) i `wys_max` (cm) są porównywane z bilansem; pozostałe wpisy to tekst na
planszę rozpoznania.

**`uwarunkowania`** — lista tekstów na planszę rozpoznania (przepisy, zgody, ograniczenia).

## poziomy

`{id, nazwa, z}` — poziomy odniesienia (kondygnacje, taras na wysokości); `z` względem ±0.

## legenda

Legenda należy do projektu: kategorie obiektów definiuje model, nie kod. Obiekt z kategorią spoza legendy to
błąd walidacji. Wyjątek to kategorie zaczynające się od `_` (`_sciana`, `_pomieszczenie`, `_wyposazenie`),
które biblioteka tworzy z modułów wnętrz.

`"<kategoria>": {nazwa, ksztalt, plan?, bryla?, zestawienie?, bilans?, kolizja?}`

| Pole | Znaczenie | Domyślnie |
|---|---|---|
| `nazwa` | opis na rysunkach i w zestawieniach | nazwa kategorii |
| `ksztalt` | `powierzchnia` \| `linia` \| `punkt` \| `bryla` \| `dach` | pole wymagane |
| `plan.wypelnienie` | `#RRGGBB` albo `null` | `#F2F2F2` (powierzchnia), `#E0E0E0` (bryła, dach), `null` (linia, punkt) |
| `plan.kreskowanie` | `brak` \| `ukos` \| `ukos_gesty` \| `krzyz` \| `kropki` \| `poziome` | `brak` |
| `plan.linia` | kolor linii `#RRGGBB` albo `null` — obiekt bez obrysu (bez linii) | `#444444` |
| `plan.grubosc` | grubość linii w jednostkach arkusza | 0,8 |
| `plan.symbol` | symbol punktu: `drzewo` \| `krzew` \| `kolo` \| `krzyz` \| `kwadrat` | `kolo` |
| `bryla.kolor` | kolor w modelu 3D `#RRGGBB` (`null` — domyślny) | `#C8C8C8`, roślinność `#8FA27F` |
| `zestawienie` | nazwy atrybutów pokazywanych w zestawieniu | `[]` |
| `bilans` | `zabudowa` \| `pbc` \| `utwardzona` \| `woda` \| `inne` \| `null` | `null` |
| `kolizja` | czy walidator i planer kontrolują nakładanie obiektów | `true` dla bryły, `false` dla reszty (także dachu, który leży na bryle budynku) |

Roślinność (domyślny kolor 3D `#8FA27F`) to kategoria z symbolem `drzewo` albo `krzew` albo z bilansem `pbc`.
Kształt z legendy wyznacza geometrię obiektu: `powierzchnia`, `bryla` i `dach` — `wielokat`; `linia` — `linia`;
`punkt` — `punkt`.

## obiekty

`{id, kategoria, ksztalt, poziom? | na_terenie?, z?, wys?, srednica?, dach?, atrybuty?, zrodlo?, dokladnosc_cm?, opis?}`

- `ksztalt`: `{"wielokat": [[x, y], …]}` | `{"linia": [[x, y], …]}` | `{"punkt": [x, y]}`. Wielokąt ma co
  najmniej 3 wierzchołki, bez samoprzecięć i bez otworów; pierwszego punktu nie trzeba powtarzać na końcu.
- **Rodzaje:**
  - powierzchnia (trawnik, rabata, nawierzchnia, strefa) — wielokąt na terenie (`na_terenie: true`; w 3D
    przylega do terenu) albo na poziomie;
  - linia (ogrodzenie, obrzeże, murek, żywopłot, kabel) — z `wys`, gdy ma bryłę;
  - punkt (drzewo, krzew, lampa, studzienka) — dla roślin `srednica` korony i `wys` w cm;
  - bryła — wielokąt wyciągnięty w pionie przez `z: [z0, z1]` albo `wys`;
  - dach — wielokąt obrysu ścian (prostokąt, także obrócony względem osi) z polem `dach`.
- **Podstawa wysokości.** `z`, `wys` i `dach.z0` liczy się od podstawy obiektu:
  - od rzędnej poziomu, gdy obiekt ma `poziom`;
  - od terenu (rzędna w środku ciężkości kształtu), gdy ma `na_terenie: true`;
  - od ±0 w pozostałych przypadkach.

  Zakres wysokości względem ±0 (`model.zakres_z`) to podstawa + `z`, albo od podstawy do podstawy + `wys`,
  albo sama podstawa (obiekt bez `z` i `wys`, np. powierzchnia); zakres dachu opisuje punkt niżej. Linie
  `na_terenie` z `wys` są w 3D drapowane po terenie; `zakres_z` linii liczy się od terenu w środku ciężkości.
  Powierzchnię `na_terenie` model 3D (`zamierzenie/bryly.py`) tnie siatką co 100 cm i każdy wierzchołek
  kładzie 1 cm nad terenem, więc przylega ona do terenu także wewnątrz dużych wielokątów.
- **`dach`** — `{typ, kat, z0, kalenica?, okap?, nizej?}`: `typ` `plaski` | `jednospadowy` | `dwuspadowy` |
  `czterospadowy`; `kat` w stopniach; `z0` — rzędna połaci nad linią ścian; kalenica równoległa do dłuższego
  boku, chyba że `kalenica: "krotszy"`; `okap` — wysięg poziomy w cm (krawędź połaci obniża się o okap · tg
  kąta). Dach z kilku części opisuje się kilkoma obiektami. Zakres wysokości dachu biegnie od okapu
  (podstawa + `z0` − `okap` · tg kąta; dach płaski: podstawa + `z0`) do kalenicy (płaski: podstawa + `z0` + 30;
  jednospadowy: podstawa + `z0` + b · tg kąta; dwuspadowy i czterospadowy: podstawa + `z0` + b/2 · tg kąta),
  gdzie b to bok obrysu ścian prostopadły do kalenicy.
  - Dach jednospadowy: `nizej` (`"N"` | `"E"` | `"S"` | `"W"`) to strona obrysu z niższą krawędzią połaci,
    w osiach modelu (N = +Y, E = +X, S = −Y, W = −X); na obróconym prostokącie to bok, którego zewnętrzna
    normalna jest najbliższa wskazanemu kierunkowi. Niższy może być tylko bok równoległy do kalenicy, czyli
    jeden z dłuższych boków (przy `kalenica: "krotszy"` jeden z krótszych, na kwadracie — boki różnią się
    o mniej niż 1 cm — dowolny). Bez pola `nizej` niższy jest bok, którego zewnętrzna normalna jest
    najbliższa −X (W), gdy oba boki równoległe do kalenicy odchylają się od osi Y o najwyżej 10°, a w
    pozostałych przypadkach bok z normalną najbliższą −Y (S; przy remisie, np. na kwadracie obróconym
    o 45°, ten bliższy −X). Wyższa krawędź leży na linii ściany, bez okapu; okap wysuwa niższą
    krawędź i oba szczyty.
  - Dach czterospadowy ma kalenicę wzdłuż dłuższego boku (połacie pod tym samym kątem); `kalenica: "krotszy"`
    jest przy nim błędem.
- **Rośliny.** Drzewo i krzew to punkt z `srednica` korony i `wys`; w `atrybuty` np. `gatunek`, `obwod_cm`
  (obwód pnia na wysokości 130 cm — drzewa istniejące), `wielkosc` (materiał szkółkarski — drzewa nowe).
  Rośliny w grupie to powierzchnia albo linia z `atrybuty.rozstaw_cm`: liczba sztuk to pole / rozstaw²,
  a dla linii długość / rozstaw, zaokrąglone w górę.
- `atrybuty` — dowolne pary nazwa–wartość; `zestawienie` w legendzie wybiera te, które trafiają do zestawień.

## moduly

`{id, rodzaj: "wnetrze", plik, poziom, przesuniecie: [x, y], obrot_stopnie?}` — moduł wnętrz to model lokalu
(`lokal/SCHEMAT.md`). `plik` to ścieżka względem pliku modelu zamierzenia. Moduł leży na poziomie `poziom`:
obrócony o `obrot_stopnie` przeciwnie do ruchu wskazówek zegara wokół swojego punktu (0, 0), a potem
przesunięty o `przesuniecie`. Budynek to poziomy, moduł wnętrz na kondygnację (opcjonalnie) oraz bryła i dach
jako obiekty ogólne.

## przekroje

`{id, linia: [[x, y], [x, y]], glebokosc?, tytul?}` — linia przekroju; `glebokosc` to zasięg widoku za
płaszczyzną przekroju (cm), po lewej stronie linii patrząc od pierwszego do drugiego punktu. Linia poprowadzona
poza budynkiem daje elewację.

## Bilans powierzchni

Klasa bilansu pochodzi z legendy. Powierzchnia klasy to suma wielokątów obiektów tej klasy przyciętych do
działki. Gdy obiekty różnych klas nakładają się, część wspólna trafia do klasy wyższej w kolejności
zabudowa > utwardzona > woda > pbc > inne, a walidator ostrzega o nakładaniu — w dobrym modelu powierzchnie
różnych klas się nie nakładają. Wysokość porównywana z `wys_max` jest liczona od ±0 (uproszczenie: plan
miejscowy zwykle mierzy ją od terenu).

## Stany

Stan istniejący, koncepcje i projekt to osobne pliki w tym schemacie. `zamierzenie/stany.py` porównuje dwa
pliki po id obiektów: usunięte, nowe i zmienione (kształt, kategoria, wysokości, średnica, dach, poziom,
położenie na terenie, atrybuty; opis i źródło nie są zmianą). W ogrodzie to wycinka i nasadzenia; w module
wnętrz różnicę pokazuje plan wyburzeń.

## Źródła i dokładność

`zrodlo` (tekst) i `dokladnosc_cm` podaje się wszędzie, gdzie mają sens: działki, teren, sąsiedztwo, obiekty.
Wartość jest niepewna, gdy `dokladnosc_cm` przekracza 5 cm albo `zrodlo` to `"ZALOZENIE"` (brak danych);
arkusze oznaczają takie wymiary i rzędne znakiem „≈”.

## Dane z geoportalu

`zamierzenie/z_geoportalu.py` wpisuje do modelu wyniki `narzedzia/geoportal.py` (działka, budynki sąsiednie, teren
z NMT, georeferencja, północ) i `narzedzia/plan_miejscowy.py`. Rekordy, które zapisuje (działka, budynki sąsiednie,
teren), mają pole `z_geoportalu: true`. Ponowny import zastępuje tylko rekordy z tym polem: działkę o tym samym `id`
(identyfikator działki z ULDK) i budynki w sąsiedztwie; budynek z geoportalu, którego nie ma już w nowych danych,
usuwa. Rekordy bez pola — wpisane albo poprawione ręcznie, np. z pomiaru geodety albo z wizji lokalnej — zostają,
także rekord o `id` działki albo budynku z geoportalu (rekord z geoportalu nie jest wtedy dopisywany, a raport
importu podaje go jako „zostawiono (reczny)”). Kto poprawia rekord z geoportalu ręcznie, usuwa z niego to pole,
żeby import go nie nadpisał. Teren bez pola (np. z pomiaru geodezyjnego) zostaje; opcja `--nadpisz-teren`
zastępuje go terenem z NMT.

## Walidacja

`python zamierzenie/waliduj.py <model>` drukuje sekcje SPOJNOSC, WARTOSCI, GEOMETRIA i OSTRZEZENIA, a na końcu
`WYNIK: OK` albo `WYNIK: BLEDY (n)` (kod wyjścia 1).

- Błędy spójności: brak albo powtórzone id; znak `:` w id działki, sąsiedztwa, obiektu albo modułu; brak
  `meta.projekt.id` albo id spoza liter A–Z, cyfr, `_`, `.`, `-` (także samo `..`); `meta.rodzaj` albo `ksztalt`
  i `bilans` w legendzie spoza listy; kolor w legendzie (`plan.wypelnienie`, `plan.linia`, `bryla.kolor`) inny
  niż `#RRGGBB` albo `null`; kategoria spoza legendy (poza `_*`); nieznany poziom albo moduł bez pola `poziom`;
  brak pliku modułu; moduł, którego nie przyjmuje `lokal/waliduj.py`; `meta.projekt.id` lokalu modułu równe id
  zamierzenia albo innego modułu (pliki wyników by się nadpisały).
- Błędy wartości (liczba, nie tekst, w dopuszczalnym zakresie): `z` — dwie liczby, z0 < z1; `wys`, `srednica`,
  `atrybuty.rozstaw_cm` i `wys` sąsiedztwa — większe od 0; `dach.kat` w przedziale (0, 90) dla dachów spadzistych
  (płaski: 0 albo brak pola); `dach.z0`; `dach.okap` ≥ 0; `z` poziomu; punkt terenu — trzy liczby `[x, y, z]`;
  `glebokosc` przekroju ≥ 0; `przesuniecie` modułu — dwie liczby, `obrot_stopnie` — liczba; `meta.lokalizacja`:
  `lat` w [−90, 90], `lon` w [−180, 180], `strefa` — znana nazwa strefy czasowej (np. `Europe/Warsaw`).
- Błędy geometrii: kształt obiektu niezgodny z legendą; niepoprawna geometria (samoprzecięcie, wielokąt z mniej
  niż 3 wierzchołkami, linia bez długości); dach na obrysie innym niż prostokąt albo o nieznanym typie; dach
  czterospadowy z `kalenica: "krotszy"`; `nizej` spoza N/E/S/W, przy dachu innym niż jednospadowy albo wskazujące
  bok prostopadły do kalenicy.
- Ostrzeżenia (bez wpływu na wynik): obiekt poza działką; nakładanie obiektów z `kolizja: true` (część wspólna
  w planie i w zakresie wysokości); nakładanie powierzchni różnych klas bilansu; obiekty `na_terenie` bez
  siatki terenu. Obiekty z błędną wartością nie biorą w nich udziału, a przy błędnym poziomie albo punkcie
  terenu ostrzeżeń się nie liczy (zależą od nich wysokości wszystkich obiektów).

Narzędzia czytające model kończą się komunikatem zamiast błędu Pythona, gdy plik nie jest poprawnym JSON-em
(„błędny JSON w linii L, kolumnie K”) albo gdy `meta.projekt.id` nie nadaje się na przedrostek nazwy pliku.
Moduł bez pliku narzędzia pomijają z uwagą w konsoli („UWAGA: modul … brak pliku … - pominiety”).

## Przykład minimalny

```json
{
  "meta": {"rodzaj": "inne", "projekt": {"id": "wiata", "obiekt": "Wiata na rowery", "faza": "KONCEPCJA"}},
  "miejsce": {"dzialki": [{"id": "DZ1", "granica": [[0, 0], [1500, 0], [1500, 2000], [0, 2000]]}]},
  "legenda": {"wiata": {"nazwa": "wiata", "ksztalt": "bryla", "bilans": "zabudowa"}},
  "obiekty": [{"id": "W1", "kategoria": "wiata", "ksztalt": {"wielokat": [[200, 200], [500, 200], [500, 400], [200, 400]]},
               "z": [0, 250]}]
}
```

Bez terenu, poziomów i modułów: teren jest płaski na ±0, a wiata stoi od ±0 do 250 cm.
