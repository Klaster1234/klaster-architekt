"""Moduly wnetrz w modelu zamierzenia: model lokalu wpiety z przesunieciem, obrotem i poziomem.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model, moduly
    M = model.wczytaj("model.json")
    for mod in moduly.moduly(M):
        print(mod["id"], moduly.transformacja(M, mod), moduly.obrys_modulu(M, mod).bounds)

Modul to {id, rodzaj, plik, poziom, przesuniecie, obrot_stopnie?} (zamierzenie/SCHEMAT.md):
model lokalu obrocony przeciwnie do ruchu wskazowek zegara wokol swojego punktu (0, 0),
przesuniety i postawiony na rzednej poziomu. Rysunki lokalu (rysunki/*.py) dzialaja
na samym pliku modulu jak dotad. moduly(M) podaje tylko moduly z istniejacym plikiem: modul bez
pliku jest pominiety z uwaga na stderr (raz na proces), a blad zglasza zamierzenie/waliduj.py.
"""
import math
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import Point

from wspolne import pliki
from lokal import geometria as _geometria, model as _lokal
from zamierzenie import model

_BEZ_PLIKU = set()   # (id modulu, sciezka) - uwaga o brakujacym pliku wypisana juz w tym procesie


def _plik(M, mod):
    """Sciezka pliku modulu wzgledem katalogu pliku modelu zamierzenia; None, gdy modul nie ma pola plik."""
    plik = mod.get("plik") if isinstance(mod, dict) else None
    return Path(M["_sciezka"]).parent / plik if isinstance(plik, str) and plik else None


def moduly(M):
    """Moduly z istniejacym plikiem (rekordy M["moduly"]); dla modulu bez pliku raz na proces uwaga na stderr."""
    wynik = []
    for mod in M.get("moduly") or []:
        p = _plik(M, mod)
        if p is not None and p.is_file():
            wynik.append(mod)
            continue
        ident = mod.get("id") if isinstance(mod, dict) else mod
        if (str(ident), str(p)) not in _BEZ_PLIKU:
            _BEZ_PLIKU.add((str(ident), str(p)))
            print("UWAGA: modul %s: brak pliku %s - pominiety (sprawdz: zamierzenie/waliduj.py)"
                  % (ident, p if p is not None else "(brak pola plik)"), file=sys.stderr, flush=True)
    return wynik


def wczytaj_modul(M, mod):
    """Model lokalu modulu; plik wzgledem katalogu pliku modelu zamierzenia, raz na model."""
    c = M.setdefault("_cache", {})
    klucz = "modul:" + mod["id"]
    if klucz not in c:
        c[klucz] = pliki.wczytaj(_plik(M, mod))
    return c[klucz]


def transformacja(M, mod):
    dx, dy = mod.get("przesuniecie") or (0, 0)
    z0 = model.poziom(M, mod["poziom"]).get("z", 0) if mod.get("poziom") is not None else 0
    return {"dx": float(dx), "dy": float(dy), "kat": float(mod.get("obrot_stopnie") or 0), "z0": float(z0)}


def punkt(T, x, y):
    """Punkt lokalu w ukladzie zamierzenia: obrot o T["kat"] wokol (0, 0), potem przesuniecie."""
    a = math.radians(T["kat"])
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s + T["dx"], x * s + y * c + T["dy"])


def geometria(T, g):
    return affinity.translate(affinity.rotate(g, T["kat"], origin=(0, 0)), T["dx"], T["dy"])


def _rekord(ident, kategoria, g, z, opis=None):
    r = {"id": ident, "kategoria": kategoria, "ksztalt": {"wielokat": [[x, y] for x, y in g.exterior.coords[:-1]]}, "z": z}
    if opis:
        r["opis"] = opis
    return r


def obiekty_modulu(M, mod):
    """Sciany, pomieszczenia i wyposazenie lokalu jako rekordy obiektow w ukladzie zamierzenia:
    kategorie _sciana (pas sciany), _pomieszczenie (obrys zewnetrzny), _wyposazenie; id
    "<modul>:<id>"; z bezwzgledne (rzedna poziomu + wysokosci lokalu), bez pola poziom."""
    L, T = wczytaj_modul(M, mod), transformacja(M, mod)
    z0, H, p = T["z0"], _lokal.wysokosc(L), mod["id"] + ":"
    wynik = []
    for s in L["sciany"]:
        a, b = s.get("wys", [0, H])
        wynik.append(_rekord(p + s["id"], "_sciana", geometria(T, _geometria.prostokat(s["pas"])), [z0 + a, z0 + b]))
    for nr, w in _geometria.wielokaty(L).items():
        if w is not None:
            wynik.append(_rekord(p + nr, "_pomieszczenie", geometria(T, w), [z0, z0], _lokal.pomieszczenie(L, nr).get("nazwa")))
    for e in _lokal.elementy(L):
        g = _geometria.prostokat(e["box"])
        if e.get("ksztalt") == "kolo":
            x0, y0, x1, y1 = g.bounds
            g = Point((x0 + x1) / 2, (y0 + y1) / 2).buffer((x1 - x0) / 2, quad_segs=8)
        a, b = e.get("wys", [0, 75])
        wynik.append(_rekord(p + e["id"], "_wyposazenie", geometria(T, g), [z0 + a, z0 + b], e.get("rodzaj")))
    return wynik


def obrys_modulu(M, mod):
    return geometria(transformacja(M, mod), _geometria.obrys(wczytaj_modul(M, mod)))
