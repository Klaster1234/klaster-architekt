"""Mierzy wysokosci na fotografii, biorac watek ceglany za linijke.

    python linijka_ceglana.py zdjecie.jpg --pas 3000 120 1400 2000 --linijka 3060

Warstwa cegla plus spoina to 7,5 cm i to jest jedyne zalozenie. Program wykrywa
spoiny w podanym pasie, dopasowuje odwzorowanie rzutowe wzdluz pionu
(y = (a*h+b)/(c*h+1)) i rysuje linijke metryczna na zdjeciu. Blad dopasowania
wypisuje w pikselach; powyzej 5 px nie ufaj wynikowi.
"""
import argparse
import numpy as np, cv2
from scipy.signal import find_peaks
from scipy.optimize import least_squares
from PIL import Image, ImageDraw, ImageFont

MODUL = 0.075  # metr na warstwe

def spoiny(szary, x0, w, y0, y1):
    p = szary[y0:y1, x0:x0 + w].mean(axis=1)
    p = p - cv2.GaussianBlur(p.reshape(-1, 1), (1, 81), 0).ravel()
    p = np.convolve(p, np.ones(5) / 5, "same")
    pk, _ = find_peaks(p, distance=max(6, int((y1 - y0) / 70)), prominence=p.std() * 0.5)
    return np.array(pk + y0, float)

def dopasuj(ys):
    if len(ys) < 8:
        raise SystemExit("za malo spoin: %d" % len(ys))
    m = np.median(np.diff(ys))
    idx = np.round((ys - ys[0]) / m)
    ok = np.r_[True, np.diff(idx) > 0]
    ys, idx = ys[ok], idx[ok]
    h = (idx.max() - idx) * MODUL
    reszta = lambda q: (q[0] * h + q[1]) / (q[2] * h + 1.0) - ys
    sol = least_squares(reszta, [-(ys[0] - ys[-1]) / max(h.max(), 1e-6), ys[-1], 0.0])
    r = np.abs(sol.fun)
    dobre = r < max(4.0, 3 * np.median(r))
    ys, h = ys[dobre], h[dobre]
    reszta = lambda q: (q[0] * h + q[1]) / (q[2] * h + 1.0) - ys
    sol = least_squares(reszta, sol.x)
    return sol.x, float(np.sqrt(np.mean(sol.fun ** 2))), len(ys)

def rysuj(src, out, abc, xr, od=-1.2, do=6.0, font="C:/Windows/Fonts/arialbd.ttf"):
    a, b, c = abc
    y = lambda hh: (a * hh + b) / (c * hh + 1.0)
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(font, max(24, im.width // 90))
    except OSError:
        f = ImageFont.load_default()
    for i in range(int(od * 10), int(do * 10)):
        hh = i / 10.0
        yy = y(hh)
        if not (0 < yy < im.height - 2):
            continue
        dl = im.width // 14 if i % 5 == 0 else im.width // 34
        d.line([(xr, yy), (xr + dl, yy)], fill=(255, 60, 0), width=6 if i % 5 == 0 else 3)
        if i % 5 == 0:
            d.text((xr + dl + 12, yy - 24), ("%.1f m" % hh).replace(".", ","), fill=(255, 60, 0), font=f)
    d.line([(xr, y(od)), (xr, y(do))], fill=(255, 60, 0), width=3)
    im.save(out, quality=92)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("zdjecie")
    ap.add_argument("--pas", nargs=4, type=int, required=True, metavar=("X0", "SZER", "Y0", "Y1"))
    ap.add_argument("--linijka", type=int, required=True, help="X, na ktorym narysowac linijke")
    ap.add_argument("--out", default="linijka.jpg")
    a = ap.parse_args()
    g = cv2.imread(a.zdjecie, cv2.IMREAD_GRAYSCALE).astype(float)
    abc, rms, n = dopasuj(spoiny(g, *a.pas))
    print("spoin %d, blad %.2f px, 1 m = %.0f px" %
          (n, rms, abs((abc[0] + abc[1]) / (abc[2] + 1) - abc[1])))
    rysuj(a.zdjecie, a.out, abc, a.linijka)
    print("zapisane:", a.out)
