// Scena 3D lokalu z danych planera (dane.json z planer3d/eksport_web.py). Jednostki modelu: cm, sceny: m.
// Osie: X three.js = x modelu (w prawo), −Z = y modelu (góra rzutu), Y = wysokość nad podłogą wykończoną.
// Wykończenie wyłącznie z danych: kolor ścian pomieszczenia (po stronie wnętrza), podłoga wg rodzaju, okładziny,
// kolory elementów i wybrane warianty. Meble to bryły parametryczne wg kategorii z modelu i ich wymiarów.
import * as THREE from 'three';
import { wPomieszczeniu, katSkrzydla, jestOknem } from './kontrole.js';
import { kolorCelu } from './warianty.js';

// neutralne kolory tego, czego model nie opisuje (jak rysunki/glb.py)
export const KOLORY = {
  sciana: '#EDEBE6', sufit: '#F7F6F3', plyta: '#D8D2C8', kontekst: '#DADADA', grzejnik: '#F4F4F2',
  rama: '#F4F4F2', drzwi: '#E9E4DA', drzwiWejsciowe: '#3B3936', szklo: '#DCEBF2', mebel: '#E9E4DA',
  ciemny: '#2B2825', metal: '#A7A9AB', ceramika: '#FBFAF7', blat: '#D9CBB4', lustro: '#D5DEE2',
  materac: '#F3F0EA', posciel: '#E6DFD3', poduszka: '#FAF8F4',
};
// kolor elementu bez koloru w modelu — wg kategorii
export const KOLORY_KATEGORII = {
  siedzisko: '#CFC3B3', sofa: '#BFB5A6', lozko: '#CFC3B3', stol: '#B89B72', stolik: '#B89B72',
  zabudowa_niska: '#E9E4DA', zabudowa_wysoka: '#E9E4DA', wiszaca: '#E9E4DA', sanitariat: '#FBFAF7',
  prysznic: '#D9D6D0', urzadzenie: '#E4E4E2', murek: '#EDEBE6', szklo: '#DCEBF2', lustro: '#D5DEE2', inne: '#E9E4DA',
};
// kolor podłogi wg rodzaju (jak rysunki/glb.py); rodzaj będący nazwą tokenu daje kolor tokenu
export const PODLOGI = { panele: '#C8A27A', deska: '#B08A5B', gres: '#D9D6D0', 'płyty tarasowe': '#A9A59E' };
const PODLOGA_INNA = '#CFC8BC';
const HEX = /^#[0-9a-f]{6}$/i;
const poprawny = (hex) => (typeof hex === 'string' && HEX.test(hex) ? hex : null);

export function uklad(dane) {
  const [x0, y0, x1, y1] = dane.meta.obrys;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  return {
    X: (x) => (x - cx) / 100,
    Z: (y) => -(y - cy) / 100,
    doModelu: (X, Z) => [X * 100 + cx, -Z * 100 + cy],
  };
}

const materialy = new Map();
export function mat(kolor, szorstkosc = 0.85) {
  const k = poprawny(kolor) ?? KOLORY.mebel, klucz = k + szorstkosc;
  if (!materialy.has(klucz)) materialy.set(klucz, new THREE.MeshStandardMaterial({ color: k, roughness: szorstkosc }));
  return materialy.get(klucz);
}
const SZKLO = new THREE.MeshStandardMaterial({ color: KOLORY.szklo, transparent: true, opacity: 0.2, roughness: 0.05, depthWrite: false });
const LUSTRO = new THREE.MeshStandardMaterial({ color: KOLORY.lustro, roughness: 0.08, metalness: 0.3 });

// ---------- kolory z danych i wariantów (te same w 3D i na rzucie) ----------
export const kolorMebla = (el, dane, wybory) =>
  kolorCelu(dane, wybory, 'element', el.id) ?? poprawny(el.kolor) ?? KOLORY_KATEGORII[el.kategoria] ?? KOLORY.mebel;
export const kolorScian = (dane, p, wybory) => kolorCelu(dane, wybory, 'sciany', p.nr) ?? poprawny(p.kolor_scian);
export const kolorOkladziny = (dane, o, wybory) => kolorCelu(dane, wybory, 'okladzina', o.id) ?? poprawny(o.hex) ?? KOLORY.sciana;

// ---------- tekstury rysowane w canvas (bez plików); każda zna swój wymiar w metrach ----------
function losowy(ziarno) {
  return () => (ziarno = (ziarno * 16807) % 2147483647) / 2147483647;
}
const rgb = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};
const css = (hex, f = 1) => `rgb(${rgb(hex).map((v) => Math.min(255, Math.round(v * f)))})`;
export const ciemniej = (hex, f) => `#${rgb(poprawny(hex) ?? KOLORY.mebel).map((v) => Math.min(255, Math.round(v * f)).toString(16).padStart(2, '0')).join('')}`;

