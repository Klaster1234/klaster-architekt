# Schemat modelu lokalu

Model to jeden plik JSON, który opisuje lokal: ściany, otwory, pomieszczenia, meble i instalacje (kolory do
podglądu są opcjonalne). Jest **jedynym źródłem prawdy**. Rzuty, karty, kłady, izometrie, DXF, GLB i dane planera
3D powstają z niego skryptami i nikt ich nie poprawia ręcznie. Zmiana w projekcie to zmiana w modelu i ponowne
wygenerowanie wyników (`python rysunki/wszystko.py model.json`).

Pełny, działający przykład: `przyklad/mieszkanie/model/lokal_projekt.json` (stan projektowany) i `przyklad/mieszkanie/model/lokal_istniejacy.json` (stan
przed zmianami).

## Konwencje

- **Jednostki: centymetry**, układ lokalny. Oś +X w prawo, oś +Y w górę arkusza.
- **Kierunki N / E / S / W** w polach `front` to kierunki osi modelu (N = +Y, E = +X), a nie strony świata.
  Strony świata wynikają z `meta.polnoc.azymut_osi_Y_stopnie`.
- **Wysokości od podłogi wykończonej.** Pomiar z natury zwykle daje światło od wylewki; przeliczając, dodaj
  grubość warstw posadzki.
- **`wys_otw` to górna krawędź otworu** od podłogi (okno z parapetem 85 i nadprożem na 235 ma `wys_otw: 235`).
- **Prostokąty** zapisuje się jako `[x0, y0, x1, y1]` w dowolnej kolejności narożników.
- **ID są globalnie unikalne** w całym modelu (ściany, otwory, elementy, punkty, trasy, okładziny, warianty,
  kłady…). Numery pomieszczeń (`nr`) to osobna przestrzeń nazw. Walidator zgłasza powtórzenia.
- **Pola zaczynające się od `_`** istnieją tylko w pamięci narzędzi; w pliku ich nie ma.
- **Ograniczenie: ściany wyłącznie prostopadłe do osi modelu.** Budynek obrócony względem północy to nie
  problem (azymut osi Y), ale ściany nieprostopadłe do siebie trzeba przybliżyć albo pominąć.
  `lokal/z_par_scian.py` wskazuje takie ściany przy imporcie.

## meta

| Pole | Znaczenie |
|---|---|
| `wersja_schematu` | 1 |
| `projekt` | `{id, obiekt, inwestor, autor, faza}` — dane tabliczki; `id` (litery A–Z i a–z, cyfry, `_`, `.`, `-`, bez spacji) jest prefiksem nazw plików wynikowych, warstw DXF i kluczy planera |
| `jednostki` | `"cm"` |
| `wysokosc_kondygnacji` | światło od podłogi wykończonej do stropu, np. 270 |
| `rzedna_sufitu` | `{wartosc, widelki: [min, max], status}` — rzędna sufitu podwieszanego (RS); elementy z `do_sufitu: true` kończą się na RS (`lokal/rzedna.py`). Jedna wartość RS na cały lokal, nie per pomieszczenie — wysokości sufitu w poszczególnych pomieszczeniach (np. obniżenia w łazience) opisuje `sufity.strefy[].h` |
| `polnoc` | `{azymut_osi_Y_stopnie, lokalizacja: {miasto, lat, lon, strefa}}` — azymut kierunku +Y od północy zgodnie z zegarem; lokalizacja i strefa czasowa dla słońca |
| `georef` | opcjonalnie `{epsg: 2180, x0, y0, obrot_stopnie}` — punkt (0, 0) modelu w układzie PL-1992 i obrót osi; wpisywany ręcznie z wartości wypisanych przez `narzedzia/geoportal.py` (`lokal/z_par_scian.py` liczy `obrot_stopnie`, ale zapisuje go tylko do własnego pliku `--wynik`, nie do `meta.georef`) |
| `zrodla` | `[{id, rodzaj, data, dokladnosc_cm, wiazace, opis}]` — materiały, z których powstał model; rekordy wskazują je polem `zrodlo` |
| `uwagi` | lista tekstów |

