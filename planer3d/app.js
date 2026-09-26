// Planer 3D lokalu: rzut 2D + scena 3D + zegar słoneczny + kontrole + spacer + warianty wykończenia + kadr PNG.
// Dane: /dane.json (planer3d/eksport_web.py z modelu lokalu; serwer planer3d/serwer.py odświeża je sam).
// Planer to piaskownica — nigdy nie zapisuje modelu. Przestawienia i wybory żyją w pamięci przeglądarki
// (klucze planer:<id projektu>:szkic|warianty|dzwignie), a „kopiuj zmiany dla Claude” daje JSON do naniesienia na model.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { uklad, zbudujLokal, zbudujMebel, zbudujSwiatla, kolorMebla } from './scena.js';
import { utworzRzut } from './rzut.js';
import { przeszkody, odleglosci, kontrolaMebla, wPomieszczeniu, srodekCiezkosci, jestOknem, pokojPunktu } from './kontrole.js';
import { pozycjaSlonca, czasLokalny, teraz, doba, poprawnaStrefa } from './slonce.js';
import { zegar, hhmm } from './zegar.js';
import { domyslne, wczytajWybory, zapiszWybory, rysujDzwignie, opcjaCelu, cele, tekstWyborow } from './warianty.js';

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (z) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[z]);
const fmt = (v) => (Math.round(v * 10) / 10).toLocaleString('pl-PL');
const m2 = (v) => (v ?? 0).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const liczba = (n, [jeden, kilka, wiele]) => `${n} ${n === 1 ? jeden : [2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100) ? kilka : wiele}`;
const RAD = Math.PI / 180;
const STRONY = ['pn.', 'pn.-wsch.', 'wsch.', 'pd.-wsch.', 'pd.', 'pd.-zach.', 'zach.', 'pn.-zach.'];
const FRONTY = { N: 'N (góra rzutu)', E: 'E (w prawo)', S: 'S (dół rzutu)', W: 'W (w lewo)' };
const KATEGORIE = {
  siedzisko: 'siedzisko', stol: 'stół', stolik: 'stolik', lozko: 'łóżko', sofa: 'sofa', zabudowa_niska: 'zabudowa niska',
  zabudowa_wysoka: 'zabudowa wysoka', wiszaca: 'zabudowa wisząca', sanitariat: 'sanitariat', prysznic: 'prysznic',
  urzadzenie: 'urządzenie', murek: 'murek', szklo: 'szkło', lustro: 'lustro', inne: 'inne',
};
const srodekBoxu = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];

// ---------- dane ----------
let dane;
try {
  const r = await fetch('./dane.json', { cache: 'no-store' });
  if (!r.ok) throw new Error(`HTTP ${r.status}${r.status >= 500 ? ` — ${(await r.text()).trim().slice(0, 600)}` : ''}`);
  dane = await r.json();
} catch (e) {
  $('#komunikat').textContent = `Nie udało się wczytać danych modelu (${e.message}).\nUruchom planer poleceniem: python planer3d/serwer.py <model.json>`;
  $('#podtytul').textContent = 'brak danych modelu';
  throw e;
}
for (const k of ['pomieszczenia', 'sciany', 'otwory', 'szachty', 'grzejniki', 'kontekst', 'swiatla', 'okladziny', 'warianty']) dane[k] ??= [];
dane.meble ??= {};
dane.tokeny ??= {};
$('#komunikat').remove();

const META = dane.meta;
const ZRODLO = (dane.zrodlo ?? '').replace(/\s*\(.*\)\s*$/, '');
document.title = `${META.nazwa} · planer 3D`;
$('#nazwa-projektu').textContent = META.nazwa;
$('#podtytul').textContent = `planer 3D · ${META.id}${ZRODLO ? ` · ${ZRODLO}` : ''}`;
const u = uklad(dane);
const POLNOC = META.polnoc ?? {}, LOK = POLNOC.lokalizacja ?? {};
const ODCHYLENIE = Number(POLNOC.azymut_osi_Y_stopnie ?? 0);  // azymut osi +y modelu (góra rzutu)
const LAT = Number(LOK.lat ?? 52.1), LON = Number(LOK.lon ?? 19.5), STREFA = poprawnaStrefa(LOK.strefa ?? 'Europe/Warsaw');
const PREFIKS = `planer:${META.id}:`;
const KLUCZ_SZKICU = `${PREFIKS}szkic`, KLUCZ_UKLADOW = `${PREFIKS}warianty`, KLUCZ_DZWIGNI = `${PREFIKS}dzwignie`;
$('#strzalka-polnocy').setAttribute('transform', `rotate(${-ODCHYLENIE})`);

