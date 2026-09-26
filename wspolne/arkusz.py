"""Arkusz rysunkowy: dopasowanie modelu do pola rysunku, ramka, tabliczka, legenda
i uwagi.

    from wspolne import arkusz, svg
    W = arkusz.Widok(zakres_cm, arkusz.POLE, skala=arkusz.skala_arkusza(zakres_cm, arkusz.POLE))
    dok = arkusz.arkusz(M, "A-01", "Rzut roboczy", "1:50 (A3)", tresc)
    svg.zapisz(dok, sciezka, pdf=True)

Arkusz jest pionowy, w proporcji A-serii (1480 x 2093 jednostek). Wydrukowany na A3
daje 1 jednostke = 420/2093 mm, stad skale 1:20 ... 1:200 w skala_arkusza().
Dane tabliczki pochodza z meta.projekt, data to dzien generowania. Pole SKALA konczy dopisek
o jednostkach (jednostki, domyslnie JEDNOSTKI - konwencja modulu wnetrz).
"""
import textwrap
from datetime import date

from wspolne import pliki, svg

SZER, WYS = 1480, 2093
MM_NA_JEDNOSTKE_A3 = 420.0 / WYS
POLE = (50, 110, 1430, 1770)          # pole rysunku nad pasem legendy i tabliczki
SKALE = (20, 25, 50, 75, 100, 200, 250, 500)
ADNOTACJA = "Rysunek roboczy — nie zastępuje projektu sporządzonego przez osobę z uprawnieniami."
JEDNOSTKI = "wymiary w cm, wysokości od podłogi wykończonej"


class Widok:
    """Przeliczenie wspolrzednych modelu (cm, Y w gore) na arkusz (Y w dol)."""

    def __init__(self, zakres_cm, pole, skala=None):
        rx0, ry0, rx1, ry1 = zakres_cm
        self.zakres = (min(rx0, rx1), min(ry0, ry1), max(rx0, rx1), max(ry0, ry1))
        rx0, ry0, rx1, ry1 = self.zakres
        X0, Y0, X1, Y1 = pole
        self.sk = skala or min((X1 - X0) / (rx1 - rx0), (Y1 - Y0) / (ry1 - ry0))
        self.X0 = X0 + ((X1 - X0) - (rx1 - rx0) * self.sk) / 2
        self.Y0 = Y0 + ((Y1 - Y0) - (ry1 - ry0) * self.sk) / 2

    def p(self, x, y):
        return self.X0 + (x - self.zakres[0]) * self.sk, self.Y0 + (self.zakres[3] - y) * self.sk

    def d(self, cm):
        return cm * self.sk

    @property
    def px_na_m(self):
        return 100 * self.sk


def jednostek_na_cm(mianownik):
    """Ile jednostek arkusza przypada na 1 cm modelu w skali 1:mianownik na A3."""
    return 10.0 / mianownik / MM_NA_JEDNOSTKE_A3


def skala_arkusza(zakres_cm, pole):
    """Najwieksza skala z SKALE, w ktorej zakres miesci sie w polu; zwraca (sk, '1:50 (A3)')."""
    rx0, ry0, rx1, ry1 = zakres_cm
    X0, Y0, X1, Y1 = pole
    for m in SKALE:
        sk = jednostek_na_cm(m)
        if abs(rx1 - rx0) * sk <= X1 - X0 and abs(ry1 - ry0) * sk <= Y1 - Y0:
            return sk, "1:%d (A3)" % m
    return None, "bez skali"


def ramka(margines=12):
    return svg.prostokat(margines, margines, SZER - margines, WYS - margines, kolor="#111", gr=2.2)


def naglowek(M, kod, tytul):
    pr = pliki.projekt(M)
    s = svg.tekst(50, 58, "%s — %s" % (kod, tytul), 26, waga="bold")
    if pr.get("obiekt"):
        s += svg.tekst(50, 86, pr["obiekt"], 14, kolor="#555")
    return s


