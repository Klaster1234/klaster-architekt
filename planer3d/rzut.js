// Rzut 2D (SVG) zsynchronizowany ze sceną 3D: pomieszczenia, ściany, otwory, meble; wybór i przeciąganie mebli,
// zoom kółkiem i przesuwanie widoku, odległości zaznaczonego mebla. Rysunek w cm modelu, oś y odwrócona (góra rzutu = +y).
import { jestOknem, katSkrzydla } from './kontrole.js';

const NS = 'http://www.w3.org/2000/svg';
const KLASY_PODLOG = { gres: 'gres', 'płyty tarasowe': 'zewnetrzne' };

function el(tag, atr = {}, rodzic) {
  const e = document.createElementNS(NS, tag);
  for (const k in atr) e.setAttribute(k, atr[k]);
  if (rodzic) rodzic.append(e);
  return e;
}
const sciezkaPierscieni = (pierscienie) => pierscienie.map((pol) => `M${pol.map(([x, y]) => `${x} ${-y}`).join(' L')} Z`).join(' ');
const prostokat = (b, atr, rodzic) => el('rect', { x: b[0], y: -b[3], width: b[2] - b[0], height: b[3] - b[1], ...atr }, rodzic);
const granice = (pol) => [Math.min(...pol.map((p) => p[0])), Math.min(...pol.map((p) => p[1])), Math.max(...pol.map((p) => p[0])), Math.max(...pol.map((p) => p[1]))];
const fmtM2 = (v) => (v == null ? '' : `${v.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`);

// linie podziału segmentów frontu od lewej patrząc na front (jak lokal/plan.py: podzialy_segmentow)
function podzialySegmentow(m) {
  const seg = m.segmenty || [];
  if (seg.length < 2 || !m.front) return [];
  const [x0, y0, x1, y1] = m.box, poziomo = m.front === 'N' || m.front === 'S';
  const dl = poziomo ? x1 - x0 : y1 - y0, suma = seg.reduce((a, s) => a + (s.dl || 0), 0) || 1;
  const [start, znak] = { S: [x0, 1], N: [x1, -1], E: [y0, 1], W: [y1, -1] }[m.front];
  const wynik = [];
  let kursor = start;
  for (const s of seg.slice(0, -1)) {
    kursor += (znak * (s.dl || 0) * dl) / suma;
    wynik.push(kursor);
  }
  return wynik.map((v) => (poziomo ? { x1: v, x2: v, y1: -y0, y2: -y1 } : { x1: x0, x2: x1, y1: -v, y2: -v }));
}
const LODOWKI = ['lodówka', 'słupek lodówki'];