// ---------- stan: meble z projektu (niezmienne) i bieżące (edytowane) ----------
const projekt = new Map(), meble = new Map(), pokojMebla = new Map();
for (const [nr, lista] of Object.entries(dane.meble)) {
  for (const el of lista) {
    projekt.set(el.id, el);
    meble.set(el.id, { ...el, box: [...el.box] });
    pokojMebla.set(el.id, nr);
  }
}
const stan = { pokoj: null, wybrany: null, dzien: '', minuty: 720, doba: null, nad: false, gra: false, sztuczne: 'auto', widok: 'orbita' };
const historia = [];
let brudne = true;
const zmieniony = (id) => {
  const a = meble.get(id), b = projekt.get(id);
  return a.front !== b.front || a.box.some((v, i) => Math.abs(v - b.box[i]) > 0.05);
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
const niebo = new THREE.HemisphereLight('#FFF4E6', '#B3A493', 1);  // „grunt” jaśniejszy: udaje światło odbite od podłogi na sufit
const slonce = new THREE.DirectionalLight('#FFFFFF', 0);
const [ox0, oy0, ox1, oy1] = META.obrys;
const ZASIEG = Math.hypot(ox1 - ox0, oy1 - oy0) / 200 + 1;  // promień lokalu [m]
// cień rzuca też otoczenie z modelu (kontekst): ramka cienia obejmuje je, do rozsądnej granicy
let zasiegCienia = ZASIEG;
for (const k of dane.kontekst) {
  const [a, b, c, d] = k.box, h = (k.z?.[1] ?? META.wysokosc) / 100;
  for (const [x, y] of [[a, b], [a, d], [c, b], [c, d]]) zasiegCienia = Math.max(zasiegCienia, Math.hypot(u.X(x), u.Z(y), h) + 1);
}
const ZASIEG_CIENIA = Math.min(zasiegCienia, 80);
slonce.castShadow = true;
slonce.shadow.mapSize.set(4096, 4096);
// słońce stoi 2 × ZASIEG_CIENIA od środka, więc cała scena mieści się w głębokości [0,9; 3,1] × ZASIEG_CIENIA;
// bias podany w metrach (ok. 8 mm), bo w jednostkach mapy zależy od tego zakresu — większy świeciłby pod sufitem
const CIEN_BLIZ = ZASIEG_CIENIA * 0.9, CIEN_DAL = ZASIEG_CIENIA * 3.1;
Object.assign(slonce.shadow.camera, { left: -ZASIEG_CIENIA, right: ZASIEG_CIENIA, top: ZASIEG_CIENIA, bottom: -ZASIEG_CIENIA, near: CIEN_BLIZ, far: CIEN_DAL });
slonce.shadow.camera.updateProjectionMatrix();
slonce.shadow.bias = -0.008 / (CIEN_DAL - CIEN_BLIZ);
slonce.shadow.normalBias = 0.02;
slonce.shadow.radius = 2.5;
scena.add(niebo, slonce, slonce.target);
let wybory = wczytajWybory(dane, KLUCZ_DZWIGNI);  // warianty wykończenia (warianty.js)
let lokal = zbudujLokal(dane, u, wybory);
const swiatla = zbudujSwiatla(dane, u);
scena.add(lokal, swiatla.grupa);

const grupaMebli = new THREE.Group(), obiekty = new Map();
scena.add(grupaMebli);
function celSiedziska(id) {  // siedzisko bez frontu w modelu: przodem do najbliższego stołu w tym samym pomieszczeniu
  const m = meble.get(id);
  if (m.kategoria !== 'siedzisko' || m.front) return null;
  const [cx, cy] = srodekBoxu(m.box);
  let naj = null;
  for (const s of meble.values()) {
    if (s.kategoria !== 'stol' || pokojMebla.get(s.id) !== pokojMebla.get(id)) continue;
    const p = srodekBoxu(s.box), d = Math.hypot(p[0] - cx, p[1] - cy);
    if (!naj || d < naj.d) naj = { d, p };
  }
  return naj?.p ?? null;
}
function zwolnij(obiekt) {  // geometrie i jednorazowe materiały (tekstury w skali okładzin)
  obiekt.traverse((o) => {
    o.geometry?.dispose();
    if ((o.userData.material ?? o.material)?.userData?.jednorazowy) (o.userData.material ?? o.material).dispose();
  });
}
function odbudujMebel(id) {
  const stary = obiekty.get(id);
  if (stary) {
    grupaMebli.remove(stary);
    zwolnij(stary);
  }
  const m = meble.get(id);
  const g = zbudujMebel(m, u, { kolor: kolorMebla(m, dane, wybory), cel: celSiedziska(id) });
  grupaMebli.add(g);
  obiekty.set(id, g);
}
function ustawPozycje(id) {
  const [x0, y0, x1, y1] = meble.get(id).box;
  obiekty.get(id).position.set(u.X((x0 + x1) / 2), 0, u.Z((y0 + y1) / 2));
}
for (const id of meble.keys()) odbudujMebel(id);

const obrys = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)),
  new THREE.LineBasicMaterial({ color: '#C2185B', depthTest: false, transparent: true }));
obrys.renderOrder = 10;
scena.add(obrys);
function ustawObrys() {
  const el = stan.wybrany && meble.get(stan.wybrany);
  obrys.visible = !!el;
  if (!el) return;
  const [x0, y0, x1, y1] = el.box, [z0, z1] = el.wys;
  obrys.scale.set((x1 - x0) / 100 + 0.02, (z1 - z0) / 100 + 0.02, (y1 - y0) / 100 + 0.02);
  obrys.position.set(u.X((x0 + x1) / 2), (z0 + z1) / 200, u.Z((y0 + y1) / 2));
}

// ---------- strony świata: róża na gruncie, droga słońca po sklepieniu ----------
function kierunek(azymut, wysokosc = 0, cel = new THREE.Vector3()) {
  const a = (azymut - ODCHYLENIE) * RAD, h = wysokosc * RAD;  // oś +y modelu (−Z sceny) wskazuje azymut ODCHYLENIE
  return cel.set(Math.sin(a) * Math.cos(h), Math.sin(h), -Math.cos(a) * Math.cos(h));
}
const R_ROZA = ZASIEG + 1.5;
const grunt = new THREE.Mesh(new THREE.CircleGeometry(Math.max(R_ROZA + 1.6, ZASIEG_CIENIA), 96).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: '#E4DACB' }));
grunt.position.y = -0.1;
grunt.receiveShadow = true;
const roza = new THREE.Group();
roza.position.y = -0.09;
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
const podpisyRozy = [[0, 'PÓŁNOC'], [90, 'WSCHÓD'], [180, 'POŁUDNIE'], [270, 'ZACHÓD']].map(([az, nazwa]) => {
  const d = Object.assign(document.createElement('div'), { className: az ? 'strona' : 'strona n', textContent: nazwa });
  const o = new CSS2DObject(d);
  o.position.copy(kierunek(az).multiplyScalar(R_ROZA + 2.1));
  roza.add(o);
  return o;
});
const sciezka = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: '#D08A2E', transparent: true, opacity: 0.8 }));
const godziny = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: '#D08A2E', size: 5, sizeAttenuation: false }));
const kula = new THREE.Mesh(new THREE.SphereGeometry(0.35, 24, 16), new THREE.MeshBasicMaterial({ color: '#FFC445', toneMapped: false }));
scena.add(grunt, roza, sciezka, godziny, kula);

