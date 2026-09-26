"""Rozmieszczanie opisow tekstowych na arkuszu SVG bez wzajemnych kolizji.

Wspolne dla karty pomieszczenia i kladow scian: obie rysuja duzo opisow (mebli,
punktow E, otworow…) i musza wybierac dla kazdego pierwsze wolne miejsce z listy
kandydatow.

    from wspolne import opisy
    miejsca = opisy.Opisy()
    r = opisy.rect_tekstu(cx, cy, [("tekst", 8)])
    if miejsca.wolne(r):
        miejsca.zajmij(r)
        tresc = opisy.blok_tekstu(r, [("tekst", 8)], kolory=["#222"])

Opisy sledzi zajete prostokaty arkusza (lista Opisy.zajete). rect_tekstu liczy
prostokat bloku linii tekstu [(tekst, rozmiar)] wysrodkowanego w punkcie (pion=True
obraca blok o -90 stopni, jak przy opisie pionowego lica). blok_tekstu rysuje te
same linie jako napisy SVG wysrodkowane w gotowym prostokacie (najczesciej wynik
rect_tekstu). szer_tekstu to przyblizona szerokosc napisu (0,52 em na znak),
uzywana wewnatrz rect_tekstu i przy recznym budowaniu kandydatow na pozycje opisu.
"""
from wspolne import svg


class Opisy:
    """Zajete prostokaty arkusza; opis trafia w pierwsze wolne miejsce z listy kandydatow."""

    def __init__(self):
        self.zajete = []

    def wolne(self, r, zapas=1.5, dodatkowe=()):
        return all(r[2] + zapas <= z[0] or z[2] + zapas <= r[0] or r[3] + zapas <= z[1] or z[3] + zapas <= r[1]
                   for z in list(self.zajete) + list(dodatkowe))

    def zajmij(self, r):
        self.zajete.append(r)

    def wybierz(self, kandydaci, dodatkowe=()):
        for r in kandydaci:
            if self.wolne(r, dodatkowe=dodatkowe):
                self.zajmij(r)
                return r
        return None


def szer_tekstu(t, r):
    return len(t) * r * 0.52


def rect_tekstu(cx, cy, linie, pion=False):
    """Prostokat bloku linii [(tekst, rozmiar)] wysrodkowanego w (cx, cy); pion = obrot o -90."""
    w = max(szer_tekstu(t, r) for t, r in linie)
    h = sum(r * 1.2 for _, r in linie)
    if pion:
        w, h = h, w
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def blok_tekstu(r, linie, pion=False, kolory=None, pogrubiony=None):
    """Linie tekstu wysrodkowane w prostokacie r (poziomo albo obrocone o -90).

    kolory: lista koloru na linie (domyslnie "#222" dla wszystkich); krotsza lista
    niz linie powtarza ostatni kolor. pogrubiony: czy pogrubic pierwsza linie —
    domyslnie (None) tylko gdy linii jest wiecej niz jedna; True/False wymusza to
    zachowanie niezaleznie od liczby linii.
    """
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    h = sum(rr * 1.2 for _, rr in linie)
    s, pos = [], -h / 2
    kolory = kolory or ["#222"] * len(linie)
    pogrubic = (len(linie) > 1) if pogrubiony is None else pogrubiony
    for i, (t, rr) in enumerate(linie):
        pos += rr * 1.2
        kol = kolory[min(i, len(kolory) - 1)]
        waga = "bold" if i == 0 and pogrubic else None
        if pion:
            s.append(svg.tekst(cx + pos - rr * 0.3, cy, t, rr, "middle", -90, kol, waga))
        else:
            s.append(svg.tekst(cx, cy + pos - rr * 0.3, t, rr, "middle", 0, kol, waga))
    return "".join(s)
