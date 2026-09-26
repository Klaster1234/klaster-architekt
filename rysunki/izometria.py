"""Izometria lokalu z modelu: sciany przyciete na wysokosci ciecia, meble w pelnych
wysokosciach, kolory z modelu (tokeny po wariantach). Arkusz SVG, PNG i PDF.

    python rysunki/izometria.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/izometria.py przyklad/mieszkanie/model/lokal_projekt.json --pomieszczenia P3,P1 --h 100 --nazwa kuchnia
    python rysunki/izometria.py model.json --widok NE --wybory V1=1

Widok od naroznika modelu (domyslnie SW, czyli od strony -X i -Y osi modelu); strona
swiata w opisie wynika z meta.polnoc. --pomieszczenia ogranicza rysunek do podlog i mebli
wskazanych pomieszczen oraz scian w ich obrebie. Zaslanianie liczone jest porzadkiem
malarza z relacji "za / pod" miedzy prostopadloscianami (nie srodkami ciezkosci).
Wynik: <wyjscie>/<id>_izometria[_<nazwa>].svg|png|pdf.
"""
import argparse
import math
import sys
from pathlib import Path

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import svg, arkusz, slonce
from lokal import model, geometria, plan
from zamierzenie import model as zmodel

COS30, SIN30 = math.cos(math.radians(30)), 0.5
PODLOGI = {"panele": "#EADBC4", "deska": "#E2CDAF", "gres": "#E4E2DD", "płyty tarasowe": "#DAD5CC"}
SCIANY = {"nosna": ("#9AA3B6", "#4D5566"), "dzialowa": ("#C9CED6", "#5C6069"), "niska": ("#DADDE2", "#6B7079")}
SZACHT = ("#F2D7E6", "#A03D78")
GRZEJNIK = ("#F7C8A8", "#B45F2A")
# obrot modelu tak, by wybrany naroznik byl najblizej patrzacego (rzutowanie zawsze od -X, -Y)
OBROTY = {"SW": lambda x, y: (x, y), "SE": lambda x, y: (y, -x),
          "NE": lambda x, y: (-x, -y), "NW": lambda x, y: (-y, x)}
KIERUNEK_WIDOKU = {"SW": (-1, -1), "SE": (1, -1), "NE": (1, 1), "NW": (-1, 1)}


def ciemniej(hexc, f):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (int(r * f), int(g * f), int(b * f))


def pierscien_ccw(pkt):
    pole = sum(pkt[i][0] * pkt[(i + 1) % len(pkt)][1] - pkt[(i + 1) % len(pkt)][0] * pkt[i][1]
               for i in range(len(pkt)))
    return pkt if pole > 0 else pkt[::-1]


def bryla(pkt, z0, z1, wyp, obr, rodzaj="inne", dziury=(), gr=0.8):
    """Prostopadloscian (graniastoslup) nad pierscieniem pkt w ukladzie juz obroconym."""
    pkt = pierscien_ccw(list(pkt))
    xs, ys = [p[0] for p in pkt], [p[1] for p in pkt]
    return {"pkt": pkt, "dziury": [list(d) for d in dziury], "z0": z0, "z1": z1, "wyp": wyp, "obr": obr,
            "gr": gr, "rodzaj": rodzaj, "bb": (min(xs), min(ys), max(xs), max(ys))}