// ---------- kamera: orbita z ujęciami, przeloty ----------
const FOV_ORBITY = 40, FOV_SPACERU = 62;  // kąt pionowy; we wnętrzu szerszy, jak z oczu, a nie przez lunetę
const kamera = new THREE.PerspectiveCamera(FOV_ORBITY, 1, 0.05, 400);
const orbita = new OrbitControls(kamera, renderer.domElement);
orbita.enableDamping = true;
orbita.maxPolarAngle = 0.49 * Math.PI;
orbita.minDistance = 1.5;
orbita.maxDistance = Math.max(80, ZASIEG_CIENIA * 2);
function granice(nr) {
  const pol = nr && dane.pomieszczenia.find((p) => p.nr === nr)?.poligon;
  return pol ? [Math.min(...pol.map((p) => p[0])), Math.min(...pol.map((p) => p[1])), Math.max(...pol.map((p) => p[0])), Math.max(...pol.map((p) => p[1]))] : META.obrys;
}
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
  const b = granice(stan.pokoj);
  const cel = new THREE.Vector3(u.X((b[0] + b[2]) / 2), stan.pokoj ? 0.8 : 1, u.Z((b[1] + b[3]) / 2));
  // odległość, przy której kula opisana na pomieszczeniu mieści się w węższym z kątów widzenia kamery
  const r = Math.hypot(b[2] - b[0], b[3] - b[1]) / 200 + (stan.pokoj ? 0.4 : 0.8);
  const pionowy = kamera.fov * RAD, poziomy = 2 * Math.atan(Math.tan(pionowy / 2) * kamera.aspect);
  const d = r / Math.sin(Math.min(pionowy, poziomy) / 2);
  const poz = rodzaj === 'gora'
    ? new THREE.Vector3(cel.x, cel.y + d, cel.z + 0.01)
    : cel.clone().add(new THREE.Vector3(0.4, stan.pokoj ? 1.3 : 0.85, 0.7).normalize().multiplyScalar(d));
  lecDo(poz, cel, natychmiast);
}

// ---------- domek dla lalek: w widoku pokoju ściany i wysokie meble od strony kamery znikają (cień zostaje) ----------
const NIEWIDOCZNY = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false });
const DUCH = new THREE.MeshStandardMaterial({ color: '#FFFFFF', transparent: true, opacity: 0.2, depthWrite: false });
let oslony = lokal.userData.oslony;
const doKamery = new THREE.Vector3();
function domekDlaLalek() {
  // kula i droga słońca oraz róża tylko nad całym lokalem — w pokoju i w spacerze stałyby tuż przy kamerze
  const calosc = stan.widok === 'orbita' && !stan.pokoj;
  kula.visible = calosc && stan.nad;
  sciezka.visible = godziny.visible = calosc;
  for (const o of podpisyRozy) o.visible = calosc;
  const nr = stan.widok === 'orbita' ? stan.pokoj : null;
  let b, cx, cy;
  if (nr) {
    b = granice(nr);
    cx = (b[0] + b[2]) / 2;
    cy = (b[1] + b[3]) / 2;
    doKamery.subVectors(kamera.position, orbita.target).setY(0).normalize();
  }
  // prostokąt z rzutu przy pokoju, po stronie kamery (kierunek od środka pokoju zgodny z kierunkiem do kamery)
  const poStronieKamery = (q, zapas) => {
    if (!nr || q[2] < b[0] - zapas || q[0] > b[2] + zapas || q[3] < b[1] - zapas || q[1] > b[3] + zapas) return false;
    const sx = (q[0] + q[2]) / 2 - cx, sy = (q[1] + q[3]) / 2 - cy, d = Math.hypot(sx, sy) || 1;
    // ściany pokoju: tylko te wyraźnie od strony kamery (boczne zostają); rzeczy za obrysem pokoju — każda przed nim
    const przyPokoju = q[2] > b[0] - 15 && q[0] < b[2] + 15 && q[3] > b[1] - 15 && q[1] < b[3] + 15;
    return (sx * doKamery.x - sy * doKamery.z) / d > (przyPokoju ? 0.3 : 0);
  };
  for (const o of oslony) o.obiekt.material = poStronieKamery(o.box, 40) ? NIEWIDOCZNY : o.material;
  for (const [id, g] of obiekty) {
    const m = meble.get(id), duch = pokojMebla.get(id) === nr && m.wys[1] > 150 && poStronieKamery(m.box, 0);
    if (!!g.userData.duch === duch) continue;
    g.userData.duch = duch;
    g.traverse((o) => {
      if (!o.isMesh) return;
      o.userData.material ??= o.material;
      o.material = duch ? DUCH : o.userData.material;
    });
  }
}

