"""Prymitywy SVG dla rysunkow z modelu i zapis do SVG, PNG i PDF.

    from wspolne import svg
    tresc = svg.linia(10, 10, 110, 10) + svg.tekst(60, 6, "100", kotwica="middle")
    svg.zapisz(svg.dokument(120, 40, tresc), "wyjscie/proba", pdf=True)

Wszystkie funkcje zwracaja napisy SVG we wspolrzednych arkusza (os Y w dol).
Przeliczenie z modelu (cm, os Y w gore) robi arkusz.Widok. PNG i PDF powstaja
z SVG przez PyMuPDF, bez innych programow.

kreski (linia, prostokat, okrag, polilinia, sciezka): wzor "a b ..." w jednostkach arkusza,
jak stroke-dasharray. PyMuPDF 1.28.2 ignoruje stroke-dasharray (linia wychodzi ciagla w PNG
i PDF), wiec element z kreski jest rysowany jawnymi odcinkami (grupa <g> z <line>) - obrys
przerywany, a przy wypelnieniu osobno wypelnienie bez obrysu i osobno przerywany obrys. Faza
wzoru trwa przez kolejne odcinki lamanej (bez restartu na wierzcholkach); wzor pusty albo None
- linia ciagla, bez zmiany wyniku.
"""
import math
from pathlib import Path

# jedna nazwa rodziny: renderer PyMuPDF nie rozumie list "Helvetica, Arial, ..." i przechodzi na szeryfowy
CZCIONKA = "sans-serif"


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt(v, dokl=1):
    """412.0 -> '412', 12.5 -> '12,5' (przecinek, bez zbednych zer)."""
    v = round(float(v), dokl)
    if abs(v - round(v)) < 10 ** -(dokl + 2):
        return str(int(round(v)))
    return ("%.*f" % (dokl, v)).rstrip("0").replace(".", ",")


def _styl(kolor="#222", gr=1.0, wyp="none", przezr=None):
    s = ' fill="%s"' % wyp if wyp is not None else ""
    if przezr is not None:
        s += ' fill-opacity="%.2f"' % przezr
    s += ' stroke="%s"' % (kolor or "none")
    if kolor:
        s += ' stroke-width="%.2f"' % gr
    return s


def _wzor_kresek(wzor):
    """Wzor 'a b ...' (jednostki arkusza, jak stroke-dasharray) jako lista dlugosci parzystej
    liczby elementow (widac/nie widac na przemian); None przy wzorze pustym, None, nieliczbowym,
    z wartoscia ujemna albo samych zerach (inaczej _kreskowana zawiesza sie - krok zawsze 0 albo
    ujemny, t nie rosnie). Wzor mieszany z pojedynczym zerem (np. "5 0") dziala jak dotad."""
    if not wzor:
        return None
    try:
        dl = [float(v) for v in str(wzor).replace(",", " ").split()]
    except ValueError:
        return None
    if not dl or any(v < 0 for v in dl) or all(v <= 0 for v in dl):
        return None
    return dl * 2 if len(dl) % 2 else dl


def _kreskowana(punkty, wzor, zamknij=False):
    """Punkty lamanej (arkusz) jako lista widocznych odcinkow [((x0,y0),(x1,y1)), ...] wg wzoru
    (jak stroke-dasharray); faza sie ciagnie przez kolejne odcinki lamanej, bez restartu na
    wierzcholkach. None przy wzorze pustym albo None (linia ciagla, bez zmiany wyniku)."""
    dl_wzoru = _wzor_kresek(wzor)
    if dl_wzoru is None:
        return None
    pkt = list(punkty) + (list(punkty[:1]) if zamknij else [])
    wynik, i, reszta, widac = [], 0, dl_wzoru[0], True
    for (x0, y0), (x1, y1) in zip(pkt, pkt[1:]):
        dl, t = math.hypot(x1 - x0, y1 - y0), 0.0
        while t < dl - 1e-9:
            krok = min(reszta, dl - t)
            if widac:
                wynik.append(((x0 + (x1 - x0) * t / dl, y0 + (y1 - y0) * t / dl),
                              (x0 + (x1 - x0) * (t + krok) / dl, y0 + (y1 - y0) * (t + krok) / dl)))
            t += krok
            reszta -= krok
            if reszta <= 1e-9:
                i = (i + 1) % len(dl_wzoru)
                reszta, widac = dl_wzoru[i], not widac
    return wynik


