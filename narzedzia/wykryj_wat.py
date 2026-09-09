"""Przeglada folder ze zdjeciami i wskazuje kadry, na ktorych watek ceglany
nadaje sie na linijke.

    python wykryj_wat.py foto/
Dla kazdego zdjecia szuka okna z najsilniejsza okresowoscia pionowa. Wypisuje
moc sygnalu, wspolrzedne okna i wynikajaca skale.
"""
import sys, os, glob
import numpy as np, cv2
from scipy.signal import find_peaks

def skan(sciezka):
    g = cv2.imread(sciezka, cv2.IMREAD_GRAYSCALE)
    if g is None:
        return None
    g = g.astype(float)
    H, W = g.shape
    best = (0, None)
    for x0 in range(150, W - 250, 200):
        for y0 in range(150, H - 450, 200):
            s = g[y0:y0 + 380, x0:x0 + 140]
            pr = s.mean(axis=1)
            pr = pr - cv2.GaussianBlur(pr.reshape(-1, 1), (1, 71), 0).ravel()
            if pr.std() < 1.5:
                continue
            ac = np.correlate(pr - pr.mean(), pr - pr.mean(), "full")[len(pr) - 1:]
            ac /= ac[0] + 1e-9
            pk, _ = find_peaks(ac[12:110], height=0.30)
            if len(pk) and ac[12 + pk[0]] > best[0]:
                best = (ac[12 + pk[0]], (x0, y0, 12 + pk[0]))
    return best if best[1] else None

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    wyniki = []
    for p in sorted(glob.glob(os.path.join(folder, "*.jpg"))):
        w = skan(p)
        if w:
            wyniki.append((w[0], os.path.basename(p), w[1]))
    for moc, nazwa, (x, y, okres) in sorted(wyniki, reverse=True):
        print("%.2f  %-34s x=%4d y=%4d  okres %2d px  ->  1 m = %4.0f px"
              % (moc, nazwa, x, y, okres, okres / 0.075))
