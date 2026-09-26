"""Polozenie slonca dla lokalizacji i godziny, bez zaleznosci zewnetrznych.

    from wspolne import slonce
    az, wys = slonce.pozycja(slonce.na_utc("2026-06-21T17:00"), 52.23, 21.01)

Wzory jak w SunCalc (dokladnosc ok. 0,1 stopnia), te same co w planer3d/slonce.js.
Azymut liczony od polnocy zgodnie z zegarem (90 = wschod, 180 = poludnie).
"""
import math
from datetime import datetime, timezone

RAD = math.pi / 180
E = 23.4397 * RAD  # nachylenie ekliptyki


def pozycja(data_utc, lat, lon):
    """(azymut, wysokosc) w stopniach dla chwili data_utc (datetime ze strefa)."""
    d = data_utc.timestamp() / 86400 - 10957.5
    m = (357.5291 + 0.98560028 * d) * RAD
    ekl = m + (1.9148 * math.sin(m) + 0.02 * math.sin(2 * m) + 0.0003 * math.sin(3 * m) + 282.9372) * RAD
    dek = math.asin(math.sin(E) * math.sin(ekl))
    ra = math.atan2(math.sin(ekl) * math.cos(E), math.cos(ekl))
    h = (280.16 + 360.9856235 * d + lon) * RAD - ra
    f = lat * RAD
    wys = math.asin(math.sin(f) * math.sin(dek) + math.cos(f) * math.cos(dek) * math.cos(h))
    az = math.atan2(math.sin(h), math.cos(h) * math.sin(f) - math.tan(dek) * math.cos(f))
    return (az / RAD + 540) % 360, wys / RAD


def na_utc(tekst, strefa="Europe/Warsaw"):
    """'RRRR-MM-DDTHH:MM' czasu lokalnego -> datetime w UTC (z uwzglednieniem czasu letniego)."""
    from zoneinfo import ZoneInfo
    lokalny = datetime.fromisoformat(tekst).replace(tzinfo=ZoneInfo(strefa))
    return lokalny.astimezone(timezone.utc)


def wektor_modelu(azymut, wysokosc, azymut_osi_Y):
    """Kierunek DO slonca w ukladzie modelu: x w prawo, y w gore arkusza, z w gore."""
    k = (azymut - azymut_osi_Y) * RAD
    h = wysokosc * RAD
    return math.sin(k) * math.cos(h), math.cos(k) * math.cos(h), math.sin(h)


def strona_swiata(azymut):
    """Nazwa kierunku (8 rumbow) dla azymutu w stopniach."""
    nazwy = ("północ", "północny wschód", "wschód", "południowy wschód",
             "południe", "południowy zachód", "zachód", "północny zachód")
    return nazwy[int(((azymut % 360) + 22.5) // 45) % 8]