const tekstury = new Map();
function tekstura(klucz, px, metry, rysuj) {
  if (!tekstury.has(klucz)) {
    const c = Object.assign(document.createElement('canvas'), { width: px, height: px });
    rysuj(c.getContext('2d'), px, losowy(7));
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    t.userData.metry = metry;
    tekstury.set(klucz, t);
  }
  return tekstury.get(klucz);
}
// deski w kolorze podłogi: pas 2,4 m, deski szer × dl cm, przesunięte styki
const deski = (hex, szer, dl) => tekstura(`deski${hex}${szer}${dl}`, 1024, 2.4, (g, n, los) => {
  const rzedy = Math.round(240 / szer), rzad = n / rzedy, deska = (n * dl) / 240, [r, gr, b] = rgb(hex);
  for (let i = 0; i < rzedy; i++) {
    for (let x = -Math.floor(los() * deska); x < n; x += deska) {
      const j = 0.9 + los() * 0.18;
      g.fillStyle = `rgb(${Math.min(255, r * j) | 0},${Math.min(255, gr * j) | 0},${Math.min(255, b * j) | 0})`;
      g.fillRect(x, i * rzad, deska, rzad);
      for (let k = 0; k < 14; k++) {
        g.fillStyle = `rgba(${(r * 0.6) | 0},${(gr * 0.52) | 0},${(b * 0.4) | 0},${0.04 + los() * 0.06})`;
        g.fillRect(x, i * rzad + los() * rzad, deska, 1 + los() * 2);
      }
      g.fillStyle = 'rgba(60,45,30,0.3)';
      g.fillRect(x, i * rzad, 2, rzad);
    }
    g.fillStyle = 'rgba(60,45,30,0.28)';
    g.fillRect(0, i * rzad, n, 1.5);
  }
});
// płytki kwadratowe bok × bok cm z fugą; tekstura to 2 × 2 płytki
const plytki = (hex, bok, fuga, kolorFugi) => tekstura(`plytki${hex}${bok}${fuga}${kolorFugi}`, 512, (2 * bok) / 100, (g, n, los) => {
  const t = n / 2, f = Math.max(1.5, (fuga / bok) * t);
  g.fillStyle = kolorFugi;
  g.fillRect(0, 0, n, n);
  for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
      g.fillStyle = css(hex, 0.97 + los() * 0.06);
      g.fillRect(i * t + f / 2, j * t + f / 2, t - f, t - f);
      for (let k = 0; k < 30; k++) {
        g.fillStyle = `rgba(${los() > 0.5 ? '255,255,255' : '0,0,0'},0.025)`;
        g.beginPath();
        g.arc(i * t + f / 2 + los() * (t - f), j * t + f / 2 + los() * (t - f), 2 + los() * 8, 0, 7);
        g.fill();
      }
    }
  }
});
function matTekstura(baza, szerM, wysM, szorstkosc = 0.8) {  // własna kopia z powtórzeniem w skali rzeczywistej
  const t = baza.clone();
  t.repeat.set(szerM / baza.userData.metry, wysM / baza.userData.metry);
  t.needsUpdate = true;
  const m = new THREE.MeshStandardMaterial({ map: t, roughness: szorstkosc });
  m.userData.jednorazowy = true;
  return m;
}
const podlogi = new Map();
function materialPodlogi(dane, p) {  // UV podłóg są w metrach, więc powtórzenie = 1 / wymiar tekstury
  const token = dane.tokeny?.[p.podloga];
  if (token && poprawny(token.hex)) return mat(token.hex, 0.7);
  const hex = PODLOGI[p.podloga] ?? PODLOGA_INNA;
  const baza = {
    panele: () => deski(hex, 20, 120),
    deska: () => deski(hex, 24, 240),
    gres: () => plytki(hex, 60, 0.3, ciemniej(hex, 0.86)),
    'płyty tarasowe': () => plytki(hex, 50, 1, ciemniej(hex, 0.62)),
  }[p.podloga];
  if (!baza) return mat(hex, 0.7);
  if (!podlogi.has(p.podloga)) {
    const t = baza().clone();
    t.repeat.set(1 / t.userData.metry, 1 / t.userData.metry);
    t.needsUpdate = true;
    podlogi.set(p.podloga, new THREE.MeshStandardMaterial({ map: t, roughness: p.podloga === 'gres' ? 0.5 : 0.7 }));
  }
  return podlogi.get(p.podloga);
}

// ---------- prymitywy ----------
function kostka(szer, wys, gleb, material, cien = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(szer, wys, gleb), material);
  m.castShadow = m.receiveShadow = cien;
  return m;
}
function bryla(u, b, z0, z1, material) {  // prostokąt z rzutu [cm] + zakres wysokości [cm]
  const w = (b[2] - b[0]) / 100, d = (b[3] - b[1]) / 100, h = (z1 - z0) / 100;
  if (w <= 0 || d <= 0 || h <= 0) return null;
  const m = kostka(w, h, d, material);
  m.position.set(u.X((b[0] + b[2]) / 2), (z0 + z1) / 200, u.Z((b[1] + b[3]) / 2));
  return m;
}
function plaszczyzna(u, poligon, z, material, doDolu = false, dziury = []) {  // podłoga (w górę) albo sufit (w dół)
  const punkty = (pol) => pol.map(([x, y]) => new THREE.Vector2(u.X(x), doDolu ? u.Z(y) : -u.Z(y)));
  const ksztalt = new THREE.Shape(punkty(poligon));
  ksztalt.holes = dziury.map((d) => new THREE.Path(punkty(d)));
  const g = new THREE.ShapeGeometry(ksztalt).rotateX(doDolu ? Math.PI / 2 : -Math.PI / 2);
  const m = new THREE.Mesh(g, material);
  m.position.y = z / 100;
  m.receiveShadow = !doDolu;
  m.castShadow = doDolu;  // sufit zasłania słońce z góry — światło wpada tylko przez okna
  return m;
}
// pierścień odsunięty o d cm na zewnątrz (d < 0 — do środka), narożniki na ostro; sufit wchodzi tak w bryły ścian
// i szacht, dzięki czemu w styku ściany z sufitem nie przecieka słońce
function odsunPierscien(pol, d) {
  let pole = 0;
  for (let i = 0; i < pol.length; i++) pole += pol[i][0] * pol[(i + 1) % pol.length][1] - pol[(i + 1) % pol.length][0] * pol[i][1];
  const zn = pole > 0 ? 1 : -1;
  const n = pol.map((a, i) => {
    const b = pol[(i + 1) % pol.length], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
    return [(zn * dy) / l, (-zn * dx) / l];
  });
  return pol.map((v, i) => {
    const n1 = n[(i + pol.length - 1) % pol.length], n2 = n[i], k = 1 + n1[0] * n2[0] + n1[1] * n2[1];
    return k < 0.2 ? v : [v[0] + (d * (n1[0] + n2[0])) / k, v[1] + (d * (n1[1] + n2[1])) / k];
  });
}
// strop nad sufitem podwieszanym: bryła niewidoczna, tylko rzuca cień. Sama płaszczyzna sufitu ma zerową grubość
// i filtr cienia (PCF) przepuszcza przy niej pasek słońca na górze ścian; gruba bryła zapisana do mapy cieni
// z obu stron (także górą) go zamyka. Pozostałe materiały zostają przy domyślnych ściankach tylnych — bez „trądziku”
const STROP = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, shadowSide: THREE.DoubleSide });
function strop(u, poligon, dziury, z0, z1) {
  const punkty = (pol) => pol.map(([x, y]) => new THREE.Vector2(u.X(x), -u.Z(y)));
  const ksztalt = new THREE.Shape(punkty(poligon));
  ksztalt.holes = dziury.map((d) => new THREE.Path(punkty(d)));
  const m = new THREE.Mesh(new THREE.ExtrudeGeometry(ksztalt, { depth: (z1 - z0) / 100, bevelEnabled: false }).rotateX(-Math.PI / 2), STROP);
  m.position.y = z0 / 100;
  m.castShadow = true;
  m.raycast = () => {};  // nie przechwytuje kliknięć w meble
  return m;
}
function walec(r, z0, z1, material, n = 32) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, z1 - z0, n), material);
  m.position.y = (z0 + z1) / 2;
  m.castShadow = m.receiveShadow = true;
  return m;
}

