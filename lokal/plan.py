"""Elementy rzutu rysowane z modelu: pomieszczenia, sciany, otwory z lukami, szachty,
grzejniki, meble, punkty elektryczne, etykiety i wymiary. Wspolne dla rzutu, kart
pomieszczen, planu wyburzen i miniatur, zeby kazdy rysunek wygladal tak samo.

    W = arkusz.Widok(zakres_cm, arkusz.POLE)
    tresc = plan.pomieszczenia(W, M) + plan.sciany(W, M) + plan.otwory(W, M) + plan.meble(W, M)

Kazda funkcja zwraca napis SVG. Parametr nr ogranicza rysunek do jednego pomieszczenia.
"""
import math
from shapely.geometry import box, Point, Polygon

from wspolne import svg, arkusz
from lokal import model, geometria

KOLOR = {
    "nosna": "#1C2B52", "dzialowa": "#9298A2", "niska": "#B8BDC6",
    "pom": "#FCFAF5", "pom_zewn": "#EEF3F6", "podswietl": "#FFF1D6",
    "szacht": ("#FDEEF6", "#C2337D"), "grzejnik": ("#FFE1CF", "#D1490F"),
    "okno": "#2F6FB4", "drzwi": "#8A6A33", "kontekst": ("#F3F3F3", "#D5D5D5"),
    "wymiar": "#7A4B16", "wymiar_zewn": "#333333",
}
KOLORY_MEBLI = {
    "siedzisko": ("#E6F0E0", "#4A7D3A"), "sofa": ("#E6F0E0", "#4A7D3A"),
    "stol": ("#EFE7DA", "#8A6A33"), "stolik": ("#EFE7DA", "#8A6A33"),
    "lozko": ("#F1E6EF", "#7D3A6E"),
    "zabudowa_niska": ("#E8ECDB", "#5C6E3A"), "zabudowa_wysoka": ("#DFE8F4", "#3B5B8C"),
    "wiszaca": ("none", "#3B5B8C"),
    "sanitariat": ("#EEF6FB", "#2F6FB4"), "prysznic": ("#EEF6FB", "#2F6FB4"),
    "urzadzenie": ("#EEEEEE", "#555555"), "murek": ("#D8D8D8", "#555555"),
    "szklo": ("#E8F4FA", "#2F6FB4"), "lustro": ("#E8F4FA", "#2F6FB4"), "inne": ("#F0F0F0", "#8A8A8A"),
}
KOLORY_E = {"gniazdo": "#1A6B3C", "łącznik": "#6D28D9", "punkt świetlny": "#B45309", "kinkiet": "#B45309",
            "wypust": "#B45309", "rozdzielnica": "#111111", "zasilanie": "#0D47A1", "rezerwa": "#8A8A8A"}
CIECIE = 130  # plaszczyzna ciecia rzutu: elementy zaczynajace sie wyzej rysuje sie przerywana


def niepewna(M, sciana_id, prog=2):
    """Czy sciana pochodzi ze zrodla niewiazacego albo ma dokladnosc gorsza niz prog cm."""
    if not sciana_id:
        return False
    s = next((x for x in M["sciany"] if x["id"] == sciana_id), None)
    if not s:
        return False
    if (s.get("dokladnosc_cm") or 0) > prog:
        return True
    z = next((x for x in M.get("meta", {}).get("zrodla", []) if x["id"] == s.get("zrodlo")), None)
    return bool(z and not z.get("wiazace", True))


def kontekst(W, M):
    """Otoczenie przyciete do kadru widoku."""
    wyp, obr = KOLOR["kontekst"]
    kadr = box(*W.zakres)
    return "".join(svg.sciezka(geometria.prostokat(k["box"]).intersection(kadr), W.p, wyp, obr, 1)
                   for k in M.get("kontekst", []))


def pomieszczenia(W, M, nr=None, podswietl=None):
    s = []
    for n, w in geometria.wielokaty(M).items():
        if w is None or (nr and n != nr):
            continue
        zewn = model.pomieszczenie(M, n).get("zewnetrzne")
        wyp = KOLOR["podswietl"] if n == podswietl else KOLOR["pom_zewn"] if zewn else KOLOR["pom"]
        s.append(svg.sciezka(w, W.p, wyp, None))
    return "".join(s)


