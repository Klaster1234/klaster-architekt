// Planer 3D modelu zamierzenia: rzut 2D + scena 3D (teren, obiekty, sąsiedztwo, moduły wnętrz) + zegar słoneczny
// + kontrole (odległość od granicy działki i od obiektu odniesienia wskazanego Shift+klikiem, kolizje)
// + przełącznik wariantów modelu.
// Dane: /dane.json?model=<nazwa> (planer3d/eksport_web.py z modelu zamierzenia; serwer planer3d/serwer.py odświeża je
// sam), warianty: /modele.json. Planer to piaskownica — nigdy nie zapisuje modelu. Przesunięcia obiektów żyją
// w pamięci przeglądarki (klucz planer:<id projektu>:<model>:szkic) razem z odciskiem położenia obiektu w modelu:
// po zmianie modelu takie przesunięcie jest przy wczytaniu pomijane (nie nakłada się drugi raz). „Kopiuj zmiany
// dla Claude” daje JSON {"model", "przesuniete": [{"id", "dx", "dy"}]} (cm, osie modelu) do naniesienia na model.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import { uklad, mat, zbudujLokal, zbudujMebel, zbudujSwiatla, kolorMebla } from './scena.js';
import { utworzRzut } from './rzut_zamierzenia.js';
import { przesun, najblizszePunkty, kolizje, poza, jestPunktem, odlegloscObiektow, szkicDoZapisu, szkicZOdczytu } from './kontrole_zamierzenia.js';
import { pozycjaSlonca, czasLokalny, teraz, doba, poprawnaStrefa } from './slonce.js';
import { zegar, hhmm } from './zegar.js';

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (z) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[z]);
const fmt = (v) => (Math.round(v * 10) / 10).toLocaleString('pl-PL');
const metry = (cm) => (cm / 100).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const liczba = (n, [jeden, kilka, wiele]) => `${n} ${n === 1 ? jeden : [2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100) ? kilka : wiele}`;
const hex = (v, domyslny) => (/^#[0-9a-f]{6}$/i.test(v ?? '') ? v : domyslny);
const r1 = (v) => Math.round(v * 10) / 10;
const RAD = Math.PI / 180;
const STRONY = ['pn.', 'pn.-wsch.', 'wsch.', 'pd.-wsch.', 'pd.', 'pd.-zach.', 'zach.', 'pn.-zach.'];
const RODZAJE = { wnetrze: 'wnętrze', ogrod: 'ogród', budynek: 'budynek', inne: 'inne' };
const KSZTALTY = { powierzchnia: 'powierzchnia', linia: 'linia', punkt: 'punkt', bryla: 'bryła', dach: 'dach' };
// wygląd planera (teren i grunt w tonacji planera lokalu; kolory obiektów wyłącznie z legendy modelu)
const TEREN = '#D8CDBB', COKOL = '#C4B8A6', GRUNT = '#E4DACB', SASIEDZTWO = '#DADADA', BEZ_KOLORU = '#C8C8C8';

// ---------- dane: wariant z adresu (?model=<nazwa>, bez parametru pierwszy model serwera), lista z /modele.json ----------
const parametry = new URLSearchParams(location.search);
let modele = [], dane = null, blad = null;
try {
  const [rm, rd] = await Promise.all([
    fetch('./modele.json', { cache: 'no-store' }).catch(() => null),
    fetch(`./dane.json${parametry.has('model') ? `?model=${encodeURIComponent(parametry.get('model'))}` : ''}`, { cache: 'no-store' }),
  ]);
  if (rm?.ok) modele = await rm.json().catch(() => []);
  if (rd.ok) dane = await rd.json();
  else blad = { kod: rd.status, tekst: (await rd.text().catch(() => '')).trim().slice(0, 600) };
} catch (e) {
  blad = { kod: null, tekst: e.message };
}
if (!Array.isArray(modele)) modele = [];
// warianty: modele zamierzenia z listy serwera (model lokalu ma własną stronę, index.html); model, którego serwer nie
// odczytał (rodzaj "blad", np. błędny JSON), to nieaktywna pigułka z komunikatem w podpowiedzi
const warianty = modele.filter((m) => ['zamierzenie', 'blad'].includes(m?.rodzaj) && typeof m.nazwa === 'string');
const adresWariantu = (nazwa, hash = location.hash) => `${location.pathname}?model=${encodeURIComponent(nazwa)}${hash}`;
function rysujWarianty(lista, biezacy, przejdz) {
  for (const m of lista) {
    const b = Object.assign(document.createElement('button'), { textContent: m.nazwa, title: m.nazwa === biezacy ? 'bieżący wariant' : 'przełącz wariant' });
    b.classList.toggle('wl', m.nazwa === biezacy);
    if (m.rodzaj === 'blad') Object.assign(b, { disabled: true, textContent: `${m.nazwa} — błąd`, title: `Nie można odczytać modelu: ${m.blad ?? ''}` });
    b.onclick = () => {
      if (m.nazwa !== biezacy) przejdz(m.nazwa);
    };
    $('#warianty').append(b);
  }
}
function przerwij(komunikat, podtytul) {  // bez danych zamierzenia: komunikat i warianty do wyboru
  $('#komunikat').textContent = komunikat;
  $('#podtytul').textContent = podtytul;
  rysujWarianty(warianty, null, (nazwa) => {
    location.href = adresWariantu(nazwa);
  });
  throw new Error(komunikat);
}
if (blad) {
  const nazwa = parametry.get('model');
  if (blad.kod === 404 && parametry.has('model') && !modele.some((m) => m?.nazwa === nazwa)) {
    przerwij(`Nie ma modelu „${nazwa}”${warianty.length ? `; dostępne: ${warianty.map((m) => m.nazwa).join(', ')}.\nWybierz wariant na górze strony.` : '.'}`,
      'nie ma takiego modelu');
  }
  przerwij(`Nie udało się wczytać danych modelu (${blad.kod ? `HTTP ${blad.kod}` : blad.tekst}${blad.kod && blad.tekst ? ` — ${blad.tekst}` : ''}).`
    + '\nUruchom planer poleceniem: python planer3d/serwer.py <model.json> [<wariant.json> …]', 'brak danych modelu');
}
if (dane.rodzaj_modelu !== 'zamierzenie') {
  przerwij('To dane modelu lokalu, nie zamierzenia.\nPlaner lokalu (index.html) pokazuje pierwszy model serwera — uruchom serwer z tym modelem jako pierwszym.',
    'model lokalu');
}
for (const k of ['dzialki', 'sasiedztwo', 'obiekty', 'moduly']) dane[k] ??= [];
dane.legenda ??= {};
$('#komunikat').remove();

const META = dane.meta;
const ZRODLO = (dane.zrodlo ?? '').replace(/\s*\(.*\)\s*$/, '');
const MODEL = parametry.get('model') ?? modele[0]?.nazwa ?? ZRODLO.replace(/\.json$/i, '');
document.title = `${META.nazwa} · planer 3D`;
$('#nazwa-projektu').textContent = META.nazwa;
$('#podtytul').textContent = `planer 3D · ${META.id}${ZRODLO ? ` · ${ZRODLO}` : ''}`;
const u = uklad(dane);
const u0 = uklad({ meta: { obrys: [0, 0, 0, 0] } });  // układ modułu: cm lokalu → metry bez centrowania (X = x/100, Z = −y/100)
const POLNOC = META.polnoc ?? {}, LOK = POLNOC.lokalizacja ?? {};
const ODCHYLENIE = Number(POLNOC.azymut_osi_Y_stopnie ?? 0);  // azymut osi +y modelu (góra rzutu)
const LAT = Number(LOK.lat ?? 52.1), LON = Number(LOK.lon ?? 19.5), STREFA = poprawnaStrefa(LOK.strefa ?? 'Europe/Warsaw');
const KLUCZ_SZKICU = `planer:${META.id}:${MODEL}:szkic`;
const KLUCZ_KAMERY = 'planer:zamierzenie:kamera';  // pamięć sesji: widok 3D przy przełączaniu wariantów
$('#strzalka-polnocy').setAttribute('transform', `rotate(${-ODCHYLENIE})`);

// ---------- stan: obiekty z modelu (niezmienne) i ich przesunięcia w planerze ----------
const obiekty = new Map(dane.obiekty.map((o) => [o.id, o]));
const przesuniecia = new Map();  // id → [dx, dy] cm w osiach modelu (tylko niezerowe)
const stan = { wybrany: null, odniesienie: null, dzien: '', minuty: 720, doba: null, nad: false, gra: false, sztuczne: 'auto' };
const historia = [];
let brudne = true;
const obrysTeraz = (o) => {
  const p = przesuniecia.get(o.id);
  return p ? przesun(o.obrys2d, p[0], p[1]) : o.obrys2d;
};

// ---------- scena ----------
const kontener = $('#scena');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;  // three r186 nie ma już PCFSoftShadowMap — miękkość daje shadow.radius
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.1;
kontener.prepend(renderer.domElement);
const etykiety = new CSS2DRenderer();
etykiety.domElement.className = 'etykiety';
kontener.append(etykiety.domElement);

const scena = new THREE.Scene();
scena.background = new THREE.Color();
const niebo = new THREE.HemisphereLight('#FFF4E6', '#B3A493', 1);
const slonce = new THREE.DirectionalLight('#FFFFFF', 0);

// siatka z danych (cm modelu, z w górę) → metry sceny; normalne łamane na krawędziach ostrzejszych niż 30°
function geometria(s) {
  const p = s.pozycje, poz = new Float32Array(p.length);
  for (let i = 0; i < p.length; i += 3) {
    poz[i] = u.X(p[i]);
    poz[i + 1] = p[i + 2] / 100;
    poz[i + 2] = u.Z(p[i + 1]);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(poz, 3));
  g.setIndex(s.trojkaty);
  const wynik = toCreasedNormals(g, Math.PI / 6);
  g.dispose();
  return wynik;
}

// teren z cokołem (makieta na podstawie): pionowe ściany od brzegu siatki do poziomu gruntu
let poziomGruntu = -0.005, promienTerenu = 0;  // m; bez terenu grunt leży na ±0
if (dane.teren?.trojkaty?.length) {
  const p = dane.teren.pozycje, tr = dane.teren.trojkaty;
  let zmin = Infinity;
  for (let i = 0; i < p.length; i += 3) {
    zmin = Math.min(zmin, p[i + 2]);
    promienTerenu = Math.max(promienTerenu, Math.hypot(u.X(p[i]), u.Z(p[i + 1])));
  }
  poziomGruntu = zmin / 100 - 0.3;
  const teren = new THREE.Mesh(geometria(dane.teren), mat(TEREN, 1));
  teren.receiveShadow = true;
  const brzeg = new Map();  // krawędź → [a, b] w obiegu jej jedynego trójkąta albo null (krawędź wewnętrzna)
  for (let f = 0; f < tr.length; f += 3) {
    for (const [a, b] of [[tr[f], tr[f + 1]], [tr[f + 1], tr[f + 2]], [tr[f + 2], tr[f]]]) {
      const k = a < b ? `${a},${b}` : `${b},${a}`;
      brzeg.set(k, brzeg.has(k) ? null : [a, b]);
    }
  }
  const gora = (i) => [u.X(p[3 * i]), p[3 * i + 2] / 100, u.Z(p[3 * i + 1])];
  const dol = (i) => [u.X(p[3 * i]), poziomGruntu, u.Z(p[3 * i + 1])];
  const sciany = [];
  for (const k of brzeg.values()) {
    if (!k) continue;
    const [a, b] = k;  // trójkąty terenu mają obieg przeciwny do zegara: teren po lewej, ściana patrzy na zewnątrz
    sciany.push(...gora(a), ...dol(b), ...gora(b), ...gora(a), ...dol(a), ...dol(b));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(sciany, 3));
  g.computeVertexNormals();
  const cokol = new THREE.Mesh(g, mat(COKOL, 1));
  cokol.receiveShadow = true;
  scena.add(teren, cokol);
}

// sąsiedztwo: obrys wyciągnięty od terenu w środku obrysu (poza terenem od gruntu) do wysokości
function pryzma(pol, z0, z1, material) {
  const ksztalt = new THREE.Shape(pol.map(([x, y]) => new THREE.Vector2(u.X(x), -u.Z(y))));
  const m = new THREE.Mesh(new THREE.ExtrudeGeometry(ksztalt, { depth: (z1 - z0) / 100, bevelEnabled: false }).rotateX(-Math.PI / 2), material);
  m.position.y = z0 / 100;
  m.castShadow = m.receiveShadow = true;
  return m;
}
for (const s of dane.sasiedztwo) {
  if (s.obrys?.length > 2 && s.z?.[1] > s.z?.[0]) scena.add(pryzma(s.obrys, Math.min(s.z[0], poziomGruntu * 100), s.z[1], mat(SASIEDZTWO, 0.95)));
}

// obiekty ogólne z siatek eksportu; przesunięcie w planerze to przesunięcie siatki (bez dopasowania do terenu)
const grupaObiektow = new THREE.Group(), siatki = new Map();
scena.add(grupaObiektow);
for (const o of dane.obiekty) {
  if (!o.siatka?.trojkaty?.length) continue;
  const m = new THREE.Mesh(geometria(o.siatka), mat(hex(dane.legenda[o.kategoria]?.kolor3d, BEZ_KOLORU), 0.9));
  m.castShadow = o.ksztalt !== 'powierzchnia';  // arkusz 1 cm nad terenem nie rzuca cienia (bez smug na terenie)
  m.receiveShadow = true;
  m.userData.id = o.id;
  grupaObiektow.add(m);
  siatki.set(o.id, m);
}

// moduły wnętrz: scena lokalu (scena.js, bez jego kontekstu) w swoim układzie, w grupie obróconej o kat przeciwnie do zegara wokół (0, 0)
// lokalu i przesuniętej o (dx, dy) na rzędną poziomu z0. −Z sceny = +y modelu, więc obrót przeciwnie do zegara
// w rzucie to dodatni obrót wokół pionowej osi Y sceny; moduły są nieruchome
const swiatlaModulow = [];
const srodekBoxu = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
function celSiedziska(el, lista) {  // siedzisko bez frontu: przodem do najbliższego stołu w tym samym pomieszczeniu
  if (el.kategoria !== 'siedzisko' || el.front) return null;
  const [cx, cy] = srodekBoxu(el.box);
  let naj = null;
  for (const s of lista) {
    if (s.kategoria !== 'stol') continue;
    const p = srodekBoxu(s.box), d = Math.hypot(p[0] - cx, p[1] - cy);
    if (!naj || d < naj.d) naj = { d, p };
  }
  return naj?.p ?? null;
}
for (const m of dane.moduly) {
  const d = m.dane;
  if (!d?.meta) continue;
  for (const k of ['pomieszczenia', 'sciany', 'otwory', 'szachty', 'grzejniki', 'kontekst', 'swiatla', 'okladziny', 'warianty']) d[k] ??= [];
  d.meble ??= {};
  d.tokeny ??= {};
  const g = new THREE.Group();
  g.add(zbudujLokal({ ...d, kontekst: [] }, u0, {}));  // otoczenie zamierzenia to miejsce.sasiedztwo, nie kontekst lokalu
  for (const lista of Object.values(d.meble)) {
    for (const el of lista) g.add(zbudujMebel(el, u0, { kolor: kolorMebla(el, d, {}), cel: celSiedziska(el, lista) }));
  }
  const sw = zbudujSwiatla(d, u0);
  g.add(sw.grupa);
  swiatlaModulow.push(sw);
  g.rotation.y = m.kat * RAD;
  g.position.set(u.X(m.dx), m.z0 / 100, u.Z(m.dy));
  g.userData.modul = m.id;
  scena.add(g);
}

// zasięg sceny i ramka cienia: obrys zamierzenia i najwyższy punkt (drzewa, dachy, sąsiedztwo, moduły)
const [ox0, oy0, ox1, oy1] = META.obrys;
const ZASIEG = Math.hypot(ox1 - ox0, oy1 - oy0) / 200 + 1;  // promień zamierzenia [m]
let najwyzej = 0;  // cm
for (const o of dane.obiekty) najwyzej = Math.max(najwyzej, o.z?.[1] ?? 0);
for (const s of dane.sasiedztwo) najwyzej = Math.max(najwyzej, s.z?.[1] ?? 0);
for (const m of dane.moduly) najwyzej = Math.max(najwyzej, m.z0 + (m.dane?.meta?.wysokosc ?? 0));
const ZASIEG_CIENIA = Math.min(Math.hypot(ZASIEG, najwyzej / 100) + 1, 150);
slonce.castShadow = true;
slonce.shadow.mapSize.set(4096, 4096);
// słońce stoi 2 × ZASIEG_CIENIA od środka, więc cała scena mieści się w głębokości [0,9; 3,1] × ZASIEG_CIENIA
const CIEN_BLIZ = ZASIEG_CIENIA * 0.9, CIEN_DAL = ZASIEG_CIENIA * 3.1;
Object.assign(slonce.shadow.camera, { left: -ZASIEG_CIENIA, right: ZASIEG_CIENIA, top: ZASIEG_CIENIA, bottom: -ZASIEG_CIENIA, near: CIEN_BLIZ, far: CIEN_DAL });
slonce.shadow.camera.updateProjectionMatrix();
slonce.shadow.bias = -0.008 / (CIEN_DAL - CIEN_BLIZ);
slonce.shadow.normalBias = 0.02;
slonce.shadow.radius = 2.5;
scena.add(niebo, slonce, slonce.target);

// obrys wybranego obiektu w 3D
const obrys3d = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)),
  new THREE.LineBasicMaterial({ color: '#C2185B', depthTest: false, transparent: true }));