def _grupa_kresek(odcinki, kolor, gr):
    """<g> jawnych odcinkow <line> (obrys przerywany); "" gdy brak koloru albo odcinkow."""
    if not kolor or not odcinki:
        return ""
    return "<g>" + "".join('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"%s/>' % (x0, y0, x1, y1, _styl(kolor, gr, None))
                           for (x0, y0), (x1, y1) in odcinki) + "</g>"


def tekst(x, y, t, r=10, kotwica="start", obrot=0, kolor="#222", waga=None, rodzina=None):
    w = ' font-weight="%s"' % waga if waga else ""
    f = ' font-family="%s"' % (rodzina or CZCIONKA)  # PyMuPDF nie dziedziczy rodziny z <svg>
    o = ' transform="rotate(%.1f %.1f %.1f)"' % (obrot, x, y) if obrot else ""
    return '<text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" text-anchor="%s"%s%s%s>%s</text>' % (
        x, y, r, kolor, kotwica, w, f, o, esc(t))


def linia(x0, y0, x1, y1, kolor="#222", gr=1.0, kreski=None):
    odcinki = _kreskowana([(x0, y0), (x1, y1)], kreski)
    if odcinki is None:    # brak kreski albo wzor niepoprawny (_wzor_kresek) - linia ciagla
        return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"%s/>' % (x0, y0, x1, y1, _styl(kolor, gr, None))
    return _grupa_kresek(odcinki, kolor, gr)


def prostokat(x0, y0, x1, y1, wyp="none", kolor="#222", gr=1.0, kreski=None, przezr=None):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    odcinki = _kreskowana([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], kreski, zamknij=True)
    if odcinki is None:
        return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s/>' % (
            x0, y0, x1 - x0, y1 - y0, _styl(kolor, gr, wyp, przezr))
    wypis = ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s/>' % (x0, y0, x1 - x0, y1 - y0, _styl(None, gr, wyp, przezr))
             if wyp != "none" else "")
    return wypis + _grupa_kresek(odcinki, kolor, gr)


def okrag(cx, cy, r, wyp="none", kolor="#222", gr=1.0, kreski=None, przezr=None):
    odcinki = None
    if kreski and _wzor_kresek(kreski) is not None:    # sprawdzenie przed budowa lamanej (>= 72 odcinki - kosztowne)
        n = max(72, int(2 * math.pi * r / 2))    # okrag przyblizony lamana przed podzialem na kreski
        pkt = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        odcinki = _kreskowana(pkt, kreski, zamknij=True)
    if odcinki is None:
        return '<circle cx="%.1f" cy="%.1f" r="%.1f"%s/>' % (cx, cy, r, _styl(kolor, gr, wyp, przezr))
    wypis = ('<circle cx="%.1f" cy="%.1f" r="%.1f"%s/>' % (cx, cy, r, _styl(None, gr, wyp, przezr))
             if wyp != "none" else "")
    return wypis + _grupa_kresek(odcinki, kolor, gr)


def polilinia(punkty, kolor="#222", gr=1.0, kreski=None, wyp="none", zamknij=False):
    punkty = list(punkty)
    odcinki = _kreskowana(punkty, kreski, zamknij=zamknij)
    if odcinki is None:
        d = "M " + " L ".join("%.1f %.1f" % (x, y) for x, y in punkty) + (" Z" if zamknij else "")
        return '<path d="%s"%s/>' % (d, _styl(kolor, gr, wyp))
    wypis = ""
    if wyp != "none":
        d = "M " + " L ".join("%.1f %.1f" % (x, y) for x, y in punkty) + (" Z" if zamknij else "")
        wypis = '<path d="%s"%s/>' % (d, _styl(None, gr, wyp))
    return wypis + _grupa_kresek(odcinki, kolor, gr)