// cienki panel na licu: lico wzdłuż osi x (y = stala) albo y (x = stala); strona = +1/−1 — po której stronie lica
// jest pomieszczenie. Zwraca { mesh, box } — box służy do chowania razem ze ścianą w „domku dla lalek”.
function panel(u, os, stala, strona, a0, a1, z0, z1, material, gr = 0.6, odsuniecie = 0) {
  const s0 = stala + strona * odsuniecie, s1 = s0 + strona * gr;
  const c0 = Math.min(s0, s1), c1 = Math.max(s0, s1);
  const box = os === 'x' ? [a0, c0, a1, c1] : [c0, a0, c1, a1];
  const mesh = bryla(u, box, z0, z1, material);
  if (mesh) mesh.castShadow = false;
  return { mesh, box };
}

// ---------- stolarka (zwraca bryły, żeby dało się je chować razem ze ścianą) ----------
function okno(u, o) {
  const [x0, y0, x1, y1] = o.box, z0 = o.parapet ?? 0, z1 = o.wys_otw, p = 6;
  const [a0, a1] = o.poziomo ? [x0, x1] : [y0, y1];
  const c = o.poziomo ? (y0 + y1) / 2 : (x0 + x1) / 2;
  const pud = (b0, b1, c0, c1, h0, h1, m) => bryla(u, o.poziomo ? [b0, c0, b1, c1] : [c0, b0, c1, b1], h0, h1, m);
  const rama = mat(KOLORY.rama, 0.5);
  const czesci = [pud(a0, a0 + p, c - 4, c + 4, z0, z1, rama), pud(a1 - p, a1, c - 4, c + 4, z0, z1, rama),
    pud(a0, a1, c - 4, c + 4, z0, z0 + p, rama), pud(a0, a1, c - 4, c + 4, z1 - p, z1, rama)];
  const [szer, wys] = o.skrzydlo ?? [];
  if (szer && szer < a1 - a0 - 5) {  // skrzydło węższe niż otwór: słupek na jego krawędzi, reszta to panel stały
    const zawias = o.luk ? (o.poziomo ? o.luk.c[0] : o.luk.c[1]) : a0;
    const kraw = Math.abs(zawias - a0) <= Math.abs(zawias - a1) ? a0 + szer : a1 - szer;
    czesci.push(pud(kraw - 3, kraw + 3, c - 4, c + 4, z0, z1, rama));
  } else if (!o.skrzydlo) {  // bez danych o skrzydłach: podział na kwatery co ok. 110 cm
    const n = Math.max(1, Math.round((a1 - a0) / 110));
    for (let i = 1; i < n; i++) czesci.push(pud(a0 + ((a1 - a0) * i) / n - 3, a0 + ((a1 - a0) * i) / n + 3, c - 4, c + 4, z0, z1, rama));
  }
  if (wys && z0 + wys < z1 - 5) czesci.push(pud(a0, a1, c - 3, c + 3, z0 + wys - 3, z0 + wys + 3, rama));  // skrzydło niższe: nadświetle
  const szyba = pud(a0 + p, a1 - p, c - 0.5, c + 0.5, z0 + p, z1 - p, SZKLO);
  if (szyba) szyba.castShadow = szyba.receiveShadow = false;
  return [...czesci, szyba].filter(Boolean);
}
function drzwi(u, o) {  // skrzydło otwarte prostopadle do ściany, jak na rzucie
  if (!o.luk) return [];
  const { c, r } = o.luk, kat = (katSkrzydla(o.luk, o.poziomo) * Math.PI) / 180, szer = r / 100;
  const h = (o.skrzydlo?.[1] ?? Math.min(o.wys_otw - 5, 200)) / 100;
  const m = kostka(szer, h, 0.04, mat(o.rodzaj === 'drzwi wejściowe' ? KOLORY.drzwiWejsciowe : KOLORY.drzwi, 0.6));
  m.position.set(u.X(c[0]) + (Math.cos(kat) * szer) / 2, h / 2, u.Z(c[1]) - (Math.sin(kat) * szer) / 2);
  m.rotation.y = kat;
  return [m];
}