obrys3d.renderOrder = 10;
scena.add(obrys3d);
const pudlo = new THREE.Box3(), rozmiar3d = new THREE.Vector3();
function ustawObrys3d() {
  const m = stan.wybrany && siatki.get(stan.wybrany);
  obrys3d.visible = !!m;
  if (!m) return;
  pudlo.setFromObject(m);
  pudlo.getSize(rozmiar3d).addScalar(0.04);
  obrys3d.scale.copy(rozmiar3d);
  pudlo.getCenter(obrys3d.position);
}

// ---------- strony świata: róża na gruncie, droga słońca po sklepieniu ----------
function kierunek(azymut, wysokosc = 0, cel = new THREE.Vector3()) {
  const a = (azymut - ODCHYLENIE) * RAD, h = wysokosc * RAD;  // oś +y modelu (−Z sceny) wskazuje azymut ODCHYLENIE
  return cel.set(Math.sin(a) * Math.cos(h), Math.sin(h), -Math.cos(a) * Math.cos(h));
}
const R_ROZA = ZASIEG + 1.5;
const grunt = new THREE.Mesh(new THREE.CircleGeometry(Math.max(R_ROZA + 1.6, ZASIEG_CIENIA, promienTerenu + 2), 96).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ color: GRUNT }));
grunt.position.y = poziomGruntu;
grunt.receiveShadow = true;
const roza = new THREE.Group();
roza.position.y = poziomGruntu + 0.01;
const kreski = [], okrag = [], linia = new THREE.LineBasicMaterial({ color: '#8A7B6E' });
for (let az = 0; az < 360; az += 5) {
  const dl = az % 90 === 0 ? 0.9 : az % 15 === 0 ? 0.45 : 0.2;
  kreski.push(kierunek(az).multiplyScalar(R_ROZA), kierunek(az).multiplyScalar(R_ROZA + dl));
}
for (let az = 0; az <= 360; az += 3) okrag.push(kierunek(az).multiplyScalar(R_ROZA));
roza.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(kreski), linia),
  new THREE.Line(new THREE.BufferGeometry().setFromPoints(okrag), linia),
  new THREE.Line(new THREE.BufferGeometry().setFromPoints([kierunek(0).multiplyScalar(R_ROZA - 0.6), kierunek(0).multiplyScalar(R_ROZA + 1.3)]),
    new THREE.LineBasicMaterial({ color: '#8C2F39' })));