## Geometria

**`sciany`** — `{id, typ, nosna, pas, wys?, zrodlo?, dokladnosc_cm?, opis?}`
- `pas` to prostokąt ściany w rzucie; grubość to krótszy bok.
- `nosna`: ściany nośne rysuje się ciemniej i nie przestawia bez projektu konstrukcji.
- `wys: [z0, z1]` tylko dla ścian niepełnej wysokości (balustrada, murek). Domyślnie pełna wysokość kondygnacji.
- `typ` jest opisem (zewnętrzna, od klatki, międzylokalowa, działowa, balustrada…).

**`otwory`** — `{id, rodzaj, sciana, zakres, szer_otw?, wys_otw, parapet?, skrzydlo?, do?, zawias?, luk?, wejscie?}`
- `rodzaj`: `drzwi` | `drzwi wejściowe` | `okno` | `portfenetr` | `przejście`.
- `zakres: [a, b]` — położenie otworu wzdłuż osi ściany (współrzędna X dla ściany poziomej, Y dla pionowej).
- `luk: {c: [x, y], r, od, do}` — łuk otwierania skrzydła: środek w zawiasie, promień, kąty w stopniach
  przeciwnie do zegara od osi +X (0 = +X, 90 = +Y); łuk biegnie od `od` do `do`.
- `skrzydlo: [szer, wys]` — wymiary skrzydła w cm; czyta je planer 3D do narysowania bryły skrzydła,
  rysunki 2D (`rysunki/rzut.py` i inne) pokazują tylko łuk otwierania z `luk`.
- `wejscie: true` przy drzwiach wejściowych (start spaceru w planerze).
- `do` — pomieszczenie, do którego prowadzą drzwi (opis; sąsiedztwo narzędzia liczą same).

**`szachty`** — `{id, box, wymiar?, opis?}`;
**`grzejniki`** — `{id, pomieszczenie, box, typ, wys: [z0, z1], wys_zrodlo?}` (`wys_zrodlo` jak w elemencie
aranżacji — założenia zbiera `lokal/zalozenia.py`).

**`strefy_wirtualne`** — `{id, miedzy: [nr, nr], polilinia: [[x, y], …]}` — granica pomieszczeń bez ściany
(np. hol przechodzący w salon). Polilinia musi dochodzić do lic ścian.

**`pomieszczenia`** — `{nr, nazwa, stamp, pow_m2?, zewnetrzne?, wydzielone_z?, zmiana?, podloga?, sciany_kolor?, opis?}`
- **Wielokąta pomieszczenia się nie wpisuje.** Narzędzia liczą go z lic ścian, szacht, stref wirtualnych i
  domknięć otworów; `stamp` to dowolny punkt wewnątrz pomieszczenia.
- `pow_m2` — pole z dokumentacji do kontroli (`lokal/waliduj.py`, tolerancja max(0,5%, 0,02 m²)).
- `zewnetrzne: true` — balkon, loggia, taras (nie wchodzi do sumy pól lokalu).
- `wydzielone_z` — część większego pomieszczenia z dokumentacji (np. wnęka); pola sumują się do bazowego.
- `zmiana` — opis zamierzonej zmiany; różnica pola jest wtedy raportowana, a nie zgłaszana jako błąd.
- `podloga`: `panele` | `gres` | `deska` | `płyty tarasowe` | inny opis.
- `sciany_kolor` — opcjonalny kolor ścian do podglądu: nazwa tokenu albo `#RRGGBB` (patrz „Wykończenie”).

**`kontekst`** — `{id, rodzaj, box, wys?}` — otoczenie, które rzuca cień lub zasłania widok (klatka, budynek
sąsiedni). Budynki z geoportalu trafiają tutaj.

**`zmiany`** — `{id, rodzaj, xy?, opis}` — opisy zmian względem stanu istniejącego; `xy` to miejsce etykiety na
planie wyburzeń.

## Aranżacja