def kolo(x0, y0, x1, y1, n=20):
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def prostokat(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def zbierz(M, h, pomieszczenia, obrot, wybory):
    """Bryly rysunku: podlogi, kawalki scian przyciete na h, szachty, grzejniki i meble."""
    wiel = geometria.wielokaty(M)
    wybrane = [n for n in wiel if wiel[n] is not None and (not pomieszczenia or n in pomieszczenia)]
    if not wybrane:
        raise SystemExit("zadne z pomieszczen %s nie daje zamknietego wielokata" % ",".join(pomieszczenia or []))
    obwiednia, wlasne = None, None
    if pomieszczenia:
        obwiednia = (min(wiel[n].bounds[0] for n in wybrane), min(wiel[n].bounds[1] for n in wybrane),
                     max(wiel[n].bounds[2] for n in wybrane), max(wiel[n].bounds[3] for n in wybrane))
        # tylko sciany i szachty ograniczajace wybrane pomieszczenia
        wlasne = {l["sciana"] or l["szacht"] for n in wybrane for l in geometria.lica(M, n)}

    def obr(pkt):
        return [obrot(x, y) for x, y in pkt]

    def w_regionie(b, ident, zapas=0.0):
        if obwiednia is None:
            return b
        if ident not in wlasne:
            return None
        x0, y0, x1, y1 = obwiednia
        g = box(*b).intersection(box(x0 - zapas - 0.5, y0 - zapas - 0.5, x1 + zapas + 0.5, y1 + zapas + 0.5))
        if g.is_empty:
            return None
        gx0, gy0, gx1, gy1 = g.bounds
        return g.bounds if min(gx1 - gx0, gy1 - gy0) >= 3 else None

    B = []
    for n in wybrane:
        w = wiel[n]
        podloga = model.pomieszczenie(M, n).get("podloga")
        B.append(bryla(obr(list(w.exterior.coords)[:-1]), -6, 0, PODLOGI.get(podloga, "#EFE9DD"), "#C9C2B0",
                       "podloga", [obr(list(d.coords)[:-1]) for d in w.interiors], 0.6))
    for s in M["sciany"]:
        styl = SCIANY["niska"] if "wys" in s else SCIANY["nosna"] if s.get("nosna") else SCIANY["dzialowa"]
        px0, py0, px1, py1 = geometria.prostokat(s["pas"]).bounds
        grub = min(px1 - px0, py1 - py0)
        for x0, y0, x1, y1, z0, z1, rodzaj in geometria.kawalki_sciany(M, s):
            z1 = min(z1, h)
            b = w_regionie((x0, y0, x1, y1), s["id"], grub)
            if b and z1 > z0 + 0.5:
                B.append(bryla(obr(prostokat(*b)), z0, z1, *styl))
    for sz in M.get("szachty", []):
        b = w_regionie(geometria.prostokat(sz["box"]).bounds, sz["id"], 100)
        if b:
            B.append(bryla(obr(prostokat(*b)), 0, h, *SZACHT))
    for g in M.get("grzejniki", []):
        if pomieszczenia and g.get("pomieszczenie") not in pomieszczenia:
            continue
        z0, z1 = g.get("wys", [15, 75])
        B.append(bryla(obr(prostokat(*geometria.prostokat(g["box"]).bounds)), z0, z1, *GRZEJNIK))
    for e in model.elementy(M):
        if pomieszczenia and e["_pom"] not in pomieszczenia:
            continue
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        z0, z1 = e.get("wys", [0, 75])
        kat = model.kategoria(e.get("rodzaj"))
        wyp_kat, obrys = plan.KOLORY_MEBLI.get(kat, plan.KOLORY_MEBLI["inne"])
        wyp = model.kolor(M, ("element", e["id"]), wybory) or (wyp_kat if wyp_kat != "none" else "#DDE4EE")
        pkt = kolo(x0, y0, x1, y1) if e.get("ksztalt") == "kolo" else prostokat(x0, y0, x1, y1)
        B.append(bryla(obr(pkt), z0, z1, wyp, obrys))
    return B


def za(a, b, eps=0.01):
    """1 gdy a lezy za b (rysowac wczesniej), -1 gdy przed, 0 gdy nie wiadomo."""
    ax0, ay0, ax1, ay1 = a["bb"]
    bx0, by0, bx1, by1 = b["bb"]
    if ax0 >= bx1 - eps or ay0 >= by1 - eps:
        return 1 if not (bx0 >= ax1 - eps or by0 >= ay1 - eps) else 0
    if bx0 >= ax1 - eps or by0 >= ay1 - eps:
        return -1
    if a["z1"] <= b["z0"] + eps:
        return 1
    if b["z1"] <= a["z0"] + eps:
        return -1
    return 0


def porzadek(B, rzut):
    """Kolejnosc malarza: podlogi, potem sortowanie topologiczne relacji "za / pod"."""
    podlogi = sorted([b for b in B if b["rodzaj"] == "podloga"], key=lambda b: -(b["bb"][0] + b["bb"][1]))
    reszta = [b for b in B if b["rodzaj"] != "podloga"]
    ekran = []
    for b in reszta:
        us, vs = [], []
        for x, y in b["pkt"]:
            for z in (b["z0"], b["z1"]):
                u, v = rzut(x, y, z)
                us.append(u)
                vs.append(v)
        ekran.append((min(us), min(vs), max(us), max(vs)))
    n = len(reszta)
    przed = [set() for _ in range(n)]     # i -> bryly, ktore trzeba narysowac po i
    stopien = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            ei, ej = ekran[i], ekran[j]
            if ei[2] <= ej[0] or ej[2] <= ei[0] or ei[3] <= ej[1] or ej[3] <= ei[1]:
                continue
            r = za(reszta[i], reszta[j])
            if r == 1:
                przed[i].add(j)
            elif r == -1:
                przed[j].add(i)
    for i in range(n):
        for j in przed[i]:
            stopien[j] += 1
    klucz = [-(b["bb"][0] + b["bb"][2] + b["bb"][1] + b["bb"][3]) / 2 + b["z0"] * 0.01 for b in reszta]
    gotowe = sorted([i for i in range(n) if stopien[i] == 0], key=lambda i: klucz[i])
    wynik, zostalo = [], set(range(n))
    while zostalo:
        if not gotowe:
            # cykl (bryly przenikajace sie): najdalsza z pozostalych
            i = min(zostalo, key=lambda k: klucz[k])
        else:
            i = gotowe.pop(0)
        if i not in zostalo:
            continue
        zostalo.discard(i)
        wynik.append(reszta[i])
        for j in przed[i]:
            stopien[j] -= 1
            if stopien[j] == 0 and j in zostalo:
                gotowe.append(j)
        gotowe.sort(key=lambda k: klucz[k])
    return podlogi + wynik


def rysuj_bryle(b, P):
    """Widoczne sciany boczne (od strony patrzacego) i wierzch; P(x, y, z) -> punkt arkusza."""
    s = []
    pkt, z0, z1 = b["pkt"], b["z0"], b["z1"]
    boki = []
    for i in range(len(pkt)):
        a, c = pkt[i], pkt[(i + 1) % len(pkt)]
        nx, ny = c[1] - a[1], -(c[0] - a[0])       # normalna zewnetrzna pierscienia CCW
        if nx + ny < -1e-9:
            boki.append((-(a[0] + a[1] + c[0] + c[1]), a, c, nx, ny))
    for _, a, c, nx, ny in sorted(boki):
        f = 0.66 + 0.18 * abs(ny) / (abs(nx) + abs(ny))
        s.append(svg.polilinia([P(*a, z0), P(*c, z0), P(*c, z1), P(*a, z1)], b["obr"], b["gr"],
                               wyp=ciemniej(b["wyp"], f), zamknij=True))
    d = "M " + " L ".join("%.1f %.1f" % P(x, y, z1) for x, y in pkt) + " Z"
    for dz in b["dziury"]:
        d += " M " + " L ".join("%.1f %.1f" % P(x, y, z1) for x, y in dz) + " Z"
    s.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" fill-rule="evenodd"/>' % (
        d, b["wyp"], b["obr"], b["gr"]))
    return "".join(s)


