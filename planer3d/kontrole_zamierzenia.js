// Kontrole planera modelu zamierzenia — czyste funkcje na obrysach w cm modelu (oś y = góra rzutu).
// Obrys to wielokąt [[x, y], …] (pierwszy punkt bez powtórzenia na końcu), łamana [[x, y], …] albo punkt [x, y].
// Działają w przeglądarce i w Node (bez DOM i three.js). Kolizje liczą się jak w zamierzenie/waliduj.py:
// część wspólna w planie (linia i punkt jako pas albo koło 20 cm) i w pionie (zakres z). Do tego odległość
// między dwoma obiektami (obiekt odniesienia w planerze) i szkic przesunięć z odciskiem położenia z modelu.
import { wPoligonie } from './kontrole.js';

export { wPoligonie };

const TOL = 0.01;   // cm: bliżej niż tyle to styk, nie nakładanie
const PROBKA = 0.1;   // cm: punkt kontrolny tuż za krawędzią, po stronie wnętrza wielokąta
const POLPAS = 10;   // cm: połowa szerokości pasa linii i promień koła punktu

export const jestPunktem = (obrys) => typeof obrys[0] === 'number';

export function przesun(obrys, dx, dy) {
  return jestPunktem(obrys) ? [obrys[0] + dx, obrys[1] + dy] : obrys.map(([x, y]) => [x + dx, y + dy]);
}

// odcinki łamanej albo pierścienia (zamknięty: z krawędzią od ostatniego punktu do pierwszego); punkt to odcinek zerowy
function odcinki(obrys, zamkniety) {
  if (jestPunktem(obrys)) return [[obrys, obrys]];
  if (obrys.length === 1) return [[obrys[0], obrys[0]]];
  const w = [];
  for (let i = 0; i + 1 < obrys.length; i++) w.push([obrys[i], obrys[i + 1]]);
  if (zamkniety && obrys.length > 2) w.push([obrys[obrys.length - 1], obrys[0]]);
  return w;
}

// najbliższy punkt odcinka [a, b] do punktu p
function rzut(p, [a, b]) {
  const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2)) : 0;
  return [a[0] + t * dx, a[1] + t * dy];
}
const odl = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]);

// strona punktu c względem prostej a→b: 1 / −1, a 0 bliżej niż TOL od prostej
function strona(a, b, c) {
  const v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]), dl = odl(a, b);
  return v > TOL * dl ? 1 : v < -TOL * dl ? -1 : 0;
}

// punkt przecięcia odcinków przecinających się we wnętrzu obu (bez styku końcem i bez nakładania współliniowego)
function przeciecie([a, b], [c, d]) {
  if (strona(c, d, a) * strona(c, d, b) !== -1 || strona(a, b, c) * strona(a, b, d) !== -1) return null;
  const r = [b[0] - a[0], b[1] - a[1]], s = [d[0] - c[0], d[1] - c[1]];
  const t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / (r[0] * s[1] - r[1] * s[0]);
  return [a[0] + t * r[0], a[1] + t * r[1]];
}

// najbliższe punkty dwóch obrysów: {odl, od (na a), do (na b), przecina}; przecina — brzegi przecinają się we wnętrzu
// obu odcinków (odl 0; np. krawędź obiektu przez wcięcie działki wklęsłej), styk końcem albo odcinkiem to nie przecięcie
export function najblizszePunkty(a, b, zamknietyA = true, zamknietyB = true) {
  let naj = { odl: Infinity, od: null, do: null, przecina: false };
  for (const s of odcinki(a, zamknietyA)) {
    for (const t of odcinki(b, zamknietyB)) {
      const x = przeciecie(s, t);
      if (x) return { odl: 0, od: x, do: x, przecina: true };
      for (const [p, q] of [[s[0], rzut(s[0], t)], [s[1], rzut(s[1], t)]]) if (odl(p, q) < naj.odl) naj = { odl: odl(p, q), od: p, do: q, przecina: false };
      for (const [q, p] of [[t[0], rzut(t[0], s)], [t[1], rzut(t[1], s)]]) if (odl(p, q) < naj.odl) naj = { odl: odl(p, q), od: p, do: q, przecina: false };
    }
  }
  return naj;
}

// najmniejsza odległość obrysu od pierścienia granicy (cm; przecięcie granicy daje 0); zamkniety = false dla łamanej (linia)
export const odlegloscOdGranicy = (obrys, granica, zamkniety = true) => najblizszePunkty(obrys, granica, zamkniety, true).odl;

// punkt wewnątrz wielokąta i dalej niż TOL od jego brzegu
function wewnatrz(p, pol) {
  return wPoligonie(p, pol) && odcinki(pol, true).every((s) => odl(p, rzut(p, s)) > TOL);
}

