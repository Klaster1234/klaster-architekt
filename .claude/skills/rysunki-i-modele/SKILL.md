---
name: rysunki-i-modele
description: >
  Praca z rysunkami budowlanymi i zdjęciami z wizji lokalnej przy pomocy Blendera
  i FreeCAD-a: skala rysunku, PDF na DXF, mierzenie wysokości ze zdjęć po wątku
  ceglanym, grubości ścian, bryła 3D, arkusze w skali, a także odczyt przestrzeni
  ze źródeł nieprecyzyjnych (geoportal, zdjęcia, skany, DWG). Użyj gdy pada: rzut,
  inwentaryzacja, wymiary z rysunku, zmierz ze zdjęcia, przerób PDF na CAD, DXF,
  zrób model lokalu, adaptacja lokalu, ile ma wysokości, skala rysunku, wizja
  lokalna, Blender, FreeCAD, makieta budynku, geoportal, ortofotomapa, działka,
  obrys budynku, zdjęcie elewacji, Google Maps, Street View, skan LiDAR, skan
  rysunku, karta sprzedażowa, DWG, północ na rzucie.
---

# Rysunki i modele budynków

## Zasada, od której się nie odchodzi

**Rysunek daje wymiary, fotografia daje rzeczywistość.**

Z rzutu bierzesz geometrię, skalę i grubości. Ze zdjęć bierzesz to, co naprawdę
stoi na miejscu, i wysokości, bo rzut ich nie ma.

Najczęstszy błąd, popełniony i naprawiony: przeniesienie z rzutu jego **treści**,
czyli rozstawienia mebli, stref parasoli i projektowanej zabudowy, i podanie tego
jako stanu istniejącego. Rzut projektowy pokazuje zamiar projektanta, nie to, co
stoi na miejscu. Do modelu wchodzi z rysunku wyłącznie geometria.

## Kolejność

1. **Skala.** `narzedzia/skala.py rzut.pdf` znajduje podziałkę liniową. Potwierdź
   opisem przy podziałce, bo segment może znaczyć 1 m albo 5 m. Wynik sprawdź na
   czymś, czego wymiar znasz z góry: brama w kamienicy ma 2,8 do 3,5 m, słup
   konstrukcyjny 0,4 do 0,8 m, stopień schodów 0,28 do 0,30 m, drzwi 0,80 do 0,90 m.
   Jeśli te liczby wychodzą absurdalne, skala jest zła i nie idź dalej.
2. **DXF.** `pdf_do_dxf.py` przenosi całą kreskę na warstwy według koloru. Na tym
   etapie nie wycinaj z rysunku niczego; wyłączanie warstw to sprawa odbiorcy.
3. **Wysokości ze zdjęć.** `wykryj_wat.py` wskaże kadry z czytelnym wątkiem,
   `linijka_ceglana.py` dopasuje odwzorowanie rzutowe wzdłuż pionu. Warstwa cegła
   plus spoina to 7,5 cm i to jedyne założenie. Błąd dopasowania powyżej 5 px
   oznacza, że pas trafił na coś, co nie jest murem.
4. **Grubości ścian.** `sciany_z_rzutu.py` paruje lica. Wyniki muszą układać się
   w wątki 0,12 / 0,25 / 0,38 / 0,51 / 0,64 m. Jeśli nie, skala jest zła.
5. **Bryła i CAD.** `bryla_blender.py` w tle, `freecad_rpc.py` do rysunku.

## Podział ról

**Blender** liczy bryłę, cień i światło. **FreeCAD** trzyma rysunek, wymiar i
warstwy. Nie próbuj robić rysunku w Blenderze ani nasłonecznienia we FreeCAD.

Serwer w Blenderze nie wstaje sam, odpalaj przez `Blender z MCP.bat`. FreeCAD
startuje RPC sam, jeśli w `freecad_mcp_settings.json` jest `auto_start_rpc: true`.
Gdy konektor MCP nie wstanie przy starcie sesji, FreeCAD-em nadal sterujesz przez
`freecad_rpc.py`, bo to zwykły XML-RPC na porcie 9875.

