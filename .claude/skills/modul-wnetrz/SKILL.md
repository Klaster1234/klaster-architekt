---
name: modul-wnetrz
description: >
  Moduł wnętrz modelu zamierzenia: model lokalu w JSON (ściany, otwory, pomieszczenia,
  aranżacja, instalacje) wpięty w model zamierzenia jako moduł, i jego narzędzia: rzut,
  karty pomieszczeń, kłady, izometria, plan wyburzeń, kontrole, DXF, GLB, planer 3D; dwa
  stany z tymi samymi ID, pomiar kontra założenie, co sprawdzić po zmianie. Użyj gdy
  pada: moduł wnętrz, model lokalu, lokal w budynku, dopisz do modelu, aranżacja, układ
  pomieszczeń, rzut z modelu, karta pomieszczenia, kład, izometria, walidacja lokalu,
  punkty elektryczne, wod-kan, rzędna sufitu, sufit podwieszany, założenia wysokości,
  wyburzenia, stan istniejący lokalu, przegeneruj rysunki, DXF, makieta GLB, planer 3D.
---

# Moduł wnętrz

## Zasada, od której się nie odchodzi

**Model jest jedynym źródłem prawdy.** Lokal opisuje jeden plik JSON w centymetrach według
`lokal/SCHEMAT.md` (działający przykład: `przyklad/mieszkanie/model/lokal_projekt.json`). Rzuty,
karty, kłady, izometrie, DXF, GLB i dane planera powstają z niego skryptami. Wyników nikt nie
poprawia ręcznie, ani w `wyjscie/`, ani w kopii otwartej w CAD: poprawka zniknie przy
następnym przegenerowaniu albo rozjedzie się z modelem. Zmienia się model i przegenerowuje
wyniki. Materiały źródłowe są tylko do odczytu.

**Zmiana geometrii idzie do geometrii.** Element opisany tylko w uwagach nie istnieje dla
rysunków: narysują stary stan. Zmieniając geometrię, popraw też `opis`, `kontrole` i
`wymiary_kontrolne`, których dotyczy.

**Stałe w kodzie rozjeżdżają się z modelem.** Wysokość kondygnacji, legenda i dane tabliczki
pochodzą z modelu. Nowy generator czyta je z `meta` i buduje arkusz na `wspolne/arkusz.py` i
`lokal/plan.py`.

**Odwołania po ID.** Elementy, ściany, otwory i punkty nazywaj ID z modelu. Opis słowny
doprecyzuj przed zmianą: które lico, w którą stronę (osie N/E/S/W modelu albo „patrząc od
drzwi”), o ile.

**Kolory są opcjonalne i należą do inwestora.** `wykonczenie`, `kolor` i `sciany_kolor` służą
tylko podglądowi (planer, makieta GLB, izometria) i wpisuje się je dopiero po ustaleniu z
inwestorem; bez nich podgląd jest neutralny. Rysunki i kontrole działają bez kolorów.

## Moduł w modelu zamierzenia

Lokal jest modułem wnętrz: model zamierzenia (`meta.rodzaj: "wnetrze"` albo `budynek`) ma
poziom i wpis w `moduly`, a lokal leży w osobnym pliku obok (przykład:
`przyklad/mieszkanie/model/projekt.json` i `lokal_projekt.json`).

```json
"poziomy": [{"id": "L3", "nazwa": "3. piętro", "z": 900}],
"moduly": [{"id": "M1", "rodzaj": "wnetrze", "plik": "lokal_projekt.json", "poziom": "L3",
            "przesuniecie": [0, 0], "obrot_stopnie": 0}]
```

- `plik` jest względny wobec pliku modelu zamierzenia; lokal leży na rzędnej poziomu, obrócony
  o `obrot_stopnie` przeciwnie do ruchu wskazówek zegara wokół swojego punktu (0, 0), a potem
  przesunięty o `przesuniecie` (cm).
- Lokal zachowuje własne `meta` (tabliczka arkuszy modułu, `meta.polnoc` w osiach lokalu). Przy
  obróconym module oś +Y lokalu ma azymut osi +Y zamierzenia pomniejszony o `obrot_stopnie`;
  wpisz go w lokalu, żeby strzałka N na arkuszach modułu się zgadzała.