def sciany(W, M, jasne=False):
    """Bryly scian z wycietymi otworami; nosne ciemne, dzialowe szare, niepelnej wysokosci jasne."""
    s = []
    typy = {x["id"]: x for x in M["sciany"]}
    for sid, g in geometria.bryly_scian(M).items():
        sc = typy[sid]
        kolor = KOLOR["niska"] if "wys" in sc else KOLOR["nosna"] if sc.get("nosna") else KOLOR["dzialowa"]
        if jasne:
            kolor = "#C9CCD2"
        s.append(svg.sciezka(g, W.p, kolor, None))
    return "".join(s)


def szachty(W, M, opisy=True):
    wyp, obr = KOLOR["szacht"]
    s = []
    for sz in M.get("szachty", []):
        x0, y0, x1, y1 = geometria.prostokat(sz["box"]).bounds
        s.append(svg.sciezka(geometria.prostokat(sz["box"]), W.p, wyp, obr, 1.2))
        s.append(svg.linia(*W.p(x0, y0), *W.p(x1, y1), obr, 0.8))
        s.append(svg.linia(*W.p(x0, y1), *W.p(x1, y0), obr, 0.8))
        if opisy:
            X, Y = W.p((x0 + x1) / 2, (y0 + y1) / 2)
            s.append(svg.tekst(X, Y + 3, sz["id"], 7.5, "middle", kolor=obr, waga="bold"))
    return "".join(s)


def grzejniki(W, M, opisy=True):
    wyp, obr = KOLOR["grzejnik"]
    s = []
    for g in M.get("grzejniki", []):
        x0, y0, x1, y1 = geometria.prostokat(g["box"]).bounds
        s.append(svg.sciezka(geometria.prostokat(g["box"]), W.p, wyp, obr, 1.1))
        poziomo = (x1 - x0) >= (y1 - y0)
        n = max(3, int(max(x1 - x0, y1 - y0) / 12))
        for i in range(1, n):
            t = i / n
            if poziomo:
                s.append(svg.linia(*W.p(x0 + (x1 - x0) * t, y0), *W.p(x0 + (x1 - x0) * t, y1), obr, 0.6))
            else:
                s.append(svg.linia(*W.p(x0, y0 + (y1 - y0) * t), *W.p(x1, y0 + (y1 - y0) * t), obr, 0.6))
        if opisy:
            X, Y = W.p((x0 + x1) / 2, (y0 + y1) / 2)
            s.append(svg.tekst(X, Y - (8 if poziomo else 0) + (0 if poziomo else 3), g["id"], 7.5,
                               "middle" if poziomo else "start", kolor=obr, waga="bold"))
    return "".join(s)


def luk_drzwi(W, M, otwor, kolor=None):
    """Luk otwierania i skrzydlo w pozycji otwartej (prostopadle do sciany)."""
    l = otwor.get("luk")
    if not l:
        return ""
    kolor = kolor or KOLOR["drzwi"]
    (cx, cy), r = l["c"], l["r"]
    od, do = l["od"], l["do"]
    if do <= od:
        do += 360
    pkt = [W.p(cx + r * math.cos(math.radians(od + (do - od) * i / 20)),
               cy + r * math.sin(math.radians(od + (do - od) * i / 20))) for i in range(21)]
    sciana = next(s for s in M["sciany"] if s["id"] == otwor["sciana"])
    prostopadly = 90 if geometria.wzdluz_x(sciana["pas"]) else 0
    kat = next((a for a in (l["od"], l["do"]) if round(a) % 180 == prostopadly), l["do"])
    koniec = W.p(cx + r * math.cos(math.radians(kat)), cy + r * math.sin(math.radians(kat)))
    return svg.polilinia(pkt, kolor, 0.7, "3 2") + svg.linia(*W.p(cx, cy), *koniec, kolor, 1.6)


