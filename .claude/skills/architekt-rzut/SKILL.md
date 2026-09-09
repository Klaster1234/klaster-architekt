---
name: architekt-rzut
description: >
  Praca z rzutami budynków i zdjęciami z wizji lokalnej: wyciąganie wymiarów z PDF,
  zamiana rzutu na DXF, mierzenie wysokości ze zdjęć po wątku ceglanym, budowa bryły
  w Blenderze i modelu w FreeCAD. Użyj gdy pada: rzut, inwentaryzacja, wymiary z rysunku,
  zmierz ze zdjęcia, przerób PDF na CAD, DXF, zrób model lokalu, adaptacja lokalu,
  ile ma wysokości, skala rysunku, wizja lokalna.
---

# Rzuty i wizje lokalne

## Zasada, od której się nie odchodzi

**Rysunek daje wymiary, fotografia daje rzeczywistość.** Z rzutu bierzesz geometrię,
skalę i grubości. Ze zdjęć bierzesz to, co naprawdę stoi na miejscu, i wysokości,
bo rzut ich nie ma.

Najczęstszy błąd: przeniesienie z rzutu jego **treści** (rozstawienie mebli, strefy
parasoli, projektowana zabudowa) i podanie tego jako stanu istniejącego. Rzut
projektowy pokazuje zamiar projektanta, nie to, co stoi.

## Kolejność

1. **Skala.** `narzedzia/skala.py rzut.pdf` znajduje podziałkę liniową. Potwierdź
   opisem przy podziałce, bo segment może znaczyć 1 m albo 5 m. Sprawdź wynik na
   czymś znanym: brama w kamienicy ma 2,8-3,5 m, słup konstrukcyjny 0,4-0,8 m,
   stopień schodów 0,28-0,30 m.
2. **DXF.** `pdf_do_dxf.py` przenosi całą kreskę na warstwy według koloru. Nie
   wycinaj z rysunku nic na tym etapie; wyłączanie warstw to sprawa odbiorcy.
3. **Wysokości ze zdjęć.** `wykryj_wat.py` wskaże kadry z czytelnym wątkiem,
   `linijka_ceglana.py` dopasuje odwzorowanie rzutowe wzdłuż pionu. Warstwa cegła
   plus spoina to 7,5 cm. Błąd dopasowania powyżej 5 px oznacza, że pas trafił na
   coś, co nie jest murem.
4. **Grubości ścian.** `sciany_z_rzutu.py` paruje lica. Wyniki układają się w wątki
   0,12 / 0,25 / 0,38 / 0,51 / 0,64 m. Jeśli nie, skala jest zła.
5. **Bryła i CAD.** `bryla_blender.py` i `freecad_rpc.py`.

## Czego nie robić

Nie rób wizualizacji fotorealistycznej z tekstur wyciętych ze zdjęć naklejanych na
prostopadłościany. Wychodzą smugi i powtórzony ten sam fragment. Model bryłowy ma
być białą makietą; realizm bierze się z edycji samych fotografii.

Nie zgaduj wysokości murów, jeśli wierzchu nie ma w kadrze. Zapytaj albo poproś o
zdjęcia aparatem w górę spod przeciwległej ściany i **opisz w modelu, co jest
pomiarem, a co założeniem**.

## Nazewnictwo

Obiekty w modelu nazywaj tak, jak nazywa je rysunek: numer i nazwa pomieszczenia
z rzutu, nie `Cube.001`. Model ma wiedzieć, co jest czym.