function obwiednia(obrys) {
  const p = jestPunktem(obrys) ? [obrys] : obrys;
  return [Math.min(...p.map((q) => q[0])), Math.min(...p.map((q) => q[1])), Math.max(...p.map((q) => q[0])), Math.max(...p.map((q) => q[1]))];
}

// punkty tuż za środkiem każdej krawędzi, po stronie wnętrza (kierunek obiegu z pola ze znakiem)
function probki(pol) {
  let pole = 0;
  for (let i = 0; i < pol.length; i++) pole += pol[i][0] * pol[(i + 1) % pol.length][1] - pol[(i + 1) % pol.length][0] * pol[i][1];
  const zn = pole > 0 ? 1 : -1;
  return odcinki(pol, true).filter(([a, b]) => odl(a, b) > 4 * PROBKA).map(([a, b]) => {
    const d = odl(a, b), nx = (-zn * (b[1] - a[1])) / d, ny = (zn * (b[0] - a[0])) / d;
    return [(a[0] + b[0]) / 2 + nx * PROBKA, (a[1] + b[1]) / 2 + ny * PROBKA];
  });
}

// wielokąty mają wspólne wnętrze (styk krawędzią albo wierzchołkiem to nie nakładanie)
export function nachodza(a, b) {
  const [ax0, ay0, ax1, ay1] = obwiednia(a), [bx0, by0, bx1, by1] = obwiednia(b);
  if (ax0 >= bx1 - TOL || bx0 >= ax1 - TOL || ay0 >= by1 - TOL || by0 >= ay1 - TOL) return false;
  const A = odcinki(a, true), B = odcinki(b, true);
  if (A.some((s) => B.some((t) => przeciecie(s, t)))) return true;
  if (a.some((p) => wewnatrz(p, b)) || b.some((p) => wewnatrz(p, a))) return true;
  // bez przecięć i bez wierzchołków we wnętrzu wspólne wnętrze leży przy krawędzi (np. wspólne krawędzie, te same obrysy)
  return probki(a).some((p) => wewnatrz(p, b)) || probki(b).some((p) => wewnatrz(p, a));
}

const wielokat = (o) => !jestPunktem(o.obrys2d) && o.ksztalt !== 'linia' && o.obrys2d.length > 2;

function wPlanie(a, b) {
  const wa = wielokat(a), wb = wielokat(b);
  if (wa && wb) return nachodza(a.obrys2d, b.obrys2d);
  if (wa || wb) {  // linia albo punkt (pas 20 cm) i wielokąt
    const [w, l] = wa ? [a, b] : [b, a], punkty = jestPunktem(l.obrys2d) ? [l.obrys2d] : l.obrys2d;
    return punkty.some((p) => wewnatrz(p, w.obrys2d)) || najblizszePunkty(l.obrys2d, w.obrys2d, false, true).odl < POLPAS - TOL;
  }
  return najblizszePunkty(a.obrys2d, b.obrys2d, false, false).odl < 2 * POLPAS - TOL;
}

function wPionie(a, b) {
  const [a0, a1] = a.z ?? [-Infinity, Infinity], [b0, b1] = b.z ?? [-Infinity, Infinity];
  return Math.min(a1, b1) > Math.max(a0, b0);
}

// pary [idA, idB] obiektów z kolizja: true, które nachodzą na siebie w planie i w pionie (kolejność jak na liście)
export function kolizje(obiekty) {
  const lista = obiekty.filter((o) => o.kolizja && o.obrys2d?.length);
  const pary = [];
  for (let i = 0; i < lista.length; i++) {
    for (let j = i + 1; j < lista.length; j++) if (wPionie(lista[i], lista[j]) && wPlanie(lista[i], lista[j])) pary.push([lista[i].id, lista[j].id]);
  }
  return pary;
}

// punkt poza wszystkimi wielokątami granic i dalej niż TOL od ich brzegów
const pozaGranic = (p, granice) => granice.every((g) => !wPoligonie(p, g) && odcinki(g, true).every((s) => odl(p, rzut(p, s)) > TOL));

