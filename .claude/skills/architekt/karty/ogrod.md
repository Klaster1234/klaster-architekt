# Karta: ogród

Ogród i zagospodarowanie działki przy istniejącym budynku: nawierzchnie, taras, zieleń, drzewa
do zachowania i do usunięcia, ogrodzenie, woda. Model: `meta.rodzaj: "ogrod"`, obiekty ogólne i
teren (skill `model-zamierzenia`); przykład `przyklad/ogrod/`. Karta zawiera wiedzę techniczną i
prawną, bez zaleceń stylu.

## Rozpoznanie

**Co zebrać**
- Działka: granice i numer (geoportal, EGiB; przy wątpliwościach mapa do celów projektowych),
  dojście i dojazd, furtki i bramy.
- Teren: punkty z NMT (`narzedzia/geoportal.py --teren`) albo z pomiaru; kierunek spływu wody,
  miejsca zastoisk, skarpy i murki.
- Drzewa i krzewy: gatunek, obwód pnia na wysokości 130 cm i na wysokości 5 cm (różne progi w
  przepisach niżej), średnica korony, wysokość, stan, gniazda i dziuple; skupiska krzewów z
  powierzchnią.
- Istniejące nawierzchnie, ogrodzenie (wysokość, bramy), obiekty (altany, wiaty, oczka).
- Uzbrojenie: podkład z `narzedzia/uzbrojenie.py` (informacyjny), przyłącza, studzienki,
  odwodnienie dachu (rury spustowe); przebieg sieci potwierdza mapa do celów projektowych.
- Sąsiedztwo z wysokościami (cienie), widoki, hałas; drzewa sąsiadów przy granicy.
- Plan miejscowy (przeznaczenie, udział powierzchni biologicznie czynnej, zasady dla
  ogrodzeń) i uchwała gminy o małej architekturze i ogrodzeniach.
- Nasłonecznienie: cienie budynku, drzew i sąsiedztwa (`rysunki/cienie.py`, planer).

**Inspiracje kolorystyki i układu** — poproś inwestora o zdjęcia, linki, tablice, szkice i
miejsca, które zna, a także o to, czego nie chce. Pliki zapisz w `zrodla/inspiracje/`, obrazy
obejrzyj (Read) i opisz słowami; w `PROJEKT.md` zanotuj, skąd są, co się powtarza, co inwestor
odrzuca i jakie wnioski wynikają dla koncepcji. Bez inspiracji pytasz, nie proponujesz stylu.

**Pytania do inwestora**
- Kto korzysta z ogrodu i jak (odpoczynek, zabawa, uprawy, zwierzęta, przyjęcia); o jakich
  porach dnia i roku.
- Ile czasu chce poświęcać na pielęgnację; czy podlewanie ręczne, czy instalacja.
- Co ma zostać (drzewa, nawierzchnie, rośliny), co przeszkadza.
- Prywatność od sąsiadów i ulicy, oświetlenie, miejsce na rowery, śmietniki, składowanie.
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
  zastosowanie przejściowe w pierwszym punkcie niżej.
- **Ustawa o ochronie przyrody** — ustawa z dnia 16 kwietnia 2004 r. o ochronie przyrody (t.j.
  Dz. U. z 2026 r. poz. 13 ze zm.).
- **Rozporządzenie o ochronie gatunkowej zwierząt** — rozporządzenie Ministra Środowiska z dnia
  16 grudnia 2016 r. w sprawie ochrony gatunkowej zwierząt (t.j. Dz. U. z 2022 r. poz. 2380).
- **Ustawa o planowaniu** — ustawa z dnia 27 marca 2003 r. o planowaniu i zagospodarowaniu
  przestrzennym (t.j. Dz. U. z 2026 r. poz. 538 ze zm.).
- **Ustawa zmieniająca z 2023 r.** — ustawa z dnia 7 lipca 2023 r. o zmianie ustawy o planowaniu
  i zagospodarowaniu przestrzennym oraz niektórych innych ustaw (Dz. U. z 2023 r. poz. 1688 ze zm.).