- W modelu zamierzenia ściany, pomieszczenia i wyposażenie modułu są obiektami kategorii
  `_sciana`, `_pomieszczenie` i `_wyposazenie` o id `<id modułu>:<id>`; nie wpisuje się ich do
  legendy.
- `zamierzenie/waliduj.py` sprawdza moduł walidatorem lokalu. `rysunki/wszystko.py` na modelu
  zamierzenia robi dla każdego modułu komplet rysunków lokalu, a stanem istniejącym modułu jest
  moduł o tym samym `id` w modelu `--istniejacy`.
- Budynek wielokondygnacyjny: moduł na kondygnację, każdy na swoim poziomie.

```bash
python zamierzenie/waliduj.py przyklad/mieszkanie/model/projekt.json
python rysunki/wszystko.py przyklad/mieszkanie/model/projekt.json --istniejacy przyklad/mieszkanie/model/istniejacy.json
```

## Polecenia i wyniki

Wyniki trafiają do `wyjscie/` folderu projektu (model w katalogu `model/`) albo do `--wyjscie`,
pod nazwą `<meta.projekt.id>_<nazwa>`; arkusze jako SVG, PNG i PDF.

| Polecenie | Wynik |
|---|---|
| `python lokal/waliduj.py przyklad/mieszkanie/model/lokal_projekt.json` | spójność ID i odwołań, pola pomieszczeń względem `pow_m2` |
| `python lokal/punkty.py przyklad/mieszkanie/model/lokal_projekt.json` | każdy punkt elektryczny i wod-kan w swoim pomieszczeniu albo z `wyjatek` |
| `python lokal/odleglosci.py przyklad/mieszkanie/model/lokal_projekt.json P3` | kolizje z uwzględnieniem wysokości, odstępy poniżej `--prog` (domyślnie 120 cm) |
| `python lokal/zalozenia.py przyklad/mieszkanie/model/lokal_projekt.json` | `<id>_zalozenia.md`: założenia wysokości, rzędna sufitu, niepewne źródła |
| `python lokal/rzedna.py przyklad/mieszkanie/model/lokal_projekt.json` | zabudowy `do_sufitu` niezgodne z rzędną sufitu; `--zapisz` poprawia model (kopia `.bak`) |
| `python rysunki/rzut.py przyklad/mieszkanie/model/lokal_projekt.json` | A-01, rzut roboczy z wymiarem każdego lica |
| `python rysunki/karta_pomieszczenia.py przyklad/mieszkanie/model/lokal_projekt.json P3` | KP-P3, karta pomieszczenia z łańcuchami i kontrolami |
| `python rysunki/izometria.py przyklad/mieszkanie/model/lokal_projekt.json --pomieszczenia P3,P1` | A-03, izometria lokalu albo wybranych pomieszczeń |
| `python rysunki/klady.py przyklad/mieszkanie/model/lokal_projekt.json --zestawienie` | kłady z wpisów `klady` (K-01…) i K-00, zestawienie punktów bez kładu |
| `python rysunki/wyburzenia.py przyklad/mieszkanie/model/lokal_istniejacy.json przyklad/mieszkanie/model/lokal_projekt.json` | A-02, plan wyburzeń i nowych ścian |
| `python rysunki/dxf.py przyklad/mieszkanie/model/lokal_projekt.json` | `<id>_rzut.dxf` w milimetrach, z warstwami |
| `python rysunki/glb.py przyklad/mieszkanie/model/lokal_projekt.json` | `<id>_makieta.glb`, obiekty nazwane ID z modelu |
| `python rysunki/wszystko.py przyklad/mieszkanie/model/lokal_projekt.json --istniejacy przyklad/mieszkanie/model/lokal_istniejacy.json` | walidacja, kontrola punktów i wszystkie rysunki lokalu naraz |

`waliduj.py`, `punkty.py`, `odleglosci.py` i `wszystko.py` kończą się kodem 1, gdy znajdą
błąd; `rzedna.py` bez `--zapisz` — gdy są zmiany do wprowadzenia.

## Po każdej zmianie