def legenda(M, B, wybory, pomieszczenia):
    poz = [(svg.prostokat(0, 3, 24, 13, SCIANY["nosna"][0], SCIANY["nosna"][1], 0.8), "ściana nośna (przekrój)"),
           (svg.prostokat(0, 3, 24, 13, SCIANY["dzialowa"][0], SCIANY["dzialowa"][1], 0.8), "ściana działowa"),
           (svg.prostokat(0, 3, 24, 13, SCIANY["niska"][0], SCIANY["niska"][1], 0.8), "balustrada, murek")]
    if M.get("szachty"):
        poz.append((svg.prostokat(2, 1, 22, 15, *SZACHT, 0.8), "szacht instalacyjny"))
    if M.get("grzejniki"):
        poz.append((svg.prostokat(0, 5, 24, 11, *GRZEJNIK, 0.8), "grzejnik"))
    tokeny, bez = [], False
    for e in model.elementy(M):
        if pomieszczenia and e["_pom"] not in pomieszczenia:
            continue
        t = model.token_celu(M, ("element", e["id"]), wybory)
        if t and t not in tokeny:
            tokeny.append(t)
        bez = bez or not t
    for t in tokeny:
        opis = model.tokeny(M).get(t, {}).get("opis")
        poz.append((svg.prostokat(0, 2, 24, 14, model.hex_tokenu(M, t), "#666", 0.6),
                    "%s%s" % (t, " — " + opis if opis else "")))
    if bez:
        poz.append((svg.prostokat(0, 2, 12, 14, plan.KOLORY_MEBLI["zabudowa_niska"][0], "#666", 0.6)
                    + svg.prostokat(12, 2, 24, 14, plan.KOLORY_MEBLI["siedzisko"][0], "#666", 0.6),
                    "element bez koloru w modelu — barwa kategorii jak na rzucie"))
    return poz


