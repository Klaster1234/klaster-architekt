// Warianty wykończenia z modelu (wykonczenie.warianty) jako dźwignie planera: jeden select na wariant, zmiana od razu
// przebarwia jego cele — elementy, ściany pomieszczenia, okładziny. Pierwszeństwo jak w lokal/model.py: kolor daje
// pierwszy wariant, który trafia w cel; bez wariantu zostaje kolor z danych (już po wariantach domyślnych).
// Wybór w planerze to podgląd — decyzję wpisuje do modelu Claude (przycisk „kopiuj zmiany dla Claude”).
const HEX = /^#[0-9a-f]{6}$/i;

export function domyslne(dane) {
  return Object.fromEntries((dane.warianty ?? []).map((w) => [w.id, Math.min(Math.max(w.domyslna ?? 0, 0), w.opcje.length - 1)]));
}

export function wczytajWybory(dane, klucz) {
  const w = domyslne(dane);
  try {
    const z = JSON.parse(localStorage.getItem(klucz)) || {};
    for (const v of dane.warianty ?? []) {
      const i = z[v.id];
      if (Number.isInteger(i) && i >= 0 && i < v.opcje.length) w[v.id] = i;
    }
  } catch { /* brak pamięci przeglądarki: zostają domyślne */ }
  return w;
}

export function zapiszWybory(klucz, wybory) {
  try {
    localStorage.setItem(klucz, JSON.stringify(wybory));
  } catch { /* tryb prywatny */ }
}

// cel wariantu: {element: id} | {pomieszczenie: nr, sciany: true} | {okladzina: id}
export function trafia(cel, rodzaj, id) {
  if (rodzaj === 'element') return cel.element === id;
  if (rodzaj === 'sciany') return cel.pomieszczenie === id && !!cel.sciany;
  if (rodzaj === 'okladzina') return cel.okladzina === id;
  return false;
}

// wariant i wybrana opcja dla celu albo null, gdy żaden wariant go nie dotyczy
export function opcjaCelu(dane, wybory, rodzaj, id) {
  for (const w of dane.warianty ?? []) {
    if (!(w.cel ?? []).some((c) => trafia(c, rodzaj, id))) continue;
    const i = Math.min(Math.max(wybory[w.id] ?? w.domyslna ?? 0, 0), w.opcje.length - 1);
    return { wariant: w, opcja: w.opcje[i], indeks: i };
  }
  return null;
}

export function kolorCelu(dane, wybory, rodzaj, id) {
  const hex = opcjaCelu(dane, wybory, rodzaj, id)?.opcja.hex;
  return hex && HEX.test(hex) ? hex : null;
}

// cele jednego wariantu pogrupowane po rodzaju
export function cele(w) {
  const wynik = { elementy: new Set(), sciany: new Set(), okladziny: new Set() };
  for (const c of w?.cel ?? []) {
    if (c.element) wynik.elementy.add(c.element);
    else if (c.okladzina) wynik.okladziny.add(c.okladzina);
    else if (c.pomieszczenie && c.sciany) wynik.sciany.add(c.pomieszczenie);
  }
  return wynik;
}

// "V1=1,V2=0" — ten sam zapis przyjmują rysunki/glb.py i rysunki/izometria.py (--wybory)
export const tekstWyborow = (dane, wybory) => (dane.warianty ?? []).map((w) => `${w.id}=${wybory[w.id]}`).join(',');

export function rysujDzwignie(dane, wybory, esc) {
  const d = domyslne(dane);
  return (dane.warianty ?? []).map((w) => {
    const i = wybory[w.id], hex = HEX.test(w.opcje[i]?.hex ?? '') ? w.opcje[i].hex : '#FFFFFF';
    return `<label class="dzwignia${i !== d[w.id] ? ' zmieniona' : ''}">`
      + `<span>${esc(w.nazwa)} <small class="cichy">${esc(w.id)}</small></span>`
      + `<span class="wybor"><i class="probka" style="background:${hex}"></i><select data-wariant-id="${esc(w.id)}">`
      + w.opcje.map((o, k) => `<option value="${k}"${k === i ? ' selected' : ''}>${esc(o.nazwa)}${k === d[w.id] ? ' ●' : ''}</option>`).join('')
      + '</select></span></label>';
  }).join('');
}
