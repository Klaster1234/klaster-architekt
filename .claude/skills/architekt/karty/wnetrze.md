# Karta: wnętrze

Mieszkanie albo inny lokal: remont, zmiana układu, aranżacja. Model: `meta.rodzaj: "wnetrze"`,
poziom lokalu i moduł wnętrz (skill `modul-wnetrz`). Karta zawiera wiedzę techniczną i prawną,
bez zaleceń stylu.

## Rozpoznanie

**Co zebrać**
- Dokumentacja lokalu i budynku: rzut techniczny, inwentaryzacja, projekt budynku, karta
  lokalu; które źródło jest wiążące, ustala inwestor (skill `rysunki-i-modele`).
- Pomiar: ściany, otwory, wysokość od podłogi wykończonej do stropu i do sufitu, grubości
  warstw posadzki; skan LiDAR albo dalmierz. Czego nie zmierzono, jest ZAŁOŻENIEM.
- Konstrukcja: które ściany są nośne i skąd to wiadomo (dokumentacja, konstruktor); nie
  wnioskuj o nośności z grubości ściany.
- Instalacje: piony, szachty, kratki i przewody wentylacyjne, urządzenia gazowe, przewody
  kominowe, grzejniki, rozdzielnica; protokoły kontroli instalacji gazowej i przewodów
  kominowych.
- Okna i strony świata (`meta.polnoc`), światło dzienne w pomieszczeniach.
- Budynek: wspólnota czy spółdzielnia, regulamin i zasady zgód na roboty, rejestr zabytków
  albo ochrona w planie miejscowym.

**Inspiracje kolorystyki i układu** — poproś inwestora o zdjęcia, linki, tablice, szkice i
miejsca, które zna, a także o to, czego nie chce. Pliki zapisz w `zrodla/inspiracje/`, obrazy
obejrzyj (Read) i opisz słowami; w `PROJEKT.md` zanotuj, skąd są, co się powtarza, co inwestor
odrzuca i jakie wnioski wynikają dla koncepcji. Bez inspiracji pytasz, nie proponujesz stylu.

**Pytania do inwestora**
- Kto mieszka i jak korzysta z lokalu w ciągu dnia; co robi w domu (praca, gotowanie, goście,
  hobby); co trzeba przechowywać.
- Co zostaje (meble, sprzęty, instalacje), a co jest do wymiany.
- Co lubi i czego nie lubi w obecnym układzie; jakie materiały i jakie światło mu odpowiadają.
- Ograniczenia: budżet, termin, zamieszkanie w czasie robót, zgody wspólnoty lub spółdzielni.

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
- **Ustawa o własności lokali** — ustawa z dnia 24 czerwca 1994 r. o własności lokali (t.j.
  Dz. U. z 2026 r. poz. 232).
- **Ustawa o spółdzielniach mieszkaniowych** — ustawa z dnia 15 grudnia 2000 r. o spółdzielniach
  mieszkaniowych (t.j. Dz. U. z 2026 r. poz. 889).
- **Kodeks cywilny** — ustawa z dnia 23 kwietnia 1964 r. – Kodeks cywilny (t.j. Dz. U. z 2026 r.
  poz. 795).

**Warunki techniczne**
- Prawo budowlane art. 102a ust. 1 i art. 102b — przez 18 miesięcy od 20.09.2026 projekt do
  pozwolenia na budowę albo zgłoszenia budowy może być sporządzony według warunków
  technicznych obowiązujących do 19.09.2026 (po oświadczeniu inwestora), a do robót z art. 29
  ust. 4 inwestor może je stosować. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 102a–102b i art. 29 ust. 3 — przepisy epizodyczne nie wymieniają wprost
  robót wymagających zgłoszenia z art. 29 ust. 3 (np. instalacji gazowej, przebudowy konstrukcji
  domu jednorodzinnego), więc według jakich warunków technicznych przygotować dla nich
  dokumentację, ustal w organie administracji architektoniczno-budowlanej. (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)