// ---------- farba ścian pomieszczenia: panele na licach brył ścian i szacht stykających się z wielokątem ----------
// krawędzie pierścienia w osiach; strona = po której stronie krawędzi jest pomieszczenie
// (wewnątrz obrysu, a przy dziurze — na zewnątrz pierścienia, niezależnie od kierunku obiegu)
function krawedzie(pol, dziura = false) {
  let pole = 0;
  for (let i = 0; i < pol.length; i++) {
    const [x0, y0] = pol[i], [x1, y1] = pol[(i + 1) % pol.length];
    pole += x0 * y1 - x1 * y0;
  }
  const znak = (pole > 0 ? 1 : -1) * (dziura ? -1 : 1), wynik = [];
  for (let i = 0; i < pol.length; i++) {
    const [x0, y0] = pol[i], [x1, y1] = pol[(i + 1) % pol.length];
    const os = Math.abs(y1 - y0) < 0.05 ? 'x' : Math.abs(x1 - x0) < 0.05 ? 'y' : null;
    if (!os) continue;  // krawędź ukośna — strefa wirtualna, bez ściany
    wynik.push({
      os, stala: os === 'x' ? y0 : x0,
      a0: os === 'x' ? Math.min(x0, x1) : Math.min(y0, y1), a1: os === 'x' ? Math.max(x0, x1) : Math.max(y0, y1),
      strona: os === 'x' ? Math.sign(x1 - x0) * znak : -Math.sign(y1 - y0) * znak,
    });
  }
  return wynik;
}
function malujPomieszczenie(u, dane, p, kolor, oslona) {
  const H = dane.meta.wysokosc, gora = p.zewnetrzne ? H : dane.meta.rzedna_sufitu, material = mat(kolor, 0.95);
  const lica = [...dane.sciany.map((s) => ({ box: s.box, z: s.z })), ...dane.szachty.map((s) => ({ box: s.box, z: [0, H] }))];
  for (const k of [...krawedzie(p.poligon), ...(p.dziury ?? []).flatMap((d) => krawedzie(d, true))]) {
    for (const l of lica) {
      const [x0, y0, x1, y1] = l.box;
      const [c0, c1, b0, b1] = k.os === 'x' ? [y0, y1, x0, x1] : [x0, x1, y0, y1];
      // bryła leży po drugiej stronie krawędzi niż wnętrze, więc jej lico wypada na linii krawędzi
      if (Math.abs((k.strona > 0 ? c1 : c0) - k.stala) > 0.6) continue;
      const lo = Math.max(k.a0, b0), hi = Math.min(k.a1, b1), z0 = l.z[0], z1 = Math.min(l.z[1], gora);
      // strefa wirtualna na tej linii nie ma bryły, więc zostaje bez farby
      if (hi - lo > 0.5 && z1 - z0 > 0.5) oslona(panel(u, k.os, k.stala, k.strona, lo, hi, z0, z1, material));
    }
  }
}

// okładzina z danych: pas na licu od strony pomieszczenia (normalna do wnętrza), wzór płytki albo gładka
function okladzinaZDanych(u, o, kolor) {
  const [ax, ay] = o.a, [bx, by] = o.b, [nx, ny] = o.normalna;
  const os = Math.abs(bx - ax) >= Math.abs(by - ay) ? 'x' : 'y';
  const stala = os === 'x' ? (ay + by) / 2 : (ax + bx) / 2, strona = Math.sign(os === 'x' ? ny : nx) || 1;
  const a0 = os === 'x' ? Math.min(ax, bx) : Math.min(ay, by), a1 = os === 'x' ? Math.max(ax, bx) : Math.max(ay, by);
  const [z0, z1] = o.z;
  if (a1 - a0 < 0.5 || z1 - z0 < 0.5) return null;
  const material = o.wzor === 'płytki'
    ? matTekstura(plytki(kolor, 20, 0.3, ciemniej(kolor, 0.84)), (a1 - a0) / 100, (z1 - z0) / 100, 0.35)
    : mat(kolor, 0.5);
  return panel(u, os, stala, strona, a0, a1, z0, z1, material, 0.8, 0.6);
}

export function zbudujLokal(dane, u, wybory) {
  const g = new THREE.Group();
  const dodaj = (...m) => g.add(...m.filter(Boolean));
  const H = dane.meta.wysokosc, RS = dane.meta.rzedna_sufitu;
  const sciana = mat(KOLORY.sciana, 0.95);
  dodaj(bryla(u, dane.meta.obrys, -8, 0, mat(KOLORY.plyta)));
  for (const p of dane.pomieszczenia) {
    dodaj(plaszczyzna(u, p.poligon, 0.2, materialPodlogi(dane, p), false, p.dziury));
    if (!p.zewnetrzne) {
      const obrys = odsunPierscien(p.poligon, 5), dziury = (p.dziury ?? []).map((d) => odsunPierscien(d, -5));
      dodaj(plaszczyzna(u, obrys, RS, mat(dane.meta.sufit || KOLORY.sufit, 0.95), true, dziury), strop(u, obrys, dziury, RS, Math.max(H, RS) + 20));
    }
  }
  // osłony = ściany, szachty, stolarka, farba i okładziny z prostokątem na rzucie; widok pokoju chowa te od strony kamery
  const oslony = [];
  const oslona = (o) => {
    if (!o?.mesh) return;
    g.add(o.mesh);
    oslony.push({ obiekt: o.mesh, box: o.box, material: o.mesh.material });
  };
  for (const s of dane.sciany) oslona({ mesh: bryla(u, s.box, s.z[0], s.z[1], sciana), box: s.box });
  for (const s of dane.szachty) oslona({ mesh: bryla(u, s.box, 0, H, sciana), box: s.box });
  for (const o of dane.otwory) for (const mesh of jestOknem(o) ? okno(u, o) : drzwi(u, o)) oslona({ mesh, box: o.box });
  const otoczenie = new THREE.MeshStandardMaterial({ color: KOLORY.kontekst, transparent: true, opacity: 0.35, depthWrite: false });
  otoczenie.userData.jednorazowy = true;
  for (const k of dane.kontekst) dodaj(bryla(u, k.box, k.z?.[0] ?? 0, k.z?.[1] ?? H, otoczenie));  // półprzezroczyste, ale rzucają cień
  for (const gr of dane.grzejniki) dodaj(bryla(u, gr.box, gr.z[0], gr.z[1], mat(KOLORY.grzejnik, 0.4)));
  for (const p of dane.pomieszczenia) {
    const kolor = kolorScian(dane, p, wybory);
    if (kolor) malujPomieszczenie(u, dane, p, kolor, oslona);
  }
  for (const o of dane.okladziny) oslona(okladzinaZDanych(u, o, kolorOkladziny(dane, o, wybory)));
  g.userData.oslony = oslony;
  return g;
}

