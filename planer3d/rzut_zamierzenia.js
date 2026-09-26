// Rzut 2D (SVG) modelu zamierzenia zsynchronizowany ze sceną 3D: działki, sąsiedztwo, obiekty w kolorach legendy
// (drzewa jako koła korony), moduły wnętrz obrysem. Klik wybiera obiekt, Shift+klik wskazuje obiekt odniesienia
// (wymiar od wybranego), przeciągnięcie wybranego przesuwa go (moduły i sąsiedztwo są nieruchome), przeciąganie poza
// nim przesuwa widok, kółko przybliża, dwuklik dopasowuje. Rysunek w cm modelu, oś y odwrócona (góra rzutu = +y).
import { jestPunktem, wPoligonie } from './kontrole_zamierzenia.js';

const NS = 'http://www.w3.org/2000/svg';
const DOMYSLNE = { nazwa: '', wypelnienie: '#F2F2F2', linia: '#444444', kolor3d: '#C8C8C8' };
const KOLEJNOSC = { powierzchnia: 0, bryla: 1, dach: 2, linia: 3, punkt: 4 };

function el(tag, atr = {}, rodzic) {
  const e = document.createElementNS(NS, tag);
  for (const k in atr) e.setAttribute(k, atr[k]);
  if (rodzic) rodzic.append(e);
  return e;
}
const punkty = (pol) => pol.map(([x, y]) => `${x},${-y}`).join(' ');
const obwiednia = (p) => [Math.min(...p.map((q) => q[0])), Math.min(...p.map((q) => q[1])), Math.max(...p.map((q) => q[0])), Math.max(...p.map((q) => q[1]))];
function pole(pol) {
  let a = 0;
  for (let i = 0; i < pol.length; i++) a += pol[i][0] * pol[(i + 1) % pol.length][1] - pol[(i + 1) % pol.length][0] * pol[i][1];
  return a / 2;
}
// miejsce na podpis: środek ciężkości wielokąta (gdy leży w nim), środek najdłuższego odcinka linii, punkt
function miejscePodpisu(o) {
  const g = o.obrys2d;
  if (jestPunktem(g)) return g;
  if (o.ksztalt === 'linia') {
    let naj = null;
    for (let i = 0; i + 1 < g.length; i++) {
      const d = Math.hypot(g[i + 1][0] - g[i][0], g[i + 1][1] - g[i][1]);
      if (!naj || d > naj.d) naj = { d, p: [(g[i][0] + g[i + 1][0]) / 2, (g[i][1] + g[i + 1][1]) / 2] };
    }
    return naj?.p ?? g[0];
  }
  const a = pole(g);
  let x = 0, y = 0;
  for (let i = 0; i < g.length; i++) {
    const [x0, y0] = g[i], [x1, y1] = g[(i + 1) % g.length], f = x0 * y1 - x1 * y0;
    x += (x0 + x1) * f;
    y += (y0 + y1) * f;
  }
  const c = a ? [x / (6 * a), y / (6 * a)] : g[0];
  return wPoligonie(c, g) ? c : null;
}

