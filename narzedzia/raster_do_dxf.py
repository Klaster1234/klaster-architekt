"""Rzut z obrazu (skan, zdjecie planu, karta sprzedazowa, zrzut ekranu) -> skala ->
linie -> DXF w mm i odcinki w metrach dla sciany_z_rzutu.py.

    python narzedzia/raster_do_dxf.py karta.png --dwa-punkty 212,1040 2268,1040 --odleglosc 10.30
    python narzedzia/raster_do_dxf.py karta.png --pole "310,420 980,420 980,905 310,905" --m2 19.10 \\
        --pole "1000,420 1480,420 1480,700 1000,700" --m2 8.2 --grube 5
    python narzedzia/raster_do_dxf.py foto_planu.jpg --perspektywa 88,140 1990,210 1930,1460 60,1390 \\
        --prostokat 10.3 7.0 --wyrownaj
    python narzedzia/sciany_z_rzutu.py wyjscie/karta_odcinki.json wyjscie/karta_pary.json

Wszystkie punkty podaje sie w pikselach obrazu wejsciowego. Skala: dwa punkty o znanej
odleglosci w metrach albo obrysy pomieszczen o znanym polu w m2 (kilka --pole daje srednia
wazona polem i rozrzut; duzy rozrzut znaczy, ze pola na karcie liczono inaczej niz w swietle
scian). --perspektywa (LG, PG, PD, LD) prostuje zdjecie kartki do prostokata --prostokat W H;
bez --dwa-punkty i --pole wymiary prostokata traktuje sie jako metry i to one daja skale.
Linie: detektor LSD (awaryjnie HoughLinesP), scalanie wspolliniowych, filtr --min-dl w m.
--grube N zostawia tylko plamy grubsze niz N px (sciany wypelnione) i gubi kreski wymiarowe,
opisy i meble. Karta czesto jest obrocona: skrypt wypisuje kierunek dominujacy, a --wyrownaj
obraca wynik tak, zeby sciany byly rownolegle do osi. Wynik jest ZALOZENIEM do sprawdzenia
pomiarem: rysunek sprzedazowy nie jest rysunkiem technicznym.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import cv2
import ezdxf
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lokal.model import json_zwarty


def punkt(t):
    x, y = t.replace(";", ",").split(",")
    return float(x), float(y)


def lista_punktow(t):
    return [punkt(p) for p in t.split()]


def czcionka(r):
    for nazwa in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(nazwa, r)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=r)
    except TypeError:
        return ImageFont.load_default()


def scal(seg, tol_kat=1.0, tol_odl=2.0, przerwa=3.0):
    """Scala odcinki wspolliniowe. tol_kat w stopniach, tol_odl i przerwa w jednostkach odcinkow.

    Najdluzszy wolny odcinek zbiera wszystkie wolne o podobnym kierunku lezace blisko jego prostej;
    ich rzuty na prosta laczy sie w przedzialy (przerwa <= przerwa), polozenie to srednia wazona dlugoscia.
    """
    s = np.asarray(seg, float).reshape(-1, 4)
    dl = np.hypot(s[:, 2] - s[:, 0], s[:, 3] - s[:, 1])
    s, dl = s[dl > 1e-9], dl[dl > 1e-9]
    kat = np.arctan2(s[:, 3] - s[:, 1], s[:, 2] - s[:, 0]) % np.pi
    sr = (s[:, :2] + s[:, 2:]) / 2
    wolne = np.ones(len(s), bool)
    wynik = []
    for i in np.argsort(-dl):
        if not wolne[i]:
            continue
        u = np.array([np.cos(kat[i]), np.sin(kat[i])])
        n = np.array([-u[1], u[0]])
        dk = np.abs((kat - kat[i] + np.pi / 2) % np.pi - np.pi / 2)
        odl = (sr - sr[i]) @ n
        grupa = np.where(wolne & (dk <= np.radians(tol_kat)) & (np.abs(odl) <= tol_odl))[0]
        wolne[grupa] = False
        t0, t1 = (s[grupa, :2] - sr[i]) @ u, (s[grupa, 2:] - sr[i]) @ u
        lo, hi = np.minimum(t0, t1), np.maximum(t0, t1)
        przedzialy = []
        for k in np.argsort(lo):
            if przedzialy and lo[k] <= przedzialy[-1][1] + przerwa:
                przedzialy[-1][1] = max(przedzialy[-1][1], hi[k])
                przedzialy[-1][2].append(k)
            else:
                przedzialy.append([lo[k], hi[k], [k]])
        for a, b, czl in przedzialy:
            off = np.average(odl[grupa[czl]], weights=dl[grupa[czl]])
            p0, p1 = sr[i] + u * a + n * off, sr[i] + u * b + n * off
            wynik.append([p0[0], p0[1], p1[0], p1[1]])
    return np.array(wynik).reshape(-1, 4)


def podziel(seg, dmax, tol_kat=2.0, min_dl=0.0):
    """Tnie kazdy odcinek w rzutach koncow odcinkow rownoleglych lezacych naprzeciw (blizej niz dmax).

    sciany_z_rzutu.py paruje linie jeden do jednego: lico ciagle naprzeciw lica przerwanego
    otworem albo sciana poprzeczna zlapaloby tylko jeden kawalek. Po podziale kazdy ma pare.
    """
    s = np.asarray(seg, float).reshape(-1, 4)
    kat = np.arctan2(s[:, 3] - s[:, 1], s[:, 2] - s[:, 0]) % np.pi
    wynik = []
    for i, (x1, y1, x2, y2) in enumerate(s):
        L = np.hypot(x2 - x1, y2 - y1)
        u = np.array([x2 - x1, y2 - y1]) / L
        n = np.array([-u[1], u[0]])
        dk = np.abs((kat - kat[i] + np.pi / 2) % np.pi - np.pi / 2)
        odl = np.abs(((s[:, :2] + s[:, 2:]) / 2 - [x1, y1]) @ n)
        obok = s[(dk <= np.radians(tol_kat)) & (odl > dmax * 0.02) & (odl <= dmax)]
        t = np.concatenate([(obok[:, :2] - [x1, y1]) @ u, (obok[:, 2:] - [x1, y1]) @ u])
        ciecia = np.unique(np.round(t[(t > dmax * 0.02) & (t < L - dmax * 0.02)], 4))
        granice = np.concatenate([[0.0], ciecia, [L]])
        for a, b in zip(granice[:-1], granice[1:]):
            if b - a > max(min_dl, 1e-9):
                wynik.append([x1 + u[0] * a, y1 + u[1] * a, x1 + u[0] * b, y1 + u[1] * b])
    return np.array(wynik).reshape(-1, 4)


def kierunek_dominujacy(seg):
    """Kat (stopnie, -45..45) ukladu prostopadlych linii, srednia kolowa 4*kat wazona dlugoscia."""
    s = np.asarray(seg, float).reshape(-1, 4)
    if not len(s):
        return 0.0
    k = np.arctan2(s[:, 3] - s[:, 1], s[:, 2] - s[:, 0])
    w = np.hypot(s[:, 2] - s[:, 0], s[:, 3] - s[:, 1])
    return float(np.degrees(np.arctan2((w * np.sin(4 * k)).sum(), (w * np.cos(4 * k)).sum()) / 4))


def obroc(seg, kat_stopnie):
    c, s_ = np.cos(np.radians(kat_stopnie)), np.sin(np.radians(kat_stopnie))
    R = np.array([[c, -s_], [s_, c]])
    s = np.asarray(seg, float).reshape(-1, 4)
    return np.hstack([s[:, :2] @ R.T, s[:, 2:] @ R.T])


def zapisz_wyniki(baza, odcinki_m, meta, warstwa="LINIE", teksty=(), inne=None):
    """<baza>.dxf (R2018, mm, $INSUNITS=4), <baza>_odcinki.json (m) i <baza>_meta.json.

    teksty: [((x, y) m, tekst, wysokosc mm)]; inne: {warstwa: odcinki m} tylko do DXF.
    """
    baza = Path(baza)
    baza.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.layers.add("OPISY", color=8)
    msp = doc.modelspace()
    for i, (nazwa, lista) in enumerate([(warstwa, odcinki_m)] + list((inne or {}).items())):
        doc.layers.add(nazwa, color=(7, 1, 5, 3, 6)[i % 5])
        for x1, y1, x2, y2 in lista:
            msp.add_line((x1 * 1000, y1 * 1000), (x2 * 1000, y2 * 1000), dxfattribs={"layer": nazwa})
    for (x, y), t, h in teksty:
        msp.add_text(t, height=h, dxfattribs={"layer": "OPISY"}).set_placement((x * 1000, y * 1000))
    sciezki = [baza.parent / (baza.name + ".dxf"), baza.parent / (baza.name + "_odcinki.json"),
               baza.parent / (baza.name + "_meta.json")]
    doc.saveas(sciezki[0])
    with open(sciezki[1], "w", encoding="utf-8") as f:
        f.write(json_zwarty([[round(float(v), 4) for v in o] for o in odcinki_m]) + "\n")
    with open(sciezki[2], "w", encoding="utf-8") as f:
        f.write(json_zwarty(meta) + "\n")
    return sciezki


def prostuj(obraz, rogi, W, H):
    """Homografia LG, PG, PD, LD -> prostokat W x H; zachowuje rozdzielczosc. Zwraca (obraz, macierz, px na jednostke)."""
    r = np.float32(rogi)
    k = float(np.mean([np.linalg.norm(r[1] - r[0]) / W, np.linalg.norm(r[2] - r[3]) / W,
                       np.linalg.norm(r[3] - r[0]) / H, np.linalg.norm(r[2] - r[1]) / H]))
    H0 = cv2.getPerspectiveTransform(r, np.float32([[0, 0], [W * k, 0], [W * k, H * k], [0, H * k]]))
    h, w = obraz.shape[:2]
    rogi_obrazu = np.float64([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]]) @ H0.T
    if (rogi_obrazu[:, 2] > 0).all():
        xy = rogi_obrazu[:, :2] / rogi_obrazu[:, 2:]
        x0, y0 = np.maximum(xy.min(0), [-W * k, -H * k])
        x1, y1 = np.minimum(xy.max(0), [2 * W * k, 2 * H * k])
    else:
        x0, y0, x1, y1 = -W * k * 0.5, -H * k * 0.5, W * k * 1.5, H * k * 1.5
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], float)
    M = T @ H0
    wynik = cv2.warpPerspective(obraz, M, (int(x1 - x0), int(y1 - y0)), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return wynik, M, k


def przeksztalc(M, pkt):
    if M is None:
        return np.float64(pkt).reshape(-1, 2)
    return cv2.perspectiveTransform(np.float64(pkt).reshape(-1, 1, 2), M).reshape(-1, 2)


def pole_px(p):
    x, y = p[:, 0], p[:, 1]
    return abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2


def wykryj(szary, grube=0, prog=None):
    """Odcinki w pikselach (x1, y1, x2, y2): LSD, a gdy niedostepny HoughLinesP na krawedziach."""
    if grube:
        t = cv2.THRESH_BINARY_INV + (cv2.THRESH_OTSU if prog is None else 0)
        prog_uzyty, maska = cv2.threshold(szary, prog or 0, 255, t)
        maska = cv2.morphologyEx(maska, cv2.MORPH_OPEN, np.ones((grube, grube), np.uint8))
        szary = 255 - maska
        print("progowanie: %d, tylko plamy grubsze niz %d px" % (prog_uzyty, grube))
    try:
        linie = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(szary)[0]
        metoda = "LSD"
    except (cv2.error, AttributeError):
        krawedzie = cv2.Canny(szary, 50, 150)
        linie = cv2.HoughLinesP(krawedzie, 1, np.pi / 720, 40, minLineLength=15, maxLineGap=3)
        metoda = "HoughLinesP"
    return (np.zeros((0, 4)) if linie is None else linie.reshape(-1, 4).astype(float)), metoda


def podglad(rgb, seg_px, punkty_kal, ppm, sciezka, maks=2400):
    im = Image.blend(Image.fromarray(rgb), Image.new("RGB", (rgb.shape[1], rgb.shape[0]), "white"), 0.55)
    k = min(1.0, maks / max(im.size))
    if k < 1:
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    gr = max(2, int(im.width / 700))
    for x1, y1, x2, y2 in seg_px:
        d.line([(x1 * k, y1 * k), (x2 * k, y2 * k)], fill=(214, 40, 40), width=gr)
    for x, y in punkty_kal:
        d.ellipse([x * k - 3 * gr, y * k - 3 * gr, x * k + 3 * gr, y * k + 3 * gr], outline=(20, 90, 200), width=gr)
    m = next(v for v in (1, 2, 5, 10, 20, 50) if v * ppm * k >= im.width / 8 or v == 50)
    x0, y0, dl = 20, im.height - 30, m * ppm * k
    for i in range(5):
        d.rectangle([x0 + i * dl / 5, y0, x0 + (i + 1) * dl / 5, y0 + 8], fill=(0, 0, 0) if i % 2 == 0 else (255, 255, 255),
                    outline=(0, 0, 0))
    d.text((x0, y0 - 22), "0", fill=(0, 0, 0), font=czcionka(16))
    d.text((x0 + dl - 10, y0 - 22), "%d m" % m, fill=(0, 0, 0), font=czcionka(16))
    im.save(sciezka)


def main():
    ap = argparse.ArgumentParser(description="Rzut z obrazu -> linie w skali (DXF, odcinki.json)")
    ap.add_argument("obraz")
    ap.add_argument("--dwa-punkty", nargs=2, metavar="X,Y", help="dwa punkty o znanej odleglosci (px)")
    ap.add_argument("--odleglosc", type=float, help="odleglosc tych punktow w metrach")
    ap.add_argument("--pole", action="append", default=[], help='obrys pomieszczenia "x,y x,y ..." (px)')
    ap.add_argument("--m2", action="append", type=float, default=[], help="pole tego obrysu w m2")
    ap.add_argument("--perspektywa", nargs=4, metavar="X,Y", help="LG PG PD LD prostokata na zdjeciu (px)")
    ap.add_argument("--prostokat", nargs=2, type=float, metavar=("W", "H"), help="wymiary prostokata z --perspektywa")
    ap.add_argument("--min-dl", type=float, default=0.3, help="najkrotszy zachowany odcinek w m")
    ap.add_argument("--grube", type=int, default=0, help="tylko plamy grubsze niz N px (sciany wypelnione)")
    ap.add_argument("--prog", type=int, help="prog jasnosci dla --grube (domyslnie Otsu)")
    ap.add_argument("--tol-px", type=float, default=2.5, help="scalanie: odleglosc linii w px (krawedzie jednej kreski)")
    ap.add_argument("--zero", metavar="X,Y", help="piksel punktu (0, 0) wyniku; domyslnie lewy dolny rog obrazu")
    ap.add_argument("--wyrownaj", action="store_true", help="obroc wynik o kierunek dominujacy")
    ap.add_argument("--wyjscie", help="katalog wynikow (domyslnie <katalog obrazu>/wyjscie)")
    ap.add_argument("--nazwa", help="przedrostek plikow wynikowych (domyslnie nazwa obrazu)")
    a = ap.parse_args()
    if len(a.pole) != len(a.m2):
        sys.exit("kazde --pole potrzebuje swojego --m2")
    if bool(a.dwa_punkty) != (a.odleglosc is not None):
        sys.exit("--dwa-punkty wymaga --odleglosc (i odwrotnie)")
    if bool(a.perspektywa) != bool(a.prostokat):
        sys.exit("--perspektywa wymaga --prostokat W H (i odwrotnie)")
    if not (a.dwa_punkty or a.pole or a.perspektywa):
        sys.exit("brak skali: podaj --dwa-punkty z --odleglosc, --pole z --m2 albo --perspektywa z --prostokat")
    sciezka = Path(a.obraz)
    if not sciezka.is_file():
        sys.exit("brak pliku %s" % sciezka)

    rgb = np.array(ImageOps.exif_transpose(Image.open(sciezka)).convert("RGB"))
    M, k_prost = None, None
    if a.perspektywa:
        rgb, M, k_prost = prostuj(rgb, [punkt(p) for p in a.perspektywa], *a.prostokat)
        print("perspektywa: obraz wyprostowany do %d x %d px" % (rgb.shape[1], rgb.shape[0]))
    szary = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    szacunki, punkty_kal = [], []
    if a.dwa_punkty:
        p = przeksztalc(M, [punkt(t) for t in a.dwa_punkty])
        d = float(np.linalg.norm(p[1] - p[0]))
        szacunki.append(("dwa punkty", d / a.odleglosc, a.odleglosc, d))
        punkty_kal += p.tolist()
    for tekst, m2 in zip(a.pole, a.m2):
        p = przeksztalc(M, lista_punktow(tekst))
        szacunki.append(("pole %.2f m2" % m2, float(np.sqrt(pole_px(p) / m2)), m2, float(np.sqrt(pole_px(p)))))
        punkty_kal += p.tolist()
    if not szacunki:
        szacunki.append(("prostokat %.2f x %.2f m" % tuple(a.prostokat), k_prost, 1.0, k_prost * min(a.prostokat)))
        print("skala z --prostokat: wymiary traktuje jako metry")
    ppm = float(np.average([s[1] for s in szacunki], weights=[s[2] for s in szacunki]))
    for opis, v, _, _ in szacunki:
        print("skala z %-18s %8.2f px/m  (%+.1f%% od sredniej)" % (opis, v, (v / ppm - 1) * 100))
    rozrzut = float(np.std([s[1] for s in szacunki]) / ppm) if len(szacunki) > 1 else 0.0
    # blad wzgledny skali: rozrzut kilku szacunkow albo klikniecie +-2 px na dlugosci kalibracji
    blad_skali = max(rozrzut, 2 * np.sqrt(2) / min(s[3] for s in szacunki))

    surowe, metoda = wykryj(szary, a.grube, a.prog)
    seg_px = scal(surowe[np.hypot(surowe[:, 2] - surowe[:, 0], surowe[:, 3] - surowe[:, 1]) >= 3],
                  tol_kat=1.0, tol_odl=a.tol_px, przerwa=a.tol_px + 1)
    dl_px = np.hypot(seg_px[:, 2] - seg_px[:, 0], seg_px[:, 3] - seg_px[:, 1])
    seg_px = seg_px[dl_px >= a.min_dl * ppm]
    seg_px = seg_px[np.argsort(-np.hypot(seg_px[:, 2] - seg_px[:, 0], seg_px[:, 3] - seg_px[:, 1]))]
    print("%s: %d surowych odcinkow -> %d po scaleniu i filtrze %.2f m" % (metoda, len(surowe), len(seg_px), a.min_dl))

    zx, zy = przeksztalc(M, [punkt(a.zero)])[0] if a.zero else (0.0, float(szary.shape[0]))
    seg_m = np.column_stack([(seg_px[:, 0] - zx) / ppm, (zy - seg_px[:, 1]) / ppm,
                             (seg_px[:, 2] - zx) / ppm, (zy - seg_px[:, 3]) / ppm])
    kat = kierunek_dominujacy(seg_m)
    print("kierunek dominujacy linii: %.2f st." % kat)
    obrot = 0.0
    if a.wyrownaj:
        obrot = -kat
        seg_m = obroc(seg_m, obrot)
        print("wyrownano: obrot %.2f st. wokol punktu zero" % obrot)
    elif abs(kat) > 0.3:
        print("uwaga: linie odchylone o %.2f st. od osi obrazu (karta obrocona?) - uzyj --wyrownaj" % kat)
    # sciany_z_rzutu.py paruje 1:1: lico ciagle dzieli sie naprzeciw koncow lica przerwanego
    seg_m = podziel(seg_m, 0.75, min_dl=0.05)
    seg_m = seg_m[np.argsort(-np.hypot(seg_m[:, 2] - seg_m[:, 0], seg_m[:, 3] - seg_m[:, 1]))]

    dokl = round(max(2 * 100 / ppm, blad_skali * 500), 1)
    wyjscie = Path(a.wyjscie) if a.wyjscie else sciezka.parent / "wyjscie"
    baza = wyjscie / (a.nazwa or sciezka.stem)
    meta = {
        "zrodlo": sciezka.name, "rodzaj": "obraz rastrowy (skan, zdjecie planu, karta)", "data": date.today().isoformat(),
        "dokladnosc_cm": dokl,
        "dokladnosc_opis": "2 px obrazu i blad kalibracji na 5 m; rysunek rastrowy to ZALOZENIE do sprawdzenia pomiarem",
        "uklad": "metry; X w prawo, Y w gore obrazu%s; 0 = %s%s" % (
            " po korekcie perspektywy" if M is not None else "",
            "punkt --zero" if a.zero else "lewy dolny rog obrazu",
            "; obrocone o %.2f st." % obrot if obrot else ""),
        "skala_px_na_m": round(ppm, 3), "skala_rozrzut_proc": round(rozrzut * 100, 2),
        "skala_szacunki": [{"z": s[0], "px_na_m": round(s[1], 3)} for s in szacunki],
        "kierunek_dominujacy_stopnie": round(kat, 3), "obrot_stopnie": round(obrot, 3),
        "detektor": metoda, "odcinkow": len(seg_m),
        "parametry": {"dwa_punkty": a.dwa_punkty, "odleglosc_m": a.odleglosc, "pole": a.pole, "m2": a.m2,
                      "perspektywa": a.perspektywa, "prostokat": a.prostokat, "min_dl_m": a.min_dl,
                      "grube_px": a.grube, "prog": a.prog, "tol_px": a.tol_px, "zero": a.zero},
    }
    for p in zapisz_wyniki(baza, seg_m, meta):
        print("zapisano", p)
    podglad(rgb, seg_px, punkty_kal, ppm, baza.parent / (baza.name + "_podglad.png"))
    print("zapisano", baza.parent / (baza.name + "_podglad.png"))
    print("skala %.2f px/m, dokladnosc ok. %.1f cm" % (ppm, dokl))


if __name__ == "__main__":
    main()