// ---------- meble: bryła w układzie frontu (t: od tyłu −L/2 do frontu +L/2, s: w poprzek, z: wysokość w m) ----------
function ramaFrontu(szerX, glebY, front) {
  const osX = front === 'E' || front === 'W', zn = front === 'E' || front === 'S' ? 1 : -1;
  const L = osX ? szerX : glebY, S = osX ? glebY : szerX;
  const punkt = (t, s) => (osX ? [zn * t, s] : [s, zn * t]);  // (X, Z) w układzie grupy mebla
  return {
    L, S,
    kostka(t0, t1, s0, s1, z0, z1, material, cien = true) {
      if (t1 - t0 <= 0.0005 || s1 - s0 <= 0.0005 || z1 - z0 <= 0.0005) return null;
      const m = kostka(osX ? t1 - t0 : s1 - s0, z1 - z0, osX ? s1 - s0 : t1 - t0, material, cien);
      const [X, Z] = punkt((t0 + t1) / 2, (s0 + s1) / 2);
      m.position.set(X, (z0 + z1) / 2, Z);
      return m;
    },
    walec(t, s, r, z0, z1, material) {  // pionowy walec w punkcie (t, s)
      if (z1 - z0 <= 0.0005) return null;
      const m = walec(r, z0, z1, material, 20);
      [m.position.x, m.position.z] = punkt(t, s);
      return m;
    },
    tarcza(t, s, z, r, material) {  // krążek na płaszczyźnie frontu (np. drzwiczki pralki)
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.012, 32), material);
      if (osX) m.rotation.z = Math.PI / 2;
      else m.rotation.x = Math.PI / 2;
      const [X, Z] = punkt(t, s);
      m.position.set(X, z, Z);
      return m;
    },
  };
}
function frontKuCelowi(el, cel) {  // siedziska bez frontu w modelu: przodem do najbliższego stołu
  if (!cel) return 'S';
  const dx = cel[0] - (el.box[0] + el.box[2]) / 2, dy = cel[1] - (el.box[1] + el.box[3]) / 2;
  return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'E' : 'W') : dy > 0 ? 'N' : 'S';
}
// segmenty w układzie frontu, od lewej patrząc na front (jak lokal/plan.py); s rośnie na +X (fronty N/S) albo +Z (E/W)
function segmentyS(el, S) {
  const seg = el.segmenty || [], suma = seg.reduce((a, s) => a + (s.dl || 0), 0) || 1;
  const rosnaco = el.front === 'S' || el.front === 'W';
  let s = rosnaco ? -S / 2 : S / 2;
  return seg.map((sg) => {
    const d = ((sg.dl || 0) * S) / suma, a = s;
    s = rosnaco ? s + d : s - d;
    return { ...sg, a: Math.min(a, s), b: Math.max(a, s) };
  });
}
const podzialy = (el, S) => segmentyS(el, S).slice(0, -1).map((sg) => (el.front === 'S' || el.front === 'W' ? sg.b : sg.a));

const BEZ_OPARCIA = ['hoker', 'stołek', 'ławka'];
const Z_BLATEM = ['ciąg kuchenny', 'wyspa'];

