// Kontrole geometryczne planera — czyste funkcje na prostokątach [x0, y0, x1, y1] w cm modelu (oś y = góra rzutu).
// Działają w przeglądarce i w Node (bez DOM i three.js). Rodzaj mebla rozpoznaje się po kategorii z modelu
// (lokal/model.py: RODZAJE → kategoria), nigdy po brzmieniu nazwy.

export const nachodzi = (a0, a1, b0, b1, tol = 0) => a0 < b1 - tol && b0 < a1 - tol;
export const prostokatyNachodza = (a, b, tol = 0) => nachodzi(a[0], a[2], b[0], b[2], tol) && nachodzi(a[1], a[3], b[1], b[3], tol);
export const jestOknem = (o) => o.rodzaj === 'okno' || o.rodzaj === 'portfenetr';

// stoły, biurka i stoliki kolidują tylko blatem (górne 5 cm) — pod spód wchodzą nogi i siedziska
export const BLATOWE = ['stol', 'stolik'];
export function zakresZ(el) {
  const [z0, z1] = el.wys;
  return BLATOWE.includes(el.kategoria) ? [Math.max(z0, z1 - 5), z1] : [z0, z1];
}

// siedzisko wsunięte pod stół albo biurko nie jest kolizją
export const podSpod = (a, c) => a.kategoria === 'siedzisko' && c.kategoria === 'stol';

export function przeszkody(dane, meble) {
  const H = dane.meta.wysokosc;
  const lista = [
    ...dane.sciany.map((s) => ({ typ: s.rodzaj === 'niski' ? 'ściana niska' : 'ściana', id: s.id, box: s.box, z: s.z })),
    ...dane.otwory.map((o) => ({ typ: jestOknem(o) ? 'okno' : 'drzwi', id: o.id, box: o.box, z: [o.parapet ?? 0, o.wys_otw] })),
    ...dane.szachty.map((s) => ({ typ: 'szacht', id: s.id, box: s.box, z: [0, H] })),
    ...dane.grzejniki.map((g) => ({ typ: 'grzejnik', id: g.id, box: g.box, z: g.z })),
    ...dane.kontekst.map((k) => ({ typ: 'otoczenie', id: k.id, box: k.box, z: k.z ?? [0, H] })),
  ];
  for (const el of meble.values()) lista.push({ typ: 'mebel', id: el.id, box: el.box, z: zakresZ(el), el });
  return lista;
}

// środek najdłuższego odcinka [lo, hi], którego nie zasłaniają przeszkody stykające się z meblem
function srodekWolnego(lo, hi, zajete) {
  let odcinki = [[lo, hi]];
  for (const z of zajete) odcinki = odcinki.flatMap(([a, c]) => [[a, Math.min(c, z.lo)], [Math.max(a, z.hi), c]]).filter(([a, c]) => c - a > 0.5);
  if (!odcinki.length) return null;
  const [a, c] = odcinki.reduce((x, y) => (y[1] - y[0] > x[1] - x[0] ? y : x));
  return c - a >= 3 ? (a + c) / 2 : null;
}

// najbliższa przeszkoda w każdą stronę (E = +x, W = −x, N = +y, S = −y) na wspólnym pasie i wspólnej wysokości;
// przeszkody dotykające mebla (np. szafki nocne przy łóżku) pomija się i mierzy obok nich
export function odleglosci(el, lista, maks = 500) {
  const b = el.box, [z0, z1] = el.wys, wynik = [];
  for (const k of ['E', 'W', 'N', 'S']) {
    const poziomo = k === 'E' || k === 'W';
    const [lo, hi] = poziomo ? [b[1], b[3]] : [b[0], b[2]];
    const kandydaci = [], stykowe = [];
    for (const p of lista) {
      if (p.id === el.id || !nachodzi(z0, z1, p.z[0], p.z[1])) continue;
      const q = p.box, [qlo, qhi] = poziomo ? [q[1], q[3]] : [q[0], q[2]];
      if (!nachodzi(lo, hi, qlo, qhi, 0.5)) continue;
      const odl = { E: q[0] - b[2], W: b[0] - q[2], N: q[1] - b[3], S: b[1] - q[3] }[k];
      if (odl <= -0.5 || odl > maks) continue;
      (odl < 1 ? stykowe : kandydaci).push({ odl, p, lo: Math.max(lo, qlo), hi: Math.min(hi, qhi) });
    }
    kandydaci.sort((a, c) => a.odl - c.odl);
    for (const c of kandydaci) {
      const m = srodekWolnego(c.lo, c.hi, stykowe);
      if (m === null) continue;
      const q = c.p.box;
      wynik.push({
        kierunek: k, odl: c.odl, przeszkoda: c.p,
        od: { E: [b[2], m], W: [b[0], m], N: [m, b[3]], S: [m, b[1]] }[k],
        do: { E: [q[0], m], W: [q[2], m], N: [m, q[1]], S: [m, q[3]] }[k],
      });
      break;
    }
  }
  return wynik;
}

export function wPoligonie([x, y], pol) {
  let w = false;
  for (let i = 0, j = pol.length - 1; i < pol.length; j = i++) {
    const [xi, yi] = pol[i], [xj, yj] = pol[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) w = !w;
  }
  return w;
}

// punkt w pomieszczeniu: w obrysie i poza dziurami (szacht albo słup stojący wolno w pomieszczeniu)
export const wPomieszczeniu = (xy, p) => wPoligonie(xy, p.poligon) && !(p.dziury ?? []).some((d) => wPoligonie(xy, d));
// pomieszczenie, w którym leży punkt (z danych planera), albo null
export const pokojPunktu = (dane, xy) => dane.pomieszczenia.find((p) => wPomieszczeniu(xy, p)) ?? null;

