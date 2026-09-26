"""Buduje sciany modelu (cm, osiowe) z par rownoleglych linii rzutu (metry).

    python lokal/z_par_scian.py pary.json --wynik sciany.json
    python lokal/z_par_scian.py pary.json --wynik sciany.json --prog-kata 3 --skala 100 --zrodlo Z2

Wejscie: JSON [[linia1, linia2, grubosc], ...], linia = [x1,y1,x2,y2], w
metrach — dokladnie format narzedzia/sciany_z_rzutu.py (para lic sciany).
Kazda para -> czworokat przez prostokat() z tamtego skryptu. Kat dominujacy
calego zestawu = wazona dlugoscia mediana katow scian zlozonych do 90 stopni
(dwie prostopadle rodziny scian daja ten sam kat po zlozeniu). Sciany, ktorych
kat odchyla sie od dominujacego o wiecej niz --prog-kata, nie sa prostopadle
do reszty budynku i trafiaja do "odrzucone" zamiast byc na sile prostowane.
Reszta jest obracana o -kat (prostowanie) i skalowana (--skala, m -> cm) do
pasow osiowych [x0,y0,x1,y1] modelu; grubosc pasa to odleglosc lic z pary. Wynik: JSON {obrot_stopnie, sciany,
odrzucone}.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "narzedzia"))
from sciany_z_rzutu import prostokat


def _zloz_do_90(kat):
    """Sklada kat (stopnie) do przedzialu (-45, 45] wzgledem najblizszej wielokrotnosci 90."""
    return ((kat + 45.0) % 90.0) - 45.0


def _obroc(x, y, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def _cm(m, skala):
    """Metry -> cm zaokraglone do 1 mm, bez ujemnego zera z zaokraglenia."""
    v = round(m * skala, 1)
    return 0.0 if v == 0 else v


def _mediana_wazona(pary):
    """Wazona mediana z listy (wartosc, waga)."""
    dane = sorted(pary)
    suma = sum(w for _, w in dane)
    if suma <= 0:
        return 0.0
    prog, biezaca = suma / 2.0, 0.0
    for wartosc, waga in dane:
        biezaca += waga
        if biezaca >= prog:
            return wartosc
    return dane[-1][0]


def przetworz(pary, prog_kata, skala, zrodlo):
    """(obrot_stopnie, sciany, odrzucone) z listy [linia1, linia2, grubosc] w metrach."""
    czworokaty = []
    odrzucone = []
    for i, (a, b, d) in enumerate(pary):
        try:
            pts = prostokat(a, b, d)
        except ZeroDivisionError:
            odrzucone.append({"para": i, "powod": "linia zerowej dlugosci", "a": a, "b": b, "d": d})
            continue
        if pts is None:
            odrzucone.append({"para": i, "powod": "za maly zaklad lic", "a": a, "b": b, "d": d})
            continue
        dl = math.hypot(a[2] - a[0], a[3] - a[1])
        kat = _zloz_do_90(math.degrees(math.atan2(a[3] - a[1], a[2] - a[0])))
        czworokaty.append({"i": i, "pts": pts, "dl": dl, "kat": kat, "a": a, "b": b, "d": d})
    if not czworokaty:
        return 0.0, [], odrzucone
    obrot = _mediana_wazona([(c["kat"], c["dl"]) for c in czworokaty])
    sciany = []
    for c in czworokaty:
        odchylenie = _zloz_do_90(c["kat"] - obrot)
        if abs(odchylenie) > prog_kata:
            odrzucone.append({"para": c["i"], "powod": "kat odchylony od dominujacego",
                              "odchylenie_deg": round(odchylenie, 2), "a": c["a"], "b": c["b"], "d": c["d"]})
            continue
        obr = [_obroc(x, y, -obrot) for x, y in c["pts"]]
        xs, ys = [p[0] for p in obr], [p[1] for p in obr]
        # grubosc z pary (d), a nie z obwiedni: sciana odchylona o kilka stopni
        # dalaby obwiednie grubsza o L*sin(odchylenie)
        kierunek = (math.degrees(math.atan2(c["a"][3] - c["a"][1], c["a"][2] - c["a"][0])) - obrot) % 180
        pol = c["d"] / 2.0
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        if kierunek < 45 or kierunek > 135:
            pas = [min(xs), cy - pol, max(xs), cy + pol]
        else:
            pas = [cx - pol, min(ys), cx + pol, max(ys)]
        pas = [_cm(v, skala) for v in pas]
        sciana = {"id": "S%d" % (len(sciany) + 1), "typ": "z pomiaru", "nosna": False, "pas": pas}
        if zrodlo:
            sciana["zrodlo"] = zrodlo
        sciany.append(sciana)
    return obrot, sciany, odrzucone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pary", help="JSON [[linia1, linia2, grubosc], ...] w metrach")
    ap.add_argument("--wynik", required=True, help="plik wynikowy JSON")
    ap.add_argument("--prog-kata", type=float, default=3.0, help="prog odrzucenia w stopniach (domyslnie 3)")
    ap.add_argument("--skala", type=float, default=100.0, help="mnoznik m -> cm (domyslnie 100)")
    ap.add_argument("--zrodlo", help="id zrodla (meta.zrodla) wpisywany do kazdej sciany")
    a = ap.parse_args()
    with open(a.pary, encoding="utf-8") as f:
        pary = json.load(f)
    obrot, sciany, odrzucone = przetworz(pary, a.prog_kata, a.skala, a.zrodlo)
    wynik = {"obrot_stopnie": round(obrot, 2), "sciany": sciany, "odrzucone": odrzucone}
    with open(a.wynik, "w", encoding="utf-8") as f:
        json.dump(wynik, f, ensure_ascii=False, indent=2)
    print("par wejsciowych: %d" % len(pary))
    print("obrot dominujacy: %.2f stopni" % obrot)
    print("scian zaakceptowanych: %d" % len(sciany))
    print("odrzuconych: %d" % len(odrzucone))
    for o in odrzucone:
        print("  para %s: %s" % (o["para"], o["powod"]))
    print("zapisano", a.wynik)
    return 0 if sciany else 1


if __name__ == "__main__":
    sys.exit(main())