def otwory(W, M, opisy=True):
    """Oscieza, szklenia, przejscia i luki drzwi; opisy=True dokleja opisy (patrz opisy_otworow)."""
    s = []
    for o in M.get("otwory", []):
        sc = next(x for x in M["sciany"] if x["id"] == o["sciana"])
        x0, y0, x1, y1 = geometria.prostokat_otworu(M, o)
        okno = o["rodzaj"] == "okno"
        kol = KOLOR["okno"] if okno else KOLOR["drzwi"]
        if geometria.wzdluz_x(sc["pas"]):
            s.append(svg.linia(*W.p(x0, y0), *W.p(x0, y1), kol, 1.1) + svg.linia(*W.p(x1, y0), *W.p(x1, y1), kol, 1.1))
            if okno:
                for t in (0.35, 0.65):
                    yy = y0 + (y1 - y0) * t
                    s.append(svg.linia(*W.p(x0, yy), *W.p(x1, yy), kol, 1.0))
            elif o["rodzaj"] == "przejście" or not o.get("luk"):
                s.append(svg.linia(*W.p(x0, (y0 + y1) / 2), *W.p(x1, (y0 + y1) / 2), kol, 0.8, "4 3"))
        else:
            s.append(svg.linia(*W.p(x0, y0), *W.p(x1, y0), kol, 1.1) + svg.linia(*W.p(x0, y1), *W.p(x1, y1), kol, 1.1))
            if okno:
                for t in (0.35, 0.65):
                    xx = x0 + (x1 - x0) * t
                    s.append(svg.linia(*W.p(xx, y0), *W.p(xx, y1), kol, 1.0))
            elif o["rodzaj"] == "przejście" or not o.get("luk"):
                s.append(svg.linia(*W.p((x0 + x1) / 2, y0), *W.p((x0 + x1) / 2, y1), kol, 0.8, "4 3"))
        s.append(luk_drzwi(W, M, o, kol))
    if opisy:
        s.append(opisy_otworow(W, M))
    return "".join(s)


def opisy_otworow(W, M):
    """Same opisy 'D1 100/210' — do rysowania na koncu, nad wymiarami i ich biala obwodka."""
    wiel = [w for w in geometria.wielokaty(M).values() if w is not None]
    meble_ = [geometria.prostokat(e["box"]) for e in model.elementy(M)]
    s = []
    for o in M.get("otwory", []):
        sc = next(x for x in M["sciany"] if x["id"] == o["sciana"])
        kol = KOLOR["okno"] if o["rodzaj"] == "okno" else KOLOR["drzwi"]
        s.append(_opis_otworu(W, o, geometria.prostokat_otworu(M, o), geometria.wzdluz_x(sc["pas"]), wiel, meble_, kol))
    return "".join(s)


def _opis_otworu(W, o, prost, poziomo, wielokaty_pom, meble_, kol):
    """Opis 'D1 100/210' po tej stronie sciany, gdzie nie ma pomieszczenia; przy scianie wewnetrznej
    poza pasem wymiarow, po stronie bez mebla."""
    x0, y0, x1, y1 = prost
    szer = o.get("szer_otw") or (x1 - x0 if poziomo else y1 - y0)
    napis = "%s %s/%s" % (o["id"], svg.fmt(szer), svg.fmt(o.get("wys_otw", 205)))
    if poziomo:
        kand = [((x0 + x1) / 2, y1 + 14), ((x0 + x1) / 2, y0 - 14)]
    else:
        kand = [(x0 - 14, (y0 + y1) / 2), (x1 + 14, (y0 + y1) / 2)]
    punkt = next((p for p in kand if not any(w.contains(Point(p)) for w in wielokaty_pom)), None)
    if punkt is None:
        # sciana wewnetrzna: opis poza pasem wymiarow pomieszczenia, najlepiej tam, gdzie nie stoi mebel
        dalej = ([((x0 + x1) / 2, y1 + 34), ((x0 + x1) / 2, y0 - 34)] if poziomo
                 else [(x0 - 34, (y0 + y1) / 2), (x1 + 34, (y0 + y1) / 2)])
        punkt = next((p for p in dalej if not any(m.contains(Point(p)) for m in meble_)), dalej[0])
    X, Y = W.p(*punkt)
    return svg.tekst(X, Y + 3, napis, 7.5, "middle", 0 if poziomo else -90, kol)


