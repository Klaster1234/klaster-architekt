import sys

# konsola Windows z kodowa strona inna niz UTF-8 (np. cp1252) inaczej wysypuje sie na polskich
# znakach w wydruku; bez reconfigure to no-op (np. gdy stdout jest juz przekierowany do pliku)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
