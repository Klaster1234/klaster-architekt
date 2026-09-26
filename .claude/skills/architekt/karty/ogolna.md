# Karta: ogólna

Każdy temat spoza kart wnętrza, ogrodu i budynku: taras, garaż, wiata, altana, ogrodzenie,
basen, murek, schody zewnętrzne i podobne. Model: `meta.rodzaj: "inne"` i obiekty ogólne
(skill `model-zamierzenia`). Karta opisuje też ustalanie trybu (pozwolenie, zgłoszenie, bez
formalności), wspólne dla wszystkich tematów. Zawiera wiedzę techniczną i prawną, bez zaleceń
stylu.

## Rozpoznanie

**Co zebrać**
- Miejsce: działka, granice, teren, dojście i dojazd, istniejące obiekty i drzewa, uzbrojenie.
- Wymiary, od których zależy tryb: powierzchnia zabudowy, wysokość, pojemność, liczba takich
  obiektów na działce; przeznaczenie obiektu.
- Plan miejscowy albo jego brak, uchwała gminy o małej architekturze i ogrodzeniach, ochrona
  zabytków i przyrody.
- Sąsiedzi: odległość od granicy, okna i budynki przy granicy, drzewa, spływ wody.

**Inspiracje kolorystyki i układu** — poproś inwestora o zdjęcia, linki, tablice, szkice i
miejsca, które zna, a także o to, czego nie chce. Pliki zapisz w `zrodla/inspiracje/`, obrazy
obejrzyj (Read) i opisz słowami; w `PROJEKT.md` zanotuj, skąd są, co się powtarza, co inwestor
odrzuca i jakie wnioski wynikają dla koncepcji. Bez inspiracji pytasz, nie proponujesz stylu.

**Pytania do inwestora**
- Do czego obiekt ma służyć, kto i jak często z niego korzysta, co w nim stoi albo się dzieje.
- Gdzie inwestor go widzi i dlaczego; co nie może się zmienić.
- Ograniczenia: budżet, termin, wykonanie własne czy przez firmę.
- Jakie materiały i jakie światło mu odpowiadają, czego nie chce.

## Uwarunkowania

Akty, na które powołuje się karta:
- **Prawo budowlane** — ustawa z dnia 7 lipca 1994 r. – Prawo budowlane (t.j. Dz. U. z 2026 r.
  poz. 524 ze zm.).
- **WT** — rozporządzenie Ministra Infrastruktury z dnia 12 kwietnia 2002 r. w sprawie warunków
  technicznych, jakim powinny odpowiadać budynki i ich usytuowanie (t.j. Dz. U. z 2022 r. poz.
  1225 ze zm.); obowiązywało do 19.09.2026, bo art. 66 ustawy z dnia 19 lipca 2019 r. o
  zapewnianiu dostępności osobom ze szczególnymi potrzebami (t.j. Dz. U. z 2024 r. poz. 1411)
  utrzymał dotychczasowe rozporządzenia najdłużej przez 84 miesiące od jej wejścia w życie, a datę
  podaje Prawo budowlane art. 102a ust. 1 (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst). ISAP podaje uchylenie z dniem 21.09.2026, a Prawo budowlane w art. 102a mówi o
  przepisach obowiązujących do 19.09.2026. Nowego rozporządzenia nie ogłoszono do 26.09.2026 —
  zastosowanie przejściowe niżej, w punkcie o warunkach technicznych.
- **Ustawa o planowaniu** — ustawa z dnia 27 marca 2003 r. o planowaniu i zagospodarowaniu
  przestrzennym (t.j. Dz. U. z 2026 r. poz. 538 ze zm.).
- **Ustawa zmieniająca z 2023 r.** — ustawa z dnia 7 lipca 2023 r. o zmianie ustawy o planowaniu
  i zagospodarowaniu przestrzennym oraz niektórych innych ustaw (Dz. U. z 2023 r. poz. 1688 ze zm.).
- **Kodeks cywilny** — ustawa z dnia 23 kwietnia 1964 r. – Kodeks cywilny (t.j. Dz. U. z 2026 r.
  poz. 795).

**Jak ustalić tryb**

1. Nazwij roboty: budowa (także odbudowa, rozbudowa, nadbudowa), przebudowa, remont, montaż,
   rozbiórka, zmiana sposobu użytkowania.
2. Poszukaj obiektu albo robót w Prawie budowlanym art. 29: ust. 1 i 3 — zgłoszenie, ust. 2 i
   4 — bez pozwolenia i bez zgłoszenia; rozbiórki w art. 31: ust. 1 — zgłoszenie, ust. 1a — bez
   pozwolenia i bez zgłoszenia (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst).
   Progi (powierzchnia, wysokość, pojemność, liczba na działce) porównaj z modelem
   (`rysunki/zestawienie.py` podaje pola i długości).