## Czego nie robić

Nie rób wizualizacji fotorealistycznej z tekstur wyciętych ze zdjęć naklejanych na
prostopadłościany. Wychodzą smugi i powtórzony ten sam fragment muru. Model bryłowy
ma być białą makietą; realizm bierze się z edycji samych fotografii.

Nie zgaduj wysokości, której nie ma w kadrze. Zapytaj albo poproś o zdjęcia
aparatem w górę spod przeciwległej ściany, a w modelu **opisz, co jest pomiarem,
a co założeniem**.

Nie licz na jedno źródło. Inwentaryzacja i rzut projektowy z różnych lat potrafią
się nie zgadzać. Ustal z zamawiającym, które źródło jest wiążące, zanim zbudujesz
cokolwiek.

## Nazewnictwo

Obiekty w modelu nazywaj tak, jak nazywa je rysunek: numer i nazwa pomieszczenia,
nie `Cube.001`. Model ma wiedzieć, co jest czym, bo inaczej nie da się go potem
czytać ani filtrować.

## Źródła nieprecyzyjne

Gdy rzutu technicznego nie ma albo jest nieaktualny, przestrzeń składa się z
geoportalu, zdjęć, skanów i starych rysunków. Każde źródło się przyda, jeśli
wiesz, ile jest warte.

**Każdy wymiar ma źródło i dokładność.** Źródła wpisz do `meta.zrodla` modelu
(rodzaj, data, `dokladnosc_cm`, `wiazace`), a rekordy wskaż polem `zrodlo`. Rzut
pokaże wymiary ze źródeł niewiążących albo mniej dokładnych niż 2 cm jako „≈”,
a `lokal/zalozenia.py` zbierze je do sprawdzenia pomiarem.

### Hierarchia i dokładność

| Źródło | Dokładność orientacyjna | Do czego |
|---|---|---|
| Projekt w DWG, pomiar dalmierzem laserowym | ok. 1 cm | geometria, grubości ścian |
| Wektorowy PDF rzutu | jak rysunek źródłowy, gdy skala jest potwierdzona | geometria |
| Skan LiDAR telefonem | 2–5 cm | położenie ścian, wysokość pomieszczenia |
| Obrys budynku z EGiB | od ok. 10 cm (pomiar geodezyjny) do metrów (stara digitalizacja) | obrys, działka, sąsiedztwo |
| Ortofotomapa | 5–25 cm na piksel | orientacja, kontekst |
| Skan rysunku rastrowego, karta sprzedażowa | 1–5% wymiaru | układ, gdy nic lepszego nie ma |
| Zdjęcie z modułem (znany prostokąt, wątek ceglany) | 1–3%, tylko w płaszczyźnie modułu | elewacja, wysokości |
| Ocena na oko, Google Maps, Street View, Google Earth | brak, to ZAŁOŻENIE | orientacja we własnej analizie |

### Pułapki

- **Ortofotomapa pokazuje dach, nie ściany.** Okap przesuwa obrys o 30–80 cm.
  Obrys ścian bierz z EGiB albo z pomiaru, z ortofoto tylko orientację i kontekst.
- **Wysokie budynki na ortofoto „leżą”.** Dach jest odsunięty od podstawy, tym
  bardziej, im budynek wyższy i dalej od środka zdjęcia. Nie odrysowuj z nich
  obrysu.
- **Karta sprzedażowa bywa obrócona** (np. o 90°), ma inne liczby niż rzut
  techniczny i pokazuje aranżację przykładową. Wiąże rzut techniczny; z karty
  bierzesz najwyżej układ ścian, nigdy meble.
- **Obrys z EGiB bywa starą digitalizacją** mapy analogowej. Zanim mu zaufasz,
  porównaj go z ortofoto i z pomiarem.