// ---------- spacer (widok z wysokości oczu) ----------
const spacer = { klawisze: new Set(), yaw: 0, pitch: 0, wzrost: 1.6 };
function ustawSpojrzenie() {
  kamera.rotation.set(spacer.pitch, spacer.yaw, 0, 'YXZ');
}
function przeszkodySpaceru() {  // prostokąty w metrach sceny [X0, Z0, X1, Z1]; okna tak, drzwi i portfenetry nie
  const b = [...dane.sciany.filter((s) => s.z[0] < 100).map((s) => s.box), ...dane.szachty.map((s) => s.box), ...dane.kontekst.map((k) => k.box),
    ...dane.otwory.filter((o) => o.rodzaj === 'okno').map((o) => o.box),
    ...[...meble.values()].filter((m) => m.wys[0] < 60 && m.wys[1] > 20).map((m) => m.box)];
  return b.map((q) => [u.X(q[0]), u.Z(q[3]), u.X(q[2]), u.Z(q[1])]);
}
const kolizjaSpaceru = (X, Z, prost) => prost.some(([x0, z0, x1, z1]) => X > x0 - 0.2 && X < x1 + 0.2 && Z > z0 - 0.2 && Z < z1 + 0.2);
function pokojWejscia() {  // pomieszczenie drzwi wejściowych (otwór z "wejscie": true), inaczej pierwsze wewnętrzne
  const wejscie = dane.otwory.find((o) => o.wejscie);
  const wewnetrzne = (n) => dane.pomieszczenia.some((p) => p.nr === n && !p.zewnetrzne);
  return (wejscie && [wejscie.do, ...wejscie.pokoje].find(wewnetrzne))
    ?? dane.pomieszczenia.find((p) => !p.zewnetrzne)?.nr ?? dane.pomieszczenia[0]?.nr ?? null;
}
function startSpaceru(skad) {
  const nr = stan.pokoj ?? pokojWejscia();
  const pokoj = dane.pomieszczenia.find((p) => p.nr === nr);
  if (!pokoj) return;
  const pol = pokoj.poligon, srodek = srodekCiezkosci(pol);
  const okno = dane.otwory.find((o) => jestOknem(o) && o.pokoje.includes(nr));
  // wejście do pokoju: drzwi wejściowe lokalu, potem drzwi prowadzące do tego pokoju, potem dowolne przejście
  const drzwi = dane.otwory.filter((o) => !jestOknem(o) && o.pokoje.includes(nr));
  const wejscie = drzwi.find((o) => o.wejscie) ?? drzwi.find((o) => o.do === nr) ?? drzwi[0];
  const [ox, oy] = skad === 'okno' && okno ? srodekBoxu(okno.box) : wejscie ? srodekBoxu(wejscie.box) : srodek;
  const dx = srodek[0] - ox, dy = srodek[1] - oy, d = Math.hypot(dx, dy) || 1;
  // start 60 cm w głąb pokoju; gdy stoi tam mebel — najbliższy wolny punkt w pokoju
  const prost = przeszkodySpaceru();
  const wolne = ([x, y]) => wPomieszczeniu([x, y], pokoj) && !kolizjaSpaceru(u.X(x), u.Z(y), prost);
  let start = [ox + (dx / d) * 60, oy + (dy / d) * 60];
  if (!wolne(start)) {
    let naj = null;
    for (let px = -150; px <= 150; px += 10) {
      for (let py = -150; py <= 150; py += 10) {
        const p = [start[0] + px, start[1] + py], odl = Math.hypot(px, py);
        if ((!naj || odl < naj.odl) && wolne(p)) naj = { p, odl };
      }
    }
    if (naj) start = naj.p;
  }
  // od okna: patrzymy w głąb pokoju; od wejścia: na okno (a bez okna — na środek)
  const cel = skad !== 'okno' && okno ? srodekBoxu(okno.box) : null;
  const v = cel ? [cel[0] - start[0], cel[1] - start[1]] : [dx || 0, dy || 1];
  stan.widok = 'spacer';
  document.body.classList.add('spacer');
  orbita.enabled = false;
  lot = null;
  kamera.fov = FOV_SPACERU;
  kamera.updateProjectionMatrix();
  kamera.position.set(u.X(start[0]), spacer.wzrost, u.Z(start[1]));
  spacer.yaw = Math.atan2(-v[0], v[1]);  // kierunek z rzutu (x, y) → obrót kamery wokół pionu
  spacer.pitch = -0.06;
  ustawSpojrzenie();
  przyciskiWidoku();
  brudne = true;
}
function koniecSpaceru() {
  stan.widok = 'orbita';
  document.body.classList.remove('spacer');
  orbita.enabled = true;
  spacer.klawisze.clear();
  kamera.fov = FOV_ORBITY;
  kamera.updateProjectionMatrix();
  ujecie('skos');
  przyciskiWidoku();
}
function krokSpaceru(dt) {
  if (stan.widok !== 'spacer') return false;
  const k = spacer.klawisze;
  const przod = (k.has('w') || k.has('arrowup')) - (k.has('s') || k.has('arrowdown'));
  const bok = (k.has('d') || k.has('arrowright')) - (k.has('a') || k.has('arrowleft'));
  if (!przod && !bok) return false;
  const v = 1.4 * dt * (k.has('shift') ? 2.2 : 1), sin = Math.sin(spacer.yaw), cos = Math.cos(spacer.yaw);
  const dx = (-sin * przod + cos * bok) * v, dz = (-cos * przod - sin * bok) * v;
  const prost = przeszkodySpaceru(), p = kamera.position;
  if (!kolizjaSpaceru(p.x + dx, p.z, prost)) p.x += dx;
  if (!kolizjaSpaceru(p.x, p.z + dz, prost)) p.z += dz;
  return true;
}
function przyciskiWidoku() {
  for (const b of document.querySelectorAll('[data-widok]')) b.classList.toggle('wl', b.dataset.widok === stan.widok);
  for (const b of document.querySelectorAll('[data-wzrost]')) b.classList.toggle('wl', Number(b.dataset.wzrost) === spacer.wzrost);
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
  slonce.intensity = 3.5 * ss(wysokosc, -0.8, 6);
  slonce.color.lerpColors(POMARANCZ, BIEL, ss(wysokosc, 0, 25));
  niebo.intensity = 0.25 + 1.9 * ss(wysokosc, -8, 10);  // zastępuje światło odbite, którego renderer nie liczy
  scena.background.lerpColors(NOC, ZMIERZCH, ss(wysokosc, -10, 0)).lerp(DZIEN, ss(wysokosc, 0, 14));
  const moc = { wl: 1, wyl: 0 }[stan.sztuczne] ?? 1 - ss(wysokosc, -4, 3);
  swiatla.ustaw(moc * 2.2);
  const [r, m, d] = stan.dzien.split('-'), db = stan.doba;
  tarcza.ustaw(stan.minuty, `${d}.${m}.${r}`, db, nad);
  const czasy = db.wschod != null && db.zachod != null
    ? `wschód ${hhmm(db.wschod)} · górowanie ${hhmm(db.gorowanie)} (${Math.round(db.wysMax)}°) · zachód ${hhmm(db.zachod)}`
    : `górowanie ${hhmm(db.gorowanie)} (${Math.round(db.wysMax)}°)`;
  $('#opis-slonca').innerHTML = (nad
    ? `Słońce <b>${Math.round(wysokosc)}°</b> nad horyzontem, azymut <b>${Math.round(azymut)}°</b> (${STRONY[Math.round(azymut / 45) % 8]})`
    : 'Słońce pod horyzontem')
    + `<br>${czasy}`
    + `<br><span title="meta.polnoc w modelu">${wspolrzedne} · ${esc(STREFA)} · góra rzutu = azymut ${fmt(ODCHYLENIE)}°</span>`;
  brudne = true;
}
function zapiszAdres() {  // czytelny adres do wklejenia: #t=RRRR-MM-DDTHH:MM&p=<nr pomieszczenia>
  const p = stan.pokoj ? `&p=${encodeURIComponent(stan.pokoj)}` : '';
  history.replaceState(null, '', `#t=${stan.dzien}T${hhmm(stan.minuty)}${p}`);
}
function zAdresu() {
  const p = new URLSearchParams(location.hash.slice(1));
  const m = (p.get('t') || '').match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$/);
  const t = m ? { dzien: m[1], minuty: m[2] * 60 + Number(m[3]) } : teraz(STREFA);
  ustawDzien(t.dzien);
  stan.minuty = t.minuty;
  const nr = p.get('p');
  wybierzPokoj(dane.pomieszczenia.some((x) => x.nr === nr) ? nr : null, true);
  odswiezSlonce();
}

