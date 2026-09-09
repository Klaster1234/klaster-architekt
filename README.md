# klaster-architekt

Narzędzia do pracy z rzutami i fotografiami budynków: wyciąganie wymiarów z
rysunków PDF, mierzenie wysokości ze zdjęć, budowa bryły 3D i sterowanie
FreeCAD-em oraz Blenderem bez klikania.

Powstało przy adaptacji lokalu przy ul. o. Jana Siemińskiego 22 w Gliwicach
(dawna Restauracja Ormiańska) na hub konferencyjny klastra.

## Zasada

Rysunek daje wymiary, fotografia daje rzeczywistość. Nie odwrotnie. Z rzutu
bierzemy geometrię i skalę, ze zdjęć to, co naprawdę stoi na miejscu i jakie ma
wysokości, bo rzut wysokości nie ma.

## Narzędzia

| Skrypt | Co robi |
|---|---|
| `narzedzia/skala.py` | Znajduje podziałkę liniową w PDF i zwraca punkty na metr |
| `narzedzia/pdf_do_dxf.py` | Wektorowy rzut PDF na warstwowy DXF w milimetrach, kolor kreski na warstwę |
| `narzedzia/rzut_arkusz.py` | Arkusz rzutu w skali 1:100 z podziałką, kreska oryginalna |
| `narzedzia/wykryj_wat.py` | Wskazuje zdjęcia, na których wątek ceglany nadaje się na linijkę |
| `narzedzia/linijka_ceglana.py` | Mierzy wysokości ze zdjęcia, biorąc warstwę cegły 7,5 cm za moduł |
| `narzedzia/sciany_z_rzutu.py` | Paruje równoległe linie rzutu i wylicza grubości ścian |
| `narzedzia/bryla_blender.py` | Buduje bryłę w Blenderze z par ścian i słupów |
| `narzedzia/freecad_rpc.py` | Steruje FreeCAD-em przez XML-RPC wtyczki FreeCADMCP |

## Kolejność pracy

```bash
python narzedzia/skala.py rzut.pdf
python narzedzia/pdf_do_dxf.py rzut.pdf rysunek.dxf --skala 30.768 --x0 272.64 --y1 2241.38
python narzedzia/wykryj_wat.py foto/
python narzedzia/linijka_ceglana.py foto/sciana.jpg --pas 3000 120 1400 2000 --linijka 3060
python narzedzia/sciany_z_rzutu.py odcinki.json pary.json --ymin 43
blender -b --python narzedzia/bryla_blender.py -- pary.json slupy.json 3.50 model.blend
python narzedzia/freecad_rpc.py --dxf rysunek.dxf --doc Projekt --zapisz model.FCStd
```

## Czego te narzędzia nie zrobią

Nie zrobią wizualizacji fotorealistycznej. Naklejanie wycinków ze zdjęć na
prostopadłościany daje smugi i powtórzenia, sprawdzone i odrzucone. Do wyglądu
służy edycja samych fotografii, do wymiarów i układu ten zestaw.

Linijka ceglana działa tylko na płaszczyźnie, na której ją dopasowano, i tylko
tam, gdzie wątek mieści się w kadrze. Wierzchu wysokiego muru zwykle w kadrze
nie ma.

## Wymagania

Python z `pymupdf`, `numpy`, `opencv-python`, `scipy`, `pillow`.
Opcjonalnie Blender 5.x i FreeCAD 1.1 z dodatkiem FreeCADMCP.