3. Sprawdź wyłączenia z art. 29 ust. 5a–7 (odstępstwo od przepisów, ocena oddziaływania na
   środowisko, zabytki), a przy rozbiórce z art. 31 ust. 1b (zabytki) (stan na 26.09.2026 — przed
   powołaniem sprawdź aktualny tekst).
4. Budowa i roboty, których nie ma na listach art. 29, wymagają pozwolenia na budowę (art. 28
   ust. 1), a rozbiórka spoza art. 31 — pozwolenia na rozbiórkę (art. 30b ust. 1) (stan na
   26.09.2026 — przed powołaniem sprawdź aktualny tekst).
5. Bez planu miejscowego sprawdź, czy potrzebna jest decyzja o warunkach zabudowy (punkty o
   ustawie o planowaniu niżej).
6. Zapisz wynik w `PROJEKT.md` („Decyzje” albo „Otwarte sprawy”) z jednostką przepisu.

- Prawo budowlane art. 28 ust. 1 — roboty budowlane można rozpocząć tylko na podstawie
  pozwolenia na budowę, z wyjątkami z art. 29–31. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Prawo budowlane art. 29 ust. 1 i 3 — wymienione tam budowy i roboty nie wymagają pozwolenia na
  budowę, ale wymagają zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 i 4 — wymienione tam budowy i roboty nie wymagają ani
  pozwolenia na budowę, ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 29 ust. 5 — zamiast zgłoszenia budowy z ust. 1 albo robót z ust. 3
  inwestor może wystąpić o pozwolenie na budowę. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Prawo budowlane art. 29 ust. 5a — roboty z ust. 1–4 wymagające zgody na odstępstwo od przepisów
  techniczno-budowlanych (art. 9) wymagają wniosku o pozwolenie na budowę. (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 6 — przedsięwzięcia wymagające oceny oddziaływania na środowisko
  albo na obszar Natura 2000 wymagają pozwolenia na budowę (z wyjątkami z ust. 1 pkt 17–19).
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 7 — roboty przy obiekcie wpisanym do rejestru zabytków wymagają
  pozwolenia na budowę, a na obszarze wpisanym do rejestru — zgłoszenia, z dokumentem
  wojewódzkiego konserwatora zabytków. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 30 ust. 1b i 2 — zgłoszenia dokonuje się w organie administracji
  architektoniczno-budowlanej i określa w nim rodzaj, zakres, miejsce i sposób wykonywania robót
  oraz termin ich rozpoczęcia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 30 ust. 5 — zgłoszenia dokonuje się przed rozpoczęciem robót, organ może
  w 21 dni wnieść sprzeciw, a bez sprzeciwu można przystąpić do robót (dom z art. 29 ust. 1
  pkt 1a — po doręczeniu zgłoszenia, art. 30 ust. 5j–5k). (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Prawo budowlane art. 30 ust. 7 — organ może nałożyć obowiązek uzyskania pozwolenia na obiekt
  albo roboty ze zgłoszenia, gdy mogą naruszać plan miejscowy albo decyzję o warunkach zabudowy
  lub spowodować zagrożenie bezpieczeństwa ludzi lub mienia, pogorszenie stanu środowiska albo
  stanu zachowania zabytków, pogorszenie warunków zdrowotno-sanitarnych albo ograniczenia lub
  uciążliwości dla terenów sąsiednich. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 71 ust. 2 — zmiana sposobu użytkowania obiektu albo jego części wymaga
  zgłoszenia z określeniem dotychczasowego i zamierzonego sposobu użytkowania. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 30b ust. 1 — rozbiórkę można rozpocząć po uzyskaniu decyzji o pozwoleniu
  na rozbiórkę, z wyjątkami z art. 31. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 31 ust. 1 pkt 1 — rozbiórka budynków i budowli o wysokości poniżej 8 m,
  oddalonych od granicy działki co najmniej o połowę swojej wysokości, nie wymaga pozwolenia na
  rozbiórkę, ale wymaga zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 31 ust. 1a pkt 1 — rozbiórka obiektów i urządzeń budowlanych, na budowę
  których nie jest wymagane pozwolenie na budowę, nie wymaga pozwolenia na rozbiórkę ani
  zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 31 ust. 1b — zwolnień z ust. 1 i ust. 1a pkt 2 nie stosuje się do
  rozbiórki obiektów i urządzeń budowlanych wpisanych do rejestru zabytków albo objętych ochroną
  konserwatorską. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o planowaniu art. 59 ust. 1 i 2a — bez planu miejscowego zmiana zagospodarowania terenu
  wymaga decyzji o warunkach zabudowy, ale nie dla obiektów z art. 29 ust. 2 Prawa budowlanego i
  części obiektów z art. 29 ust. 1 (z wyjątkami z ust. 2b). (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)

**Częste obiekty** (szczegóły i pozostałe obiekty ogrodu w `ogrod.md`)
- Prawo budowlane art. 29 ust. 2 pkt 31 i ust. 1 pkt 22 — przydomowy taras naziemny do 35 m²
  (zadaszony — z dachem do 35 m²) nie wymaga pozwolenia ani zgłoszenia, a większy (zadaszony — z
  dachem do 50 m²) wymaga zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 29 ust. 1 pkt 14 — wolno stojące parterowe budynki gospodarcze oraz wolno
  stojące garaże i wiaty, o powierzchni zabudowy do 35 m² (najwyżej dwa takie obiekty na każde
  500 m² działki), wymagają zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 29 ust. 2 pkt 2 — wiata o powierzchni zabudowy do 50 m² na działce z
  budynkiem mieszkalnym albo przeznaczonej pod budownictwo mieszkaniowe (najwyżej dwie na każde
  1000 m² działki) nie wymaga pozwolenia ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 3 — wolno stojąca altana o powierzchni zabudowy do 35 m²
  (najwyżej dwie na każde 500 m² działki) nie wymaga pozwolenia ani zgłoszenia. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 20 i ust. 1 pkt 21 — ogrodzenie o wysokości do 2,20 m nie
  wymaga pozwolenia ani zgłoszenia, a wyższe wymaga zgłoszenia. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 13 — baseny i oczka wodne do 50 m² przy budynkach
  mieszkalnych jednorodzinnych i budynkach rekreacji indywidualnej nie wymagają pozwolenia ani
  zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 38 — konstrukcje oporowe o wysokości do 0,80 m nie wymagają
  pozwolenia ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 7 — stanowiska postojowe dla samochodów osobowych do 10
  stanowisk (poza obszarem Natura 2000) nie wymagają pozwolenia ani zgłoszenia. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 4 pkt 3 lit. c — instalowanie pomp ciepła, wolno stojących
  kolektorów słonecznych i urządzeń fotowoltaicznych do 150 kW nie wymaga pozwolenia ani
  zgłoszenia, a przy urządzeniach fotowoltaicznych powyżej 6,5 kW projekt uzgadnia się z
  rzeczoznawcą do spraw zabezpieczeń przeciwpożarowych i zawiadamia się Państwową Straż Pożarną
  o zakończeniu instalowania (z planem urządzenia dla ekip ratowniczych). (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)

**Warunki techniczne**
- Prawo budowlane art. 102a ust. 1 i art. 102b — przez 18 miesięcy od 20.09.2026 projekt do
  pozwolenia na budowę albo zgłoszenia budowy może być sporządzony według warunków
  technicznych obowiązujących do 19.09.2026 (po oświadczeniu inwestora), a do budowy z art. 29
  ust. 2 i robót z art. 29 ust. 4 inwestor może je stosować. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 102a–102b i art. 29 ust. 3 — przepisy epizodyczne nie wymieniają wprost
  robót wymagających zgłoszenia z art. 29 ust. 3, więc według jakich warunków technicznych
  przygotować dla nich dokumentację, ustal w organie administracji architektoniczno-budowlanej.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- WT § 41 ust. 2 i § 42 ust. 1 — na ogrodzeniu poniżej 1,8 m nie wolno umieszczać ostro
  zakończonych elementów, drutu kolczastego ani tłuczonego szkła, a bramy i furtki nie mogą
  otwierać się na zewnątrz działki. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)

**Plan miejscowy**
- Ustawa o planowaniu art. 4 ust. 1–2 — przeznaczenie terenu, sposób zagospodarowania i warunki
  zabudowy ustala plan miejscowy, a gdy go nie ma, sposób zagospodarowania i warunki zabudowy
  (bez przeznaczenia terenu) określa decyzja o warunkach zabudowy, dla inwestycji celu
  publicznego — decyzja o lokalizacji inwestycji celu publicznego. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Ustawa o planowaniu art. 15 ust. 2 pkt 6 — plan miejscowy określa obowiązkowo m.in. minimalny
  udział powierzchni biologicznie czynnej, maksymalny udział powierzchni zabudowy, maksymalną
  wysokość zabudowy, linie zabudowy i gabaryty obiektów. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Ustawa o planowaniu art. 30 ust. 1 — każdy ma prawo wglądu do planu ogólnego i planu
  miejscowego oraz otrzymania z nich wypisów i wyrysów. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Ustawa o planowaniu art. 37a ust. 1 i 3 — rada gminy może uchwałą ustalić zasady sytuowania
  obiektów małej architektury i ogrodzeń, ich gabaryty, standardy i materiały, a także zakaz
  sytuowania ogrodzeń. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 30 ust. 6 pkt 2 — organ wnosi sprzeciw, gdy roboty ze zgłoszenia naruszają
  plan miejscowy, decyzję o warunkach zabudowy, inne akty prawa miejscowego albo inne przepisy.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa zmieniająca z 2023 r. art. 59 ust. 3 — decyzję o warunkach zabudowy na wniosek złożony od
  1 września 2026 r. można wydać tylko wtedy, gdy w gminie wszedł w życie plan ogólny. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa zmieniająca z 2023 r. art. 67 ust. 1 — dotychczasowe plany miejscowe zachowują moc do
  wejścia w życie nowych planów na tym obszarze. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)