// ---------- panele ----------
const poleP = (p) => p.pow_m2 ?? p.m2;
function odswiezPokoj() {
  const p = stan.pokoj && dane.pomieszczenia.find((x) => x.nr === stan.pokoj);
  const wew = dane.pomieszczenia.filter((x) => !x.zewnetrzne), zew = dane.pomieszczenia.filter((x) => x.zewnetrzne);
  $('#pokoj-nazwa').textContent = p ? `${p.nazwa} · ${p.nr}` : `Cały lokal · ${META.nazwa}`;
  $('#pokoj-opis').textContent = p
    ? `${m2(poleP(p))} m²${p.zewnetrzne ? ' · zewnętrzne' : ''}${p.podloga ? ` · ${p.podloga}` : ''} · ${p.status ? `aranżacja: ${p.status}` : 'bez aranżacji w modelu'}`
    : `${m2(wew.reduce((a, x) => a + (poleP(x) ?? 0), 0))} m² · ${liczba(wew.length, ['pomieszczenie', 'pomieszczenia', 'pomieszczeń'])}`
      + (zew.length ? ` + ${zew.map((x) => `${x.nazwa} ${m2(poleP(x))} m²`).join(', ')}` : '');
}
function opisPrzesuniecia(p, el) {
  const dx = (el.box[0] + el.box[2] - p.box[0] - p.box[2]) / 2, dy = (el.box[1] + el.box[3] - p.box[1] - p.box[3]) / 2;
  const cz = [];
  if (Math.abs(dx) >= 0.5) cz.push(`${fmt(Math.abs(dx))} cm ${dx > 0 ? 'w prawo' : 'w lewo'}`);
  if (Math.abs(dy) >= 0.5) cz.push(`${fmt(Math.abs(dy))} cm ${dy > 0 ? 'w górę rzutu' : 'w dół rzutu'}`);
  const obrot = el.front !== p.front || Math.abs(el.box[2] - el.box[0] - (p.box[2] - p.box[0])) > 0.05;
  return [cz.length && `przesunięty o ${cz.join(' i ')}`,
    obrot && `obrócony o 90°${el.front !== p.front ? ` (front ${p.front ?? '—'} → ${el.front ?? '—'})` : ''}`].filter(Boolean).join(', ');
}
function nazwaKoloru(el) {
  const op = opcjaCelu(dane, wybory, 'element', el.id);
  if (op) return `${op.opcja.nazwa} — wariant ${op.wariant.id} „${op.wariant.nazwa}”`;
  if (!el.kolor) return 'kolor spoza modelu (neutralny wg kategorii)';
  const token = Object.entries(dane.tokeny).find(([, t]) => t.hex?.toUpperCase() === el.kolor.toUpperCase());
  return token ? token[0] : el.kolor;
}
function odswiezWybrany() {
  const el = stan.wybrany && meble.get(stan.wybrany);
  if (!el) {
    $('#wybrany').innerHTML = '<p class="cichy">Kliknij mebel na rzucie albo w 3D. Przeciągnij go, żeby przestawić; <kbd>R</kbd> obraca o 90°, strzałki przesuwają o 1 cm (z Shift o 10 cm).</p>';
    return;
  }
  const [x0, y0, x1, y1] = el.box, w = x1 - x0, d = y1 - y0;
  const [szer, gl] = el.front === 'E' || el.front === 'W' ? [d, w] : [w, d];
  const zm = zmieniony(el.id), pokoj = dane.pomieszczenia.find((p) => p.nr === pokojMebla.get(el.id));
  $('#wybrany').innerHTML = `
    <div class="tytul-el"><b>${esc(el.id)}</b> ${esc(el.rodzaj)} <span class="cichy">· ${esc(pokoj?.nazwa ?? pokojMebla.get(el.id))}</span></div>
    <div>${el.ksztalt === 'kolo' ? `⌀ ${fmt(w)}` : `${fmt(szer)} × ${fmt(gl)}`} cm · wys. ${fmt(el.wys[0])}–${fmt(el.wys[1])} cm${el.front ? ` · front ${FRONTY[el.front] ?? esc(el.front)}` : ''}</div>
    <div class="cichy"><i class="probka-el" style="background:${kolorMebla(el, dane, wybory)}"></i>${esc(nazwaKoloru(el))} · ${esc(KATEGORIE[el.kategoria] ?? el.kategoria)}</div>
    ${zm ? `<div class="zmiana">${esc(opisPrzesuniecia(projekt.get(el.id), el))}</div>` : '<div class="cichy">pozycja jak w projekcie</div>'}
    <div class="przyciski">
      ${el.ksztalt === 'kolo' ? '' : '<button data-akcja="obroc-l">↺ 90°</button><button data-akcja="obroc-p">↻ 90°</button>'}
      ${zm ? '<button data-akcja="przywroc">przywróć z projektu</button>' : ''}
    </div>
    ${el.opis || el.wys_zrodlo ? `<details><summary>opis z modelu</summary>${el.opis ? `<p>${esc(el.opis)}</p>` : ''}${el.wys_zrodlo ? `<p class="cichy">wysokość: ${esc(el.wys_zrodlo)}</p>` : ''}</details>` : ''}`;
}
function odswiezKontrole() {
  const lista = przeszkody(dane, meble), kolizje = new Set(), wiersze = [];
  const zmienione = [...meble.keys()].filter(zmieniony);
  for (const id of zmienione) {
    const el = meble.get(id), uwagi = kontrolaMebla(el, lista, dane, pokojMebla.get(id));
    const poziom = ['kolizja', 'uwaga', 'info'].find((p) => uwagi.some((x) => x.poziom === p)) ?? 'ok';
    if (poziom === 'kolizja') kolizje.add(id);
    wiersze.push(`<li class="${poziom}"><b>${esc(id)}</b> ${esc(el.rodzaj)}: ${uwagi.length ? uwagi.map((x) => esc(x.tekst)).join('; ') : 'bez kolizji ✓'}</li>`);
  }
  const p = stan.pokoj && dane.pomieszczenia.find((x) => x.nr === stan.pokoj);
  $('#kontrole').innerHTML = (zmienione.length
    ? `<ul class="uwagi">${wiersze.join('')}</ul>`
    : '<p class="cichy">Układ jak w projekcie (model). Przestaw mebel, a tu pojawią się kolizje, drzwi, okna i grzejniki.</p>')
    + (p?.kontrole?.length ? `<details><summary>kontrole z projektu (${p.kontrole.length})</summary><ul class="projektowe">${p.kontrole.map((k) => `<li>${esc(k)}</li>`).join('')}</ul></details>` : '');
  const ile = zmienione.filter((id) => kolizje.has(id)).length;
  $('#licznik-kontroli').innerHTML = ile ? `<span class="licznik">${ile}</span>` : '';
  return { lista, zmienione: new Set(zmienione), kolizje };
}
// bieżące przestawienia zapisują się same — odświeżenie strony ich nie kasuje
function zapiszSzkic(zmienione) {
  try {
    if (zmienione.size) localStorage.setItem(KLUCZ_SZKICU, JSON.stringify(Object.fromEntries([...zmienione].map((id) => [id, { box: meble.get(id).box, front: meble.get(id).front }]))));
    else localStorage.removeItem(KLUCZ_SZKICU);
  } catch { /* tryb prywatny: bez autozapisu */ }
}
function wczytajSzkic() {
  try {
    const z = JSON.parse(localStorage.getItem(KLUCZ_SZKICU)) || {};
    return new Map(Object.entries(z).filter(([id, v]) => meble.has(id) && Array.isArray(v?.box) && v.box.length === 4));
  } catch {
    return new Map();
  }
}
function odswiezWszystko() {
  const { lista, zmienione, kolizje } = odswiezKontrole();
  zapiszSzkic(zmienione);
  const el = stan.wybrany && meble.get(stan.wybrany);
  rzut.rysuj({ meble, projekt, wybrany: stan.wybrany, zmienione, kolizje, wymiary: el ? odleglosci(el, lista) : [] });
  odswiezWybrany();
  ustawObrys();
  $('#cofnij').disabled = !historia.length;
  $('#projekt').disabled = !zmienione.size;
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

// ---------- operacje na meblach ----------
function zapamietaj() {
  historia.push(new Map([...meble].map(([id, m]) => [id, { box: [...m.box], front: m.front }])));
  if (historia.length > 60) historia.shift();
}
function przywrocStan(s) {
  for (const [id, v] of s) {
    const m = meble.get(id);
    if (m.front !== v.front || m.box.some((x, i) => x !== v.box[i])) {
      m.box = [...v.box];
      m.front = v.front;
      odbudujMebel(id);
    }
  }
}
function cofnij() {
  const s = historia.pop();
  if (!s) return;
  przywrocStan(s);
  odswiezWszystko();
}
function obroc(id, wPrawo) {
  const m = meble.get(id);
  if (!m || m.ksztalt === 'kolo') return;
  zapamietaj();
  const [x0, y0, x1, y1] = m.box, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, w = x1 - x0, d = y1 - y0;
  m.box = [cx - d / 2, cy - w / 2, cx + d / 2, cy + w / 2].map((v) => Math.round(v * 10) / 10);
  const kolej = ['N', 'E', 'S', 'W'];
  if (m.front) m.front = kolej[(kolej.indexOf(m.front) + (wPrawo ? 1 : 3)) % 4];
  odbudujMebel(id);
  odswiezWszystko();
}
function przesun(id, dx, dy) {
  zapamietaj();
  const m = meble.get(id);
  m.box = m.box.map((v, i) => Math.round((v + (i % 2 ? dy : dx)) * 10) / 10);
  ustawPozycje(id);
  zaplanuj();
}
function przywrocMebel(id) {
  zapamietaj();
  const m = meble.get(id), p = projekt.get(id);
  m.box = [...p.box];
  m.front = p.front;
  odbudujMebel(id);
  odswiezWszystko();
}
function wybierz(id) {
  stan.wybrany = id;
  odswiezWszystko();
}
function wybierzPokoj(nr, natychmiast = false) {
  stan.pokoj = nr;
  for (const b of $('#pokoje').children) b.classList.toggle('wl', b.dataset.nr === (nr ?? ''));
  rzut.pokaz(nr);
  if (stan.widok === 'spacer') startSpaceru('drzwi');
  else ujecie('skos', natychmiast);
  odswiezPokoj();
  odswiezWszystko();
  if (!natychmiast) zapiszAdres();
}

// ---------- moje warianty układu (pamięć przeglądarki) i eksport dla Claude ----------
const czytajUklady = () => {
  try {
    const l = JSON.parse(localStorage.getItem(KLUCZ_UKLADOW));
    return Array.isArray(l) ? l : [];
  } catch {
    return [];
  }
};
const piszUklady = (l) => {
  try {
    localStorage.setItem(KLUCZ_UKLADOW, JSON.stringify(l));
  } catch {
    toast('Przeglądarka nie pozwala zapisać wariantu');
  }
};
function odswiezUklady() {
  const l = czytajUklady();
  $('#uklady').innerHTML = l.length
    ? l.map((w, i) => `<li><button data-uklad="${i}" title="wczytaj">${esc(w.nazwa)}</button><small class="cichy">${Object.keys(w.zmiany ?? {}).length} zm.</small><button class="x" data-usun="${i}" title="usuń">×</button></li>`).join('')
    : '<li class="cichy">brak zapisanych — punktem wyjścia jest układ z projektu</li>';
}
function zapiszUklad() {
  const l = czytajUklady();
  const nazwa = $('#nazwa-ukladu').value.trim() || `wariant ${l.length + 1}`;
  const zmiany = Object.fromEntries([...meble.keys()].filter(zmieniony).map((id) => [id, { box: meble.get(id).box, front: meble.get(id).front }]));
  l.push({ nazwa, kiedy: new Date().toISOString(), zmiany });
  piszUklady(l);
  $('#nazwa-ukladu').value = '';
  odswiezUklady();
  toast(`Zapisano „${nazwa}”`);
}
function wczytajUklad(i) {
  const w = czytajUklady()[i];
  if (!w) return;
  zapamietaj();
  przywrocStan(new Map([...projekt].map(([id, p]) => [id, w.zmiany?.[id] ?? { box: p.box, front: p.front }])));
  odswiezWszystko();
  toast(`Wczytano „${w.nazwa}”`);
}
function zmianyDlaClaude() {
  const przestawione = [...meble.keys()].filter(zmieniony).map((id) => {
    const m = meble.get(id), p = projekt.get(id), teraz_ = pokojPunktu(dane, srodekBoxu(m.box))?.nr ?? null;
    return {
      id, pomieszczenie: pokojMebla.get(id), ...(teraz_ !== pokojMebla.get(id) ? { pomieszczenie_teraz: teraz_ } : {}),
      rodzaj: m.rodzaj, box: m.box, front: m.front ?? null, bylo: { box: p.box, front: p.front ?? null },
    };
  });
  const d = domyslne(dane);
  const warianty = dane.warianty.map((w) => {
    const i = wybory[w.id];
    return { id: w.id, nazwa: w.nazwa, wybor: i, opcja: w.opcje[i].nazwa, token: w.opcje[i].token, domyslna: d[w.id], zmiana: i !== d[w.id] };
  });
  const tekst = JSON.stringify({
    opis: 'Zmiany z planera 3D względem modelu — do naniesienia na model. box w cm [x0, y0, x1, y1]; front N/E/S/W to kierunki osi modelu.',
    projekt: META.id, model: ZRODLO || null, kiedy: new Date().toLocaleString('sv-SE').slice(0, 16),
    przestawione, warianty, wybory: tekstWyborow(dane, wybory),
  }, null, 2);
  return tekst.replace(/\[\s+([-\d.,\s]+?)\s+\]/g, (_, w) => `[${w.replace(/\s+/g, ' ')}]`);  // liczby w tablicach w jednej linii
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
  toast('Skopiowano — wklej w rozmowie z Claude, żeby nanieść zmiany na model');
}

// ---------- kadr PNG bieżącego widoku 3D ----------
function zapiszKadr() {
  const bylo = obrys.visible;
  obrys.visible = false;
  domekDlaLalek();
  renderer.render(scena, kamera);  // render i odczyt w tym samym zadaniu — bufor rysunku jeszcze nie jest wyczyszczony
  const url = renderer.domElement.toDataURL('image/png');
  obrys.visible = bylo;
  brudne = true;
  const bin = atob(url.split(',')[1]), bajty = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bajty[i] = bin.charCodeAt(i);
  const pom = stan.widok === 'spacer' ? pokojPunktu(dane, u.doModelu(kamera.position.x, kamera.position.z))?.nr ?? stan.pokoj : stan.pokoj;
  const [r, m, d] = stan.dzien.split('-');
  const nazwa = `kadr_${String(pom ?? 'lokal').replace(/[^\p{L}\p{N}._-]+/gu, '_')}_${r}${m}${d}-${hhmm(stan.minuty).replace(':', '')}.png`;
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([bajty], { type: 'image/png' })), download: nazwa });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 30000);
  toast(`Zapisano kadr ${nazwa}`);
}

