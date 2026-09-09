---
name: rysunki-i-modele
description: >
  Praca z rysunkami budowlanymi i zdjęciami z wizji lokalnej przy pomocy Blendera
  i FreeCAD-a: skala rysunku, PDF na DXF, mierzenie wysokości ze zdjęć po wątku
  ceglanym, grubości ścian, bryła 3D, arkusze w skali. Użyj gdy pada: rzut,
  inwentaryzacja, wymiary z rysunku, zmierz ze zdjęcia, przerób PDF na CAD, DXF,
  zrób model lokalu, adaptacja lokalu, ile ma wysokości, skala rysunku, wizja
  lokalna, Blender, FreeCAD, makieta budynku.
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