def _front(e):
    """Odcinek frontu w ukladzie modelu dla elementu z polem front."""
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    return {"N": ((x0, y1), (x1, y1)), "S": ((x0, y0), (x1, y0)),
            "E": ((x1, y0), (x1, y1)), "W": ((x0, y0), (x0, y1))}.get(e.get("front"))


def podzialy_segmentow(e):
    """Wspolrzedne linii podzialu segmentow wzdluz frontu, liczone od lewej patrzac na front."""
    if not e.get("segmenty") or not e.get("front"):
        return []
    x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
    start, znak, os = {"S": (x0, 1, "x"), "N": (x1, -1, "x"), "E": (y0, 1, "y"), "W": (y1, -1, "y")}[e["front"]]
    wynik, kursor = [], start
    for seg in e["segmenty"][:-1]:
        kursor += znak * seg["dl"]
        wynik.append((os, kursor))
    return wynik


def meble(W, M, nr=None, ciecie=CIECIE, opisy=True):
    s = []
    for e in model.elementy(M, nr):
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        wyp, obr = KOLORY_MEBLI.get(model.kategoria(e.get("rodzaj")), KOLORY_MEBLI["inne"])
        powyzej = e.get("wys", [0, 0])[0] >= ciecie
        kreski = "5 3" if powyzej else ("4 3" if e.get("mobilne") else None)
        if powyzej:
            wyp = "none"
        if e.get("ksztalt") == "kolo":
            X, Y = W.p((x0 + x1) / 2, (y0 + y1) / 2)
            rx, ry = W.d(x1 - x0) / 2, W.d(y1 - y0) / 2
            if kreski:
                # obwod elipsy jako lamana (>= 72 odcinki), zeby svg.sciezka mogla ja przerywac jawnymi odcinkami
                n = max(72, int(2 * math.pi * max(rx, ry) / 2))
                g = Polygon([(X + rx * math.cos(2 * math.pi * i / n), Y + ry * math.sin(2 * math.pi * i / n)) for i in range(n)])
                s.append(svg.sciezka(g, lambda x, y: (x, y), wyp, obr, 1.0, kreski, 0.9))
            else:
                s.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f"%s/>' % (
                    X, Y, rx, ry, svg._styl(obr, 1.0, wyp, 0.9)))
        else:
            s.append(svg.sciezka(box(x0, y0, x1, y1), W.p, wyp, obr, 1.0, kreski, 0.9 if wyp != "none" else None))
        for os, v in podzialy_segmentow(e):
            if os == "x":
                s.append(svg.linia(*W.p(v, y0), *W.p(v, y1), obr, 0.6, kreski))
            else:
                s.append(svg.linia(*W.p(x0, v), *W.p(x1, v), obr, 0.6, kreski))
        fr = _front(e)
        if fr and not powyzej:
            s.append(svg.linia(*W.p(*fr[0]), *W.p(*fr[1]), obr, 2.2))
        if opisy and W.d(x1 - x0) * W.d(y1 - y0) > 500:
            X, Y = W.p((x0 + x1) / 2, (y0 + y1) / 2)
            s.append(svg.tekst(X, Y + 3, e["id"], 8, "middle", kolor="#555"))
    return "".join(s)