export function zbudujMebel(el, u, { kolor, cel }) {
  const grupa = new THREE.Group();
  const [x0, y0, x1, y1] = el.box;
  grupa.position.set(u.X((x0 + x1) / 2), 0, u.Z((y0 + y1) / 2));
  grupa.userData = { id: el.id };
  const kat = el.kategoria ?? 'inne', rodzaj = el.rodzaj ?? '';
  const k = mat(kolor, 0.8), ciemny = mat(ciemniej(kolor, 0.6), 0.7);
  const z0 = el.wys[0] / 100, z1 = Math.max(el.wys[1], el.wys[0] + 1) / 100;
  const F = ramaFrontu((x1 - x0) / 100, (y1 - y0) / 100, el.front || frontKuCelowi(el, cel));
  const { L, S } = F;
  const dodaj = (...m) => grupa.add(...m.flat().filter(Boolean));
  const nogi = (r, zOd, zDo, material, wciecie = 0.03) => [-1, 1].flatMap((i) => [-1, 1].map((j) =>
    F.kostka(i * (L / 2 - wciecie) - r, i * (L / 2 - wciecie) + r, j * (S / 2 - wciecie) - r, j * (S / 2 - wciecie) + r, zOd, zDo, material)));
  // korpus zabudowy: cokół, bryła, blat, fugi między segmentami frontu
  const korpus = (cokol, blat) => {
    const czesci = [];
    if (cokol) czesci.push(F.kostka(-L / 2, L / 2 - 0.05, -S / 2, S / 2, z0, z0 + cokol, ciemny));
    czesci.push(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0 + cokol, z1 - blat, k));
    if (blat) czesci.push(F.kostka(-L / 2, L / 2 + 0.01, -S / 2, S / 2, z1 - blat, z1, mat(KOLORY.blat, 0.45)));
    if (el.front) {
      for (const s of podzialy(el, S)) czesci.push(F.kostka(L / 2 - 0.002, L / 2 + 0.004, s - 0.003, s + 0.003, z0 + cokol + 0.02, z1 - blat - 0.02, ciemny, false));
    }
    return czesci;
  };

  if (el.ksztalt === 'kolo') {  // bryły okrągłe: box to obwiednia (elipsa, gdy boki różne)
    const R = (x1 - x0) / 200, spl = (y1 - y0) / (x1 - x0) || 1;
    const czesci = kat === 'stol' || kat === 'stolik'
      ? [walec(R, z1 - 0.04, z1, k), walec(0.05, z0, z1 - 0.04, ciemny), walec(R * 0.45, z0, z0 + 0.03, ciemny)]
      : kat === 'siedzisko' && z1 > 0.6
        ? [walec(R, z1 - 0.06, z1, k), walec(0.025, 0, z1 - 0.06, ciemny), walec(R * 0.8, 0, 0.02, ciemny)]
        : [walec(R, z0, z1, k)];
    for (const m of czesci) m.scale.z = spl;
    dodaj(czesci);
    return grupa;
  }

  switch (kat) {
    case 'lozko': {
      const materac = Math.max(z1, 0.4), rama = Math.max(0.12, materac - 0.22);
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, rama, k),
        F.kostka(-L / 2 + 0.06, L / 2 - 0.02, -S / 2 + 0.03, S / 2 - 0.03, rama, materac, mat(KOLORY.materac)),
        F.kostka(-L / 2, -L / 2 + 0.08, -S / 2, S / 2, z0, materac + 0.45, k),  // wezgłowie przy tylnej krawędzi
        F.kostka(-L / 2 + 0.55, L / 2 - 0.01, -S / 2 + 0.01, S / 2 - 0.01, materac, materac + 0.05, mat(KOLORY.posciel)));
      const n = S > 1.1 ? 2 : 1;
      for (let i = 0; i < n; i++) {
        dodaj(F.kostka(-L / 2 + 0.12, -L / 2 + 0.5, -S / 2 + (S * i) / n + 0.07, -S / 2 + (S * (i + 1)) / n - 0.07, materac, materac + 0.12, mat(KOLORY.poduszka)));
      }
      break;
    }
    case 'sofa': {
      const siedz = Math.min(0.44, z1 * 0.52), oparcie = Math.min(0.25, L * 0.3), bok = S > 1.2 ? 0.18 : 0.1;
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0 + 0.05, siedz, k), F.kostka(-L / 2, -L / 2 + oparcie, -S / 2, S / 2, siedz, z1, k),
        F.kostka(-L / 2, L / 2, -S / 2, -S / 2 + bok, siedz, siedz + 0.2, k), F.kostka(-L / 2, L / 2, S / 2 - bok, S / 2, siedz, siedz + 0.2, k),
        nogi(0.02, z0, z0 + 0.05, ciemny, 0.06));
      break;
    }
    case 'siedzisko': {
      if (rodzaj === 'pufa' || (z1 <= 0.5 && !BEZ_OPARCIA.includes(rodzaj))) {
        dodaj(F.kostka(-L / 2 + 0.01, L / 2 - 0.01, -S / 2 + 0.01, S / 2 - 0.01, z0, z1, k));
      } else if (BEZ_OPARCIA.includes(rodzaj)) {  // siedzisko na nogach (hoker, stołek, ławka)
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z1 - 0.05, z1, k), nogi(0.015, z0, z1 - 0.05, ciemny, 0.04));
      } else if (rodzaj === 'fotel biurowy') {
        const siedz = Math.min(0.5, z1 - 0.25), r = Math.min(L, S) / 2;
        dodaj(F.kostka(-L / 2 + 0.04, L / 2 - 0.04, -S / 2 + 0.04, S / 2 - 0.04, siedz - 0.07, siedz, k),
          F.kostka(-L / 2 + 0.04, -L / 2 + 0.1, -S / 2 + 0.08, S / 2 - 0.08, siedz + 0.05, z1, k),
          F.walec(0, 0, 0.025, 0.08, siedz - 0.07, ciemny), F.walec(0, 0, r * 0.85, z0 + 0.03, z0 + 0.08, ciemny));
      } else if (Math.min(L, S) >= 0.6) {  // fotel: tapicerowana baza, oparcie, podłokietniki
        const siedz = Math.min(0.44, z1 * 0.5);
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0 + 0.05, siedz, k), F.kostka(-L / 2, -L / 2 + Math.min(0.2, L * 0.3), -S / 2, S / 2, siedz, z1, k),
          F.kostka(-L / 2, L / 2, -S / 2, -S / 2 + 0.12, siedz, siedz + 0.2, k), F.kostka(-L / 2, L / 2, S / 2 - 0.12, S / 2, siedz, siedz + 0.2, k),
          nogi(0.02, z0, z0 + 0.05, ciemny, 0.05));
      } else {  // krzesło: siedzisko, oparcie przy tylnej krawędzi, cztery nogi
        const siedz = Math.max(0.3, Math.min(0.47, z1 - 0.3));
        dodaj(F.kostka(-L / 2 + 0.02, L / 2 - 0.02, -S / 2 + 0.02, S / 2 - 0.02, siedz - 0.04, siedz, k),
          F.kostka(-L / 2 + 0.02, -L / 2 + 0.05, -S / 2 + 0.02, S / 2 - 0.02, siedz, z1, k), nogi(0.015, z0, siedz - 0.04, k, 0.04));
      }
      break;
    }
    case 'stol':
    case 'stolik': {
      const blat = kat === 'stol' ? 0.04 : 0.03;
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z1 - blat, z1, k));
      if (kat === 'stol' && el.front) {  // biurko, toaletka: pełne boki i blenda od tyłu
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, -S / 2 + 0.025, z0, z1 - blat, k), F.kostka(-L / 2, L / 2, S / 2 - 0.025, S / 2, z0, z1 - blat, k),
          F.kostka(-L / 2 + 0.02, -L / 2 + 0.04, -S / 2 + 0.025, S / 2 - 0.025, Math.max(z0, z1 - 0.4), z1 - blat, k));
      } else dodaj(nogi(kat === 'stol' ? 0.025 : 0.02, z0, z1 - blat, kat === 'stol' ? k : ciemny, 0.05));
      break;
    }
    case 'zabudowa_niska': {
      dodaj(korpus(z0 < 0.01 ? 0.08 : 0, Z_BLATEM.includes(rodzaj) ? 0.04 : 0));
      if (rodzaj === 'szafka z umywalką') {  // blat z umywalką i bateria przy ścianie
        const cer = mat(KOLORY.ceramika, 0.3);
        dodaj(F.kostka(-L / 2, L / 2 + 0.01, -S / 2, S / 2, z1, z1 + 0.02, cer),
          F.kostka(-L / 2 + 0.1, L / 2 - 0.06, -S / 2 + 0.1, S / 2 - 0.1, z1 + 0.02, z1 + 0.022, mat('#C9CCCE', 0.3), false),
          F.walec(-L / 2 + 0.05, 0, 0.012, z1 + 0.02, z1 + 0.2, mat(KOLORY.metal, 0.3)));
      }
      break;
    }
    case 'zabudowa_wysoka': {
      if (rodzaj === 'regał') {  // otwarte półki co ok. 35 cm
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, -S / 2 + 0.02, z0, z1, k), F.kostka(-L / 2, L / 2, S / 2 - 0.02, S / 2, z0, z1, k),
          F.kostka(-L / 2, -L / 2 + 0.01, -S / 2, S / 2, z0, z1, k));
        const n = Math.max(1, Math.round((z1 - z0) / 0.35));
        for (let i = 0; i <= n; i++) dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0 + ((z1 - z0 - 0.02) * i) / n, z0 + ((z1 - z0 - 0.02) * i) / n + 0.02, k));
      } else if (rodzaj === 'witryna') {  // rama, szyba na froncie, półki
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z0 + 0.03, k), F.kostka(-L / 2, L / 2, -S / 2, S / 2, z1 - 0.03, z1, k),
          F.kostka(-L / 2, -L / 2 + 0.02, -S / 2, S / 2, z0, z1, k), F.kostka(-L / 2, L / 2, -S / 2, -S / 2 + 0.02, z0, z1, k),
          F.kostka(-L / 2, L / 2, S / 2 - 0.02, S / 2, z0, z1, k), F.kostka(L / 2 - 0.012, L / 2, -S / 2 + 0.02, S / 2 - 0.02, z0 + 0.03, z1 - 0.03, SZKLO, false));
        for (let i = 1; i < 4; i++) dodaj(F.kostka(-L / 2, L / 2 - 0.02, -S / 2, S / 2, z0 + ((z1 - z0) * i) / 4, z0 + ((z1 - z0) * i) / 4 + 0.02, k));
      } else dodaj(korpus(z0 < 0.01 ? 0.08 : 0, 0));
      break;
    }
    case 'wiszaca':
      dodaj(korpus(0, 0));
      break;
    case 'sanitariat': {
      if (rodzaj === 'toaleta' || rodzaj === 'bidet') {
        const h = Math.min(z1, 0.42);
        if (rodzaj === 'toaleta' && z1 >= 0.6) dodaj(F.kostka(-L / 2, -L / 2 + 0.18, -S / 2 + 0.02, S / 2 - 0.02, h, z1, k));  // zbiornik
        dodaj(F.kostka(-L / 2 + 0.06, L / 2 - 0.12, -S * 0.22, S * 0.22, z0, h - 0.1, k),
          F.kostka(-L / 2 + 0.02, L / 2, -S / 2 + 0.03, S / 2 - 0.03, h - 0.1, h - 0.02, k),
          F.kostka(-L / 2 + 0.04, L / 2 - 0.01, -S / 2 + 0.035, S / 2 - 0.035, h - 0.02, h, mat('#FFFFFF', 0.3)));
      } else if (rodzaj === 'umywalka') {
        const dol = Math.max(z0, z1 - 0.15);
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, dol, z1, k),
          F.kostka(-L / 2 + 0.08, L / 2 - 0.05, -S / 2 + 0.06, S / 2 - 0.06, z1 - 0.002, z1 + 0.001, mat('#C9CCCE', 0.3), false),
          F.walec(-L / 2 + 0.04, 0, 0.012, z1, z1 + 0.18, mat(KOLORY.metal, 0.3)));
        if (z0 < 0.3 && dol > 0.3) dodaj(F.kostka(-L / 4, L / 4, -S / 6, S / 6, 0, dol, k));  // postument
      } else if (rodzaj === 'wanna') {
        dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, k),
          F.kostka(-L / 2 + 0.07, L / 2 - 0.07, -S / 2 + 0.07, S / 2 - 0.07, z1 - 0.002, z1 + 0.001, mat('#E3E6E8', 0.3), false));
      } else dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, k));
      break;
    }
    case 'prysznic': {  // brodzik albo posadzka strefy prysznica; przy froncie szyba walk-in na 2/3 szerokości
      const brodzik = Math.max(0.02, Math.min(0.05, z1 - z0));
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z0 + brodzik, k));
      if (el.front && z1 - z0 > 1) dodaj(F.kostka(L / 2 - 0.01, L / 2, -S / 2, -S / 2 + S * 0.66, z0 + brodzik, Math.min(z1, 2.1), SZKLO, false));
      break;
    }
    case 'urzadzenie': {
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, k));
      const h = z1 - z0;
      if (rodzaj === 'pralka' || rodzaj === 'pralko-suszarka') {
        const r = Math.min(S, h) * 0.3;
        dodaj(F.tarcza(L / 2 + 0.006, 0, z0 + h * 0.55, r, ciemny), F.tarcza(L / 2 + 0.012, 0, z0 + h * 0.55, r * 0.75, SZKLO));
      } else if (h > 1.2) dodaj(F.kostka(L / 2, L / 2 + 0.004, -S / 2 + 0.01, S / 2 - 0.01, z0 + h * 0.36, z0 + h * 0.36 + 0.006, ciemny, false));
      else if (el.front) dodaj(F.kostka(L / 2, L / 2 + 0.02, -S * 0.35, S * 0.35, z1 - 0.1, z1 - 0.08, mat(KOLORY.metal, 0.3), false));
      break;
    }
    case 'szklo':
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, SZKLO, false));
      break;
    case 'lustro':
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, LUSTRO, false));
      break;
    default:  // murek, inne
      dodaj(F.kostka(-L / 2, L / 2, -S / 2, S / 2, z0, z1, k));
  }
  return grupa;
}