// czy jakaś część obrysu leży poza wszystkimi granicami: wierzchołek albo kawałek krawędzi między jej przecięciami
// i stykami z brzegami granic (działka wklęsła: wierzchołki w działce, krawędź przez wcięcie); zamkniety = false
// dla łamanej (linia). Kilka działek to jedna całość: obiekt nad wspólną granicą dwóch działek nie leży poza
export function poza(obrys, granice, zamkniety = true) {
  if (!granice.length) return false;
  if (jestPunktem(obrys)) return pozaGranic(obrys, granice);
  if (obrys.some((p) => pozaGranic(p, granice))) return true;
  const brzegi = granice.flatMap((g) => odcinki(g, true));
  return odcinki(obrys, zamkniety).some(([p, q]) => {
    const dl = odl(p, q);
    if (dl <= 2 * TOL) return false;
    const t = [0, 1];  // podział krawędzi: przecięcia z brzegami i wierzchołki granic leżące na krawędzi (0..1 wzdłuż p→q)
    for (const e of brzegi) {
      const x = przeciecie([p, q], e);
      if (x) t.push(odl(p, x) / dl);
      for (const v of e) {
        if (odl(v, rzut(v, [p, q])) <= TOL) t.push(Math.min(1, Math.max(0, ((v[0] - p[0]) * (q[0] - p[0]) + (v[1] - p[1]) * (q[1] - p[1])) / (dl * dl))));
      }
    }
    t.sort((a, b) => a - b);
    for (let i = 0; i + 1 < t.length; i++) {
      if ((t[i + 1] - t[i]) * dl <= 2 * TOL) continue;
      const k = (t[i] + t[i + 1]) / 2;
      if (pozaGranic([p[0] + k * (q[0] - p[0]), p[1] + k * (q[1] - p[1])], granice)) return true;
    }
    return false;
  });
}

// odległość obiektu a od obiektu b ({obrys2d, ksztalt}; linia — łamana, punkt — oś pnia): {odl, od (na a), do (na b),
// nachodza}; nachodza — obrysy mają część wspólną (wspólne wnętrze wielokątów, punkt albo linia w wielokącie,
// przecinające się brzegi): odl 0, bez odcinka wymiaru. Styk krawędzią albo punktem to odl 0 bez nakładania
export function odlegloscObiektow(a, b) {
  const wa = wielokat(a), wb = wielokat(b);
  const w = najblizszePunkty(a.obrys2d, b.obrys2d, wa, wb);
  const punkty = (o) => (jestPunktem(o.obrys2d) ? [o.obrys2d] : o.obrys2d);
  const wspolne = w.przecina || (wa && wb ? nachodza(a.obrys2d, b.obrys2d)
    : wa ? punkty(b).some((p) => wewnatrz(p, a.obrys2d)) : wb ? punkty(a).some((p) => wewnatrz(p, b.obrys2d)) : false);
  return wspolne ? { odl: 0, od: null, do: null, nachodza: true } : { odl: w.odl, od: w.od, do: w.do, nachodza: false };
}

// ---------- szkic planera (localStorage): przesunięcia z odciskiem położenia obiektu w modelu ----------
// odcisk położenia bazowego obiektu z modelu: krótki skrót (FNV-1a, 8 znaków hex) współrzędnych obrys2d zaokrąglonych
// do 0,1 cm; inny odcisk przy wczytaniu szkicu znaczy, że obiekt w modelu zmienił się od zapisania przesunięcia
export function odcisk(obrys) {
  const tekst = (jestPunktem(obrys) ? [obrys] : obrys).map(([x, y]) => `${Math.round(x * 10)},${Math.round(y * 10)}`).join(';');
  let h = 0x811c9dc5;
  for (let i = 0; i < tekst.length; i++) h = Math.imul(h ^ tekst.charCodeAt(i), 0x01000193) >>> 0;
  return h.toString(16).padStart(8, '0');
}

// szkic do zapisu: {id: {dx, dy, odcisk}}; przesuniecia — Map id → [dx, dy], obiekty — Map id → obiekt z modelu (obrys2d)
export function szkicDoZapisu(przesuniecia, obiekty) {
  const wynik = {};
  for (const [id, [dx, dy]] of przesuniecia) {
    const o = obiekty.get(id);
    if (o) wynik[id] = { dx, dy, odcisk: odcisk(o.obrys2d) };
  }
  return wynik;
}

// szkic z odczytu: {przesuniecia: Map id → [dx, dy], pominiete} — przywrócone tylko wpisy z odciskiem zgodnym z obecnym
// modelem; pominiete liczy resztę (obiekt przesunięty albo zmieniony w modelu, usunięty z modelu, stary szkic bez
// odcisku, uszkodzony wpis)
export function szkicZOdczytu(zapis, obiekty) {
  const przesuniecia = new Map();
  let pominiete = 0;
  if (!zapis || typeof zapis !== 'object' || Array.isArray(zapis)) return { przesuniecia, pominiete };
  for (const [id, w] of Object.entries(zapis)) {
    const o = obiekty.get(id);
    if (o && w && typeof w === 'object' && Number.isFinite(w.dx) && Number.isFinite(w.dy) && w.odcisk === odcisk(o.obrys2d)) {
      przesuniecia.set(id, [w.dx, w.dy]);
    } else pominiete++;
  }
  return { przesuniecia, pominiete };
}