def symbol_e(typ, X, Y, r=4.5):
    """Symbol punktu elektrycznego w punkcie arkusza (X, Y)."""
    k = KOLORY_E.get(typ, "#555")
    if typ == "gniazdo":
        return svg.okrag(X, Y, r, "#FFFFFF", k, 1.4) + svg.linia(X - r, Y, X + r, Y, k, 1.2)
    if typ == "łącznik":
        return svg.prostokat(X - r, Y - r, X + r, Y + r, "#FFFFFF", k, 1.4) + svg.linia(X - r, Y + r, X + r, Y - r, k, 1)
    if typ in ("punkt świetlny", "kinkiet"):
        d = r * 0.7
        return (svg.okrag(X, Y, r, "#FFFFFF" if typ == "punkt świetlny" else "#FDE9CF", k, 1.4)
                + svg.linia(X - d, Y - d, X + d, Y + d, k, 1) + svg.linia(X - d, Y + d, X + d, Y - d, k, 1))
    if typ == "wypust":
        return svg.polilinia([(X, Y - r), (X + r, Y + r), (X - r, Y + r)], k, 1.3, wyp="#FFFFFF", zamknij=True)
    if typ == "rozdzielnica":
        return svg.prostokat(X - r * 1.4, Y - r, X + r * 1.4, Y + r, k, k, 1)
    if typ == "zasilanie":
        return svg.polilinia([(X, Y - r), (X + r, Y), (X, Y + r), (X - r, Y)], k, 1.3, wyp="#FFFFFF", zamknij=True)
    return svg.okrag(X, Y, r, "#FFFFFF", k, 1, "2 1.5")


def punkty_e(W, M, nr=None, opisy=True):
    s = []
    for e in M.get("elektryka", []):
        if nr and e.get("pomieszczenie") != nr:
            continue
        X, Y = W.p(*e["xy"])
        s.append(symbol_e(e["typ"], X, Y))
        if opisy:
            s.append(svg.tekst(X + 6, Y - 5, e["id"], 6.5, kolor=KOLORY_E.get(e["typ"], "#555")))
    return "".join(s)


def etykiety(W, M, nr=None, pole=True):
    s = []
    pola = geometria.pola(M)
    for n, w in geometria.wielokaty(M).items():
        if w is None or (nr and n != nr):
            continue
        p = model.pomieszczenie(M, n)
        rp = Point(*p["stamp"]) if w.contains(Point(*p["stamp"])) else w.representative_point()
        X, Y = W.p(rp.x, rp.y)
        s.append(svg.tekst(X, Y - 6, n, 13, "middle", waga="bold"))
        s.append(svg.tekst(X, Y + 7, p["nazwa"], 9.5, "middle", kolor="#555"))
        if pole and pola.get(n) is not None:
            s.append(svg.tekst(X, Y + 19, "%s m²" % svg.fmt(pola[n], 2), 9.5, "middle", kolor="#555"))
    return "".join(s)


def _podzialy_lica(M, lico):
    """Odleglosci od poczatku lica do osciezy otworow lezacych na tym licu."""
    if not lico["sciana"]:
        return []
    (ax, ay), (bx, by) = lico["a"], lico["b"]
    dl = lico["dl"]
    wynik = []
    for o in M.get("otwory", []):
        if o["sciana"] != lico["sciana"]:
            continue
        for v in o["zakres"]:
            t = (v - ax) / (bx - ax) * dl if abs(bx - ax) > abs(by - ay) else (v - ay) / (by - ay) * dl
            if 0.5 < t < dl - 0.5:
                wynik.append(t)
    return sorted(wynik)