export function utworzRzut(svg, dane, { kolor, naWybor, naStart, naPrzesuniecie, naKoniec }) {
  const defs = el('defs', {}, svg);
  const wzor = el('pattern', { id: 'kreski', width: 8, height: 8, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, defs);
  el('line', { x1: 0, y1: 0, x2: 0, y2: 8, stroke: '#A89A8C', 'stroke-width': 2 }, wzor);
  const W = {};
  for (const n of ['kontekst', 'pokoje', 'podpisy', 'sciany', 'otwory', 'instalacje', 'duchy', 'meble', 'wymiary']) W[n] = el('g', { class: n }, svg);

  for (const k of dane.kontekst) prostokat(k.box, { class: 'sasiad' }, W.kontekst);
  for (const p of dane.pomieszczenia) {
    const klasa = p.zewnetrzne ? 'zewnetrzne' : KLASY_PODLOG[p.podloga] ?? '';
    el('path', { d: sciezkaPierscieni([p.poligon, ...(p.dziury ?? [])]), 'fill-rule': 'evenodd', class: `pokoj ${klasa}`.trim(), 'data-nr': p.nr }, W.pokoje);
    const t = el('text', { x: p.stamp[0], y: -p.stamp[1], class: 'podpis' }, W.podpisy);
    el('tspan', { x: p.stamp[0], class: 'nazwa' }, t).textContent = p.nazwa;
    el('tspan', { x: p.stamp[0], dy: '1.25em' }, t).textContent = `${p.nr} · ${fmtM2(p.pow_m2 ?? p.m2)}`;
  }

  // kawałki ścian poniżej 100 cm od podłogi (bez nadproży, żeby otwory było widać); balustrady i murki jaśniej
  for (const s of dane.sciany) {
    if (s.z[0] < 100) prostokat(s.box, { class: `sciana${s.nosna ? ' nosna' : ''}${s.rodzaj === 'niski' ? ' niska' : ''}` }, W.sciany);
  }
  for (const s of dane.szachty) prostokat(s.box, { class: 'szacht' }, W.instalacje);
  for (const g of dane.grzejniki) prostokat(g.box, { class: 'grzejnik' }, W.instalacje);
  for (const o of dane.otwory) {
    prostokat(o.box, { class: 'otwor' }, W.otwory);
    const [x0, y0, x1, y1] = o.box;
    if (jestOknem(o)) {
      for (const f of [0.38, 0.62]) {
        if (o.poziomo) el('line', { x1: x0, x2: x1, y1: -(y0 + (y1 - y0) * f), y2: -(y0 + (y1 - y0) * f), class: 'szyba' }, W.otwory);
        else el('line', { y1: -y0, y2: -y1, x1: x0 + (x1 - x0) * f, x2: x0 + (x1 - x0) * f, class: 'szyba' }, W.otwory);
      }
    }
    if (o.luk) {
      const { c, r, od, do: dokad } = o.luk;
      const a0 = (od * Math.PI) / 180;
      let a1 = (dokad * Math.PI) / 180;
      if (a1 <= a0) a1 += 2 * Math.PI;
      const p0 = [c[0] + r * Math.cos(a0), c[1] + r * Math.sin(a0)], p1 = [c[0] + r * Math.cos(a1), c[1] + r * Math.sin(a1)];
      const ks = (katSkrzydla(o.luk, o.poziomo) * Math.PI) / 180;
      el('line', { x1: c[0], y1: -c[1], x2: c[0] + r * Math.cos(ks), y2: -(c[1] + r * Math.sin(ks)), class: 'skrzydlo' }, W.otwory);
      el('path', { d: `M${p0[0]} ${-p0[1]} A${r} ${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 0 ${p1[0]} ${-p1[1]}`, class: 'luk' }, W.otwory);
    }
  }

  // --- widok (viewBox) ---
  let widok = { x: 0, y: 0, w: 100, h: 100 }, u = 1, biezacyPokoj = null, ostatni = null;
  function ustawWidok() {
    svg.setAttribute('viewBox', `${widok.x} ${widok.y} ${widok.w} ${widok.h}`);
    u = widok.w / Math.max(1, svg.clientWidth);  // cm na piksel ekranu
    svg.style.setProperty('--u', u);
  }
  function dopasuj(b, margines) {
    const w = b[2] - b[0] + 2 * margines, h = b[3] - b[1] + 2 * margines;
    const pw = Math.max(1, svg.clientWidth), ph = Math.max(1, svg.clientHeight), s = Math.max(w / pw, h / ph);
    widok = { w: pw * s, h: ph * s, x: (b[0] + b[2]) / 2 - (pw * s) / 2, y: -(b[1] + b[3]) / 2 - (ph * s) / 2 };
    ustawWidok();
  }
  function pokaz(nr) {
    biezacyPokoj = nr;
    for (const p of W.pokoje.querySelectorAll('.pokoj')) p.classList.toggle('aktywny', p.dataset.nr === nr);
    const pol = nr && dane.pomieszczenia.find((p) => p.nr === nr)?.poligon;
    dopasuj(pol ? granice(pol) : dane.meta.obrys, pol ? 45 : 20);
    if (ostatni) rysuj(ostatni);
  }

  // --- meble i wymiary (przerysowywane po każdej zmianie) ---
  function ksztalt(m, atr, rodzic) {
    const [x0, y0, x1, y1] = m.box;
    return m.ksztalt === 'kolo'
      ? el('ellipse', { cx: (x0 + x1) / 2, cy: -(y0 + y1) / 2, rx: (x1 - x0) / 2, ry: (y1 - y0) / 2, ...atr }, rodzic)
      : prostokat(m.box, atr, rodzic);
  }
  function rysuj(s) {
    ostatni = s;
    const { meble, projekt, wybrany, zmienione, kolizje, wymiary } = s;
    W.meble.replaceChildren();
    W.duchy.replaceChildren();
    W.wymiary.replaceChildren();
    const wiszacy = (m) => m.wys[0] >= 130;  // powyżej płaszczyzny cięcia rzutu (jak lokal/plan.py)
    const lista = [...meble.values()].sort((a, b) => wiszacy(a) - wiszacy(b) || (a.id === wybrany) - (b.id === wybrany));
    for (const m of lista) {
      if (zmienione.has(m.id)) ksztalt(projekt.get(m.id), { class: 'duch' }, W.duchy);
      const klasy = ['mebel', m.id === wybrany && 'wybrany', zmienione.has(m.id) && 'zmieniony', kolizje.has(m.id) && 'kolizja', wiszacy(m) && 'wiszacy'];
      const g = el('g', { class: klasy.filter(Boolean).join(' '), 'data-id': m.id }, W.meble);
      ksztalt(m, { class: 'bryla', fill: kolor(m) }, g);
      for (const l of podzialySegmentow(m)) el('line', { ...l, class: 'podzial' }, g);
      const [x0, y0, x1, y1] = m.box;
      if (m.kategoria === 'urzadzenie' || LODOWKI.includes(m.rodzaj)) {  // urządzenia i słupki lodówki: przekątne
        el('path', { d: `M${x0} ${-y0} L${x1} ${-y1} M${x0} ${-y1} L${x1} ${-y0}`, class: 'podzial' }, g);
      }
      const wPx = (x1 - x0) / u, hPx = (y1 - y0) / u;
      if (Math.min(wPx, hPx) >= 13) {
        const t = el('text', { x: (x0 + x1) / 2, y: -(y0 + y1) / 2, class: 'etykieta' }, g);
        t.textContent = wPx > 70 && hPx > 24 ? `${m.id} ${m.rodzaj.split(' ')[0]}` : m.id;
      }
    }
    for (const w of wymiary) {
      const [ax, ay] = w.od, [bx, by] = w.do, poziomo = w.kierunek === 'E' || w.kierunek === 'W', t = 5 * u;
      el('line', { x1: ax, y1: -ay, x2: bx, y2: -by, class: 'wymiar' }, W.wymiary);
      for (const [x, y] of [w.od, w.do]) {
        el('line', poziomo ? { x1: x, x2: x, y1: -y - t, y2: -y + t, class: 'wymiar' } : { x1: x - t, x2: x + t, y1: -y, y2: -y, class: 'wymiar' }, W.wymiary);
      }
      const tekst = `${Math.round(w.odl)}`, sz = (tekst.length * 7 + 12) * u, wy = 16 * u;
      const mx = (ax + bx) / 2, my = -(ay + by) / 2;
      el('rect', { x: mx - sz / 2, y: my - wy / 2, width: sz, height: wy, rx: wy / 2, class: 'wymiar-tlo' }, W.wymiary);
      el('text', { x: mx, y: my, class: 'wymiar-tekst' }, W.wymiary).textContent = tekst;
    }
  }

  // --- interakcja ---
  const doModelu = (e) => {
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [p.x, -p.y];
  };
  let ciag = null;
  svg.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const g = e.target.closest('.mebel');
    ciag = g
      ? { tryb: 'mebel', id: g.dataset.id, start: doModelu(e), ruszyl: false }
      : { tryb: 'widok', start: [e.clientX, e.clientY], widok0: { ...widok }, ruszyl: false };
    if (g) naWybor(g.dataset.id);
    try {
      svg.setPointerCapture(e.pointerId);
    } catch { /* zdarzenie syntetyczne bez aktywnego wskaźnika */ }
  });
  svg.addEventListener('pointermove', (e) => {
    if (!ciag) return;
    if (ciag.tryb === 'mebel') {
      const p = doModelu(e), dx = Math.round(p[0] - ciag.start[0]), dy = Math.round(p[1] - ciag.start[1]);
      if (!ciag.ruszyl) {
        if (Math.hypot(dx, dy) < 3 * u) return;
        ciag.ruszyl = true;
        svg.classList.add('ciagniecie');
        naStart(ciag.id);
      }
      naPrzesuniecie(ciag.id, dx, dy);
    } else {
      const dx = e.clientX - ciag.start[0], dy = e.clientY - ciag.start[1];
      if (!ciag.ruszyl && Math.hypot(dx, dy) < 4) return;
      ciag.ruszyl = true;
      widok.x = ciag.widok0.x - dx * u;
      widok.y = ciag.widok0.y - dy * u;
      ustawWidok();
    }
  });
  const koniec = () => {
    if (ciag?.tryb === 'widok' && !ciag.ruszyl) naWybor(null);
    if (ciag?.tryb === 'mebel' && ciag.ruszyl) naKoniec(ciag.id);
    svg.classList.remove('ciagniecie');
    ciag = null;
  };
  svg.addEventListener('pointerup', koniec);
  svg.addEventListener('pointercancel', koniec);
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    const [mx, my] = doModelu(e), f = Math.exp(e.deltaY * 0.0015), sy = -my;
    widok = { x: mx - (mx - widok.x) * f, y: sy - (sy - widok.y) * f, w: widok.w * f, h: widok.h * f };
    ustawWidok();
    if (ostatni) rysuj(ostatni);
  }, { passive: false });
  svg.addEventListener('dblclick', () => pokaz(biezacyPokoj));
  new ResizeObserver(() => pokaz(biezacyPokoj)).observe(svg);

  return { rysuj, pokaz };
}