def _czesci(geom):
    if geom is None or geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        wynik = []
        for g in geom.geoms:
            wynik += _czesci(g)
        return wynik
    return [geom]


def sciezka(geom, P, wyp="none", kolor="#222", gr=1.0, kreski=None, przezr=None):
    """Geometria shapely (wielokaty z dziurami, linie) jako jedna sciezka; P mapuje (x, y) modelu.

    kreski rysuje obrys jawnymi odcinkami zamiast stroke-dasharray, kazdy pierscien wielokata
    i kazda linia osobno (faza wzoru wlasna dla kazdego); wypelnienie (gdy wyp != "none") zostaje
    jedna sciezka bez obrysu, przerywany obrys dochodzi osobno. Wzor niepoprawny (_wzor_kresek) -
    jak brak kreski, linia ciagla.
    """
    czesci = _czesci(geom)
    if _wzor_kresek(kreski) is None:
        d = []
        for g in czesci:
            if g.geom_type == "Polygon":
                for ring in [g.exterior] + list(g.interiors):
                    d.append("M " + " L ".join("%.1f %.1f" % P(x, y) for x, y in list(ring.coords)[:-1]) + " Z")
            elif g.geom_type in ("LineString", "LinearRing"):
                d.append("M " + " L ".join("%.1f %.1f" % P(x, y) for x, y in g.coords))
        if not d:
            return ""
        return '<path d="%s" fill-rule="evenodd"%s/>' % (" ".join(d), _styl(kolor, gr, wyp, przezr))
    d, odcinki = [], []
    for g in czesci:
        if g.geom_type == "Polygon":
            for ring in [g.exterior] + list(g.interiors):
                pkt = [P(x, y) for x, y in list(ring.coords)[:-1]]
                if wyp != "none":
                    d.append("M " + " L ".join("%.1f %.1f" % p for p in pkt) + " Z")
                odcinki += _kreskowana(pkt, kreski, zamknij=True)
        elif g.geom_type in ("LineString", "LinearRing"):
            pkt = [P(x, y) for x, y in g.coords]
            odcinki += _kreskowana(pkt, kreski)
    wypis = '<path d="%s" fill-rule="evenodd"%s/>' % (" ".join(d), _styl(None, gr, wyp, przezr)) if d else ""
    return wypis + _grupa_kresek(odcinki, kolor, gr)


def wymiar(p0, p1, opis, niepewny=False, r=9, kolor="#7a4b16", strona=1, znaczniki=True, tlo=True, czesci=False):
    """Linia wymiarowa p0-p1 (arkusz) z ukosnymi znacznikami i opisem rownoleglym do linii.

    strona=1 kladzie opis po lewej stronie kierunku p0->p1 (na arkuszu), -1 po prawej.
    niepewny dodaje przed opisem znak "≈" (wymiar ze zrodla o slabej dokladnosci).
    tlo podklada pod linie biala obwodke, a pod opis polprzezroczysty bialy prostokat, zeby wymiar
    byl czytelny takze tam, gdzie przecina meble. czesci=True zwraca pare (linie, opis), zeby
    przy wielu wymiarach narysowac najpierw wszystkie linie, a opisy na wierzchu.
    """
    (x0, y0), (x1, y1) = p0, p1
    dl = math.hypot(x1 - x0, y1 - y0)
    if dl < 1e-6:
        return ("", "") if czesci else ""
    ux, uy = (x1 - x0) / dl, (y1 - y0) / dl
    nx, ny = uy * strona, -ux * strona
    s = [linia(x0, y0, x1, y1, "#FFFFFF", 2.8), linia(x0, y0, x1, y1, kolor, 0.7)] if tlo else [linia(x0, y0, x1, y1, kolor, 0.7)]
    if znaczniki:
        k = 3.2
        for x, y in (p0, p1):
            s.append(linia(x - (ux + nx) * k, y - (uy + ny) * k, x + (ux + nx) * k, y + (uy + ny) * k, kolor, 0.9))
    kat = math.degrees(math.atan2(uy, ux))
    if kat > 90 or kat <= -90:
        kat += 180
    rozmiar = r if dl >= 3.2 * r else r * 0.78
    kr = math.radians(kat)
    gora_x, gora_y = math.sin(kr), -math.cos(kr)  # kierunek "w gore" obroconego tekstu
    odl = 3.5 if nx * gora_x + ny * gora_y > 0 else rozmiar + 1
    mx, my = (x0 + x1) / 2 + nx * odl, (y0 + y1) / 2 + ny * odl
    napis = ("≈ " if niepewny else "") + str(opis)
    o = []
    if tlo:
        w = len(napis) * rozmiar * 0.56 + 3
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#FFFFFF" fill-opacity="0.85" '
                 'transform="rotate(%.1f %.1f %.1f)"/>' % (mx - w / 2, my - rozmiar * 0.82, w, rozmiar * 1.05, kat, mx, my))
    o.append(tekst(mx, my, napis, rozmiar, "middle", kat, kolor, waga="bold" if niepewny else None))
    if czesci:
        return "".join(s), "".join(o)
    return "".join(s + o)