for (const [az, nazwa] of [[0, 'PÓŁNOC'], [90, 'WSCHÓD'], [180, 'POŁUDNIE'], [270, 'ZACHÓD']]) {
  const o = new CSS2DObject(Object.assign(document.createElement('div'), { className: az ? 'strona' : 'strona n', textContent: nazwa }));
  o.position.copy(kierunek(az).multiplyScalar(R_ROZA + 2.1));
  roza.add(o);
}
const sciezka = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: '#D08A2E', transparent: true, opacity: 0.8 }));
const godziny = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: '#D08A2E', size: 5, sizeAttenuation: false }));
const kula = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.35, ZASIEG / 40), 24, 16), new THREE.MeshBasicMaterial({ color: '#FFC445', toneMapped: false }));
scena.add(grunt, roza, sciezka, godziny, kula);

// ---------- kamera: orbita z ujęciami ----------
const kamera = new THREE.PerspectiveCamera(40, 1, 0.3, Math.max(2000, ZASIEG_CIENIA * 12));
const orbita = new OrbitControls(kamera, renderer.domElement);
orbita.enableDamping = true;
orbita.maxPolarAngle = 0.49 * Math.PI;
orbita.minDistance = 1.5;
orbita.maxDistance = Math.max(80, ZASIEG_CIENIA * 3);
let lot = null;
function lecDo(pozycja, cel, natychmiast = false) {
  if (natychmiast) {
    kamera.position.copy(pozycja);
    orbita.target.copy(cel);
    lot = null;
  } else lot = { t0: performance.now(), p0: kamera.position.clone(), c0: orbita.target.clone(), p1: pozycja, c1: cel };
}
function krokLotu(t) {
  if (!lot) return false;
  const k = Math.min(1, (t - lot.t0) / 650), e = k * k * (3 - 2 * k);
  kamera.position.lerpVectors(lot.p0, lot.p1, e);
  orbita.target.lerpVectors(lot.c0, lot.c1, e);
  if (k >= 1) lot = null;
  return true;
}
function ujecie(rodzaj, natychmiast = false) {
  const cel = new THREE.Vector3(u.X((ox0 + ox1) / 2), 1, u.Z((oy0 + oy1) / 2));
  // odległość, przy której kula opisana na obrysie mieści się w węższym z kątów widzenia kamery
  const r = Math.hypot(ox1 - ox0, oy1 - oy0) / 200 + 1;
  const pionowy = kamera.fov * RAD, poziomy = 2 * Math.atan(Math.tan(pionowy / 2) * kamera.aspect);
  const d = r / Math.sin(Math.min(pionowy, poziomy) / 2);
  const poz = rodzaj === 'gora'
    ? new THREE.Vector3(cel.x, cel.y + d, cel.z + 0.01)
    : cel.clone().add(new THREE.Vector3(0.4, 0.85, 0.7).normalize().multiplyScalar(d));
  lecDo(poz, cel, natychmiast);
}
// przełączenie wariantu przeładowuje stronę; widok 3D przechodzi przez pamięć sesji w osiach modelu (warianty mogą
// mieć inny obrys, a więc inny środek sceny)
function zapiszKamere() {
  try {
    const [px, py] = u.doModelu(kamera.position.x, kamera.position.z), [cx, cy] = u.doModelu(orbita.target.x, orbita.target.z);
    sessionStorage.setItem(KLUCZ_KAMERY, JSON.stringify({ p: [px, py, kamera.position.y], c: [cx, cy, orbita.target.y] }));
  } catch { /* bez pamięci sesji: widok domyślny */ }
}
function wczytajKamere() {
  try {
    const k = JSON.parse(sessionStorage.getItem(KLUCZ_KAMERY));
    sessionStorage.removeItem(KLUCZ_KAMERY);
    if (!Array.isArray(k?.p) || !Array.isArray(k?.c) || k.p.length !== 3 || k.c.length !== 3 || ![...k.p, ...k.c].every(Number.isFinite)) return false;
    lecDo(new THREE.Vector3(u.X(k.p[0]), k.p[2], u.Z(k.p[1])), new THREE.Vector3(u.X(k.c[0]), k.c[2], u.Z(k.c[1])), true);
    return true;
  } catch {
    return false;
  }
}