- **Prawo wodne** — ustawa z dnia 20 lipca 2017 r. – Prawo wodne (t.j. Dz. U. z 2025 r. poz. 960
  ze zm.).
- **Kodeks cywilny** — ustawa z dnia 23 kwietnia 1964 r. – Kodeks cywilny (t.j. Dz. U. z 2026 r.
  poz. 795).

**Warunki techniczne**
- Prawo budowlane art. 102a ust. 1 i art. 102b — przez 18 miesięcy od 20.09.2026 projekt do
  pozwolenia na budowę albo zgłoszenia budowy może być sporządzony według warunków
  technicznych obowiązujących do 19.09.2026 (po oświadczeniu inwestora), a do budowy z art. 29
  ust. 2 i robót z art. 29 ust. 4 inwestor może je stosować. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)

**Usuwanie drzew i krzewów**
- Ustawa o ochronie przyrody art. 83 ust. 1 i art. 83a ust. 1 — usunięcie drzewa lub krzewu
  wymaga zezwolenia wójta, burmistrza albo prezydenta miasta (na nieruchomości w rejestrze
  zabytków — wojewódzkiego konserwatora zabytków), chyba że przepis je wyłącza. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 1 pkt 3 — zezwolenia nie wymaga usunięcie drzewa,
  którego obwód pnia na wysokości 5 cm nie przekracza 80 cm (topole, wierzby, klon jesionolistny
  i srebrzysty), 65 cm (kasztanowiec zwyczajny, robinia akacjowa, platan klonolistny) albo 50 cm
  (pozostałe gatunki). (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 1 pkt 1 — zezwolenia nie wymaga usunięcie krzewów
  rosnących w skupisku o powierzchni do 25 m². (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 1 pkt 5 — zezwolenia nie wymaga usunięcie drzew i
  krzewów owocowych, poza nieruchomościami w rejestrze zabytków i terenami zieleni. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 1 pkt 3a i ust. 4 — drzewa i krzewy rosnące na
  nieruchomości stanowiącej własność osoby fizycznej, usuwane na cele niezwiązane z
  działalnością gospodarczą, nie wymagają zezwolenia, ale usunięcie drzewa o obwodzie na
  wysokości 5 cm powyżej progów z pkt 3 właściciel nieruchomości zgłasza organowi, który wydaje
  zezwolenia (art. 83a ust. 1). (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 6 i 8 — po zgłoszeniu organ w 21 dni dokonuje
  oględzin, a w 14 dni od oględzin może wnieść sprzeciw; bez sprzeciwu drzewo można usunąć.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83f ust. 13 — drzewa nieusuniętego przed upływem 6 miesięcy
  od oględzin można usunąć dopiero po ponownym zgłoszeniu. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Ustawa o ochronie przyrody art. 83b ust. 1 pkt 5 — we wniosku o zezwolenie podaje się obwód
  pnia mierzony na wysokości 130 cm. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Rozporządzenie o ochronie gatunkowej zwierząt § 6 ust. 1 pkt 7 i 8 — wobec dziko występujących
  zwierząt gatunków chronionych obowiązuje m.in. zakaz niszczenia ich siedlisk i ostoi oraz
  niszczenia, usuwania lub uszkadzania gniazd i innych schronień. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Rozporządzenie o ochronie gatunkowej zwierząt § 8 ust. 1 pkt 6 — wobec dziko występujących
  pozostałych gatunków ptaków z lp. 479 załącznika nr 1 obowiązuje m.in. zakaz niszczenia,
  usuwania lub uszkadzania gniazd. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Rozporządzenie o ochronie gatunkowej zwierząt § 9 pkt 2 — zakaz usuwania gniazd nie dotyczy
  usuwania gniazd ptasich z obiektów budowlanych lub terenów zieleni od 16 października do końca
  lutego, jeżeli wymagają tego względy bezpieczeństwa lub sanitarne. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)

**Plan miejscowy**
- Ustawa o planowaniu art. 15 ust. 2 pkt 6 — plan miejscowy określa obowiązkowo m.in. minimalny
  udział powierzchni biologicznie czynnej, maksymalny udział powierzchni zabudowy, maksymalną
  wysokość zabudowy, linie zabudowy i gabaryty obiektów. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Ustawa o planowaniu art. 2 pkt 28 — powierzchnia biologicznie czynna to teren zapewniający
  naturalną wegetację roślin i retencję wód opadowych, teren pod ciekami i zbiornikami wodnymi
  (bez basenów) oraz 50 % powierzchni tarasów i stropodachów i innych powierzchni zapewniających
  naturalną wegetację roślin, o powierzchni nie mniejszej niż 10 m². (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Ustawa zmieniająca z 2023 r. art. 67 ust. 1–2 — dotychczasowe plany miejscowe zachowują moc, a
  definicji z art. 2 pkt 27–35 ustawy o planowaniu nie stosuje się do nich (poza częścią planu
  zmienioną po reformie), więc definicje sprawdź w uchwale planu. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Ustawa o planowaniu art. 37a ust. 1 i 3 — rada gminy może uchwałą ustalić zasady sytuowania
  obiektów małej architektury i ogrodzeń, ich gabaryty, standardy i materiały, a także zakaz
  sytuowania ogrodzeń. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o planowaniu art. 30 ust. 1 — każdy ma prawo wglądu do planu ogólnego i planu
  miejscowego oraz otrzymania z nich wypisów i wyrysów. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)

**Obiekty małej architektury, altany, wiaty, tarasy, oczka, murki**
- Prawo budowlane art. 3 pkt 4 — obiekty małej architektury to niewielkie obiekty, m.in. posągi,
  wodotryski i inne obiekty architektury ogrodowej oraz obiekty użytkowe do rekreacji codziennej
  i utrzymania porządku (piaskownice, huśtawki, drabinki, śmietniki). (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 19 i ust. 1 pkt 28 — obiekty małej architektury nie wymagają
  pozwolenia ani zgłoszenia, z wyjątkiem obiektów w miejscach publicznych, które wymagają
  zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 3 — wolno stojąca altana o powierzchni zabudowy do 35 m²
  (najwyżej dwie na każde 500 m² działki) nie wymaga pozwolenia ani zgłoszenia. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 2 — wiata o powierzchni zabudowy do 50 m² na działce z
  budynkiem mieszkalnym albo przeznaczonej pod budownictwo mieszkaniowe (najwyżej dwie na każde
  1000 m² działki) nie wymaga pozwolenia ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 1 pkt 14 — wolno stojące parterowe budynki gospodarcze oraz wolno
  stojące garaże i wiaty, o powierzchni zabudowy do 35 m² (najwyżej dwa takie obiekty na każde
  500 m² działki), wymagają zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 29 ust. 2 pkt 31 i ust. 1 pkt 22 — przydomowy taras naziemny o
  powierzchni zabudowy do 35 m² (zadaszony — z dachem do 35 m²) nie wymaga pozwolenia ani
  zgłoszenia, a większy (zadaszony — z dachem do 50 m²) wymaga zgłoszenia. (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 13 — baseny i oczka wodne do 50 m² przy budynkach
  mieszkalnych jednorodzinnych i budynkach rekreacji indywidualnej nie wymagają pozwolenia ani
  zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 38 — konstrukcje oporowe o wysokości do 0,80 m nie wymagają
  pozwolenia ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 4 pkt 4 — utwardzenie powierzchni gruntu na działce budowlanej
  nie wymaga pozwolenia ani zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Ustawa o planowaniu art. 59 ust. 2a–2b — zmiana zagospodarowania terenu dotycząca obiektów z
  art. 29 ust. 2 Prawa budowlanego i części obiektów z art. 29 ust. 1 nie wymaga decyzji o
  warunkach zabudowy, poza wyjątkami (m.in. zabytki, parki narodowe, rezerwaty i ich otuliny,
  Natura 2000, formy ochrony przyrody). (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)

**Ogrodzenia**
- Prawo budowlane art. 29 ust. 2 pkt 20 i ust. 1 pkt 21 — ogrodzenie o wysokości do 2,20 m nie
  wymaga pozwolenia ani zgłoszenia, a wyższe wymaga zgłoszenia. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- WT § 41 ust. 1–2 — ogrodzenie nie może zagrażać bezpieczeństwu ludzi i zwierząt, a na wysokości
  mniejszej niż 1,8 m nie wolno umieszczać na nim ostro zakończonych elementów, drutu kolczastego,
  tłuczonego szkła i podobnych materiałów. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- WT § 42 ust. 1 — bramy i furtki w ogrodzeniu nie mogą otwierać się na zewnątrz działki. (stan
  na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)

**Odległości od granicy**
- WT § 12 ust. 1 — budynek sytuuje się co najmniej 4 m od granicy działki ścianą z oknami lub
  drzwiami i 3 m ścianą bez okien i drzwi (budynek mieszkalny wielorodzinny o wysokości ponad 4
  kondygnacji nadziemnych — 5 m), jeśli inne przepisy nie stanowią inaczej. (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)
- WT § 12 ust. 6 pkt 1 i ust. 7 — okap, gzyms, balkon, daszek nad wejściem, galeria, taras, schody
  zewnętrzne, rampa i pochylnia (poza pochylnią dla osób niepełnosprawnych) muszą być co najmniej
  1,5 m od granicy działki, a okap w przypadkach z ust. 2 i 4 — co najmniej 1 m. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Kodeks cywilny art. 147 — nie wolno prowadzić robót ziemnych tak, by groziło to nieruchomościom
  sąsiednim utratą oparcia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Odległości nasadzeń od granicy sprawdź w planie miejscowym i uchwałach gminy; stosunki z
  sąsiadem regulują przepisy Kodeksu cywilnego w punkcie o gałęziach i korzeniach niżej.

**Wody opadowe i zmiana stosunków wodnych**
- Prawo wodne art. 234 ust. 1 — właściciel gruntu nie może zmieniać kierunku i natężenia odpływu
  wód opadowych lub roztopowych ze szkodą dla gruntów sąsiednich ani odprowadzać wód i ścieków na
  grunty sąsiednie. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo wodne art. 234 ust. 3 — gdy zmiany stanu wody szkodzą gruntom sąsiednim, wójt, burmistrz
  lub prezydent miasta nakazuje decyzją przywrócenie stanu poprzedniego albo wykonanie urządzeń
  zapobiegających szkodom. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- WT § 28 ust. 2 i § 29 — przy budynkach niskich albo bez kanalizacji deszczowej wody opadowe
  można odprowadzić na własny teren nieutwardzony, do dołów chłonnych lub zbiorników retencyjnych,
  a zmiana naturalnego spływu w celu kierowania ich na sąsiednią nieruchomość jest zabroniona.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 2 pkt 36 i ust. 1 pkt 38 — bezodpływowe zbiorniki na wody opadowe
  lub roztopowe o łącznej pojemności do 5 m³ nie wymagają pozwolenia ani zgłoszenia, a od 5 do
  15 m³ wymagają zgłoszenia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)

**Gałęzie i korzenie przy granicy**
- Kodeks cywilny art. 150 — właściciel gruntu może obciąć i zachować korzenie przechodzące z
  sąsiedniego gruntu, a gałęzie i owoce zwieszające się z niego — po wyznaczeniu sąsiadowi
  odpowiedniego terminu do ich usunięcia. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Kodeks cywilny art. 149 — właściciel gruntu może wejść na grunt sąsiedni, żeby usunąć
  zwieszające się z jego drzew gałęzie lub owoce, a sąsiad może żądać naprawienia szkody. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Kodeks cywilny art. 154 § 1 — domniemywa się, że płoty, mury, miedze, rowy oraz drzewa i krzewy
  na granicy służą do wspólnego użytku sąsiadów. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Kodeks cywilny art. 144 — właściciel powinien powstrzymywać się od działań zakłócających
  korzystanie z nieruchomości sąsiednich ponad przeciętną miarę. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)

## Model

- `meta.rodzaj: "ogrod"`; `miejsce` (działka, teren, sąsiedztwo, plan miejscowy z parametrami,
  uwarunkowania); budynek jako bryła i dach, poziom parteru, gdy taras albo wejście odnosi się do
  ±0.
- Podpowiedź legendy (kategorie i klasy bilansu ustalasz z inwestorem; kolory domyślnie neutralne,
  rośliny w jednej zieleni, chyba że inwestor zdecyduje inaczej):

| Kategoria | Kształt | Bilans | Zestawienie |
|---|---|---|---|
| budynek, altana, wiata | bryła | zabudowa (sprawdź definicję w planie) | — |
| dach | dach | — | — |
| taras | bryła albo powierzchnia | utwardzona | — |
| nawierzchnia | powierzchnia | utwardzona | — |
| trawnik, rabata, krzewy | powierzchnia | pbc | gatunek, rozstaw_cm |
| drzewo | punkt (symbol drzewo) | — | gatunek, obwod_cm, wielkosc |
| żywopłot | linia | — | gatunek, rozstaw_cm |
| woda | powierzchnia | woda | — |
| ogrodzenie, murek | linia z `wys` | — | — |

- Klasę bilansu wody, tarasów z roślinnością, altan i wiat dobierz do definicji z planu
  (powierzchnia biologicznie czynna według ustawy o planowaniu — w „Uwarunkowaniach”).
- Wiata jest budowlą (Prawo budowlane art. 3 pkt 5b), a ustawa o planowaniu art. 2 pkt 35 liczy
  do udziału powierzchni zabudowy budynki, więc o klasie `zabudowa` dla wiaty rozstrzyga
  definicja w planie. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Drzewa istniejące z `obwod_cm` (na 130 cm) i `dokladnosc_cm`; obwód na 5 cm zapisz w
  atrybutach (np. `obwod_5_cm`), gdy decyduje o zezwoleniu albo zgłoszeniu. Stan istniejący i
  projekt w osobnych plikach, te same id dla obiektów bez zmian (różnica P-02 to wycinka i
  nasadzenia).

## Koncepcja

Warianty pokazują różne odpowiedzi na program: układ stref (wypoczynek, zabawa, uprawy,
gospodarcza), komunikację i dojścia, relację z domem i tarasem, drzewa zachowane i usunięte,
nasłonecznienie stref (P-03, planer), bilans powierzchni względem planu (Z-02) i tryb dla
obiektów (altana, wiata, taras, murek, zbiornik). Przy każdym wariancie zaznacz, które elementy
wymagają zgłoszenia albo zezwolenia.

## Projekt roboczy

- Plan P-01 z wymiarami i rzędnymi, różnica stanów P-02 (wycinka i nasadzenia), cienie P-03,
  przekroje i elewacje P-11…, zestawienie Z-01 (rośliny ze sztukami z rozstawu, nawierzchnie,
  długości ogrodzeń i żywopłotów), bilans Z-02, DXF, makieta GLB, planer 3D.
- `rysunki/wszystko.py` na projekcie z `--istniejacy` robi komplet; bilans przelicz ręcznie, gdy
  plan definiuje powierzchnię biologicznie czynną albo wysokość inaczej niż narzędzie.

## Do przekazania

- Inwestor do gminy: zgłoszenie zamiaru usunięcia drzew albo wniosek o zezwolenie (z obwodami na
  5 cm i 130 cm, mapką położenia).
- Geodeta: mapa do celów projektowych i rzędne (gdy wymaga ich zgłoszenie albo wykonanie
  tarasu, murków, spadków).
- Osoba z uprawnieniami: obiekty wymagające zgłoszenia z projektem albo pozwolenia (np. taras
  powyżej 35 m², konstrukcje oporowe powyżej 0,80 m, wiaty i budynki gospodarcze); konstruktor —
  murki oporowe, altany i wiaty.
- Projektanci instalacji z uprawnieniami: oświetlenie i zasilanie w ogrodzie, odwodnienie,
  zbiorniki na deszczówkę, nawadnianie.
- Specjalista od drzew: ocena stanu drzew zachowanych i ochrona ich korzeni w czasie robót.