def tabliczka(M, kod, tytul, skala_txt, x=720, y=1800, szer=720, wys=260, jednostki=JEDNOSTKI):
    pr = pliki.projekt(M)
    wiersze = [
        ("INWESTOR", pr.get("inwestor") or "—"),
        ("OBIEKT", pr.get("obiekt") or "—"),
        ("RYSUNEK", "%s  %s" % (kod, tytul)),
        ("FAZA", pr.get("faza") or "—"),
        ("SKALA", skala_txt + ("; " + jednostki if jednostki else "")),
        ("DATA / OPRAC.", "%s  /  %s" % (date.today().strftime("%d.%m.%Y"), pr.get("autor") or "—")),
        ("", ADNOTACJA),
    ]
    h = wys / len(wiersze)
    s = [svg.prostokat(x, y, x + szer, y + wys, kolor="#111", gr=1.6),
         svg.linia(x + 130, y, x + 130, y + wys, "#111", 0.8)]
    for i, (k, v) in enumerate(wiersze):
        yy = y + i * h
        if i:
            s.append(svg.linia(x, yy, x + szer, yy, "#111", 0.8))
        s.append(svg.tekst(x + 10, yy + h / 2 + 4, k, 9, waga="bold"))
        linie = textwrap.wrap(v, int((szer - 150) / 5.2)) or [""]
        for j, lin in enumerate(linie[:2]):
            s.append(svg.tekst(x + 142, yy + h / 2 + 4 + (j - (len(linie[:2]) - 1) / 2) * 12, lin, 9.5))
    return "".join(s)


def legenda(pozycje, x, y, szer, tytul="LEGENDA"):
    """pozycje: [(svg symbolu rysowanego w polu 0..24 x 0..16, opis)]; zwraca (svg, wysokosc)."""
    s = [svg.tekst(x, y + 12, tytul, 11, waga="bold")]
    yy = y + 24
    for symbol, opis in pozycje:
        s.append('<g transform="translate(%.1f %.1f)">%s</g>' % (x, yy, symbol))
        for j, lin in enumerate(textwrap.wrap(opis, int((szer - 36) / 5.0)) or [""]):
            s.append(svg.tekst(x + 34, yy + 11 + j * 11, lin, 9))
            yy += 11 if j else 0
        yy += 20
    return "".join(s), yy - y


def uwagi(linie, x, y, szer, r=10, tytul="UWAGI"):
    """Numerowane uwagi zawijane do szerokosci; zwraca (svg, wysokosc)."""
    s = [svg.tekst(x, y + 12, tytul, 11, waga="bold")]
    yy = y + 28
    znakow = int(szer / (r * 0.52))
    for i, tekst in enumerate(linie, 1):
        for j, lin in enumerate(textwrap.wrap(tekst, znakow - 4) or [""]):
            s.append(svg.tekst(x + (0 if j == 0 else 18), yy, ("%d. " % i if j == 0 else "") + lin, r))
            yy += r * 1.35
        yy += 3
    return "".join(s), yy - y


def arkusz(M, kod, tytul, skala_txt, tresc, legenda_poz=None, uwagi_linie=None, jednostki=JEDNOSTKI):
    """Pelny dokument SVG: ramka, naglowek, tresc, legenda i uwagi po lewej na dole, tabliczka po prawej.
    jednostki - dopisek o jednostkach w polu SKALA tabliczki (None: bez dopisku)."""
    s = [ramka(), naglowek(M, kod, tytul), tresc]
    y = 1800
    if legenda_poz:
        czesc, h = legenda(legenda_poz, 50, y, 640)
        s.append(czesc)
        y += h + 8
    if uwagi_linie:
        czesc, h = uwagi(uwagi_linie, 50, y, 640)
        s.append(czesc)
    s.append(tabliczka(M, kod, tytul, skala_txt, jednostki=jednostki))
    return svg.dokument(SZER, WYS, "\n".join(s))