**`aranzacja`** — `{nr: {status?, elementy: [...], wymiary_kontrolne?: [{od, do, opis}], kontrole?: [tekst]}}`

Element: `{id, rodzaj, box, wys: [z0, z1], front?, segmenty?, kolor?, wys_zrodlo?, do_sufitu?, mobilne?, ksztalt?,
produkt?, zrodlo?, dokladnosc_cm?, opis?}`
- `rodzaj` z listy poniżej (inny tekst działa jak bryła ogólna).
- `front`: N / E / S / W — strona frontu (kierunek osi modelu).
- `segmenty: [{dl, opis}]` — podział frontu na moduły od lewej, patrząc na front.
- `kolor` — opcjonalny kolor do podglądu: nazwa tokenu z `wykonczenie.tokeny` albo `#RRGGBB`.
- `wys_zrodlo` — skąd wysokość: `użytkownik …`, `produkt …` albo `ZAŁOŻENIE …`. Założenia zbiera
  `lokal/zalozenia.py`.
- `do_sufitu: true` — zabudowa kończy się na rzędnej sufitu (`lokal/rzedna.py`).
- `ksztalt: "kolo"` — bryła okrągła (box to obwiednia).
- `produkt: {nazwa, wymiary?, url?}` — realny produkt, jeśli dobrany; pole opisowe, dziś nie czyta go żadne
  narzędzie.

| Kategoria | Rodzaje |
|---|---|
| siedzisko | krzesło, hoker, fotel, fotel biurowy, fotel rozkładany, pufa, stołek, ławka |
| stol | stół, biurko, toaletka |
| stolik | stolik kawowy, stolik |
| lozko | łóżko |
| sofa | sofa, narożnik, kanapa |
| zabudowa_niska | ciąg kuchenny, wyspa, komoda, szafka RTV, szafka nocna, szafka, szafka z umywalką |
| zabudowa_wysoka | szafa, szafa w zabudowie, regał, witryna, słupek, słupek lodówki, zabudowa |
| wiszaca | szafka wisząca, półka, front wiszący, blenda |
| sanitariat | toaleta, umywalka, bidet, wanna |
| prysznic | prysznic |
| urzadzenie | lodówka, pralka, pralko-suszarka, zmywarka, zamrażarka, piekarnik |
| murek, szklo, lustro | murek, drzwi szklane, lustro |

Kategoria decyduje o rysunku, bryle w planerze i kontrolach (np. siedzisko może wejść pod stół).
Rodzaj może mieć dopisek: „szafka wisząca górna” trafia do kategorii rodzaju „szafka wisząca”
(liczy się najdłuższy pasujący początek). Rodzaj spoza tabeli to bryła ogólna (`inne`).

## Instalacje

**`elektryka`** — `{id, pomieszczenie, typ, xy, h?, wariant?, krotnosc?, ip?, obwod?, wyjatek?, opis?}`
- `typ`: `gniazdo` | `łącznik` | `punkt świetlny` | `kinkiet` | `wypust` | `rozdzielnica` | `zasilanie` | `rezerwa`.
- `wariant` doprecyzowuje (np. `nadblatowe`, `AGD`, `zwis`, `LED pod szafkami`, `3F płyta indukcyjna`,
  `klimatyzacja`); `krotnosc` — gniazda wielokrotne; `ip` — np. 44.
- `h` — wysokość osi od podłogi wykończonej.
- `xy` leży na licu ściany (gniazda, łączniki, kinkiety) albo w polu pomieszczenia (punkty sufitowe).
- `wyjatek` — uzasadnienie, gdy punkt świadomie leży poza swoim pomieszczeniem (np. łącznik światła łazienki
  w holu). Bez tego pola `lokal/punkty.py` zgłasza błąd.

**`wod_kan`** — `{punkty: [{id, medium, typ, pomieszczenie, xy | linia, h?, opis?}], trasy: [{id, od, polilinia, opis?}]}`
- `medium`: `kanalizacja` | `woda zimna` | `woda ciepła`. Każdy przybór ma osobne podejścia dla każdego medium.
- `linia` zamiast `xy` dla odpływów liniowych.
- `trasy` (przebieg rur): opisane i walidowane; arkusze branżowe — w planach.