**Remont a przebudowa**
- Prawo budowlane art. 3 pkt 8 — remont to roboty w istniejącym obiekcie polegające na
  odtworzeniu stanu pierwotnego, niebędące bieżącą konserwacją, także z użyciem innych wyrobów
  budowlanych niż pierwotne. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 3 pkt 7a — przebudowa to roboty zmieniające parametry użytkowe lub
  techniczne istniejącego obiektu, bez zmiany kubatury, powierzchni zabudowy, wysokości,
  długości, szerokości i liczby kondygnacji. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Prawo budowlane art. 29 ust. 4 pkt 1 lit. a — przebudowa budynku, którego budowa wymaga
  pozwolenia, i budynku mieszkalnego jednorodzinnego, z wyłączeniem przebudowy przegród
  zewnętrznych i elementów konstrukcyjnych, nie wymaga pozwolenia na budowę ani zgłoszenia.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 4 pkt 2 lit. a — remont nie wymaga pozwolenia ani zgłoszenia,
  z wyjątkami z art. 29 ust. 3 pkt 2 (m.in. remont przegród zewnętrznych albo elementów
  konstrukcyjnych budynku, którego budowa wymaga pozwolenia, wymaga zgłoszenia). (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 71 ust. 1 pkt 2 i ust. 2 — zmiana sposobu użytkowania obiektu albo jego
  części, m.in. podjęcie działalności zmieniającej warunki bezpieczeństwa pożarowego,
  zdrowotne, higieniczno-sanitarne albo wielkość lub układ obciążeń, wymaga zgłoszenia.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 7 — roboty przy obiekcie wpisanym do rejestru zabytków wymagają
  pozwolenia na budowę, a na obszarze wpisanym do rejestru — zgłoszenia, z dokumentem
  wojewódzkiego konserwatora zabytków. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)

**Ingerencja w ściany nośne**
- Prawo budowlane art. 28 ust. 1 — roboty budowlane można rozpocząć tylko na podstawie
  pozwolenia na budowę, z wyjątkami z art. 29–31; przebudowy elementów konstrukcyjnych budynku,
  którego budowa wymaga pozwolenia (np. wielorodzinnego), nie ma wśród wyjątków z art. 29 ust. 3
  i 4. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 3 pkt 1 lit. a — przebudowa przegród zewnętrznych i elementów
  konstrukcyjnych budynku mieszkalnego jednorodzinnego wymaga zgłoszenia, o ile nie powiększa
  obszaru oddziaływania budynku poza działkę. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- Prawo budowlane art. 12 ust. 1 pkt 1 i ust. 2 — projektowanie jest samodzielną funkcją
  techniczną w budownictwie, którą wykonują wyłącznie osoby z uprawnieniami budowlanymi.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)

**Zgody wspólnoty lub spółdzielni**
- Ustawa o własności lokali art. 3 ust. 2 — nieruchomość wspólną stanowią grunt oraz części
  budynku i urządzenia, które nie służą wyłącznie do użytku właścicieli lokali. (stan na
  26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o własności lokali art. 22 ust. 2 i ust. 3 pkt 5 — we wspólnocie z więcej niż trzema
  lokalami (art. 20 ust. 1) zgoda na przebudowę nieruchomości wspólnej przekracza zwykły zarząd i
  wymaga uchwały właścicieli lokali. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o własności lokali art. 22 ust. 4 — połączenie dwóch lokali stanowiących odrębne
  nieruchomości albo podział lokalu wymaga zgody właścicieli lokali wyrażonej w uchwale.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Ustawa o własności lokali art. 19 i Kodeks cywilny art. 199 — gdy lokali jest najwyżej trzy,
  do zarządu nieruchomością wspólną stosuje się przepisy o współwłasności, a czynność
  przekraczająca zwykły zarząd wymaga zgody wszystkich współwłaścicieli. (stan na 26.09.2026 —
  przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 32 ust. 4 pkt 2 i art. 3 pkt 11 — pozwolenie na budowę dostaje tylko ten,
  kto oświadczył, że ma prawo do dysponowania nieruchomością na cele budowlane, czyli tytuł
  prawny przewidujący uprawnienie do wykonywania robót. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- Ustawa o spółdzielniach mieszkaniowych — w budynku spółdzielni sprawdź w ustawie i w statucie
  spółdzielni, jakie prawo do lokalu ma inwestor i czyjej zgody wymagają roboty w lokalu i w
  częściach wspólnych. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)

**Wysokość i doświetlenie pomieszczeń**
- WT § 72 ust. 1 — najmniejsza wysokość w świetle pokoi w budynkach mieszkalnych wynosi 2,5 m,
  a pokoi na poddaszu w budynkach jednorodzinnych 2,2 m; przy stropach pochyłych wymóg spełnia
  wysokość średnia między największą a najmniejszą wysokością, przy czym najmniejszej nie
  przyjmuje się poniżej 1,9 m, a przestrzeni niższej niż 1,9 m nie wlicza się do pomieszczenia.
  (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- WT § 57 ust. 2 — w pomieszczeniu przeznaczonym na pobyt ludzi powierzchnia okien w świetle
  ościeżnic wynosi co najmniej 1/8 powierzchni podłogi. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)
- WT § 60 ust. 1–3 — pokój mieszkalny ma mieć co najmniej 3 godziny nasłonecznienia w dniach
  równonocy w godzinach 7–17, w mieszkaniu wielopokojowym przynajmniej jeden pokój, a w
  zabudowie śródmiejskiej dopuszcza się 1,5 godziny. (stan na 26.09.2026 — przed powołaniem
  sprawdź aktualny tekst)

**Wentylacja i instalacja gazowa (zakres dla uprawnionych)**
- WT § 147 ust. 2 — wentylację mechaniczną lub grawitacyjną zapewnia się w pomieszczeniach
  przeznaczonych na pobyt ludzi, w pomieszczeniach bez otwieranych okien i tam, gdzie wymaga
  tego zdrowie, technologia lub bezpieczeństwo. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)