- **Zdjęcie mierzy tylko płaszczyznę modułu.** Wykusz, balkon albo parapet przed
  tą płaszczyzną lub za nią wyjdzie z błędem.
- **PDF bywa przeskalowany przy druku** („dopasuj do strony”). Skalę z arkusza
  sprawdź na wymiarze opisanym na rysunku.
- **DWG ma własne jednostki i współrzędne.** Sprawdź `$INSUNITS` (4 = mm, 5 = cm,
  6 = m; przy 0 ustal jednostki z opisanego wymiaru). Współrzędne globalne przenieś
  do układu lokalnego modelu, a powiązanie zapisz w `meta.georef`.

### Wymiar tylko z kalibracji

Wymiar z obrazu istnieje dopiero po kalibracji: podziałka, wymiar opisany na
arkuszu, dwa punkty o znanej odległości, znane pole pomieszczenia albo moduł w tej
samej płaszczyźnie (cegła, płytka, znany prostokąt). Kalibruj na możliwie długim
odcinku i sprawdzaj na drugim, niezależnym.

**Liczba odczytana na oko to ZAŁOŻENIE, nie wymiar.** Zapisz ją tak w modelu
(`wys_zrodlo: "ZAŁOŻENIE …"` albo źródło z `wiazace: false`); `lokal/zalozenia.py`
zbierze ją do sprawdzenia pomiarem.

Skala wektorowego PDF z arkusza: 1 pt to 0,3528 mm na papierze, więc przy 1:50
jeden punkt to 17,64 mm w naturze.

Północ bierz z róży wiatrów albo strzałki na rysunku, a gdy jej nie ma, z kierunku
ścian w EGiB lub na ortofoto. Zapisz ją w `meta.polnoc` (azymut osi +Y i
lokalizacja): korzystają z niej strzałka N na arkuszach i słońce w planerze.

### Google Maps, Street View, Google Earth

Służą do podglądu i orientacyjnego pomiaru **wyłącznie na własny użytek
analityczny**. Wynik jest ZAŁOŻENIEM. Zrzutów nie publikuj (arkusze, opisy,
repozytoria) i nie odrysowuj z nich obrysów do modelu, bo nie pozwala na to
licencja. Obrysy bierz z otwartych danych GUGiK (`narzedzia/geoportal.py`) albo
z własnych zdjęć i pomiarów.

### Łączenie źródeł

- Z każdego źródła bierz tylko to, w czym jest najlepsze (kolumna „Do czego”).
- Rozbieżność w granicach dokładności obu źródeł rozstrzyga źródło wiążące.
  Większa oznacza błąd jednego z nich (skala, obrót, inna wersja projektu, inna
  kondygnacja): wyjaśnij ją, zanim pójdziesz dalej. Nie uśredniaj po cichu.
- **O tym, które źródło wiąże, decyduje zamawiający.** Zapisz to w `meta.zrodla`
  (`wiazace: true`) i nie zmieniaj bez jego zgody.
- Pola pomieszczeń liczone z lic porównuje z dokumentacją `lokal/waliduj.py`.
  Gdy strefa z programu CAD daje inne pole niż lica sprawdzone wymiarami, wiążą
  lica.

### Narzędzia

Każde narzędzie zapisuje DXF w mm, `<nazwa>_odcinki.json` (odcinki w metrach,
format wejścia `sciany_z_rzutu.py`) i `<nazwa>_meta.json` (źródło, data,
dokładność). `dwg_do_dxf.py` daje sam DXF z raportem.

```bash
python narzedzia/dwg_do_dxf.py rzut.dwg
python narzedzia/geoportal.py --adres "Warszawa, Plac Defilad 1" --promien 50
python narzedzia/zdjecie_prostuj.py elewacja.jpg --punkty 412,318 1630,290 1655,1702 398,1731 --wymiar 120 150
python narzedzia/raster_do_dxf.py skan_rzutu.png --dwa-punkty 120,80 980,80 --odleglosc 6.3
python narzedzia/przekroj_skanu.py skan.glb --h 1.0
python narzedzia/sciany_z_rzutu.py wyjscie/skan_odcinki.json pary.json
python lokal/z_par_scian.py pary.json --wynik sciany.json --zrodlo Z2
```

