"""Roznica dwoch stanow zamierzenia (np. istniejacy -> projekt) po id obiektow.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from zamierzenie import model, stany
    r = stany.roznica(model.wczytaj("przyklad/ogrod/model/istniejacy.json"),
                      model.wczytaj("przyklad/ogrod/model/projekt.json"))
    print([o["id"] for o in r["usuniete"]], [o["id"] for o in r["nowe"]])

Obiekt jest zmieniony, gdy rozni sie ksztaltem, kategoria, wysokosciami, srednica,
dachem, poziomem, polozeniem na terenie albo atrybutami; opis i zrodlo nie sa zmiana.
Brak pola i pole puste (false, 0, {}, []) znacza to samo.
"""

POLA = ("ksztalt", "kategoria", "z", "wys", "srednica", "dach", "poziom", "na_terenie", "atrybuty")


def _inny(a, b):
    return any((a.get(k) or None) != (b.get(k) or None) for k in POLA)


def roznica(M_a, M_b):
    """{"usuniete": [o_a], "nowe": [o_b], "zmienione": [(o_a, o_b)], "bez_zmian": [o_b]} - rekordy modeli."""
    a = {o["id"]: o for o in M_a.get("obiekty") or []}
    b = {o["id"]: o for o in M_b.get("obiekty") or []}
    wspolne = [(a[i], o) for i, o in b.items() if i in a]
    return {"usuniete": [o for i, o in a.items() if i not in b],
            "nowe": [o for i, o in b.items() if i not in a],
            "zmienione": [(x, y) for x, y in wspolne if _inny(x, y)],
            "bez_zmian": [y for x, y in wspolne if not _inny(x, y)]}