def izometria(M, h=120, pomieszczenia=None, widok="SW", wybory=None, nazwa=None):
    obrot = OBROTY[widok]
    B = zbierz(M, h, pomieszczenia, obrot, wybory)

    def rzut(x, y, z):
        return (x - y) * COS30, -(x + y) * SIN30 - z

    kolejne = porzadek(B, rzut)
    us, vs = [], []
    for b in B:
        for x, y in b["pkt"]:
            for z in (b["z0"], b["z1"]):
                u, v = rzut(x, y, z)
                us.append(u)
                vs.append(v)
    X0, Y0, X1, Y1 = arkusz.POLE
    Y0 += 40
    sk = min((X1 - X0 - 40) / (max(us) - min(us)), (Y1 - Y0 - 20) / (max(vs) - min(vs)))
    ox = X0 + ((X1 - X0) - (max(us) - min(us)) * sk) / 2 - min(us) * sk
    oy = Y0 + ((Y1 - Y0) - (max(vs) - min(vs)) * sk) / 2 - min(vs) * sk

    def P(x, y, z):
        u, v = rzut(x, y, z)
        return ox + u * sk, oy + v * sk

    s = [rysuj_bryle(b, P) for b in kolejne]
    # numery pomieszczen na podlodze
    wiel = geometria.wielokaty(M)
    for n, w in wiel.items():
        if w is None or (pomieszczenia and n not in pomieszczenia):
            continue
        rp = w.representative_point()
        stamp = model.pomieszczenie(M, n)["stamp"]
        x, y = obrot(*(stamp if w.contains(box(stamp[0] - 1, stamp[1] - 1, stamp[0] + 1, stamp[1] + 1))
                       else (rp.x, rp.y)))
        X, Y = P(x, y, 0)
        t = "%s %s" % (n, model.pomieszczenie(M, n).get("nazwa", ""))
        s.append(svg.prostokat(X - len(t) * 2.6 - 3, Y - 9, X + len(t) * 2.6 + 3, Y + 4, "#FFFFFF", None, przezr=0.7))
        s.append(svg.tekst(X, Y, t, 9.5, "middle", kolor="#555"))
    az_osi = M.get("meta", {}).get("polnoc", {}).get("azymut_osi_Y_stopnie", 0)
    kx, ky = KIERUNEK_WIDOKU[widok]
    strona = slonce.strona_swiata((az_osi + math.degrees(math.atan2(kx, ky))) % 360)
    opis = ("Ściany przycięte na wysokości %s cm, meble w pełnych wysokościach, kolory z modelu%s. "
            "Widok od narożnika %s osi modelu (od strony: %s)." % (
                svg.fmt(h), " (warianty: %s)" % ", ".join("%s=%d" % kv for kv in sorted(wybory.items())) if wybory else "",
                widok, strona))
    s.append(svg.tekst(X0, arkusz.POLE[1] + 14, opis, 11, kolor="#444"))
    tytul = "Izometria" + (" — %s" % nazwa if nazwa else "")
    if pomieszczenia:
        tytul += " (%s)" % ", ".join(pomieszczenia)
    poz = legenda(M, B, wybory, pomieszczenia)
    polowa = (len(poz) + 1) // 2
    tresc = "".join(s) + arkusz.legenda(poz[:polowa], 50, 1800, 320)[0] + \
        arkusz.legenda(poz[polowa:], 375, 1800, 320, tytul="")[0]
    return arkusz.arkusz(M, "A-03", tytul, "bez skali (aksonometria izometryczna)", tresc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--pomieszczenia", help="numery pomieszczen po przecinku, np. P3,P1 (domyslnie caly lokal)")
    ap.add_argument("--h", type=float, default=120, help="wysokosc ciecia scian w cm (domyslnie 120)")
    ap.add_argument("--nazwa", help="dopisek w nazwie pliku i tytule, np. kuchnia")
    ap.add_argument("--widok", default="SW", choices=sorted(OBROTY), help="naroznik osi modelu, od ktorego patrzymy")
    ap.add_argument("--wybory", default="", help="warianty wykonczenia, np. V1=1,V2=0")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj rysunki/glb.py (makieta 3D) albo planer3d/serwer.py; "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        sys.exit(2)
    pom = [p.strip() for p in a.pomieszczenia.split(",") if p.strip()] if a.pomieszczenia else None
    for nr in pom or []:
        try:
            model.pomieszczenie(M, nr)
        except KeyError:
            raise SystemExit("brak pomieszczenia %s w modelu" % nr)
    dok = izometria(M, a.h, pom, a.widok, model.wybory_z_tekstu(a.wybory), a.nazwa)
    nazwa = "izometria" + ("_" + a.nazwa if a.nazwa else "")
    for p in svg.zapisz(dok, model.sciezka_wyniku(M, nazwa, a.wyjscie), pdf=True):
        print("zapisano", p)


if __name__ == "__main__":
    main()