// ---------- słońce ----------
const NOC = new THREE.Color('#1D2230'), ZMIERZCH = new THREE.Color('#E8C4A2'), DZIEN = new THREE.Color('#F4EFE8');
const POMARANCZ = new THREE.Color('#FF9D57'), BIEL = new THREE.Color('#FFF3E2');
const ss = THREE.MathUtils.smoothstep;
const kier = new THREE.Vector3();
function podmien(obiekt, punkty) {
  obiekt.geometry.dispose();
  obiekt.geometry = new THREE.BufferGeometry().setFromPoints(punkty);
}
function ustawDzien(dzien) {
  stan.dzien = dzien;
  stan.doba = doba(dzien, LAT, LON, STREFA);
  $('#dzien').value = dzien;
  const { wschod, zachod } = stan.doba, luk = [], pelne = [];
  const poz = (m) => {
    const p = pozycjaSlonca(czasLokalny(dzien, m, STREFA), LAT, LON);
    return kierunek(p.azymut, p.wysokosc).multiplyScalar(R_ROZA);
  };
  if (wschod != null && zachod != null && zachod > wschod) {
    for (let m = wschod; m < zachod; m += 5) luk.push(poz(m));
    luk.push(poz(zachod));
    for (let g = Math.ceil(wschod / 60); g * 60 <= zachod; g++) pelne.push(poz(g * 60));
  }
  podmien(sciezka, luk);
  podmien(godziny, pelne);
}
const wspolrzedne = `${fmt(Math.abs(LAT))}° ${LAT >= 0 ? 'N' : 'S'}, ${fmt(Math.abs(LON))}° ${LON >= 0 ? 'E' : 'W'}`;
function odswiezSlonce() {
  const { azymut, wysokosc } = pozycjaSlonca(czasLokalny(stan.dzien, stan.minuty, STREFA), LAT, LON);
  kierunek(azymut, wysokosc, kier);
  slonce.position.copy(kier).multiplyScalar(ZASIEG_CIENIA * 2);
  kula.position.copy(kier).multiplyScalar(R_ROZA);
  const nad = (stan.nad = wysokosc > -0.833);
  kula.visible = nad;
  slonce.intensity = 3.5 * ss(wysokosc, -0.8, 6);
  slonce.color.lerpColors(POMARANCZ, BIEL, ss(wysokosc, 0, 25));
  niebo.intensity = 0.25 + 1.9 * ss(wysokosc, -8, 10);  // zastępuje światło odbite, którego renderer nie liczy
  scena.background.lerpColors(NOC, ZMIERZCH, ss(wysokosc, -10, 0)).lerp(DZIEN, ss(wysokosc, 0, 14));
  const moc = { wl: 1, wyl: 0 }[stan.sztuczne] ?? 1 - ss(wysokosc, -4, 3);
  for (const s of swiatlaModulow) s.ustaw(moc * 2.2);
  const [r, m, d] = stan.dzien.split('-'), db = stan.doba;
  tarcza.ustaw(stan.minuty, `${d}.${m}.${r}`, db, nad);
  const czasy = db.wschod != null && db.zachod != null
    ? `wschód ${hhmm(db.wschod)} · górowanie ${hhmm(db.gorowanie)} (${Math.round(db.wysMax)}°) · zachód ${hhmm(db.zachod)}`
    : `górowanie ${hhmm(db.gorowanie)} (${Math.round(db.wysMax)}°)`;
  $('#opis-slonca').innerHTML = (nad
    ? `Słońce <b>${Math.round(wysokosc)}°</b> nad horyzontem, azymut <b>${Math.round(azymut)}°</b> (${STRONY[Math.round(azymut / 45) % 8]})`
    : 'Słońce pod horyzontem')
    + `<br>${czasy}`
    + `<br><span title="meta.lokalizacja i meta.polnoc w modelu">${wspolrzedne} · ${esc(STREFA)} · góra rzutu = azymut ${fmt(ODCHYLENIE)}°</span>`;
  brudne = true;
}
function zapiszAdres() {  // czytelny adres do wklejenia: #t=RRRR-MM-DDTHH:MM (wariant zostaje w ?model=)
  history.replaceState(null, '', `#t=${stan.dzien}T${hhmm(stan.minuty)}`);
}
function zAdresu() {
  const m = (new URLSearchParams(location.hash.slice(1)).get('t') || '').match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$/);
  const t = m ? { dzien: m[1], minuty: m[2] * 60 + Number(m[3]) } : teraz(STREFA);
  ustawDzien(t.dzien);
  stan.minuty = t.minuty;
  odswiezSlonce();
}