// środek ciężkości wielokąta — w pokojach w kształcie L leży bliżej wnętrza niż środek obrysu
export function srodekCiezkosci(pol) {
  let a = 0, x = 0, y = 0;
  for (let i = 0, j = pol.length - 1; i < pol.length; j = i++) {
    const f = pol[j][0] * pol[i][1] - pol[i][0] * pol[j][1];
    a += f;
    x += (pol[j][0] + pol[i][0]) * f;
    y += (pol[j][1] + pol[i][1]) * f;
  }
  return a ? [x / (3 * a), y / (3 * a)] : pol[0];
}

// kąt skrzydła otwartego na rysunkach: ten koniec łuku, który jest prostopadły do ściany (jak lokal/plan.py)
export function katSkrzydla(luk, poziomo) {
  const prostopadly = poziomo ? 90 : 0;
  const kat = [luk.od, luk.do].find((a) => ((Math.round(a) % 180) + 180) % 180 === prostopadly);
  return kat ?? luk.do;
}

export function wLuku([x, y], { c, r, od, do: dokad }) {
  const dx = x - c[0], dy = y - c[1];
  if (dx * dx + dy * dy >= (r - 0.5) ** 2) return false;
  const rozp = (((dokad - od) % 360) + 360) % 360 || 360;
  const a = ((((Math.atan2(dy, dx) * 180) / Math.PI - od) % 360) + 360) % 360;
  return a > 0.5 && a < rozp - 0.5;
}
export function prostokatWLuku(b, luk) {
  for (let i = 0; i <= 6; i++) {
    for (let j = 0; j <= 6; j++) if (wLuku([b[0] + ((b[2] - b[0]) * i) / 6, b[1] + ((b[3] - b[1]) * j) / 6], luk)) return true;
  }
  const rozp = (((luk.do - luk.od) % 360) + 360) % 360 || 360;
  for (let k = 1; k < 8; k++) {
    for (const f of [0.35, 0.7, 0.95]) {
      const a = ((luk.od + (rozp * k) / 8) * Math.PI) / 180;
      const [x, y] = [luk.c[0] + luk.r * f * Math.cos(a), luk.c[1] + luk.r * f * Math.sin(a)];
      if (x > b[0] && x < b[2] && y > b[1] && y < b[3]) return true;
    }
  }
  return false;
}

// odległość prostopadła do elementu przy ścianie (okno, grzejnik), gdy mebel stoi na jego odcinku; inaczej Infinity
export function przed(b, q) {
  const poziomo = q[2] - q[0] >= q[3] - q[1];
  const naOdcinku = poziomo ? nachodzi(b[0], b[2], q[0], q[2], 1) : nachodzi(b[1], b[3], q[1], q[3], 1);
  const odl = poziomo ? Math.max(q[1] - b[3], b[1] - q[3]) : Math.max(q[0] - b[2], b[0] - q[2]);
  return naOdcinku ? odl : Infinity;
}

const OPIS_TYPU = {
  'ściana': (p) => `wchodzi w ścianę ${p.id}`,
  'ściana niska': (p) => `wchodzi w balustradę lub murek ${p.id}`,
  szacht: (p) => `wchodzi w szacht ${p.id}`,
  grzejnik: (p) => `koliduje z grzejnikiem ${p.id}`,
  otoczenie: (p) => `wychodzi poza lokal (${p.id})`,
  mebel: (p) => `nachodzi na ${p.id} (${p.el.rodzaj})`,
};

// uwagi do jednego mebla: kolizje (twarde) i ostrzeżenia (drzwi, okna, grzejniki, pomieszczenie)
export function kontrolaMebla(el, lista, dane, pokojProjektu) {
  const uwagi = [], [z0, z1] = zakresZ(el), b = el.box;
  for (const p of lista) {
    if (p.id === el.id || p.typ === 'okno' || p.typ === 'drzwi') continue;
    if (p.typ === 'mebel' && (podSpod(el, p.el) || podSpod(p.el, el))) continue;
    if (nachodzi(z0, z1, p.z[0], p.z[1]) && prostokatyNachodza(b, p.box, 0.5)) uwagi.push({ poziom: 'kolizja', tekst: OPIS_TYPU[p.typ](p) });
  }
  for (const o of dane.otwory) {
    const skrzydlo = o.skrzydlo?.[1] ?? o.wys_otw ?? 200;
    if (o.luk && z0 < skrzydlo && prostokatWLuku(b, o.luk)) {
      uwagi.push({ poziom: 'uwaga', tekst: `wchodzi w pole otwierania ${jestOknem(o) ? 'skrzydła' : 'drzwi'} ${o.id}` });
    }
    if (jestOknem(o) && z1 > (o.parapet ?? 0) + 5) {
      const d = przed(b, o.box);
      if (d > -0.5 && d < 30) uwagi.push({ poziom: 'uwaga', tekst: `zasłania okno ${o.id} (${Math.round(Math.max(d, 0))} cm od okna)` });
    }
  }
  for (const g of dane.grzejniki) {
    const d = przed(b, g.box);
    if (z0 < g.z[1] && d > 0.5 && d < 15) uwagi.push({ poziom: 'uwaga', tekst: `stoi przed grzejnikiem ${g.id} (${Math.round(d)} cm)` });
  }
  const pokoj = pokojPunktu(dane, [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]);
  if (!pokoj) uwagi.push({ poziom: 'uwaga', tekst: 'środek poza pomieszczeniami lokalu' });
  else if (pokoj.nr !== pokojProjektu) uwagi.push({ poziom: 'info', tekst: `przeniesiony do: ${pokoj.nazwa} (${pokoj.nr})` });
  return uwagi;
}