let czasToastu;
function toast(tekst) {
  const t = $('#toast');
  t.textContent = tekst;
  t.classList.add('widoczny');
  clearTimeout(czasToastu);
  czasToastu = setTimeout(() => t.classList.remove('widoczny'), 2600);
}

// ---------- rzut, zegar, zakładki pomieszczeń ----------
let startCiagu = null;
const rzut = utworzRzut($('#rzut'), dane, {
  kolor: (m) => kolorMebla(m, dane, wybory),
  naWybor: (id) => wybierz(id),
  naStart: (id) => {
    zapamietaj();
    startCiagu = [...meble.get(id).box];
  },
  naPrzesuniecie: (id, dx, dy) => {
    meble.get(id).box = startCiagu.map((v, i) => Math.round((v + (i % 2 ? dy : dx)) * 10) / 10);
    ustawPozycje(id);
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
for (const p of [null, ...dane.pomieszczenia]) {
  const b = Object.assign(document.createElement('button'), { textContent: p ? p.nazwa : 'cały lokal', title: p ? p.nr : META.id });
  b.dataset.nr = p?.nr ?? '';
  b.onclick = () => wybierzPokoj(p?.nr ?? null);
  $('#pokoje').append(b);
}
function przyciskGraj() {
  $('#graj').textContent = stan.gra ? '❚❚' : '▶';
  $('#graj').classList.toggle('wl', stan.gra);
}

// ---------- warianty wykończenia (dźwignie z modelu) ----------
function przebudujLokal() {
  scena.remove(lokal);
  zwolnij(lokal);
  lokal = zbudujLokal(dane, u, wybory);
  oslony = lokal.userData.oslony;
  scena.add(lokal);
}
function przebarw(idWariantow) {  // od razu nowe kolory celów: elementy przebudowane, ściany i okładziny z lokalem
  let lokalTez = false;
  const elementy = new Set();
  for (const id of idWariantow) {
    const c = cele(dane.warianty.find((w) => w.id === id));
    if (c.sciany.size || c.okladziny.size) lokalTez = true;
    for (const e of c.elementy) elementy.add(e);
  }
  if (lokalTez) przebudujLokal();
  for (const id of elementy) if (meble.has(id)) odbudujMebel(id);
  odswiezWszystko();
}
function odswiezDzwignie() {
  $('#dzwignie').innerHTML = dane.warianty.length ? rysujDzwignie(dane, wybory, esc) : '<p class="cichy maly">Model nie ma wariantów wykończenia.</p>';
  $('#dzwignie-domyslne').disabled = !dane.warianty.length;
}
$('#dzwignie').addEventListener('change', (e) => {
  const id = e.target.dataset.wariantId;
  if (!id) return;
  wybory = { ...wybory, [id]: Number(e.target.value) };
  zapiszWybory(KLUCZ_DZWIGNI, wybory);
  odswiezDzwignie();
  przebarw([id]);
});
$('#dzwignie-domyslne').onclick = () => {
  const d = domyslne(dane), zmienione = dane.warianty.filter((w) => wybory[w.id] !== d[w.id]).map((w) => w.id);
  wybory = d;
  zapiszWybory(KLUCZ_DZWIGNI, wybory);
  odswiezDzwignie();
  przebarw(zmienione);
};
odswiezDzwignie();

// ---------- zdarzenia ----------
$('#prawy').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  const a = b.dataset.akcja;
  if (a === 'obroc-l' || a === 'obroc-p') obroc(stan.wybrany, a === 'obroc-p');
  else if (a === 'przywroc') przywrocMebel(stan.wybrany);
  else if (b.dataset.uklad) wczytajUklad(Number(b.dataset.uklad));
  else if (b.dataset.usun) {
    const l = czytajUklady();
    l.splice(Number(b.dataset.usun), 1);
    piszUklady(l);
    odswiezUklady();
  } else if (b.dataset.pora) {
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
$('#zapisz-uklad').onclick = zapiszUklad;
$('#eksport').onclick = eksportuj;
$('#cofnij').onclick = cofnij;
$('#kadr').onclick = zapiszKadr;
$('#projekt').onclick = () => {
  zapamietaj();
  przywrocStan(new Map([...projekt].map(([id, p]) => [id, { box: p.box, front: p.front }])));
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
  if (!b) return;
  if (b.dataset.widok === 'spacer' && stan.widok !== 'spacer') startSpaceru('drzwi');
  else if (b.dataset.widok === 'orbita' && stan.widok !== 'orbita') koniecSpaceru();
  else if (b.dataset.ujecie) ujecie(b.dataset.ujecie);
  else if (b.dataset.start) startSpaceru(b.dataset.start);
  else if (b.dataset.wzrost) {
    spacer.wzrost = Number(b.dataset.wzrost);
    kamera.position.y = spacer.wzrost;
    przyciskiWidoku();
    brudne = true;
  }
});
addEventListener('keydown', (e) => {
  if (e.target.closest?.('input, textarea, select')) return;
  const k = e.key.toLowerCase();
  if ((e.metaKey || e.ctrlKey) && k === 'z') {
    e.preventDefault();
    cofnij();
    return;
  }
  if (stan.widok === 'spacer') {
    if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'shift'].includes(k)) {
      spacer.klawisze.add(k);
      e.preventDefault();
    }
    if (k === 'escape') koniecSpaceru();
    return;
  }
  if (!stan.wybrany) return;
  const krok = e.shiftKey ? 10 : 1;
  const ruch = { arrowleft: [-krok, 0], arrowright: [krok, 0], arrowup: [0, krok], arrowdown: [0, -krok] }[k];
  if (ruch) {
    e.preventDefault();
    przesun(stan.wybrany, ...ruch);
  } else if (k === 'r') obroc(stan.wybrany, !e.shiftKey);
  else if (k === 'escape') wybierz(null);
});
addEventListener('keyup', (e) => spacer.klawisze.delete(e.key.toLowerCase()));
addEventListener('blur', () => spacer.klawisze.clear());
addEventListener('hashchange', zAdresu);

// klik w 3D wybiera mebel; w spacerze przeciąganie obraca spojrzenie
const promien = new THREE.Raycaster(), mysz = new THREE.Vector2();
let dol = null;
renderer.domElement.addEventListener('pointerdown', (e) => {
  dol = { x: e.clientX, y: e.clientY, yaw: spacer.yaw, pitch: spacer.pitch };
  if (stan.widok === 'spacer') {
    try {
      renderer.domElement.setPointerCapture(e.pointerId);
    } catch { /* zdarzenie syntetyczne */ }
  }
});
renderer.domElement.addEventListener('pointermove', (e) => {
  if (stan.widok !== 'spacer' || !dol || !renderer.domElement.hasPointerCapture(e.pointerId)) return;
  spacer.yaw = dol.yaw - (e.clientX - dol.x) * 0.005;
  spacer.pitch = THREE.MathUtils.clamp(dol.pitch - (e.clientY - dol.y) * 0.005, -1.2, 1.2);
  ustawSpojrzenie();
  brudne = true;
});
renderer.domElement.addEventListener('pointerup', (e) => {
  if (dol && Math.hypot(e.clientX - dol.x, e.clientY - dol.y) < 5) {
    const r = renderer.domElement.getBoundingClientRect();
    mysz.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    promien.setFromCamera(mysz, kamera);
    // pomija schowane ściany, szkło i meble-duchy — klik trafia w to, co widać
    let o = promien.intersectObjects([grupaMebli, lokal], true)
      .find((h) => h.object.material !== NIEWIDOCZNY && !(h.object.material.transparent && h.object.material.opacity < 0.5))?.object;
    while (o && !o.userData.id) o = o.parent;
    wybierz(o?.userData.id ?? null);
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
  if (stan.widok === 'orbita') ruch = orbita.update() || ruch;
  ruch = krokSpaceru(dt) || ruch;
  if (stan.gra) {
    const d = stan.doba, w = d.wschod ?? 0, z = d.zachod ?? 1440;
    stan.minuty += dt * 60;  // godzina doby na sekundę
    if (stan.minuty > z + 30) stan.minuty = Math.max(0, w - 30);
    odswiezSlonce();
  }
  if (ruch || brudne) {
    domekDlaLalek();
    renderer.render(scena, kamera);
    etykiety.render(scena, kamera);
    brudne = false;
  }
});

odswiezUklady();
const szkic = wczytajSzkic();
if (szkic.size) {
  przywrocStan(new Map([...szkic].map(([id, v]) => [id, { box: v.box.map(Number), front: v.front ?? undefined }])));
  toast(`Przywrócono niezapisane przestawienia (${szkic.size})`);
}
rozmiar();
zAdresu();