// ---------- panele ----------
function pole(pol) {
  let a = 0;
  for (let i = 0; i < pol.length; i++) a += pol[i][0] * pol[(i + 1) % pol.length][1] - pol[(i + 1) % pol.length][0] * pol[i][1];
  return Math.abs(a / 2);
}
function odswiezZamierzenie() {
  const m2 = (dane.dzialki.reduce((a, d) => a + pole(d.granica), 0) / 1e4).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  $('#zam-nazwa').textContent = META.nazwa;
  $('#zam-opis').textContent = [RODZAJE[META.rodzaj] ?? META.rodzaj, dane.dzialki.length ? `działka ${m2} m²` : 'bez działki',
    liczba(dane.obiekty.length, ['obiekt', 'obiekty', 'obiektów']),
    dane.moduly.length ? liczba(dane.moduly.length, ['moduł wnętrz', 'moduły wnętrz', 'modułów wnętrz']) : '',
    dane.sasiedztwo.length ? `sąsiedztwo: ${dane.sasiedztwo.length}` : ''].filter(Boolean).join(' · ');
  const uzyte = new Set(dane.obiekty.map((o) => o.kategoria));
  $('#legenda').innerHTML = Object.entries(dane.legenda).filter(([k]) => uzyte.has(k)).map(([k, l]) => {
    const tlo = hex(l.wypelnienie, hex(l.kolor3d, '#FFFFFF')), ramka = hex(l.linia, 'rgba(0,0,0,.2)');
    return `<li><i class="probka-el" style="background:${tlo};border-color:${ramka}"></i>${esc(l.nazwa || k)}</li>`;
  }).join('') || '<li class="cichy">brak obiektów</li>';
}
function opisPrzesuniecia([dx, dy]) {
  const cz = [];
  if (Math.abs(dx) >= 0.5) cz.push(`${metry(Math.abs(dx))} m ${dx > 0 ? 'w prawo' : 'w lewo'}`);
  if (Math.abs(dy) >= 0.5) cz.push(`${metry(Math.abs(dy))} m ${dy > 0 ? 'w górę rzutu' : 'w dół rzutu'}`);
  return cz.length ? `przesunięty o ${cz.join(' i ')}` : 'przesunięty o mniej niż 1 cm';
}
function odswiezWybrany() {
  const o = stan.wybrany && obiekty.get(stan.wybrany);
  if (!o) {
    $('#wybrany').innerHTML = '<p class="cichy">Kliknij obiekt na rzucie albo w 3D. Przeciągnij wybrany na rzucie, żeby go przesunąć; strzałki przesuwają o 10 cm (z Shift o 1 m). Shift+klik na innym obiekcie mierzy odległość od niego (Esc usuwa odniesienie). Moduły wnętrz i sąsiedztwo są nieruchome.</p>';
    return;
  }
  const lg = dane.legenda[o.kategoria] ?? {}, p = przesuniecia.get(o.id);
  const wys = o.z ? (o.z[1] > o.z[0] ? `wys. ${metry(o.z[0])} … ${metry(o.z[1])} m` : `rzędna ${metry(o.z[0])} m`) : '';
  const atrybuty = Object.entries(o.atrybuty ?? {}).map(([k, v]) => `${esc(k)}: ${esc(typeof v === 'object' ? JSON.stringify(v) : v)}`).join(' · ');
  $('#wybrany').innerHTML = `
    <div class="tytul-el"><b>${esc(o.id)}</b> ${esc(lg.nazwa ?? o.kategoria ?? '')} <span class="cichy">· ${esc(KSZTALTY[o.ksztalt] ?? o.ksztalt)}</span></div>
    <div>${[wys, o.srednica ? `⌀ korony ${metry(o.srednica)} m` : '', o.siatka ? '' : 'bez bryły 3D'].filter(Boolean).join(' · ')}</div>
    ${atrybuty ? `<div class="cichy">${atrybuty}</div>` : ''}
    ${p ? `<div class="zmiana">${esc(opisPrzesuniecia(p))}</div><div class="przyciski"><button data-akcja="przywroc">przywróć z modelu</button></div>`
    : '<div class="cichy">położenie jak w modelu</div>'}`;
}
// najbliższy punkt granicy działki (przy kilku działkach — najbliższej z nich); przecieta — działka, której granicę
// obrys przecina (także krawędzią przez wcięcie działki wklęsłej, gdy wierzchołki leżą w działce)
function wymiarDoGranicy(o) {
  let naj = null, przecieta = null;
  for (const d of dane.dzialki) {
    const w = najblizszePunkty(obrysTeraz(o), d.granica, o.ksztalt !== 'linia', true);
    if (w.przecina && !przecieta) przecieta = d;
    if (!naj || w.odl < naj.odl) naj = { ...w, dzialka: d.id };
  }
  return { ...naj, przecieta };
}
// obiekt odniesienia (Shift+klik) inny niż wybrany i odległość wybranego od niego (oba z bieżącymi przesunięciami)
function odniesienieDla(o) {
  const r = o && stan.odniesienie !== o.id ? obiekty.get(stan.odniesienie) : null;
  return r ? { r, ...odlegloscObiektow({ ...o, obrys2d: obrysTeraz(o) }, { ...r, obrys2d: obrysTeraz(r) }) } : null;
}
function odswiezKontrole(pary) {
  const wiersze = [], o = stan.wybrany && obiekty.get(stan.wybrany);
  if (o && !dane.dzialki.length) wiersze.push('<li class="info">Model nie ma działki — odległości od granicy nie ma do czego liczyć.</li>');
  else if (o) {
    const w = wymiarDoGranicy(o), r = jestPunktem(o.obrys2d) && o.srednica ? o.srednica / 2 : 0;
    const dz = (id) => (dane.dzialki.length > 1 ? ` ${esc(id)}` : '');
    const wychodzi = poza(obrysTeraz(o), dane.dzialki.map((d) => d.granica), o.ksztalt !== 'linia');
    if (w.przecieta || (wychodzi && w.odl < 0.5)) {
      wiersze.push(`<li class="uwaga"><b>${esc(o.id)}</b> przecina granicę działki${dz(w.przecieta?.id ?? w.dzialka)}</li>`);
    } else if (wychodzi) {
      wiersze.push(`<li class="uwaga"><b>${esc(o.id)}</b> leży poza działką — <b>${metry(w.odl)} m</b> od granicy${dz(w.dzialka)}</li>`);
    } else {
      const korona = !r ? '' : w.odl >= r ? ` · korona ${metry(w.odl - r)} m` : ` · korona wychodzi za granicę o ${metry(r - w.odl)} m`;
      wiersze.push(`<li class="${r > w.odl ? 'uwaga' : 'ok'}"><b>${esc(o.id)}</b> od granicy działki${dz(w.dzialka)}: <b>${metry(w.odl)} m</b>${korona}</li>`);
    }
  }
  const odn = odniesienieDla(o), ref = stan.odniesienie && obiekty.get(stan.odniesienie);
  if (odn) {
    const pien = jestPunktem(o.obrys2d) || jestPunktem(odn.r.obrys2d) ? ' (od osi pnia albo punktu)' : '';
    wiersze.push(odn.nachodza
      ? `<li class="uwaga"><b>${esc(o.id)}</b> i <b>${esc(odn.r.id)}</b> (obiekt odniesienia) nachodzą na siebie w planie</li>`
      : `<li class="ok"><b>${esc(o.id)}</b> od <b>${esc(odn.r.id)}</b> (obiekt odniesienia): <b>${metry(odn.odl)} m</b>${pien}</li>`);
  } else if (ref) {
    wiersze.push(`<li class="info">Obiekt odniesienia: <b>${esc(ref.id)}</b> — wybierz inny obiekt, żeby zmierzyć odległość od niego (Esc usuwa odniesienie).</li>`);
  } else if (o) {
    wiersze.push('<li class="info">Shift+klik na innym obiekcie pokaże odległość od niego.</li>');
  }
  if (!dane.obiekty.some((x) => x.kolizja)) wiersze.push('<li class="info">Legenda nie ma kategorii z kontrolą kolizji.</li>');
  else if (!pary.length) wiersze.push('<li class="ok">Obiekty z kontrolą kolizji nie nachodzą na siebie ✓</li>');
  for (const [a, b] of pary) wiersze.push(`<li class="kolizja"><b>${esc(a)}</b> i <b>${esc(b)}</b> nachodzą na siebie w planie i w pionie</li>`);
  $('#kontrole').innerHTML = `<ul class="uwagi">${wiersze.join('')}</ul>`;
  $('#licznik-kontroli').innerHTML = pary.length ? `<span class="licznik">${pary.length}</span>` : '';
}
function odswiezZmiany() {
  $('#zmiany').innerHTML = przesuniecia.size
    ? [...przesuniecia].map(([id, [dx, dy]]) => `<li><button data-obiekt="${esc(id)}" title="wybierz">${esc(id)}</button>`
      + `<small class="cichy">dx ${fmt(dx)} · dy ${fmt(dy)} cm</small><button class="x" data-przywroc="${esc(id)}" title="przywróć z modelu">×</button></li>`).join('')
    : '<li class="cichy">brak — położenie wszystkich obiektów jak w modelu</li>';
}
// bieżące przesunięcia zapisują się same — odświeżenie strony ich nie kasuje; każdy wpis ma odcisk położenia obiektu
// w modelu, więc po zmianie modelu (np. naniesieniu tego przesunięcia) stary wpis nie przesuwa obiektu drugi raz
function zapiszSzkic() {
  try {
    if (przesuniecia.size) localStorage.setItem(KLUCZ_SZKICU, JSON.stringify(szkicDoZapisu(przesuniecia, obiekty)));
    else localStorage.removeItem(KLUCZ_SZKICU);
  } catch { /* tryb prywatny: bez autozapisu */ }
}
function wczytajSzkic() {  // {przesuniecia, pominiete}: wpisy z innym odciskiem (albo bez odcisku) są pomijane
  try {
    return szkicZOdczytu(JSON.parse(localStorage.getItem(KLUCZ_SZKICU)), obiekty);
  } catch {
    return { przesuniecia: new Map(), pominiete: 0 };
  }
}
function odswiezWszystko() {
  const pary = kolizje(dane.obiekty.map((o) => (przesuniecia.has(o.id) ? { ...o, obrys2d: obrysTeraz(o) } : o)));
  zapiszSzkic();
  const o = stan.wybrany && obiekty.get(stan.wybrany), odn = odniesienieDla(o);
  rzut.rysuj({ przesuniecia, wybrany: stan.wybrany, kolizje: new Set(pary.flat()), wymiar: o && dane.dzialki.length ? wymiarDoGranicy(o) : null,
    odniesienie: stan.odniesienie, wymiarOdniesienia: odn && !odn.nachodza ? odn : null });
  odswiezWybrany();
  odswiezKontrole(pary);
  odswiezZmiany();
  ustawObrys3d();
  $('#cofnij').disabled = !historia.length;
  $('#projekt').disabled = !przesuniecia.size;
  brudne = true;
}
let zaplanowane = false;
function zaplanuj() {
  if (zaplanowane) return;
  zaplanowane = true;
  requestAnimationFrame(() => {
    zaplanowane = false;
    odswiezWszystko();
  });
}

