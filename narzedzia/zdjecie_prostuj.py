"""Prostuje zdjecie plaskiej powierzchni (sciana, elewacja, posadzka, plan na kartce) do skali
z czterech narozy prostokata o znanych wymiarach i mierzy na nim odcinki.

    python narzedzia/zdjecie_prostuj.py sciana.jpg --punkty 412,318 1630,352 1602,1190 398,1150 --wymiar 90 205
    python narzedzia/zdjecie_prostuj.py sciana.jpg --punkty 412,318 1630,352 1602,1190 398,1150 --wymiar 90 205 \\
        --mierz 120,1400 1850,1420 640,300 640,1180 --px-na-cm 3

--punkty to piksele zdjecia w kolejnosci LG, PG, PD, LD (lewy gorny, prawy gorny, prawy dolny,
lewy dolny) prostokata o znanych wymiarach --wymiar W H w cm: drzwi, okno, plytka, arkusz.
--mierz to pary punktow zdjecia; dlugosc liczy sie po wyprostowaniu. Wynik: obraz w skali
z siatka co 10 i 50 cm i podzialka (<nazwa>_prosto.png), DXF w mm z prostokatem i pomiarami,
odcinki pomiarow w metrach i meta. Uklad: 0 w lewym dolnym narozu prostokata, X w prawo,
Y w gore (na scianie: wysokosc od dolnej krawedzi prostokata).
Mierzy tylko w plaszczyznie prostokata: wneka, parapet czy mebel przed sciana wyjda falszywie,
a im dalej od prostokata, tym wiekszy blad. Szeroki kat (0,5x) ma dystorsje, ktorej homografia
nie usunie. Zrzut ze Street View albo Google Maps: pomiar na wlasny uzytek, wynik to ZALOZENIE.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raster_do_dxf import punkt, czcionka, zapisz_wyniki


def na_plaszczyzne(H, pkt):
    return cv2.perspectiveTransform(np.float64(pkt).reshape(-1, 1, 2), H).reshape(-1, 2)


def skala_lokalna(H, p):
    """cm na piksel zdjecia w punkcie p (najwieksze rozciagniecie)."""
    q = na_plaszczyzne(H, [p, (p[0] + 1, p[1]), (p[0], p[1] + 1)])
    return float(np.linalg.svd(np.column_stack([q[1] - q[0], q[2] - q[0]]), compute_uv=False)[0])


def main():
    ap = argparse.ArgumentParser(description="Zdjecie plaszczyzny -> obraz w skali i pomiary")
    ap.add_argument("zdjecie")
    ap.add_argument("--punkty", nargs=4, required=True, metavar="X,Y", help="LG PG PD LD prostokata (px zdjecia)")
    ap.add_argument("--wymiar", nargs=2, type=float, required=True, metavar=("W", "H"), help="wymiary prostokata w cm")
    ap.add_argument("--px-na-cm", type=float, default=2.0, help="rozdzielczosc obrazu wynikowego")
    ap.add_argument("--mierz", nargs="+", metavar="X,Y", help="pary punktow zdjecia do pomiaru")
    ap.add_argument("--margines", type=float, help="zakres wokol prostokata w cm (domyslnie cale zdjecie, max 3x prostokat)")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog zdjecia>/wyjscie)")
    ap.add_argument("--nazwa", help="przedrostek plikow wynikowych (domyslnie nazwa zdjecia)")
    a = ap.parse_args()
    sciezka = Path(a.zdjecie)
    if not sciezka.is_file():
        sys.exit("brak pliku %s" % sciezka)
    if a.mierz and len(a.mierz) % 2:
        sys.exit("--mierz wymaga par punktow (parzystej liczby)")
    W, Hp = a.wymiar
    rgb = np.array(ImageOps.exif_transpose(Image.open(sciezka)).convert("RGB"))
    zrodlo = np.float32([punkt(p) for p in a.punkty])
    H = cv2.getPerspectiveTransform(zrodlo, np.float32([[0, Hp], [W, Hp], [W, 0], [0, 0]]))

    # zakres obrazu wynikowego w cm plaszczyzny
    L = 3 * max(W, Hp)
    if a.margines is not None:
        X0, Y0, X1, Y1 = -a.margines, -a.margines, W + a.margines, Hp + a.margines
    else:
        h, w = rgb.shape[:2]
        rogi = np.float64([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]]) @ H.T
        if (rogi[:, 2] > 0).all():
            xy = rogi[:, :2] / rogi[:, 2:]
            X0, Y0 = np.maximum(xy.min(0), [-L, -L])
            X1, Y1 = np.minimum(xy.max(0), [W + L, Hp + L])
        else:
            X0, Y0, X1, Y1 = -max(W, Hp), -max(W, Hp), W + max(W, Hp), Hp + max(W, Hp)
    s = a.px_na_cm
    if max(X1 - X0, Y1 - Y0) * s > 8000:
        s = 8000 / max(X1 - X0, Y1 - Y0)
        print("uwaga: obraz za duzy, rozdzielczosc zmniejszona do %.2f px/cm" % s)
    T = np.array([[s, 0, -X0 * s], [0, -s, Y1 * s], [0, 0, 1]])
    prosto = cv2.warpPerspective(rgb, T @ H, (int(round((X1 - X0) * s)), int(round((Y1 - Y0) * s))),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    P = lambda x, y: ((x - X0) * s, (Y1 - y) * s)

    # dokladnosc: klikniecie +-2 px w narozach przenosi sie na skale (blad wzgledny) i na kazdy punkt
    skale = [skala_lokalna(H, p) for p in zrodlo]
    blad_wzgl = 2 * np.sqrt(2) * max(skale) / min(W, Hp)
    dokl = round(2 * np.sqrt(2) * max(skale), 1)
    print("prostokat %.0f x %.0f cm; 1 px zdjecia w narozach = %s cm" % (W, Hp, ", ".join("%.2f" % v for v in skale)))

    pomiary, odcinki = [], []
    pary = [(punkt(a.mierz[i]), punkt(a.mierz[i + 1])) for i in range(0, len(a.mierz or []), 2)]
    for n, (pa, pb) in enumerate(pary, 1):
        (xa, ya), (xb, yb) = na_plaszczyzne(H, [pa, pb])
        dl = float(np.hypot(xb - xa, yb - ya))
        d = dl * blad_wzgl + 2 * np.sqrt(2) * max(skala_lokalna(H, pa), skala_lokalna(H, pb))
        poza = any(x < -max(W, Hp) or x > W + max(W, Hp) or y < -max(W, Hp) or y > Hp + max(W, Hp)
                   for x, y in ((xa, ya), (xb, yb)))
        pomiary.append({"nr": n, "od_cm": [round(xa, 1), round(ya, 1)], "do_cm": [round(xb, 1), round(yb, 1)],
                        "dl_cm": round(dl, 1), "dokladnosc_cm": round(d, 1), "daleko_od_prostokata": poza})
        odcinki.append([xa / 100, ya / 100, xb / 100, yb / 100])
        print("P%d: %s cm (+-%s cm)%s" % (n, ("%.1f" % dl).replace(".", ","), ("%.1f" % d).replace(".", ","),
                                          "  UWAGA: daleko od prostokata, ekstrapolacja" if poza else ""))
    if pary:
        print("pomiar poprawny tylko w plaszczyznie prostokata (ta sama sciana, ta sama glebokosc)")

    # rysunek: siatka co 10 i 50 cm, prostokat, pomiary, podzialka 1 m
    im = Image.fromarray(prosto).convert("RGBA")
    warstwa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(warstwa)
    f = czcionka(max(12, int(6 * s)))
    krok_opisu = 50 if s >= 1.5 else 100
    for x in range(int(np.ceil(X0 / 10)) * 10, int(X1) + 1, 10):
        d.line([P(x, Y0), P(x, Y1)], fill=(255, 170, 0, 170) if x % 50 == 0 else (128, 128, 128, 110),
               width=2 if x % 50 == 0 else 1)
        if x % krok_opisu == 0:
            d.text((P(x, Y1)[0] + 3, 3), str(x), fill=(255, 140, 0, 255), font=f)
    for y in range(int(np.ceil(Y0 / 10)) * 10, int(Y1) + 1, 10):
        d.line([P(X0, y), P(X1, y)], fill=(255, 170, 0, 170) if y % 50 == 0 else (128, 128, 128, 110),
               width=2 if y % 50 == 0 else 1)
        if y % krok_opisu == 0 and P(X0, y)[1] > 30:
            d.text((3, P(X0, y)[1] + 2), str(y), fill=(255, 140, 0, 255), font=f)
    d.polygon([P(0, 0), P(W, 0), P(W, Hp), P(0, Hp)], outline=(230, 30, 30, 255), width=3)
    for p in pomiary:
        A, B = P(*p["od_cm"]), P(*p["do_cm"])
        d.line([A, B], fill=(0, 200, 255, 255), width=3)
        d.text(((A[0] + B[0]) / 2 + 6, (A[1] + B[1]) / 2 + 6), "P%d %s cm" % (p["nr"], ("%.1f" % p["dl_cm"]).replace(".", ",")),
               fill=(0, 90, 160, 255), font=f, stroke_width=2, stroke_fill=(255, 255, 255, 255))
    x0, y0 = 10, im.height - 26
    d.rectangle([x0 - 6, y0 - 12, x0 + 100 * s + 60, y0 + 14], fill=(255, 255, 255, 220))
    for i in range(10):
        d.rectangle([x0 + i * 10 * s, y0, x0 + (i + 1) * 10 * s, y0 + 8], outline=(0, 0, 0, 255),
                    fill=(0, 0, 0, 255) if i % 2 == 0 else (255, 255, 255, 255))
    d.text((x0 + 100 * s + 6, y0 - 6), "1 m", fill=(0, 0, 0, 255), font=f, stroke_width=2, stroke_fill=(255, 255, 255, 255))
    im = Image.alpha_composite(im, warstwa).convert("RGB")

    wyjscie = Path(a.wyjscie) if a.wyjscie else sciezka.parent / "wyjscie"
    baza = wyjscie / (a.nazwa or sciezka.stem)
    meta = {
        "zrodlo": sciezka.name, "rodzaj": "zdjecie plaszczyzny (homografia z prostokata)",
        "data": date.today().isoformat(), "dokladnosc_cm": dokl,
        "dokladnosc_opis": "klikniecie +-2 px w narozach prostokata; pomiary maja wlasne dokladnosci; "
                           "tylko punkty w plaszczyznie prostokata, bez dystorsji obiektywu",
        "uklad": "plaszczyzna prostokata, 0 = lewy dolny naroze, X w prawo, Y w gore; odcinki w m, DXF w mm",
        "parametry": {"punkty": a.punkty, "wymiar_cm": a.wymiar, "px_na_cm": round(s, 3), "margines_cm": a.margines},
        "obraz": {"plik": baza.name + "_prosto.png", "zakres_cm": [round(v, 1) for v in (X0, Y0, X1, Y1)]},
        "pomiary": pomiary,
        "ostrzezenie": "Pomiar poza plaszczyzna prostokata (wneka, parapet, mebel) jest falszywy; "
                       "zrzut z map internetowych daje wynik tylko na wlasny uzytek, jako ZALOZENIE.",
    }
    prostokat = [[0, 0, W / 100, 0], [W / 100, 0, W / 100, Hp / 100], [W / 100, Hp / 100, 0, Hp / 100], [0, Hp / 100, 0, 0]]
    teksty = [(((o[0] + o[2]) / 2, (o[1] + o[3]) / 2), "P%d %.1f cm" % (p["nr"], p["dl_cm"]), 40)
              for o, p in zip(odcinki, pomiary)]
    for p in zapisz_wyniki(baza, odcinki, meta, "POMIARY", teksty, {"PROSTOKAT": prostokat}):
        print("zapisano", p)
    im.save(baza.parent / (baza.name + "_prosto.png"))
    print("zapisano", baza.parent / (baza.name + "_prosto.png"))


if __name__ == "__main__":
    main()