def strzalka_polnocy(x, y, azymut_osi_Y, r=24, kolor="#b06020"):
    """Strzalka N: przy azymucie osi +Y rownym A polnoc lezy o A stopni w lewo od gory arkusza."""
    k = math.radians(-azymut_osi_Y)
    nx, ny = x + r * math.sin(k), y - r * math.cos(k)
    s = [okrag(x, y, r + 4, "#FFFFFF", kolor, 1.4), linia(x, y, nx, ny, kolor, 3)]
    s.append(tekst(nx + (nx - x) * 0.45, ny + (ny - y) * 0.45 + 4, "N", 12, "middle", kolor=kolor, waga="bold"))
    return "".join(s)


def podzialka(x, y, px_na_m, metry=5, kolor="#222"):
    """Podzialka liniowa czarno-biala: metry segmentow po 1 m."""
    s = []
    for i in range(metry):
        s.append(prostokat(x + i * px_na_m, y, x + (i + 1) * px_na_m, y + 6,
                           kolor if i % 2 == 0 else "#FFFFFF", kolor, 0.8))
    s.append(tekst(x, y - 4, "0", 8, "middle", kolor=kolor))
    s.append(tekst(x + metry * px_na_m, y - 4, "%d m" % metry, 8, "middle", kolor=kolor))
    return "".join(s)


def dokument(szer, wys, tresc, tlo="#FFFFFF"):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f" '
            'font-family="%s">\n<rect width="%.0f" height="%.0f" fill="%s"/>\n%s\n</svg>\n' % (
                szer, wys, szer, wys, CZCIONKA, szer, wys, tlo, tresc))


def zapisz(tresc_svg, sciezka_bez_rozszerzenia, png=True, pdf=False, skala_png=2.0):
    """Zapisuje .svg oraz opcjonalnie .png i .pdf; zwraca liste sciezek.

    Rozszerzenie jest doklejane do nazwy (with_name), nie zastepowane (with_suffix): nazwa
    zbudowana z ID projektu albo numeru pomieszczenia bywa z kropka ("ul.Lipowa", "1.01"),
    a with_suffix obcinaloby wtedy nazwe po tej kropce.
    """
    baza = Path(sciezka_bez_rozszerzenia)
    baza.parent.mkdir(parents=True, exist_ok=True)
    wynik = [baza.with_name(baza.name + ".svg")]
    wynik[0].write_text(tresc_svg, encoding="utf-8")
    if png or pdf:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        dok = fitz.open(stream=tresc_svg.encode("utf-8"), filetype="svg")
        if png:
            pix = dok[0].get_pixmap(matrix=fitz.Matrix(skala_png, skala_png))
            sciezka_png = baza.with_name(baza.name + ".png")
            pix.save(str(sciezka_png))
            wynik.append(sciezka_png)
        if pdf:
            pdf_bajty = dok.convert_to_pdf()
            sciezka_pdf = baza.with_name(baza.name + ".pdf")
            sciezka_pdf.write_bytes(pdf_bajty)
            wynik.append(sciezka_pdf)
    return wynik