**`klimatyzacja`** — `{jednostki: [{id, pomieszczenie, box, wys}], trasy: [{id, od, polilinia}], przekucia: [{id, xy, sciana}]}`
Opisana i walidowana; arkusze branżowe — w planach.

**`sufity`** — `{strefy: [{pomieszczenie, h, plyta}], klapy: [{id, xy, wymiar}], kratki: [{id, xy}]}`
Opisane i walidowane; arkusze branżowe — w planach.

**`klady`** — `{id, pomieszczenie, sciana, tytul?, strona?}` — kład lica ściany `sciana` (albo szachtu o tym id)
widziany z wnętrza pomieszczenia.
`id` jest kodem arkusza (np. `K-01`). Oś, punkt zerowy (lewy koniec lica patrząc na ścianę) i kierunek liczy
`rysunki/klady.py`. `strona` (N/E/S/W) wybiera lico, gdy pomieszczenie dotyka tej samej ściany z kilku stron
(np. narożnik) — to strona ściany, po której leży lico, nie strona świata.

## Wykończenie (opcjonalne)

Sekcja `wykonczenie` oraz pola `sciany_kolor` i `kolor` służą tylko podglądowi: kolorom w planerze 3D, makiecie GLB
i izometrii, nazwie koloru ścian na karcie pomieszczenia i pasom okładzin na kładach. Model, walidacja i rysunki
działają bez nich. Czego model nie koloruje, narzędzia pokazują w barwach domyślnych: neutralnych albo zależnych od
kategorii mebla i rodzaju podłogi.

**`wykonczenie.tokeny`** — `{nazwa: {hex, opis?}}` — nazwane kolory. W polach `kolor`, `sciany_kolor`, `sufit`,
`token` i w opcjach wariantów można wpisać nazwę tokenu albo wprost `#RRGGBB`. `opis` trafia do legendy izometrii.

**`wykonczenie.sufit`** — kolor sufitów (makieta GLB z `--sufit`, planer); domyślnie biel.

**`wykonczenie.okladziny`** — `{id, pomieszczenie, odcinek: [[x, y], [x, y]], z: [z0, z1], token, wzor?}`
- Pas na licu ściany od strony pomieszczenia (fartuch kuchenny, płytki w strefie prysznica).
- `wzor`: `płytki` | `gładka` (planer dobiera teksturę).

**`wykonczenie.warianty`** — `{id, nazwa, cel: [...], opcje: [{nazwa, token}], domyslna}`
- `cel`: `{element: id}` | `{pomieszczenie: nr, sciany: true}` | `{okladzina: id}`.
- Wariant nadpisuje kolor celu. Planer pokazuje warianty jako przełączniki, a `rysunki/glb.py` i
  `rysunki/izometria.py` przyjmują wybór `--wybory V1=1,V2=0`.

## Dwa stany

Stan istniejący i projektowany to dwa pliki w tym samym schemacie (`istniejacy.json`, `projekt.json`).
Ściany, które się nie zmieniają, mają te same ID. `rysunki/wyburzenia.py istniejacy.json projekt.json` liczy
różnicę brył ścian: rozbiórki i nowe ściany. Każdy stan musi mieć własne `meta.projekt.id` — ten sam id w obu
plikach nadpisuje sobie nawzajem pliki wynikowe (id jest ich przedrostkiem) i planer może wtedy serwować
nieaktualne dane drugiego stanu; plan wyburzeń zapisuje się pod id wziętym z pliku projektu (`projekt.json`).

## Źródła i dokładność

Rekord może wskazać materiał, z którego pochodzi (`zrodlo`), i dokładność w cm (`dokladnosc_cm`). Wymiary
krawędzi leżących na ścianach z niewiążącego źródła albo z dokładnością gorszą niż 2 cm rzut opisuje jako
„≈ 412”. `lokal/zalozenia.py` zbiera je do sprawdzenia pomiarem z natury.
