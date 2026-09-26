// Położenie słońca i czas lokalny w strefie z modelu (meta.polnoc.lokalizacja.strefa, np. Europe/Warsaw) — bez zależności.
// Wzory astronomiczne jak w SunCalc (V. Agafonkin / Astronomy Answers); dokładność ok. 0,1°, wystarczy do nasłonecznienia.
// Te same wzory ma wspolne/slonce.py.
const RAD = Math.PI / 180;
const E = 23.4397 * RAD;  // nachylenie ekliptyki

// azymut: stopnie od północy zgodnie z ruchem wskazówek (90 = wschód, 180 = południe); wysokość: stopnie nad horyzontem
export function pozycjaSlonca(data, lat, lon) {
  const d = data.valueOf() / 86400000 - 10957.5;  // dni od J2000.0
  const M = (357.5291 + 0.98560028 * d) * RAD;   // anomalia średnia
  const L = M + (1.9148 * Math.sin(M) + 0.02 * Math.sin(2 * M) + 0.0003 * Math.sin(3 * M) + 282.9372) * RAD;  // długość ekliptyczna
  const dek = Math.asin(Math.sin(E) * Math.sin(L));
  const ra = Math.atan2(Math.sin(L) * Math.cos(E), Math.cos(L));
  const H = (280.16 + 360.9856235 * d + lon) * RAD - ra;  // kąt godzinny
  const f = lat * RAD;
  const wys = Math.asin(Math.sin(f) * Math.sin(dek) + Math.cos(f) * Math.cos(dek) * Math.cos(H));
  const az = Math.atan2(Math.sin(H), Math.cos(H) * Math.sin(f) - Math.tan(dek) * Math.cos(f));  // od południa, + na zachód
  return { azymut: (az / RAD + 540) % 360, wysokosc: wys / RAD };
}

// formatery Intl na strefę (tworzone raz); nieznana strefa → UTC
const formaty = new Map();
function format(strefa) {
  if (!formaty.has(strefa)) {
    let s = strefa || 'UTC';
    try {
      new Intl.DateTimeFormat('en-US', { timeZone: s });
    } catch {
      s = 'UTC';
    }
    formaty.set(strefa, {
      strefa: s,
      offset: new Intl.DateTimeFormat('en-US', { timeZone: s, timeZoneName: 'shortOffset' }),
      teraz: new Intl.DateTimeFormat('en-CA', {
        timeZone: s, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
      }),
    });
  }
  return formaty.get(strefa);
}
export const poprawnaStrefa = (strefa) => format(strefa).strefa;

function przesuniecie(data, strefa) {  // minuty względem UTC w danej chwili (z czasem letnim), np. 60 albo 120
  const s = format(strefa).offset.formatToParts(data).find((p) => p.type === 'timeZoneName')?.value ?? '';
  const [, g = 0, m = 0] = s.match(/([+-]\d+)(?::(\d+))?/) || [];
  return g * 60 + Math.sign(g) * m;
}

// dzień "RRRR-MM-DD" + minuty od północy czasu lokalnego strefy -> moment w czasie. Przy zmianie czasu jak
// wspolne/slonce.py (zoneinfo, fold=0): godzina podwójna — pierwsze wystąpienie, godzina nieistniejąca — przesunięcie sprzed zmiany
export function czasLokalny(dzien, minuty, strefa) {
  const [r, m, d] = dzien.split('-').map(Number);
  const utc = Date.UTC(r, m - 1, d) + minuty * 60000;
  const przed = przesuniecie(new Date(utc - 43200000), strefa), po = przesuniecie(new Date(utc + 43200000), strefa);
  for (const p of [przed, po]) {
    if (przesuniecie(new Date(utc - p * 60000), strefa) === p) return new Date(utc - p * 60000);
  }
  return new Date(utc - przed * 60000);
}

export function teraz(strefa) {
  const p = Object.fromEntries(format(strefa).teraz.formatToParts(new Date()).map((x) => [x.type, x.value]));
  return { dzien: `${p.year}-${p.month}-${p.day}`, minuty: p.hour * 60 + Number(p.minute) };
}

// wschód i zachód (górny brzeg tarczy z refrakcją: −0,833°) oraz górowanie — w minutach od północy czasu lokalnego;
// przy dniu lub nocy polarnej wschód i zachód są null
export function doba(dzien, lat, lon, strefa) {
  const polnoc = czasLokalny(dzien, 0, strefa).valueOf();
  const wys = (m) => pozycjaSlonca(new Date(polnoc + m * 60000), lat, lon).wysokosc + 0.833;
  const w = { wschod: null, zachod: null, gorowanie: 0, wysMax: -90 };
  let poprz = wys(0);
  for (let m = 2; m <= 1440; m += 2) {
    const h = wys(m);
    if (poprz < 0 && h >= 0) w.wschod = m - (2 * h) / (h - poprz);
    if (poprz >= 0 && h < 0) w.zachod = m - (2 * h) / (h - poprz);
    if (h - 0.833 > w.wysMax) {
      w.wysMax = h - 0.833;
      w.gorowanie = m;
    }
    poprz = h;
  }
  return w;
}