`rysunki/wszystko.py` na lokalu (z `--istniejacy`) uruchamia walidatory i wszystkie rysunki. Na
modelu zamierzenia zaczyna od walidacji zamierzenia razem z modułami (`lokal/waliduj.py`), a gdy ta
nie przejdzie, arkusze nie powstają: pozostałe kroki są „pominiety - walidacja nie przeszla”, kod 1.
Rozbieżność pola pomieszczenia z dokumentacją (`POZA TOLERANCJA`) poprawia się w `pow_m2` albo
oznacza polem `zmiana` pomieszczenia (opis zamierzonej zmiany, `lokal/SCHEMAT.md`). Zmianę zamyka
czysta walidacja i obejrzenie zmienionych arkuszy.

**Kontrola wzrokowa nie wystarcza.** Punkt spoza pomieszczenia też się narysuje; wyłapie go
`lokal/punkty.py`. Świadomy wyjątek (np. łącznik po drugiej stronie ściany, przy drzwiach)
opisuje pole `wyjatek`. `lokal/odleglosci.py` pokazuje kolizje i odstępy z uwzględnieniem
wysokości: szafka dolna i wisząca nad nią nie kolidują.

### Po zmianie sprawdź

| Zmiana w modelu | Sprawdź |
|---|---|
| `wys` blatu (np. ciągu kuchennego) | `h` punktów nad blatem, `z` okładziny nad blatem, kład tej ściany |
| `meta.rzedna_sufitu` | `lokal/rzedna.py` (zabudowy `do_sufitu`), linia RS na kładach, `sufity.strefy` i `sufity.klapy` |
| ściana przesunięta albo nowa | pola (`lokal/waliduj.py`), punkty (`lokal/punkty.py`), kłady tej ściany, plan wyburzeń |
| nowy element aranżacji | kolizje (`lokal/odleglosci.py`), punkty `elektryka` przy nim, karta pomieszczenia |
| otwór (`zakres`, `luk`, `wys_otw`) | `luk` zgodny z otworem, punkty przy otworze, elementy w polu otwierania (karta, planer) |
| `wys` elementu | kład ściany, `h` punktów nad elementem, `do_sufitu` (`lokal/rzedna.py`) |
| położenie modułu (`przesuniecie`, `obrot_stopnie`, `poziom`) | plan i przekroje zamierzenia, `meta.polnoc` lokalu, walidacja zamierzenia |

## Dwa stany

Stan istniejący i projektowany to dwa pliki w tym samym schemacie (`lokal_istniejacy.json`,
`lokal_projekt.json`). Ściany, które się nie zmieniają, mają w obu te same ID.
`rysunki/wyburzenia.py` liczy różnicę brył ścian (geometrię, nie ID): rozbiórki, nowe ściany i
zamurowania; ściana przesunięta z tym samym ID to rozbiórka starej i nowa w nowym miejscu. Każdy
stan ma własne `meta.projekt.id`, bo id jest przedrostkiem nazw wyników. Geometrię stanu
istniejącego odczytuje się ze źródeł według skilla `rysunki-i-modele`.

## Pomiar kontra założenie

Każda wysokość elementu i grzejnika ma `wys_zrodlo`: `użytkownik …`, `produkt …` albo
`ZAŁOŻENIE …`. Geometria z niepewnego źródła ma `zrodlo` (wpis w `meta.zrodla` z
`dokladnosc_cm` i `wiazace`) i własne `dokladnosc_cm`. Rzut opisuje wymiary ze źródeł
niewiążących albo mniej dokładnych niż 2 cm jako „≈ 412”.

`lokal/zalozenia.py` zbiera założenia wysokości, rzędną sufitu ze statusem założenia i rekordy
z niepewnych źródeł do `<id>_zalozenia.md`. W kolumnie „Odpowiedź” wpisuje się „OK” albo nową
wartość; potwierdzoną wartość przenosi się do modelu i zmienia `wys_zrodlo` albo `zrodlo`.

**Klasa założenia** mówi, co je zamknie: A — wybór wartości, B — dobór produktu, C — pomiar na
miejscu, D — inna wartość, z której wynika (np. rzędna sufitu). Można ją dopisać w
`wys_zrodlo` (np. „ZAŁOŻENIE C — …”). Wysokości przy ścianie (punkty, meble, RS) pokazują kłady.

**Dwa poziomy odniesienia.** Wysokości w modelu liczy się od podłogi WYKOŃCZONEJ, a pomiar z
natury zwykle daje światło od WYLEWKI: przeliczając, dodaj grubość warstw posadzki. Sprawdź, od
czego liczona jest wysokość z rysunku.