def lancuch(W, a, b, normalna, odsuniecie_cm, podzialy=(), niepewny=False, kolor=None, r=8.5, min_seg=3,
            czesci=False):
    """Lancuch wymiarowy wzdluz odcinka modelu a-b przesuniety o odsuniecie_cm w kierunku normalnej.

    czesci=True zwraca pare (linie, opisy) — patrz svg.wymiar.
    """
    kolor = kolor or KOLOR["wymiar"]
    (ax, ay), (bx, by) = a, b
    dl = math.hypot(bx - ax, by - ay)
    if dl < 1:
        return ("", "") if czesci else ""
    ux, uy = (bx - ax) / dl, (by - ay) / dl
    nx, ny = normalna
    punkty = [0.0] + [t for t in podzialy if 0.5 < t < dl - 0.5] + [dl]
    s, opisy = [], []
    for t0, t1 in zip(punkty, punkty[1:]):
        if t1 - t0 < min_seg:
            continue
        p0 = W.p(ax + ux * t0 + nx * odsuniecie_cm, ay + uy * t0 + ny * odsuniecie_cm)
        p1 = W.p(ax + ux * t1 + nx * odsuniecie_cm, ay + uy * t1 + ny * odsuniecie_cm)
        # opis po stronie przeciwnej do mierzonego lica (dalej wzdluz normalnej)
        q = W.p(ax + nx * (odsuniecie_cm + 10), ay + ny * (odsuniecie_cm + 10))
        q0 = W.p(ax + nx * odsuniecie_cm, ay + ny * odsuniecie_cm)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        strona = 1 if (dy * (q[0] - q0[0]) - dx * (q[1] - q0[1])) > 0 else -1
        linie, opis = svg.wymiar(p0, p1, svg.fmt(t1 - t0), niepewny, r, kolor, strona, czesci=True)
        s.append(linie)
        opisy.append(opis)
    if czesci:
        return "".join(s), "".join(opisy)
    return "".join(s + opisy)


def _glebokosc_przy_licu(M, nr, lico, tol=5, maks=70):
    """Jak gleboko siegaja zabudowy przystawione do lica (cm, 0 gdy brak).

    Liczy tylko elementy plytkie (do maks cm: szafy, ciagi kuchenne, szafki); lozka, sofy
    i stoly pomija, bo odsuniecie wymiaru za nie wyprowadziloby go na srodek pokoju.
    """
    (ax, ay), (bx, by) = lico["a"], lico["b"]
    nx, ny = lico["normalna"]
    poziomo = abs(bx - ax) >= abs(by - ay)
    lo, hi = sorted((ax, bx)) if poziomo else sorted((ay, by))
    naj = 0.0
    for e in model.elementy(M, nr):
        x0, y0, x1, y1 = geometria.prostokat(e["box"]).bounds
        e_lo, e_hi = (x0, x1) if poziomo else (y0, y1)
        if e_hi <= lo or e_lo >= hi:
            continue
        # odleglosci krawedzi bryly od lica mierzone wzdluz normalnej (do wnetrza)
        d = sorted(((x - ax) * nx + (y - ay) * ny) for x, y in ((x0, y0), (x1, y1)))
        if d[0] <= tol and d[1] <= maks:
            naj = max(naj, d[1])
    return naj


def wymiary_pomieszczen(W, M, nr=None, odsuniecie_px=13):
    """Wymiar kazdego lica pomieszczenia z podzialem na oscieza; lica z niepewnych scian z '≈'.

    Lancuch biegnie przy licu, a gdy stoja przy nim meble - tuz za ich frontem, w wolnym polu.
    """
    s, opisy = [], []
    bazowe = odsuniecie_px / W.sk
    for n in geometria.wielokaty(M):
        if nr and n != nr:
            continue
        for lico in geometria.lica(M, n):
            if lico["dl"] < 12:
                continue
            meble_ = _glebokosc_przy_licu(M, n, lico)
            odsuniecie = max(bazowe, meble_ + bazowe * 0.8) if meble_ else bazowe
            linie, opis = lancuch(W, lico["a"], lico["b"], lico["normalna"], odsuniecie,
                                  _podzialy_lica(M, lico), niepewna(M, lico["sciana"]), czesci=True)
            s.append(linie)
            opisy.append(opis)
    return "".join(s + opisy)


def grubosci_scian(W, M):
    s = []
    for sc in M["sciany"]:
        x0, y0, x1, y1 = geometria.prostokat(sc["pas"]).bounds
        g = min(x1 - x0, y1 - y0)
        if W.d(g) < 7:
            continue
        poziomo = geometria.wzdluz_x(sc["pas"])
        a0, a1 = (x0, x1) if poziomo else (y0, y1)
        zajete = [sorted(o["zakres"]) for o in M.get("otwory", []) if o["sciana"] == sc["id"]]
        poz = next((a0 + (a1 - a0) * f for f in (0.5, 0.25, 0.75, 0.1, 0.9)
                    if all(not (za - 10 < a0 + (a1 - a0) * f < zb + 10) for za, zb in zajete)), None)
        if poz is None:
            continue
        cx, cy = (poz, (y0 + y1) / 2) if poziomo else ((x0 + x1) / 2, poz)
        X, Y = W.p(cx, cy)
        s.append(svg.tekst(X, Y + 2.6, svg.fmt(g), 7, "middle", 0 if poziomo else -90, "#FFFFFF"))
    return "".join(s)