- `dwg_do_dxf.py` konwertuje przez ODA File Converter (zmienna `ODA_CONVERTER`
  albo typowa lokalizacja) i wypisuje warstwy, liczbę encji, `$INSUNITS` i zakres.
  Digitalizuj z lic ścian, encji DIMENSION i metryczek pomieszczeń; elementy
  sąsiednich lokali w kadrze pomijaj.
- `geoportal.py` (`--adres`, `--xy lon,lat` albo `--dzialka`) pobiera z usług
  GUGiK działkę, budynek i budynki w promieniu (`kontekst.json` do wklejenia w
  model; prostokąty są w osiach siatki PL-1992, więc przy modelu obróconym względem
  niej przelicz je o kąt z `meta.georef`), wycinek ortofotomapy z plikiem
  georeferencji i wysokość terenu z NMT.
  Wysokość budynku bez danych to kondygnacje × ok. 3 m jako ZAŁOŻENIE. Poza Polską
  `--osm` (dane OpenStreetMap na licencji ODbL: podaj „© OpenStreetMap
  contributors”).
- `zdjecie_prostuj.py` prostuje zdjęcie z czterech narożników znanego prostokąta
  (lewy górny, prawy górny, prawy dolny, lewy dolny; wymiar w cm), rysuje siatkę i
  mierzy odcinki podane w `--mierz`, tylko w tej płaszczyźnie.
- `raster_do_dxf.py` kalibruje skan dwoma punktami (`--dwa-punkty … --odleglosc`
  w metrach) albo znanym polem (`--pole … --m2`, kilka pól daje średnią), w razie
  potrzeby prostuje sfotografowany arkusz (`--perspektywa … --prostokat`) i wyciąga
  linie. Obróconą kartę wyrównuje do osi `--wyrownaj`.
- `przekroj_skanu.py` (OBJ, GLB, PLY) znajduje podłogę i sufit, tnie skan poziomo
  na wysokości `--h` metrów nad podłogą i podaje wysokość pomieszczenia. Przekrój
  łapie też meble, a parowanie lic robi z nich fałszywe ściany: najczystszy obrys
  daje skan pustego lokalu; inaczej zmień `--h` i przejrzyj pary przed mostem.
- **Most do modelu:** odcinki → `sciany_z_rzutu.py` (pary lic) →
  `lokal/z_par_scian.py` → ściany w osiach modelu. Most obraca układ do
  dominującego kierunku, dociąga ściany do osi, a nieprostopadłe odrzuca i wypisuje.
  Nie wie, które ściany są nośne: `nosna` i `typ` uzupełnij z rysunku. Kąt obrotu
  (`obrot_stopnie`) **nie jest wprost azymutem północy**, nawet gdy źródło zna północ
  (geoportal): `azymut_osi_Y_stopnie = zbieżność południków − obrot_stopnie` (dokładnie
  to liczy i wypisuje `narzedzia/geoportal.py`, kod ok. linii 570–620); skan telefonem
  ma układ dowolny i bez dodatkowego pomiaru kierunku północy w ogóle nie da się z niego
  wyliczyć azymutu.

## Powiązane skille

- **architekt**: prowadzenie zamierzenia etapami od tematu do projektu roboczego; odczyt
  źródeł służy mu w rozpoznaniu stanu istniejącego.
- **modul-wnetrz**: gdy odczytana geometria ma trafić do modelu lokalu
  (`lokal_istniejacy.json`, `lokal_projekt.json`), a z niego do rysunków i kontroli.
- **model-zamierzenia**: gdy działka, teren, sąsiedztwo albo obiekty mają trafić do modelu
  zamierzenia.