**Rzędna sufitu (RS)** to `meta.rzedna_sufitu`, jedna na cały lokal: `wartosc`, `status` i
opcjonalnie `widelki` — zakres dopuszczalny `[min, max]` (`lokal/SCHEMAT.md`), który
`lokal/zalozenia.py` pokazuje obok wartości, gdy status jest założeniem. Zabudowy z
`do_sufitu: true` kończą się na RS: `lokal/rzedna.py` pokazuje rozbieżności, a z
`--zapisz` poprawia je w modelu (kopia `.bak`). Kłady rysują linię RS. Niższy sufit w
pojedynczym pomieszczeniu opisuje `sufity.strefy[].h`.

## Arkusze

- Arkusz (`wspolne/arkusz.py`): ramka, tabliczka z `meta.projekt` i datą wygenerowania (pole
  FAZA pokazuje `meta.projekt.faza` dosłownie), adnotacja „Rysunek roboczy — nie zastępuje
  projektu sporządzonego przez osobę z uprawnieniami.”, legenda z konwencją wysokości (h to oś
  od podłogi wykończonej) i uwagi. Elementy rzutu rysuje `lokal/plan.py`. Kody: A-01 rzut, A-02
  plan wyburzeń, A-03 izometria, KP-<nr> karta pomieszczenia, K-01… kłady (kod to `id` wpisu
  `klady`), K-00 zestawienie punktów bez kładu.
- Karta pomieszczenia: łańcuchy wymiarowe, wymiary kontrolne przejść, pas kontroli nad rysunkiem
  (`aranzacja[nr].kontrole`), bryły powyżej płaszczyzny cięcia (130 cm) linią przerywaną.
- Izometria: ściany ucięte na wysokości `--h` (domyślnie 120 cm), meble w pełnej wysokości;
  szybki podgląd układu.
- Kład definiuje wpis `klady` w modelu (`id`, `pomieszczenie`, `sciana`); oś i znak liczy
  silnik. Przy każdym punkcie para a·h (a od lewego końca lica, patrząc na ścianę), łańcuch
  poziomy i wysokości, linia RS i elementy przed płaszczyzną przerywaną, miniatura z kierunkiem
  patrzenia, tabela punktów z obwodami. Punkty ze ścian bez kładu trafiają do zestawienia K-00
  (`klady.py --zestawienie`).
- DXF jest w milimetrach, z warstwami (`rysunki/dxf.py`). Makieta GLB ma obiekty nazwane ID z
  modelu i otwiera się w Blenderze, three.js i przeglądarkach glTF.

## Planer 3D

`python planer3d/serwer.py przyklad/mieszkanie/model/lokal_projekt.json` pokazuje lokal w
przeglądarce: rzut i 3D, przestawianie mebli z kontrolami, słońce według `meta.polnoc`.
`python planer3d/serwer.py przyklad/mieszkanie/model/projekt.json przyklad/mieszkanie/model/istniejacy.json`
pokazuje moduł w modelu zamierzenia, z przełączaniem stanów. Planer nigdy nie zapisuje modelu.
Przestawienia trzyma w przeglądarce, a „kopiuj zmiany dla Claude” daje JSON z ID, nowym `box` i
`front` (w planerze zamierzenia: przesunięcia `dx`, `dy`), który nanosi się na model; potem
przegenerowuje się wyniki. Dane planera (`<id>_planer.json`) serwer odtwarza sam, gdy model się
zmieni.

## Czego nie robić

Nie poprawiaj ręcznie wyników wygenerowanych z modelu: zmień model i przegeneruj.

Nie zapisuj zmiany geometrii tylko w opisie albo w uwagach.

Nie zamykaj zmiany bez czystej walidacji i bez przejrzenia tabeli „Po zmianie sprawdź”.

Nie nadawaj obu stanom tego samego `meta.projekt.id`.

Nie wpisuj kolorów, których inwestor nie ustalił.

## Powiązane skille

- **architekt** — prowadzenie zamierzenia etapami (temat, rozpoznanie, koncepcja, projekt
  roboczy); karta `karty/wnetrze.md` opisuje rozpoznanie i uwarunkowania dla wnętrz.
- **model-zamierzenia** — model zamierzenia, w który lokal jest wpięty jako moduł.
- **rysunki-i-modele** — odczyt geometrii lokalu z rysunków, zdjęć i skanów.