def lancuchy_zewnetrzne(W, M, odstep_px=34):
    """Dwa lancuchy na kazdym boku obrysu: z podzialem na oscieza i koncowki scian oraz calkowity."""
    x0, y0, x1, y1 = geometria.obrys(M).bounds
    boki = {
        "N": ((x0, y1), (x1, y1), (0, 1), lambda r: abs(r[3] - y1) < 5, 0),
        "S": ((x1, y0), (x0, y0), (0, -1), lambda r: abs(r[1] - y0) < 5, 0),
        "E": ((x1, y1), (x1, y0), (1, 0), lambda r: abs(r[2] - x1) < 5, 1),
        "W": ((x0, y0), (x0, y1), (-1, 0), lambda r: abs(r[0] - x0) < 5, 1),
    }
    s, opisy = [], []
    for a, b, n, na_boku, os in boki.values():
        wart = set()
        for sc in M["sciany"]:
            r = geometria.prostokat(sc["pas"]).bounds
            if not na_boku(r):
                continue
            wart.update((r[os], r[os + 2]))
            rownolegla = geometria.wzdluz_x(sc["pas"]) == (os == 0)
            for o in M.get("otwory", []):
                if rownolegla and o["sciana"] == sc["id"]:
                    wart.update(o["zakres"])
        poczatek = a[os]
        dl = math.hypot(b[0] - a[0], b[1] - a[1])
        kier = 1 if b[os] > a[os] else -1
        podzialy = sorted(abs(v - poczatek) for v in wart if 0.5 < (v - poczatek) * kier < dl - 0.5)
        k = odstep_px / W.sk
        for czesc in (lancuch(W, a, b, n, k, podzialy, kolor=KOLOR["wymiar_zewn"], r=9, czesci=True),
                      lancuch(W, a, b, n, 2 * k, kolor=KOLOR["wymiar_zewn"], r=10, czesci=True)):
            s.append(czesc[0])
            opisy.append(czesc[1])
    return "".join(s + opisy)


def miniatura(M, x, y, szer, wys, nr=None, patrz=None):
    """Obrys lokalu w malym oknie; nr podswietla pomieszczenie, patrz = ((x, y), kat_stopni) strzalka."""
    W = arkusz.Widok(geometria.obrys(M).bounds, (x + 6, y + 6, x + szer - 6, y + wys - 6))
    s = [svg.prostokat(x, y, x + szer, y + wys, "#FFFFFF", "#999", 0.8)]
    for n, w in geometria.wielokaty(M).items():
        if w is not None:
            s.append(svg.sciezka(w, W.p, "#F6D9A8" if n == nr else "#F4F2EE", "#BBB", 0.5))
    s.append(svg.sciezka(geometria.obrys(M).boundary, W.p, "none", "#555", 0.9))
    for g in geometria.bryly_scian(M).values():
        s.append(svg.sciezka(g, W.p, "#777", None))
    if patrz:
        (px, py), kat = patrz
        X, Y = W.p(px, py)
        k = math.radians(kat)
        dx, dy = math.cos(k), -math.sin(k)
        s.append(svg.linia(X, Y, X + dx * 26, Y + dy * 26, "#C0392B", 2.2))
        s.append(svg.polilinia([(X + dx * 32, Y + dy * 32), (X + dx * 22 - dy * 5, Y + dy * 22 + dx * 5),
                                (X + dx * 22 + dy * 5, Y + dy * 22 - dx * 5)], "#C0392B", 1, wyp="#C0392B", zamknij=True))
    return "".join(s)