**Sąsiedzi**
- Prawo budowlane art. 28 ust. 2 — stronami postępowania o pozwolenie na budowę są inwestor oraz
  właściciele, użytkownicy wieczyści lub zarządcy nieruchomości w obszarze oddziaływania obiektu.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 3 pkt 20 — obszar oddziaływania obiektu to teren w jego otoczeniu, na
  którym przepisy odrębne wprowadzają związane z nim ograniczenia w zabudowie. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 5 ust. 1 pkt 9 — obiekt projektuje się i buduje z poszanowaniem
  uzasadnionych interesów osób trzecich w obszarze oddziaływania, w tym dostępu do drogi
  publicznej. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 30a — o zgłoszeniu m.in. budowy domu jednorodzinnego i o sprzeciwie albo
  jego braku organ informuje w Biuletynie Informacji Publicznej przez 30–60 dni. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- WT § 12 ust. 1 — budynek sytuuje się co najmniej 4 m od granicy działki ścianą z oknami lub
  drzwiami i 3 m ścianą bez okien i drzwi (budynek mieszkalny wielorodzinny o wysokości ponad 4
  kondygnacji nadziemnych — 5 m), jeśli inne przepisy nie stanowią inaczej (wyjątki w
  `budynek.md`). (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Kodeks cywilny art. 144 — właściciel powinien powstrzymywać się od działań zakłócających
  korzystanie z nieruchomości sąsiednich ponad przeciętną miarę. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Kodeks cywilny art. 152–153 — sąsiedzi współdziałają przy rozgraniczeniu i utrzymaniu znaków
  granicznych, a gdy granica jest sporna i nie można stwierdzić stanu prawnego, ustala się ją
  według ostatniego spokojnego stanu posiadania, a gdy i tego nie można stwierdzić, a
  rozgraniczenie nie skończyło się ugodą — ustala ją sąd. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)