// ---------- światło sztuczne z punktów elektryki (lokal/model.py: jest_swiatlem) ----------
function kierunekDoWnetrza(dane, s) {  // punkt na licu ściany: kierunek w głąb jego pomieszczenia
  const pokoj = dane.pomieszczenia.find((p) => p.nr === s.pomieszczenie);
  const probki = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const wPokoju = (q) => (pokoj ? wPomieszczeniu(q, pokoj) : dane.pomieszczenia.some((p) => wPomieszczeniu(q, p)));
  return probki.find(([a, b]) => wPokoju([s.xy[0] + a * 15, s.xy[1] + b * 15])) ?? [0, 0];
}

export function zbudujSwiatla(dane, u) {
  const grupa = new THREE.Group(), lampy = [];
  const RS = dane.meta.rzedna_sufitu / 100;
  const oprawa = new THREE.MeshStandardMaterial({ color: '#FFF6E8', emissive: '#FFC98A', emissiveIntensity: 0 });
  const klosz = new THREE.MeshStandardMaterial({ color: '#FBF3E6', emissive: '#FFD7A0', emissiveIntensity: 0, roughness: 0.4, side: THREE.DoubleSide });
  const czern = mat(KOLORY.ciemny, 0.5), metal = mat(KOLORY.metal, 0.35);
  const stoly = Object.values(dane.meble).flat().filter((e) => e.kategoria === 'stol');
  const lampa = (x, y, z, waga) => {
    const l = new THREE.PointLight('#FFD3A6', 0, 7, 2);  // ok. 2700 K
    l.position.set(x, y, z);
    l.userData.waga = waga;
    grupa.add(l);
    lampy.push(l);
  };
  for (const s of dane.swiatla) {
    const X = u.X(s.xy[0]), Z = u.Z(s.xy[1]), wariant = s.wariant ?? '';
    if (s.typ === 'punkt świetlny' && wariant.includes('zwis')) {  // zwis: nad stołem 75 cm nad blatem, gdzie indziej ok. 195
      const stol = stoly.find((e) => s.xy[0] > e.box[0] && s.xy[0] < e.box[2] && s.xy[1] > e.box[1] && s.xy[1] < e.box[3]);
      const dol = Math.min(RS - 0.3, stol ? stol.wys[1] / 100 + 0.75 : 1.95);
      const k = new THREE.Mesh(new THREE.SphereGeometry(stol ? 0.2 : 0.09, 32, 16), klosz);
      if (stol) k.scale.set(1, 0.42, 1);
      k.position.set(X, dol, Z);
      const kabel = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, RS - dol), czern);
      kabel.position.set(X, (RS + dol) / 2, Z);
      grupa.add(kabel, k);
      lampa(X, dol - 0.06, Z, stol ? 1 : 0.6);
    } else if (s.typ === 'punkt świetlny') {  // plafon — widoczny tylko od dołu
      const z = Math.min(s.h ?? dane.meta.rzedna_sufitu, dane.meta.rzedna_sufitu) / 100;
      const m = new THREE.Mesh(new THREE.CircleGeometry(0.07, 24).rotateX(Math.PI / 2), oprawa);
      m.position.set(X, z - 0.005, Z);
      grupa.add(m);
      lampa(X, z - 0.08, Z, 1);
    } else if (s.typ === 'kinkiet') {  // kinkiet: klosz 12 cm od lica ściany
      const [dx, dy] = kierunekDoWnetrza(dane, s);
      const zk = (s.h ?? 170) / 100, Xk = u.X(s.xy[0] + dx * 12), Zk = u.Z(s.xy[1] + dy * 12);
      const ramie = kostka(0.02, 0.02, 0.02, metal, false);
      ramie.position.set(u.X(s.xy[0] + dx * 6), zk, u.Z(s.xy[1] + dy * 6));
      const k = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.12, 24, 1, true), klosz);
      k.position.set(Xk, zk + 0.02, Zk);
      grupa.add(ramie, k);
      lampa(Xk, zk, Zk, 0.5);
    } else {  // wypust oświetleniowy (np. LED pod szafkami): samo światło tuż przed licem
      const [dx, dy] = kierunekDoWnetrza(dane, s);
      lampa(u.X(s.xy[0] + dx * 10), (s.h ?? 220) / 100 - 0.03, u.Z(s.xy[1] + dy * 10), 0.4);
    }
  }
  return {
    grupa,
    ustaw(moc) {
      for (const l of lampy) l.intensity = moc * l.userData.waga;
      oprawa.emissiveIntensity = moc > 0 ? 2 : 0;
      klosz.emissiveIntensity = moc > 0 ? 1.6 : 0;
    },
  };
}
