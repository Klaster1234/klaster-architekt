"""Klady scian z modelu: lico sciany widziane z wnetrza pomieszczenia z punktami
elektrycznymi opisanymi para a·h, meblami przy scianie, otworami i linia sufitu.

    python rysunki/klady.py przyklad/mieszkanie/model/lokal_projekt.json
    python rysunki/klady.py przyklad/mieszkanie/model/lokal_projekt.json --tylko K-01
    python rysunki/klady.py przyklad/mieszkanie/model/lokal_projekt.json --zestawienie

Konfiguracja w modelu: klady[] = {id, pomieszczenie, sciana, tytul?, strona?}; id jest
kodem arkusza (K-01 ...), sciana to id sciany, strona (N/E/S/W) wybiera
lico, gdy pomieszczenie dotyka tej sciany z kilku stron (strona sciany, po ktorej lezy
lico). Patrzacy stoi w pomieszczeniu twarza do sciany: a = 0 na lewym koncu lica, a
rosnie w prawo; h to wysokosc osi od podlogi wykonczonej (elektryka[].h).

Na kladzie: punkty E lezace nie dalej niz 5 cm od lica, meble przy licu (do 5 cm) z
wysokosciami z pola wys, otwory i okladziny lica, przeciete sciany sasiednie, strop
i rzedna sufitu (RS), lancuch polozen a, rzedne h, miniatura z kierunkiem patrzenia
i tabela punktow. --zestawienie dodaje arkusz K-00 z punktami ze scian bez kladu
(pogrupowanymi wg pomieszczenia i sciany) oraz punktami w polu (sufitowymi).
Wynik: <wyjscie>/<id>_<kod>.svg|png|pdf oraz <id>_K-00_zestawienie.svg|png|pdf.
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wspolne import svg, arkusz
from wspolne.opisy import Opisy, blok_tekstu, rect_tekstu, szer_tekstu as szer
from lokal import model, geometria, plan
from zamierzenie import model as zmodel

DOTYK = 5                              # punkt lub mebel "na licu": nie dalej niz 5 cm
STRONY = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
POLE_KLADU = (50, 122, 1430, 1160)     # pole widoku sciany; pod nim tabela i miniatura
KOLOR_SCIANY = "#F7F5EF"
KOLOR_RS = "#8A7F6A"
KOLOR_WYM = plan.KOLOR["wymiar"]


def wlasciciel(lico):
    return lico["sciana"] or lico["szacht"]


def rodzaj_elementu(M, ident):
    return "ściana" if any(s["id"] == ident for s in M["sciany"]) else "szacht"


def strona_normalnej(n):
    """Strona sciany, po ktorej lezy lico (kierunek od sciany do pomieszczenia)."""
    if abs(n[1]) >= abs(n[0]):
        return "N" if n[1] > 0 else "S"
    return "E" if n[0] > 0 else "W"


def uklad_lica(M, nr, ident, strona=None):
    """Uklad kladu: lewy koniec P0, kierunek a (e), normalna do wnetrza (n), dlugosc L i sasiedzi.

    Wspolliniowe lica tej samej sciany po tej samej stronie (np. przerwane szachtem) tworza
    jeden klad. None, gdy pomieszczenie nie ma lica tej sciany.
    """
    lica = [l for l in geometria.lica(M, nr) if wlasciciel(l) == ident]
    if strona:
        v = STRONY[strona]
        lica = [l for l in lica if l["normalna"][0] * v[0] + l["normalna"][1] * v[1] > 0.7]
    if not lica:
        return None
    F = max(lica, key=lambda l: l["dl"])
    n = F["normalna"]
    # patrzacy twarza do lica ma po lewej koniec "b" lica (wnetrze po lewej stronie krawedzi a->b)
    e = ((F["a"][0] - F["b"][0]) / F["dl"], (F["a"][1] - F["b"][1]) / F["dl"])
    grupa = [l for l in lica if abs(l["normalna"][0] - n[0]) + abs(l["normalna"][1] - n[1]) < 1e-6
             and abs((l["a"][0] - F["a"][0]) * n[0] + (l["a"][1] - F["a"][1]) * n[1]) < 0.5]
    pkt = sorted(((p[0] * e[0] + p[1] * e[1]), p) for l in grupa for p in (l["a"], l["b"]))
    U = {"nr": nr, "ident": ident, "P0": pkt[0][1], "P1": pkt[-1][1], "e": e, "n": n,
         "L": pkt[-1][0] - pkt[0][0], "lica": grupa}
    U["lewy"] = sasiad(M, U, lewy=True)
    U["prawy"] = sasiad(M, U, lewy=False)
    return U


def a_s(U, xy):
    """(a, s): polozenie wzdluz lica od lewego konca i odleglosc od lica w strone pomieszczenia."""
    dx, dy = xy[0] - U["P0"][0], xy[1] - U["P0"][1]
    return dx * U["e"][0] + dy * U["e"][1], dx * U["n"][0] + dy * U["n"][1]


def sasiad(M, U, lewy):
    """Lico sasiadujace z kladem na lewym (albo prawym) koncu; wypukly = sciana sasiada jest przecieta."""
    punkt = U["P0"] if lewy else U["P1"]
    for l in geometria.lica(M, U["nr"]):
        if l in U["lica"]:
            continue
        q = l["a"] if lewy else l["b"]
        if math.hypot(q[0] - punkt[0], q[1] - punkt[1]) < 0.5:
            d = ((l["b"][0] - l["a"][0]) / l["dl"], (l["b"][1] - l["a"][1]) / l["dl"])
            dn = d[0] * U["n"][0] + d[1] * U["n"][1]
            return {"lico": l, "wypukly": dn > 0.5 if lewy else dn < -0.5}
    return None


def opis_sasiada(M, U, lewy=True):
    """Slowny opis punktu a = 0 (albo prawego konca): z czym styka sie koniec lica."""
    s = U["lewy"] if lewy else U["prawy"]
    if not s:
        return "koniec lica"
    l = s["lico"]
    if l["sciana"]:
        typ = next((x.get("typ", "") for x in M["sciany"] if x["id"] == l["sciana"]), "")
        rodzaj = "narożnik ze ścianą" if s["wypukly"] else "narożnik wklęsły ze ścianą"
        return "%s %s%s" % (rodzaj, l["sciana"], " (%s)" % typ if typ else "")
    if l["szacht"]:
        return "lico szachtu %s" % l["szacht"]
    return "granica strefy (bez ściany)"


def przekroj_sasiada(M, U, lewy):
    """(a0, a1, rodzaj, id, z0, z1) przecietej sciany lub szachtu na koncu kladu albo None."""
    s = U["lewy"] if lewy else U["prawy"]
    if not s or not s["wypukly"]:
        return None
    l = s["lico"]
    if l["sciana"]:
        sc = next(x for x in M["sciany"] if x["id"] == l["sciana"])
        b = geometria.prostokat(sc["pas"]).bounds
        rodzaj = "niska" if "wys" in sc else "nosna" if sc.get("nosna") else "dzialowa"
        z0, z1 = sc.get("wys", [0, model.wysokosc(M)])
    else:
        sz = next(x for x in M.get("szachty", []) if x["id"] == l["szacht"])
        b = geometria.prostokat(sz["box"]).bounds
        rodzaj, z0, z1 = "szacht", 0, model.wysokosc(M)
    aa = [a_s(U, (x, y))[0] for x in (b[0], b[2]) for y in (b[1], b[3])]
    if lewy:
        a0, a1 = max(min(aa), -60), 0.0
    else:
        a0, a1 = U["L"], min(max(aa), U["L"] + 60)
    return (a0, a1, rodzaj, wlasciciel(l), z0, z1) if a1 - a0 > 0.5 else None


def najblizsze_lico(M, nr, xy):
    """(lico, odleglosc) najblizszego lica sciany lub szachtu pomieszczenia (z zakresem lica) albo (None, None)."""
    naj = (None, None)
    for l in geometria.lica(M, nr):
        if not wlasciciel(l):
            continue
        (ax, ay), (bx, by) = l["a"], l["b"]
        nx, ny = l["normalna"]
        s = abs((xy[0] - ax) * nx + (xy[1] - ay) * ny)
        t = ((xy[0] - ax) * (bx - ax) + (xy[1] - ay) * (by - ay)) / l["dl"]
        if s <= DOTYK and -1 <= t <= l["dl"] + 1 and (naj[1] is None or s < naj[1] - 0.01):
            naj = (l, s)
    return naj


def punkty_lica(M, U):
    """Punkty E na licu: [(a, h, punkt)] posortowane wzdluz lica.

    Punkt przy narozniku (do 5 cm od dwoch lic) nalezy do lica, do ktorego ma blizej.
    """
    wynik = []
    for e in M.get("elektryka", []):
        a, s = a_s(U, e["xy"])
        if abs(s) <= DOTYK and -1 <= a <= U["L"] + 1:
            l, odl = najblizsze_lico(M, U["nr"], e["xy"])
            if l is not None and l not in U["lica"] and odl < abs(s) - 0.01:
                continue
            wynik.append((a, e.get("h"), e))
    return sorted(wynik, key=lambda w: (w[0], w[1] if w[1] is not None else -1))


def meble_lica(M, U):
    """Elementy aranzacji przy licu: [(a0, a1, z0, z1, gleb, element, frontem)]."""
    wynik = []
    for e in model.elementy(M):
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        pkt = [a_s(U, (x, y)) for x in (x0, x1) for y in (y0, y1)]
        s_min, s_max = min(p[1] for p in pkt), max(p[1] for p in pkt)
        a0, a1 = max(min(p[0] for p in pkt), 0), min(max(p[0] for p in pkt), U["L"])
        if s_min > DOTYK or s_max <= 0 or a1 - a0 < 1:
            continue
        z0, z1 = e.get("wys", [0, 75])
        # bez pola front element rysuje sie jak widziany z przodu; przerywana tylko bok lub tyl
        v = STRONY.get(e.get("front"), U["n"])
        frontem = v[0] * U["n"][0] + v[1] * U["n"][1] > 0.7
        wynik.append((a0, a1, z0, z1, s_max, e, frontem))
    return sorted(wynik, key=lambda m: m[4])


def podzialy_a(U, e):
    """Polozenia a linii podzialu segmentow elementu stojacego frontem do patrzacego."""
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    wynik = []
    for os, v in plan.podzialy_segmentow(e):
        xy = (v, (y0 + y1) / 2) if os == "x" else ((x0 + x1) / 2, v)
        wynik.append(a_s(U, xy)[0])
    return sorted(wynik)


def otwory_lica(M, U):
    """Otwory w licu: [(a0, a1, z0, z1, otwor)]."""
    wynik = []
    for o in M.get("otwory", []):
        if o["sciana"] != U["ident"]:
            continue
        x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
        aa = [a_s(U, (x, y))[0] for x in (x0, x1) for y in (y0, y1)]
        a0, a1 = max(min(aa), 0), min(max(aa), U["L"])
        if a1 - a0 > 1:
            wynik.append((a0, a1, o.get("parapet") or 0, o.get("wys_otw", 205), o))
    return wynik


def okladziny_lica(M, U):
    wynik = []
    for ok in (M.get("wykonczenie") or {}).get("okladziny", []):
        (p, q) = ok["odcinek"]
        (ap, sp), (aq, sq) = a_s(U, p), a_s(U, q)
        if abs(sp) <= DOTYK and abs(sq) <= DOTYK:
            a0, a1 = max(min(ap, aq), 0), min(max(ap, aq), U["L"])
            if a1 - a0 > 1:
                wynik.append((a0, a1, ok["z"][0], ok["z"][1], ok))
    return wynik


def opis_punktu(e):
    t = e.get("typ", "")
    if e.get("krotnosc"):
        t += " %d×" % e["krotnosc"]
    if e.get("ip"):
        t += " IP%s" % e["ip"]
    return t


def symbol(e, X, Y):
    s = plan.symbol_e(e["typ"], X, Y, 7)
    if e.get("ip"):
        s += svg.okrag(X, Y, 10, "none", plan.KOLORY_E.get(e["typ"], "#555"), 0.8)
    return s


def widok_kladu(zakres, pole):
    sk, skala_txt = arkusz.skala_arkusza(zakres, pole)
    return arkusz.Widok(zakres, pole, sk), skala_txt


def rysuj_klad(M, U):
    """Tresc arkusza kladu (bez ramki i tabliczki): widok lica, tabela punktow, miniatura, uwagi."""
    H, RS, L = model.wysokosc(M), model.rzedna_sufitu(M), U["L"]
    lewy, prawy = przekroj_sasiada(M, U, True), przekroj_sasiada(M, U, False)
    punkty = punkty_lica(M, U)
    meble = meble_lica(M, U)
    otwory = otwory_lica(M, U)
    amin = (lewy[0] if lewy else 0) - 48
    amax = (prawy[1] if prawy else L) + 18
    W, skala_txt = widok_kladu((amin, -58, amax, H + 44), POLE_KLADU)
    P = W.p
    miejsca = Opisy()
    s = []

    def rect(a0, h0, a1, h1):
        (X0, Y0), (X1, Y1) = P(a0, h1), P(a1, h0)
        return (X0, Y0, X1, Y1)

    # sciana, okladziny, otwory, przekroje sasiednich scian
    s.append(svg.prostokat(*rect(0, 0, L, H), KOLOR_SCIANY, None))
    for a0, a1, z0, z1, ok in okladziny_lica(M, U):
        s.append(svg.prostokat(*rect(a0, z0, a1, z1), model.kolor(M, ("okladzina", ok["id"])) or "#E8E4DC",
                               "#B8B0A0", 0.6, "3 2", 0.55))
        r = rect(a0, z0, a1, z1)
        s.append(svg.tekst(r[2] - 4, r[3] - 3, "%s %s" % (ok["id"], ok.get("wzor", "")), 7, "end", kolor="#8A8272"))
    for a0, a1, z0, z1, o in otwory:
        okno = o["rodzaj"] == "okno"
        kol = plan.KOLOR["okno"] if okno else plan.KOLOR["drzwi"]
        r = rect(a0, z0, a1, z1)
        s.append(svg.prostokat(*r, "#EEF5FB" if okno else "#FFFFFF", kol, 1.2))
        if okno:
            s.append(svg.linia((r[0] + r[2]) / 2, r[1], (r[0] + r[2]) / 2, r[3], kol, 0.6))
        linie = [("%s %s/%s" % (o["id"], svg.fmt(o.get("szer_otw") or a1 - a0), svg.fmt(z1)), 8)]
        if z0:
            linie.append(("parapet %s" % svg.fmt(z0), 7.5))
        pion = rect_tekstu(0, 0, linie)[2] * 2 > (r[2] - r[0]) - 6
        k = rect_tekstu((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, linie, pion)
        miejsca.zajmij(k)
        s.append(blok_tekstu(k, linie, pion, kolory=[kol], pogrubiony=True))
    for prz in (lewy, prawy):
        if not prz:
            continue
        a0, a1, rodzaj, ident, z0, z1 = prz
        wyp, obr = plan.KOLOR["szacht"] if rodzaj == "szacht" else (plan.KOLOR[rodzaj], None)
        r = rect(a0, z0, a1, z1)
        s.append(svg.prostokat(*r, wyp, obr, 1))
        k = rect_tekstu((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, [(ident, 8)], True)
        miejsca.zajmij(k)
        s.append(blok_tekstu(k, [(ident, 8)], True, kolory=["#FFFFFF" if rodzaj != "szacht" else obr], pogrubiony=True))

    # meble przy licu
    lan_meble = {0.0, round(L, 1)}
    krawedzie = []
    for a0, a1, z0, z1, gleb, e, frontem in meble:
        kat = model.kategoria(e.get("rodzaj"))
        wyp, obr = plan.KOLORY_MEBLI.get(kat, plan.KOLORY_MEBLI["inne"])
        r = rect(a0, z0, a1, z1)
        s.append(svg.prostokat(*r, wyp if wyp != "none" else "#E6ECF4", obr, 1.3 if frontem else 1.0,
                               None if frontem else "6 3", 0.92))
        krawedzie += [(r[0], r[1], r[2], r[1]), (r[0], r[3], r[2], r[3]), (r[0], r[1], r[0], r[3]), (r[2], r[1], r[2], r[3])]
        lan_meble.update((round(a0, 1), round(a1, 1)))
        if frontem:
            dz = podzialy_a(U, e)
            lan_meble.update(round(v, 1) for v in dz if a0 < v < a1)
            granice = [a0] + [v for v in dz if a0 + 0.5 < v < a1 - 0.5] + [a1]
            for v in granice[1:-1]:
                X = P(v, 0)[0]
                s.append(svg.linia(X, r[1], X, r[3], obr, 0.7))
                krawedzie.append((X, r[1], X, r[3]))
    # strop, podloga, rzedna sufitu
    X0, X1 = P(amin + 30, 0)[0], P(amax - 4, 0)[0]
    s.append(svg.linia(X0, P(0, 0)[1], X1, P(0, 0)[1], "#111", 2.4))
    s.append(svg.linia(X0, P(0, H)[1], X1, P(0, H)[1], "#111", 2.4))
    t = "podłoga wykończona ±0"
    k = (X0 + 2, P(0, 0)[1] + 3, X0 + 2 + szer(t, 8.5), P(0, 0)[1] + 14)
    miejsca.zajmij(k)
    s.append(svg.tekst(k[0], k[3] - 2, t, 8.5, kolor="#555"))
    t = "strop +%s" % svg.fmt(H)
    k = (X0 + 2, P(0, H)[1] - 14, X0 + 2 + szer(t, 8.5), P(0, H)[1] - 3)
    miejsca.zajmij(k)
    s.append(svg.tekst(k[0], k[3] - 2, t, 8.5, kolor="#555"))
    if RS < H - 0.5:
        Y = P(0, RS)[1]
        s.append(svg.linia(X0, Y, X1, Y, KOLOR_RS, 1.2, "9 4"))
        status = ((M.get("meta", {}).get("rzedna_sufitu") or {}).get("status") or "").strip()
        t = "spód sufitu RS +%s%s" % (svg.fmt(RS), " — " + status if status else "")
        Xp = P(0, 0)[0] + 4
        k = (Xp, Y - 12, Xp + szer(t, 8), Y - 2) if P(0, H)[1] < Y - 13 else (Xp, Y + 2, Xp + szer(t, 8), Y + 12)
        miejsca.zajmij(k)
        s.append(svg.tekst(k[0], k[3] - 1.5, t, 8, kolor=KOLOR_RS))

    # punkty E i opisy a·h (przed opisami mebli, bo sa wazniejsze)
    rysowane = [(a, h, e) for a, h, e in punkty if h is not None]
    for a, h, e in rysowane:
        X, Y = P(a, h)
        miejsca.zajmij((X - 11, Y - 11, X + 11, Y + 11))
    opisy_pkt = []
    for a, h, e in rysowane:
        X, Y = P(a, h)
        linie = [(e["id"] + (" · %d×" % e["krotnosc"] if e.get("krotnosc", 1) > 1 else ""), 9.5),
                 ("a=%s · h=%s" % (svg.fmt(a), svg.fmt(h)), 8)]
        w0 = rect_tekstu(0, 0, linie)
        hw, hh = (w0[2] - w0[0]) / 2, (w0[3] - w0[1]) / 2
        kand = []
        for odl in (13, 24, 38):
            kand += [rect_tekstu(X, Y + odl + hh - 4, linie), rect_tekstu(X, Y - odl - hh + 4, linie),
                     rect_tekstu(X + odl + hw, Y, linie), rect_tekstu(X - odl - hw, Y, linie)]
        k = miejsca.wybierz(kand) or kand[0]
        opisy_pkt.append(svg.prostokat(k[0] - 1, k[1], k[2] + 1, k[3], "#FFFFFF", None, przezr=0.82))
        opisy_pkt.append(blok_tekstu(k, linie, kolory=["#111", "#444"], pogrubiony=True))
    # opisy mebli i segmentow (w wolnych miejscach wewnatrz bryly, bez przecinania krawedzi)
    for k in krawedzie:
        miejsca.zajmij(k)
    for a0, a1, z0, z1, gleb, e, frontem in meble:
        kat = model.kategoria(e.get("rodzaj"))
        obr = plan.KOLORY_MEBLI.get(kat, plan.KOLORY_MEBLI["inne"])[1]
        r = rect(a0, z0, a1, z1)
        if frontem and e.get("segmenty"):
            dz = [v for v in podzialy_a(U, e) if a0 + 0.5 < v < a1 - 0.5]
            granice = [a0] + dz + [a1]
            for seg, (s0, s1) in zip(e["segmenty"], zip(granice, granice[1:])):
                rs = rect(s0, z0, s1, z1)
                linie = [(seg.get("opis") or svg.fmt(seg["dl"]), 7.5)]
                kand = []
                for f in (0.12, 0.3, 0.5, 0.7, 0.88):
                    for pion in (False, True):
                        k = rect_tekstu((rs[0] + rs[2]) / 2, rs[3] - (rs[3] - rs[1]) * f, linie, pion)
                        if k[0] >= rs[0] + 2 and k[2] <= rs[2] - 2 and k[1] >= rs[1] + 2 and k[3] <= rs[3] - 2:
                            kand.append((k, pion))
                wyb = next(((k, pion) for k, pion in kand if miejsca.wolne(k)), None)
                if wyb:
                    miejsca.zajmij(wyb[0])
                    s.append(blok_tekstu(wyb[0], linie, wyb[1], kolory=[obr], pogrubiony=False))
        h_txt = "h %s–%s" % (svg.fmt(z0), svg.fmt(z1)) if z0 else "h %s" % svg.fmt(z1)
        linie = [("%s %s" % (e["id"], e.get("rodzaj", "")), 8.5), (h_txt, 7.5)]
        kand = []
        # srodki segmentow (od srodka bryly), zeby opis nie przecinal linii podzialu
        srodki_a = [0.5, 0.3, 0.7]
        if frontem and e.get("segmenty"):
            gr = [a0] + [v for v in podzialy_a(U, e) if a0 + 0.5 < v < a1 - 0.5] + [a1]
            srodki_a = sorted((((p + q) / 2 - a0) / (a1 - a0) for p, q in zip(gr, gr[1:])),
                              key=lambda g: abs(g - 0.5)) + srodki_a
        for f in (0.5, 0.75, 0.25, 0.88, 0.12):
            for g in srodki_a:
                for pion in (False, True):
                    k = rect_tekstu(r[0] + (r[2] - r[0]) * g, r[3] - (r[3] - r[1]) * f, linie, pion)
                    if k[0] >= r[0] + 2 and k[2] <= r[2] - 2 and k[1] >= r[1] + 2 and k[3] <= r[3] - 2:
                        kand.append((k, pion))
        kand.sort(key=lambda kp: kp[1])
        wyb = next(((k, pion) for k, pion in kand if miejsca.wolne(k)), None)
        if wyb:
            miejsca.zajmij(wyb[0])
            s.append(blok_tekstu(wyb[0], linie, wyb[1], kolory=[obr, "#555"], pogrubiony=True))
    s += [symbol(e, *P(a, h)) for a, h, e in rysowane]
    s += opisy_pkt

    # lancuchy: polozenia a pod podloga, calosc, meble nad stropem, rzedne h z lewej
    a_pkt = sorted({round(a, 1) for a, h, e in punkty if 0.5 < a < L - 0.5})
    s.append(plan.lancuch(W, (0, 0), (L, 0), (0, -1), 20, a_pkt, kolor=KOLOR_WYM, r=8.5, min_seg=1))
    s.append(plan.lancuch(W, (0, 0), (L, 0), (0, -1), 40, kolor=plan.KOLOR["wymiar_zewn"], r=9.5))
    s.append(svg.tekst(P(0, 0)[0], P(0, -52)[1] + 4, "a — od lewego końca lica (a = 0: %s)" % opis_sasiada(M, U),
                       8, kolor=KOLOR_WYM))
    for a0, a1, z0, z1, o in otwory:
        lan_meble.update((round(a0, 1), round(a1, 1)))
    if len(lan_meble) > 2:
        podz = sorted(v for v in lan_meble if 0.5 < v < L - 0.5)
        s.append(plan.lancuch(W, (0, H), (L, H), (0, 1), 16, podz, kolor=KOLOR_WYM, r=8, min_seg=1))
        s.append(svg.tekst(P(0, 0)[0], P(0, H + 34)[1] + 3, "meble, segmenty i otwory przy ścianie", 8, kolor=KOLOR_WYM))
    rzedne = sorted({0.0, round(H, 1)} | {round(h, 1) for a, h, e in rysowane} | ({round(RS, 1)} if RS < H else set()))
    Xv = P(amin + 14, 0)[0]
    s.append(svg.linia(Xv, P(0, 0)[1], Xv, P(0, H)[1], KOLOR_WYM, 0.9))
    poprz = None
    for h in rzedne:
        Y = P(0, h)[1]
        s.append(svg.linia(Xv - 3.2, Y + 3.2, Xv + 3.2, Y - 3.2, KOLOR_WYM, 1.1))
        s.append(svg.linia(Xv, Y, P(0, 0)[0], Y, KOLOR_WYM, 0.35, "2 3"))
        if poprz is None or abs(Y - poprz) > 9:
            s.append(svg.tekst(Xv - 6, Y + 3, svg.fmt(h), 8, "end", kolor=KOLOR_WYM))
            poprz = Y
    s.append(svg.tekst(Xv - 6, P(0, H)[1] - 12, "h", 8.5, "end", kolor=KOLOR_WYM, waga="bold"))
    return "".join(s), skala_txt, punkty


def tabela_punktow(punkty, x, y, szer_tab, maks_y):
    """Tabela punktow kladu; zwraca svg."""
    kolumny = [("Punkt", 0), ("Typ", 56), ("Wariant", 230), ("a", 410), ("h", 460), ("Obwód", 510), ("Uwagi", 620)]
    s = [svg.tekst(x, y + 12, "PUNKTY NA KŁADZIE", 11, waga="bold")]
    yy = y + 34
    for naz, dx in kolumny:
        s.append(svg.tekst(x + dx, yy, naz, 9, waga="bold"))
    s.append(svg.linia(x, yy + 5, x + szer_tab, yy + 5, "#111", 0.8))
    yy += 20
    if not punkty:
        s.append(svg.tekst(x, yy, "Na tym licu nie ma punktów elektrycznych.", 9, kolor="#555"))
    for a, h, e in punkty:
        if yy > maks_y:
            s.append(svg.tekst(x, yy, "… dalsze punkty w modelu (tabela nie mieści się na arkuszu)", 8.5, kolor="#A00"))
            break
        uwagi = e.get("opis") or ""
        if e.get("wyjatek"):
            uwagi = (uwagi + "; " if uwagi else "") + "wyjątek: " + e["wyjatek"]
        wiersz = [e["id"], opis_punktu(e), e.get("wariant") or "—", svg.fmt(a), svg.fmt(h) if h is not None else "—",
                  e.get("obwod") or "—", uwagi]
        for (naz, dx), v in zip(kolumny, wiersz):
            maks = {"Typ": 30, "Wariant": 30, "Obwód": 18, "Uwagi": 44}.get(naz)
            v = str(v)
            if maks and len(v) > maks:
                v = v[:maks - 1] + "…"
            s.append(svg.tekst(x + dx, yy, v, 9 if naz == "Punkt" else 8.5, waga="bold" if naz == "Punkt" else None))
        yy += 17
    return "".join(s)


def miniatura_kladu(M, U, x, y, w, h):
    """plan.miniatura z kierunkiem patrzenia i zaznaczonym licem."""
    L = U["L"]
    (px, py), (nx, ny) = U["P0"], U["n"]
    sx, sy = px + U["e"][0] * L / 2, py + U["e"][1] * L / 2
    wiel = geometria.wielokaty(M)[U["nr"]]
    glab = max((vx - px) * nx + (vy - py) * ny for vx, vy in wiel.exterior.coords)
    odl = min(90.0, glab * 0.45)
    kat = math.degrees(math.atan2(-ny, -nx))
    s = plan.miniatura(M, x, y, w, h, nr=U["nr"], patrz=((sx + nx * odl, sy + ny * odl), kat))
    Wm = arkusz.Widok(geometria.obrys(M).bounds, (x + 6, y + 6, x + w - 6, y + h - 6))
    for l in U["lica"]:
        s += svg.linia(*Wm.p(*l["a"]), *Wm.p(*l["b"]), "#C0392B", 3)
    s += svg.tekst(x + 6, y + h + 13, "lokalizacja kładu i kierunek patrzenia", 8, kolor="#666")
    return s


def legenda_kladu(punkty, meble, otwory):
    poz = [(svg.prostokat(0, 2, 24, 14, KOLOR_SCIANY, "#999", 0.6), "lico ściany (widok z wnętrza)"),
           (svg.linia(0, 8, 24, 8, KOLOR_RS, 1.2, "9 4"), "spód sufitu podwieszanego (RS)")]
    typy = []
    for a, h, e in punkty:
        if e["typ"] not in typy:
            typy.append(e["typ"])
    for t in typy:
        poz.append((plan.symbol_e(t, 12, 8, 6), "punkt: %s" % t))
    if any(e.get("ip") for a, h, e in punkty):
        poz.append((svg.okrag(12, 8, 7, "none", "#555", 0.8), "podwójny okrąg: stopień ochrony IP"))
    if meble:
        poz.append((svg.prostokat(0, 2, 24, 14, "#E8ECDB", "#5C6E3A", 1.3),
                    "mebel frontem do patrzącego (podziały segmentów)"))
        poz.append((svg.prostokat(0, 2, 24, 14, "#E8ECDB", "#5C6E3A", 1, "6 3"), "mebel bokiem lub tyłem do patrzącego"))
    if otwory:
        poz.append((svg.prostokat(2, 1, 22, 15, "#EEF5FB", plan.KOLOR["okno"], 1), "okno / drzwi w licu"))
    return poz


def arkusz_kladu(M, K):
    U = uklad_lica(M, K["pomieszczenie"], K["sciana"], K.get("strona"))
    if U is None:
        raise ValueError("klad %s: pomieszczenie %s nie ma lica sciany %s%s" % (
            K["id"], K["pomieszczenie"], K["sciana"], " (strona %s)" % K["strona"] if K.get("strona") else ""))
    tresc, skala_txt, punkty = rysuj_klad(M, U)
    p = model.pomieszczenie(M, K["pomieszczenie"])
    tytul = K.get("tytul") or "Kład ściany %s — %s %s" % (K["sciana"], K["pomieszczenie"], p.get("nazwa", ""))
    podtytul = "%s %s — %s %s widziana z wnętrza pomieszczenia; długość lica %s cm" % (
        K["pomieszczenie"], p.get("nazwa", ""), rodzaj_elementu(M, K["sciana"]), K["sciana"], svg.fmt(U["L"]))
    tresc = svg.tekst(50, 108, podtytul, 10.5, kolor="#555") + tresc
    tresc += tabela_punktow(punkty, 50, 1190, 900, 1760)
    tresc += miniatura_kladu(M, U, 1000, 1195, 430, 250)
    H, RS = model.wysokosc(M), model.rzedna_sufitu(M)
    uwagi = [
        "Każdy punkt opisany parą a · h: a — odległość osi od lewego końca lica patrząc na ścianę z wnętrza "
        "pomieszczenia, h — wysokość osi od podłogi wykończonej.",
        "a = 0: %s; prawy koniec lica: %s." % (opis_sasiada(M, U), opis_sasiada(M, U, lewy=False)),
        "Strop +%s, spód sufitu RS +%s. Wymiary w cm." % (svg.fmt(H), svg.fmt(RS)),
        "Meble i otwory z modelu lokalu; wiążące wymiary zabudowy podaje jej projekt wykonawczy.",
    ]
    czesc, _ = arkusz.uwagi(uwagi, 1000, 1480, 430)
    tresc += czesc
    poz = legenda_kladu(punkty, meble_lica(M, U), otwory_lica(M, U))
    polowa = (len(poz) + 1) // 2
    tresc += arkusz.legenda(poz[:polowa], 50, 1800, 320)[0] + arkusz.legenda(poz[polowa:], 375, 1800, 320, tytul="")[0]
    return arkusz.arkusz(M, K["id"], tytul, skala_txt, tresc)


def gdzie_lezy(M, e):
    """(nr, lico) najblizszej sciany lub szachtu przy punkcie; najpierw lica wlasnego pomieszczenia."""
    kolej = [e.get("pomieszczenie")] + [n for n in geometria.wielokaty(M) if n != e.get("pomieszczenie")]
    for nr in kolej:
        if not nr or geometria.wielokaty(M).get(nr) is None:
            continue
        l, _ = najblizsze_lico(M, nr, e["xy"])
        if l is not None:
            return nr, l
    return None, None


def arkusze_zestawienia(M, uklady):
    """Arkusz(e) K-00: punkty na scianach bez kladu (a·h) i punkty w polu pomieszczen."""
    na_kladach = set()
    for U in uklady:
        na_kladach.update(e["id"] for a, h, e in punkty_lica(M, U))
    grupy, w_polu = {}, []
    for e in M.get("elektryka", []):
        if e["id"] in na_kladach:
            continue
        nr, l = gdzie_lezy(M, e)
        if l is None:
            w_polu.append(e)
            continue
        klucz = (nr, wlasciciel(l), strona_normalnej(l["normalna"]))
        grupy.setdefault(klucz, []).append(e)
    wiersze = []    # ("naglowek", tekst) | ("punkt", [...]) | ("tekst", tekst)
    for (nr, ident, strona), lista in sorted(grupy.items()):
        U = uklad_lica(M, nr, ident, strona)
        p = model.pomieszczenie(M, nr)
        wiersze.append(("naglowek", "%s %s — %s %s (lico dł. %s); a = 0: %s" % (
            nr, p.get("nazwa", ""), rodzaj_elementu(M, ident), ident, svg.fmt(U["L"]), opis_sasiada(M, U))))
        for e in sorted(lista, key=lambda e: a_s(U, e["xy"])[0]):
            a = a_s(U, e["xy"])[0]
            wiersze.append(("punkt", [e["id"], e.get("pomieszczenie") or "—", svg.fmt(a),
                                      svg.fmt(e["h"]) if e.get("h") is not None else "—",
                                      opis_punktu(e) + (" · " + e["wariant"] if e.get("wariant") else ""),
                                      e.get("obwod") or "—", e.get("opis") or e.get("wyjatek") or ""]))
    if w_polu:
        wiersze.append(("naglowek", "Punkty w polu pomieszczeń (sufitowe i stropowe) — położenie na rzucie"))
        for e in sorted(w_polu, key=lambda e: (e.get("pomieszczenie") or "", e["id"])):
            wiersze.append(("punkt", [e["id"], e.get("pomieszczenie") or "—", "—",
                                      svg.fmt(e["h"]) if e.get("h") is not None else "—",
                                      opis_punktu(e) + (" · " + e["wariant"] if e.get("wariant") else ""),
                                      e.get("obwod") or "—", e.get("opis") or ""]))
    if not wiersze:
        wiersze.append(("tekst", "Wszystkie punkty elektryczne leżą na ścianach z kładami."))
    kolumny = [("Punkt", 0), ("Pom.", 60), ("a", 118), ("h", 170), ("Typ, wariant", 222), ("Obwód", 600),
               ("Uwagi", 740)]
    strony, biezaca, y = [], [], None
    Y0, YMAX = 150, 1770
    for w in wiersze:
        if y is None or y > YMAX:
            if biezaca:
                strony.append(biezaca)
            biezaca, y = [], Y0 + 26
        biezaca.append((w, y))
        y += 24 if w[0] == "naglowek" else 17
    strony.append(biezaca)
    dokumenty = []
    for i, strona in enumerate(strony):
        s = [svg.tekst(50, 108, "Punkty elektryczne na ścianach bez kładu: para a · h od lewego końca lica "
                                "(patrząc z wnętrza pomieszczenia); h od podłogi wykończonej. Wymiary w cm.",
                       10.5, kolor="#555")]
        for naz, dx in kolumny:
            s.append(svg.tekst(50 + dx, Y0 + 12, naz, 9.5, waga="bold"))
        s.append(svg.linia(50, Y0 + 18, 1430, Y0 + 18, "#111", 0.9))
        for (rodzaj, dane), yy in strona:
            if rodzaj == "naglowek":
                s.append(svg.prostokat(50, yy - 4, 1430, yy + 12, "#F1EEE6", None))
                s.append(svg.tekst(56, yy + 8, dane, 9.5, waga="bold", kolor="#333"))
            elif rodzaj == "tekst":
                s.append(svg.tekst(56, yy + 8, dane, 9.5))
            else:
                for (naz, dx), v in zip(kolumny, dane):
                    v = str(v)
                    maks = {"Typ, wariant": 64, "Obwód": 24, "Uwagi": 110}.get(naz)
                    if maks and len(v) > maks:
                        v = v[:maks - 1] + "…"
                    s.append(svg.tekst(50 + dx, yy + 8, v, 9 if naz == "Punkt" else 8.5,
                                       waga="bold" if naz == "Punkt" else None))
        uwagi = ["Punkty na ścianach z kładami — patrz arkusze kładów (%s)." % (
            ", ".join(K["id"] for K in M.get("klady", [])) or "brak kładów"),
            "a = 0 w każdej grupie: lewy koniec lica patrząc na ścianę z wnętrza pomieszczenia."]
        tytul = "Zestawienie punktów na ścianach bez kładu"
        if len(strony) > 1:
            tytul += " (%d/%d)" % (i + 1, len(strony))
        dokumenty.append(arkusz.arkusz(M, "K-00", tytul, "bez skali (tabela)", "".join(s), uwagi_linie=uwagi))
    return dokumenty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--tylko", help="kody kladow po przecinku, np. K-01,K-02")
    ap.add_argument("--zestawienie", action="store_true", help="dodaj arkusz K-00 z punktami ze scian bez kladu")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog modelu>/wyjscie)")
    a = ap.parse_args()
    M = model.wczytaj(a.model)
    if zmodel.rodzaj_pliku(M) == "zamierzenie":
        print("%s: to model zamierzenia - uzyj rysunki/przekroj.py (przekroje i elewacje); "
              "ten skrypt dziala na modelu lokalu (np. pliku modulu wnetrz z sekcji moduly)." % Path(a.model).name)
        return 2
    klady = M.get("klady", [])
    tylko = [k.strip() for k in a.tylko.split(",")] if a.tylko else None
    if tylko:
        brak = [k for k in tylko if k not in {K["id"] for K in klady}]
        if brak:
            raise SystemExit("brak kladow w modelu: %s" % ", ".join(brak))
    bledy = 0
    for K in klady:
        if tylko and K["id"] not in tylko:
            continue
        try:
            dok = arkusz_kladu(M, K)
        except ValueError as ex:
            print("BLAD:", ex)
            bledy += 1
            continue
        for p in svg.zapisz(dok, model.sciezka_wyniku(M, K["id"], a.wyjscie), pdf=True):
            print("zapisano", p)
    if a.zestawienie:
        uklady = [U for U in (uklad_lica(M, K["pomieszczenie"], K["sciana"], K.get("strona")) for K in klady) if U]
        for i, dok in enumerate(arkusze_zestawienia(M, uklady)):
            nazwa = "K-00_zestawienie" + ("_%d" % (i + 1) if i else "")
            for p in svg.zapisz(dok, model.sciezka_wyniku(M, nazwa, a.wyjscie), pdf=True):
                print("zapisano", p)
    if not klady and not a.zestawienie:
        print("model nie ma kladow (sekcja klady[]); nic do zrobienia")
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