## Model

- `meta.rodzaj: "inne"`; `miejsce` z działką i terenem, gdy obiekt stoi na działce; legenda
  tylko z kategorii, których temat potrzebuje. Przykład minimalny w `zamierzenie/SCHEMAT.md`.
- Kształty: wiata, garaż, altana — bryła (`z` albo `wys`) i dach jako osobny obiekt; taras —
  bryła albo powierzchnia; ogrodzenie i murek — linia z `wys`; basen i oczko — powierzchnia
  z klasą bilansu dobraną do definicji z planu (ustawa o planowaniu art. 2 pkt 28 wlicza
  zbiorniki wodne do powierzchni biologicznie czynnej, a baseny rekreacyjne nie; stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst).
- Istniejące obiekty i drzewa w pobliżu opisz w stanie istniejącym, żeby różnica stanów i
  odległości były kompletne. Kolory legendy domyślnie neutralne.

## Koncepcja

Warianty pokazują położenie obiektu na działce, jego wymiary względem progów trybu (np.
powierzchnia zabudowy, wysokość), relację z budynkiem, granicą i drzewami, cienie (P-03) i
wpływ na bilans powierzchni (Z-02). Przy każdym wariancie zapisz ustalony tryb.

## Projekt roboczy

- Plan P-01 z wymiarami i odległościami od granic, przekrój albo elewacja P-11, cienie P-03
  (gdy obiekt ma bryłę), zestawienie Z-01, bilans Z-02 (gdy jest działka), DXF, makieta GLB.
- `rysunki/wszystko.py` na projekcie z `--istniejacy` robi komplet.

## Do przekazania

- Osoba z uprawnieniami: projekt, gdy tryb wymaga pozwolenia albo zgłoszenia z projektem.
- Konstruktor: konstrukcja wiat, garaży, tarasów nadziemnych, murków oporowych i schodów.
- Projektanci instalacji z uprawnieniami: zasilanie, oświetlenie, odwodnienie, instalacje basenu.
- Geodeta: mapa do celów projektowych, wytyczenie, rozgraniczenie przy spornej granicy.