// ---------- operacje na obiektach ----------
function ustawPrzesuniecie(id, dx, dy) {
  const p = [r1(dx), r1(dy)];
  if (Math.abs(p[0]) < 0.05 && Math.abs(p[1]) < 0.05) przesuniecia.delete(id);
  else przesuniecia.set(id, p);
  const [x, y] = przesuniecia.get(id) ?? [0, 0];
  siatki.get(id)?.position.set(x / 100, 0, -y / 100);
}
function zapamietaj() {
  historia.push(new Map(przesuniecia));
  if (historia.length > 60) historia.shift();
}
function przywrocStan(s) {
  for (const id of new Set([...przesuniecia.keys(), ...s.keys()])) {
    const [dx, dy] = s.get(id) ?? [0, 0];
    ustawPrzesuniecie(id, dx, dy);
  }
}
function cofnij() {
  const s = historia.pop();
  if (!s) return;
  przywrocStan(s);
  odswiezWszystko();
}
function przesunWybrany(dx, dy) {
  const [x, y] = przesuniecia.get(stan.wybrany) ?? [0, 0];
  zapamietaj();
  ustawPrzesuniecie(stan.wybrany, x + dx, y + dy);
  zaplanuj();
}
function przywrocObiekt(id) {
  if (!przesuniecia.has(id)) return;
  zapamietaj();
  ustawPrzesuniecie(id, 0, 0);
  odswiezWszystko();
}
function wybierz(id) {
  stan.wybrany = id && obiekty.has(id) ? id : null;
  if (stan.odniesienie === stan.wybrany) stan.odniesienie = null;  // obiekt odniesienia stał się wybranym
  odswiezWszystko();
}
function ustawOdniesienie(id) {  // Shift+klik: obiekt, od którego panel „Kontrole” i rzut mierzą odległość wybranego
  if (!id || !obiekty.has(id) || id === stan.wybrany) return;
  stan.odniesienie = id;
  odswiezWszystko();
}