export function utworzRzut(svg, dane, { naWybor, naStart, naPrzesuniecie, naKoniec }) {
  const W = {};
  for (const n of ['sasiedztwo', 'obiekty', 'moduly', 'dzialki', 'duchy', 'wybor', 'wymiary']) W[n] = el('g', { class: n }, svg);
  const styl = (o) => ({ ...DOMYSLNE, ...(dane.legenda[o.kategoria] ?? {}) });

  for (const s of dane.sasiedztwo) el('polygon', { points: punkty(s.obrys), class: 'sasiad' }, W.sasiedztwo);
  for (const d of dane.dzialki) el('polygon', { points: punkty(d.granica), class: 'dzialka' }, W.dzialki);
  for (const m of dane.moduly) {
    for (const p of m.pomieszczenia2d) el('polygon', { points: punkty(p), class: 'modul-pokoj' }, W.moduly);
    for (const s of m.sciany2d) el('polygon', { points: punkty(s), class: 'modul-sciana' }, W.moduly);
  }

  // kształt obiektu: wielokąt, linia albo punkt (drzewo z koroną) w kolorach legendy; z klasą (duch na miejscu
  // z modelu, zaznaczenie wybranego) sam obrys, wygląd z CSS
  function ksztalt(o, g, rodzic, klasa = null) {
    const st = styl(o);
    if (jestPunktem(g)) {
      const r = o.srednica ? o.srednica / 2 : 25;
      const e = el('circle', { cx: g[0], cy: -g[1], r, class: klasa ?? 'korona' }, rodzic);
      if (!klasa) {
        e.setAttribute('fill', st.kolor3d ?? DOMYSLNE.kolor3d);
        e.setAttribute('stroke', st.linia ?? st.kolor3d ?? DOMYSLNE.linia);
        el('circle', { cx: g[0], cy: -g[1], r: Math.max(5, r * 0.08), class: 'pien', fill: st.linia ?? '#6B5D52' }, rodzic);
      }
      return e;
    }
    if (o.ksztalt === 'linia') {
      const e = el('polyline', { points: punkty(g), class: klasa ?? 'linia' }, rodzic);
      if (!klasa) e.setAttribute('stroke', st.linia ?? st.kolor3d ?? DOMYSLNE.linia);
      return e;
    }
    const e = el('polygon', { points: punkty(g), class: klasa ?? 'wielokat' }, rodzic);
    if (!klasa) {
      e.setAttribute('fill', st.wypelnienie ?? 'none');
      e.setAttribute('stroke', st.linia ?? (st.wypelnienie ? 'none' : st.kolor3d ?? DOMYSLNE.linia));
    }
    return e;
  }

  // obiekty rysowane raz; przesunięcie to transform grupy. Kolejność: duże powierzchnie pod spodem, punkty na wierzchu
  const grupy = new Map();
  const kolejne = [...dane.obiekty].sort((a, b) => (KOLEJNOSC[a.ksztalt] ?? 1) - (KOLEJNOSC[b.ksztalt] ?? 1)
    || (a.ksztalt === 'powierzchnia' && b.ksztalt === 'powierzchnia' ? Math.abs(pole(b.obrys2d)) - Math.abs(pole(a.obrys2d)) : 0));
  for (const o of kolejne) {
    const g = el('g', { class: 'obiekt', 'data-id': o.id }, W.obiekty);
    const k = ksztalt(o, o.obrys2d, g);
    // linia i wielokąt bez wypełnienia: szeroki niewidoczny pas do trafienia kursorem
    if (!jestPunktem(o.obrys2d) && (o.ksztalt === 'linia' || k.getAttribute('fill') === 'none')) {
      el(o.ksztalt === 'linia' ? 'polyline' : 'polygon', { points: punkty(o.obrys2d), class: 'trafienie' }, g);
    }
    const p = miejscePodpisu(o);
    const t = p && el('text', { x: p[0], y: -p[1], class: 'etykieta' }, g);
    if (t) t.textContent = o.id;
    const [x0, y0, x1, y1] = jestPunktem(o.obrys2d) ? [0, 0, o.srednica ?? 50, o.srednica ?? 50] : obwiednia(o.obrys2d);
    grupy.set(o.id, { g, t, rozmiar: Math.max(x1 - x0, y1 - y0) });
  }

  // --- widok (viewBox) ---
  let widok = { x: 0, y: 0, w: 100, h: 100 }, u = 1, ostatni = null;
  function ustawWidok() {
    svg.setAttribute('viewBox', `${widok.x} ${widok.y} ${widok.w} ${widok.h}`);
    u = widok.w / Math.max(1, svg.clientWidth);  // cm na piksel ekranu
    svg.style.setProperty('--u', u);
    for (const { t, rozmiar } of grupy.values()) if (t) t.style.display = rozmiar / u >= 22 ? '' : 'none';
  }
  function dopasuj(b, margines) {
    const w = b[2] - b[0] + 2 * margines, h = b[3] - b[1] + 2 * margines;
    const pw = Math.max(1, svg.clientWidth), ph = Math.max(1, svg.clientHeight), s = Math.max(w / pw, h / ph);
    widok = { w: pw * s, h: ph * s, x: (b[0] + b[2]) / 2 - (pw * s) / 2, y: -(b[1] + b[3]) / 2 - (ph * s) / 2 };
    ustawWidok();
  }
  function pokaz() {
    const b = dane.meta.obrys;
    dopasuj(b, Math.max(100, 0.04 * Math.max(b[2] - b[0], b[3] - b[1])));
    if (ostatni) rysuj(ostatni);
  }

  // wymiar {od, do, odl} (cm modelu): linia z kreskami na końcach i opis w metrach; odn — wymiar do obiektu odniesienia
  function rysujWymiar(wymiar, odn = false) {
    const [ax, ay] = wymiar.od, [bx, by] = wymiar.do, dl = wymiar.odl, t = 5 * u, k = odn ? ' odn' : '';
    const nx = (-(by - ay) / dl) * t, ny = ((bx - ax) / dl) * t;
    el('line', { x1: ax, y1: -ay, x2: bx, y2: -by, class: 'wymiar' + k }, W.wymiary);
    for (const [x, y] of [wymiar.od, wymiar.do]) el('line', { x1: x - nx, y1: -(y - ny), x2: x + nx, y2: -(y + ny), class: 'wymiar' + k }, W.wymiary);
    const tekst = `${(dl / 100).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`;
    const sz = (tekst.length * 6.5 + 12) * u, wy = 16 * u, mx = (ax + bx) / 2, my = -(ay + by) / 2;
    el('rect', { x: mx - sz / 2, y: my - wy / 2, width: sz, height: wy, rx: wy / 2, class: 'wymiar-tlo' + k }, W.wymiary);
    el('text', { x: mx, y: my, class: 'wymiar-tekst' }, W.wymiary).textContent = tekst;
  }

  // --- stan: przesunięcia, wybór, obiekt odniesienia, kolizje, duchy na miejscu z modelu, wymiary do granicy i do
  // obiektu odniesienia ---
  function rysuj(s) {
    ostatni = s;
    const { przesuniecia, wybrany, kolizje, wymiar, odniesienie, wymiarOdniesienia } = s;
    for (const n of ['duchy', 'wybor', 'wymiary']) W[n].replaceChildren();
    for (const o of dane.obiekty) {
      const { g } = grupy.get(o.id), p = przesuniecia.get(o.id);
      g.setAttribute('transform', p ? `translate(${p[0]} ${-p[1]})` : '');
      g.classList.toggle('wybrany', o.id === wybrany);
      g.classList.toggle('zmieniony', !!p);
      g.classList.toggle('kolizja', kolizje.has(o.id));
      if (p) ksztalt(o, o.obrys2d, W.duchy, 'duch');
      if (o.id === wybrany || o.id === odniesienie) {  // obrys wybranego i odniesienia nad wszystkim, bez zmiany kolejności
        const z = el('g', p ? { transform: `translate(${p[0]} ${-p[1]})` } : {}, W.wybor);
        ksztalt(o, o.obrys2d, z, o.id === wybrany ? 'zaznaczenie' : 'odniesienie');
      }
    }
    if (wymiar && wymiar.odl > 0.5) rysujWymiar(wymiar);
    if (wymiarOdniesienia && wymiarOdniesienia.odl > 0.5) rysujWymiar(wymiarOdniesienia, true);
  }

  // --- interakcja: klik wybiera, przeciągnięcie wybranego przesuwa, poza nim przesuwa widok ---
  const doModelu = (e) => {
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [p.x, -p.y];
  };
  let ciag = null;
  svg.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const id = e.target.closest?.('.obiekt')?.dataset.id ?? null;
    ciag = { id, tryb: id && id === ostatni?.wybrany ? 'obiekt' : 'widok', start: doModelu(e), klient: [e.clientX, e.clientY],
      widok0: { ...widok }, ruszyl: false, shift: e.shiftKey };
    try {
      svg.setPointerCapture(e.pointerId);
    } catch { /* zdarzenie syntetyczne bez aktywnego wskaźnika */ }
  });
  svg.addEventListener('pointermove', (e) => {
    if (!ciag) return;
    if (ciag.tryb === 'obiekt') {
      const p = doModelu(e), dx = Math.round(p[0] - ciag.start[0]), dy = Math.round(p[1] - ciag.start[1]);
      if (!ciag.ruszyl) {
        if (Math.hypot(dx, dy) < 3 * u) return;
        ciag.ruszyl = true;
        svg.classList.add('ciagniecie');
        naStart(ciag.id);
      }
      naPrzesuniecie(ciag.id, dx, dy);
    } else {
      const dx = e.clientX - ciag.klient[0], dy = e.clientY - ciag.klient[1];
      if (!ciag.ruszyl && Math.hypot(dx, dy) < 4) return;
      ciag.ruszyl = true;
      widok.x = ciag.widok0.x - dx * u;
      widok.y = ciag.widok0.y - dy * u;
      ustawWidok();
    }
  });
  const koniec = () => {
    if (ciag && !ciag.ruszyl) naWybor(ciag.id, ciag.shift);
    if (ciag?.tryb === 'obiekt' && ciag.ruszyl) naKoniec(ciag.id);
    svg.classList.remove('ciagniecie');
    ciag = null;
  };
  svg.addEventListener('pointerup', koniec);
  svg.addEventListener('pointercancel', () => {
    if (ciag?.tryb === 'obiekt' && ciag.ruszyl) naKoniec(ciag.id);
    svg.classList.remove('ciagniecie');
    ciag = null;
  });
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    const [mx, my] = doModelu(e), f = Math.exp(e.deltaY * 0.0015), sy = -my;
    widok = { x: mx - (mx - widok.x) * f, y: sy - (sy - widok.y) * f, w: widok.w * f, h: widok.h * f };
    ustawWidok();
    if (ostatni) rysuj(ostatni);
  }, { passive: false });
  svg.addEventListener('dblclick', pokaz);
  new ResizeObserver(pokaz).observe(svg);

  return { rysuj, pokaz };
}