- WT § 170 ust. 1–2 — urządzenia gazowe instaluje się tylko w pomieszczeniach spełniających
  warunki wysokości, kubatury, wentylacji, odprowadzenia spalin i dopływu powietrza, a urządzeń z
  otwartą komorą spalania (typ A i B) nie instaluje się w pomieszczeniach mieszkalnych
  (z zastrzeżeniem § 93). (stan na 26.09.2026 — przed powołaniem sprawdź aktualny tekst)
- Prawo budowlane art. 29 ust. 3 pkt 3 lit. d — instalowanie instalacji gazowej wewnątrz i na
  zewnątrz użytkowanego budynku wymaga zgłoszenia; inne instalacje wewnątrz budynku zwalnia z
  niego art. 29 ust. 4 pkt 3 lit. d. (stan na 26.09.2026 — przed powołaniem sprawdź aktualny
  tekst)
- Prawo budowlane art. 62 ust. 1 pkt 1 lit. c — instalacje gazowe i przewody kominowe (dymowe,
  spalinowe i wentylacyjne) kontroluje się co najmniej raz w roku. (stan na 26.09.2026 — przed
  powołaniem sprawdź aktualny tekst)
- WT § 326 ust. 4b — w budynku mieszkalnym wielorodzinnym, jednorodzinnym z dwoma lokalami oraz
  w zabudowie szeregowej lub bliźniaczej roboty w lokalu nie mogą pogorszyć wymagań akustycznych
  określonych w analizie akustycznej budynku. (stan na 26.09.2026 — przed powołaniem sprawdź
  aktualny tekst)

## Model

- `meta.rodzaj: "wnetrze"`, `poziomy` z poziomem lokalu, `moduly` z modułem wnętrz na tym
  poziomie; lokal w osobnym pliku (`lokal_istniejacy.json`, `lokal_projekt.json`) według
  `lokal/SCHEMAT.md` i skilla `modul-wnetrz`. Przykład: `przyklad/mieszkanie/`.
- Ściany nośne z polem `nosna` według źródła, nie według grubości; niepewne wymiary z
  `zrodlo` i `dokladnosc_cm`, wysokości z `wys_zrodlo`.
- Legenda zamierzenia zwykle pusta: ściany, pomieszczenia i wyposażenie opisuje lokal. Kategorie
  dopisujesz tylko dla obiektów spoza lokalu (np. taras przed lokalem na parterze).
- Kolory (`wykonczenie`, `kolor`) tylko wtedy, gdy inwestor je ustalił; domyślnie neutralne.

## Koncepcja

Warianty pokazują różne odpowiedzi na program: układ funkcji i komunikacji, ściany do
wyburzenia i nowe (A-02 dla każdego wariantu), ustawienie wyposażenia z kontrolą kolizji i
przejść, dostęp do światła dziennego (planer, słońce według `meta.polnoc`). Przy każdym
wariancie zaznacz, które zmiany dotykają konstrukcji, instalacji albo części wspólnych, bo od
tego zależą tryb i zgody.

## Projekt roboczy

- Rzut roboczy A-01, plan wyburzeń A-02, izometria A-03, karty pomieszczeń KP-…, kłady ścian
  K-… z zestawieniem K-00, lista założeń `<id>_zalozenia.md`, DXF, makieta GLB, planer 3D
  (`rysunki/wszystko.py` na modelu zamierzenia robi komplet dla modułu).
- Kontrole przed akceptacją: walidacja lokalu, punkty w pomieszczeniach, kolizje i przejścia,
  rzędna sufitu (skill `modul-wnetrz`).

## Do przekazania

- Konstruktor z uprawnieniami: każda zmiana ściany nośnej, stropu, otworu w ścianie nośnej i
  obciążeń (np. zabudowy murowane, wanny, księgozbiory).
- Projektant instalacji z uprawnieniami: gaz, wentylacja (przewody, nawiew i wywiew), wod-kan,
  ogrzewanie; kominiarz: przewody kominowe i wentylacyjne.
- Projektant instalacji elektrycznej z uprawnieniami: rozdzielnica i obwody (punkty z modelu
  są podkładem).
- Architekt z uprawnieniami: projekt, gdy roboty wymagają pozwolenia albo zgłoszenia z
  projektem, oraz zmiana sposobu użytkowania.
- Zarząd wspólnoty albo spółdzielnia: zgody na roboty w częściach wspólnych i na łączenie lub
  podział lokali; konserwator zabytków, gdy budynek jest w rejestrze albo pod ochroną planu.