// ---------- eksport zmian dla Claude ----------
function zmianyDlaClaude() {  // JSON z jednym obiektem w wierszu: {"model", "przesuniete": [{"id", "dx", "dy"}]}
  const wiersze = [...przesuniecia].map(([id, [dx, dy]]) => `    ${JSON.stringify({ id, dx, dy })}`);
  return `{\n  "model": ${JSON.stringify(ZRODLO || MODEL)},\n  "przesuniete": [${wiersze.length ? `\n${wiersze.join(',\n')}\n  ` : ''}]\n}`;
}
async function eksportuj() {
  const tekst = zmianyDlaClaude();
  try {
    await navigator.clipboard.writeText(tekst);
  } catch {
    const t = Object.assign(document.createElement('textarea'), { value: tekst });
    document.body.append(t);
    t.select();
    const ok = document.execCommand('copy');
    t.remove();
    if (!ok) {
      toast('Przeglądarka nie pozwoliła skopiować');
      return;
    }
  }
  toast(przesuniecia.size ? 'Skopiowano — wklej w rozmowie z Claude, żeby nanieść przesunięcia na model' : 'Skopiowano — brak przesunięć względem modelu');
}

let czasToastu;
function toast(tekst) {
  const t = $('#toast');
  t.textContent = tekst;
  t.classList.add('widoczny');
  clearTimeout(czasToastu);
  czasToastu = setTimeout(() => t.classList.remove('widoczny'), 2600);
}

// ---------- rzut, zegar, warianty ----------
let startCiagu = null;
const rzut = utworzRzut($('#rzut'), dane, {
  naWybor: (id, shift) => (shift ? ustawOdniesienie(id) : wybierz(id)),
  naStart: (id) => {
    zapamietaj();
    startCiagu = przesuniecia.get(id) ?? [0, 0];
  },
  naPrzesuniecie: (id, dx, dy) => {
    ustawPrzesuniecie(id, startCiagu[0] + dx, startCiagu[1] + dy);
    zaplanuj();
  },
  naKoniec: () => {
    startCiagu = null;
    odswiezWszystko();
  },
});
const tarcza = zegar($('#tarcza'), (m) => {
  stan.gra = false;
  stan.minuty = m;
  odswiezSlonce();
  zapiszAdres();
  przyciskGraj();
});
rysujWarianty(warianty.length ? warianty : [{ nazwa: MODEL }], MODEL, (nazwa) => {  // ten sam kadr 3D i ta sama chwila słońca
  zapiszKamere();
  location.href = adresWariantu(nazwa, `#t=${stan.dzien}T${hhmm(stan.minuty)}`);
});
function przyciskGraj() {
  $('#graj').textContent = stan.gra ? '❚❚' : '▶';
  $('#graj').classList.toggle('wl', stan.gra);
}

