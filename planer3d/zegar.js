// Tarcza zegara 24 h: północ (0:00) na dole, południe (12:00) na górze. Słońce obiega tarczę tak jak niebo
// widziane twarzą na południe (półkula północna): wschodzi z lewej, zachodzi z prawej.
// Przeciąganie i strzałki ustawiają godzinę co 5 min (z Shift co godzinę).
const NS = 'http://www.w3.org/2000/svg';
const S = 100, R = 80;  // środek i promień pierścienia (viewBox 200 × 200)

export const hhmm = (m) => {
  const c = ((Math.floor(m) % 1440) + 1440) % 1440;
  return `${String(Math.floor(c / 60)).padStart(2, '0')}:${String(c % 60).padStart(2, '0')}`;
};

function punkt(min, r) {
  const b = (min / 1440 + 0.5) * 2 * Math.PI;  // kąt od góry zgodnie ze wskazówkami
  return [S + r * Math.sin(b), S - r * Math.cos(b)];
}
function luk(m0, m1) {
  const [x0, y0] = punkt(m0, R), [x1, y1] = punkt(m1, R);
  return `M${x0} ${y0} A${R} ${R} 0 ${(m1 - m0 + 1440) % 1440 > 720 ? 1 : 0} 1 ${x1} ${y1}`;
}
function dodaj(rodzic, tag, atr = {}) {
  const e = document.createElementNS(NS, tag);
  for (const k in atr) e.setAttribute(k, atr[k]);
  return rodzic.appendChild(e);
}

export function zegar(svg, naZmiane) {
  svg.setAttribute('viewBox', '0 0 200 200');
  dodaj(svg, 'circle', { cx: S, cy: S, r: R, class: 'noc' });
  const dzien = dodaj(svg, 'path', { class: 'dzien' });
  for (let g = 0; g < 24; g++) {
    const [x1, y1] = punkt(g * 60, R - 11), [x2, y2] = punkt(g * 60, R - (g % 3 ? 15 : 19));
    dodaj(svg, 'line', { x1, y1, x2, y2, class: 'kreska' });
    if (g % 3 === 0) {
      const [x, y] = punkt(g * 60, R - 29);
      dodaj(svg, 'text', { x, y, class: 'godz' }).textContent = g;
    }
  }
  const czas = dodaj(svg, 'text', { x: S, y: S - 4, class: 'czas' });
  const data = dodaj(svg, 'text', { x: S, y: S + 17, class: 'data' });
  const slonce = dodaj(svg, 'circle', { r: 8.5, class: 'slonce' });
  let biezace = 0;

  const minutyZ = (e) => {
    const p = svg.getBoundingClientRect();
    const x = ((e.clientX - p.left) / p.width) * 200 - S, y = ((e.clientY - p.top) / p.height) * 200 - S;
    const b = Math.atan2(x, -y) / (2 * Math.PI);
    return { m: (Math.round((((b + 1.5) % 1) * 1440) / 5) * 5) % 1440, r: Math.hypot(x, y) };
  };
  svg.addEventListener('pointerdown', (e) => {
    const { m, r } = minutyZ(e);
    if (r < 45) return;  // środek tarczy nie przestawia godziny
    svg.setPointerCapture(e.pointerId);
    naZmiane(m);
  });
  svg.addEventListener('pointermove', (e) => {
    if (svg.hasPointerCapture(e.pointerId)) naZmiane(minutyZ(e).m);
  });
  svg.addEventListener('keydown', (e) => {
    const krok = { ArrowRight: 5, ArrowUp: 5, ArrowLeft: -5, ArrowDown: -5 }[e.key];
    if (!krok) return;
    e.preventDefault();
    e.stopPropagation();
    naZmiane((Math.round(biezace / 5) * 5 + krok * (e.shiftKey ? 12 : 1) + 1440) % 1440);
  });

  return {
    ustaw(minuty, dataTekst, d, nadHoryzontem) {
      biezace = minuty;
      const [x, y] = punkt(minuty, R);
      slonce.setAttribute('cx', x);
      slonce.setAttribute('cy', y);
      slonce.classList.toggle('pod', !nadHoryzontem);
      czas.textContent = hhmm(minuty);
      data.textContent = dataTekst;
      dzien.setAttribute('d', d.wschod == null || d.zachod == null ? '' : luk(d.wschod, d.zachod));
      svg.setAttribute('aria-valuenow', Math.floor(minuty));
      svg.setAttribute('aria-valuetext', hhmm(minuty));
    },
  };
}