// ---------- zdarzenia ----------
$('#prawy').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  if (b.dataset.akcja === 'przywroc') przywrocObiekt(stan.wybrany);
  else if (b.dataset.obiekt) wybierz(b.dataset.obiekt);
  else if (b.dataset.przywroc) przywrocObiekt(b.dataset.przywroc);
  else if (b.dataset.pora) {
    const d = stan.doba, w = d.wschod ?? 360, z = d.zachod ?? 1080;
    const m = { rano: w + 60, poludnie: d.gorowanie, popoludnie: (d.gorowanie + z) / 2, wieczor: z + 60 }[b.dataset.pora];
    stan.minuty = ((Math.round(m / 5) * 5) % 1440 + 1440) % 1440;
    stan.gra = false;
    przyciskGraj();
    odswiezSlonce();
    zapiszAdres();
  } else if (b.dataset.md) {
    ustawDzien(stan.dzien.slice(0, 5) + b.dataset.md);
    odswiezSlonce();
    zapiszAdres();
  }
});
$('#eksport').onclick = eksportuj;
$('#cofnij').onclick = cofnij;
$('#projekt').onclick = () => {
  zapamietaj();
  przywrocStan(new Map());
  odswiezWszystko();
};
$('#pokaz-rzut').onclick = () => document.body.classList.toggle('rzut-otwarty');
$('#dzien').onchange = (e) => {
  if (!e.target.value) return;
  ustawDzien(e.target.value);
  odswiezSlonce();
  zapiszAdres();
};
$('#teraz').onclick = () => {
  const t = teraz(STREFA);
  ustawDzien(t.dzien);
  stan.minuty = t.minuty;
  odswiezSlonce();
  zapiszAdres();
};
$('#graj').onclick = () => {
  stan.gra = !stan.gra;
  const d = stan.doba, w = d.wschod ?? 0, z = d.zachod ?? 1440;
  if (stan.gra && (stan.minuty < w - 30 || stan.minuty > z + 30)) stan.minuty = Math.max(0, w - 30);
  if (!stan.gra) {
    stan.minuty = Math.round(stan.minuty / 5) * 5;
    zapiszAdres();
  }
  przyciskGraj();
  odswiezSlonce();
};
$('#sztuczne').onchange = (e) => {
  stan.sztuczne = e.target.value;
  odswiezSlonce();
};
$('#pasek3d').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b?.dataset.ujecie) ujecie(b.dataset.ujecie);
});
addEventListener('keydown', (e) => {
  if (e.target.closest?.('input, textarea, select')) return;
  const k = e.key.toLowerCase();
  if ((e.metaKey || e.ctrlKey) && k === 'z') {
    e.preventDefault();
    cofnij();
    return;
  }
  if (k === 'escape' && stan.odniesienie) {  // Esc najpierw usuwa obiekt odniesienia, drugi raz — wybór
    stan.odniesienie = null;
    odswiezWszystko();
    return;
  }
  if (!stan.wybrany) return;
  const krok = e.shiftKey ? 100 : 10;
  const ruch = { arrowleft: [-krok, 0], arrowright: [krok, 0], arrowup: [0, krok], arrowdown: [0, -krok] }[k];
  if (ruch) {
    e.preventDefault();
    przesunWybrany(...ruch);
  } else if (k === 'escape') wybierz(null);
});
addEventListener('hashchange', zAdresu);

// klik w 3D wybiera obiekt ogólny (moduły, teren i sąsiedztwo zdejmują wybór); Shift+klik ustawia obiekt odniesienia
const promien = new THREE.Raycaster(), mysz = new THREE.Vector2();
let dol = null;
renderer.domElement.addEventListener('pointerdown', (e) => {
  dol = { x: e.clientX, y: e.clientY };
});
renderer.domElement.addEventListener('pointerup', (e) => {
  if (dol && Math.hypot(e.clientX - dol.x, e.clientY - dol.y) < 5) {
    const r = renderer.domElement.getBoundingClientRect();
    mysz.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    promien.setFromCamera(mysz, kamera);
    const traf = promien.intersectObjects(scena.children, true)
      .find((h) => h.object.isMesh && h.object !== kula && h.object.material?.colorWrite !== false && !(h.object.material?.transparent && h.object.material.opacity < 0.5));
    const id = traf?.object.userData.id ?? null;
    if (e.shiftKey) ustawOdniesienie(id);
    else wybierz(id);
  }
  dol = null;
});

// ---------- pętla renderowania (rysuje tylko, gdy coś się zmieniło) ----------
let poprzedni = performance.now();
function rozmiar() {
  const w = kontener.clientWidth, h = Math.max(1, kontener.clientHeight);
  renderer.setSize(w, h);
  etykiety.setSize(w, h);
  kamera.aspect = w / h;
  kamera.updateProjectionMatrix();
  brudne = true;
}
new ResizeObserver(rozmiar).observe(kontener);
renderer.setAnimationLoop((t) => {
  const dt = Math.min(0.1, (t - poprzedni) / 1000);
  poprzedni = t;
  let ruch = krokLotu(t);
  ruch = orbita.update() || ruch;
  if (stan.gra) {
    const d = stan.doba, w = d.wschod ?? 0, z = d.zachod ?? 1440;
    stan.minuty += dt * 60;  // godzina doby na sekundę
    if (stan.minuty > z + 30) stan.minuty = Math.max(0, w - 30);
    odswiezSlonce();
  }
  if (ruch || brudne) {
    renderer.render(scena, kamera);
    etykiety.render(scena, kamera);
    brudne = false;
  }
});

odswiezZamierzenie();
const szkic = wczytajSzkic();
for (const [id, [dx, dy]] of szkic.przesuniecia) ustawPrzesuniecie(id, dx, dy);
const oSzkicu = [];
if (szkic.przesuniecia.size) oSzkicu.push(`Przywrócono niezapisane przesunięcia (${szkic.przesuniecia.size})`);
if (szkic.pominiete) oSzkicu.push(`Pominięto ${liczba(szkic.pominiete, ['przesunięcie', 'przesunięcia', 'przesunięć'])} — model zmienił się od ich zapisania`);
if (oSzkicu.length) toast(oSzkicu.join(' · '));
rozmiar();
if (!wczytajKamere()) ujecie('skos', true);
zAdresu();
odswiezWszystko();
