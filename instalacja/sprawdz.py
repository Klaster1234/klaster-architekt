"""Sprawdza, czy serwery Blendera i FreeCAD-a odpowiadaja, i co jeszcze jest pod reka.

    python instalacja/sprawdz.py

Kod wyjscia zalezy tylko od serwerow MCP. Reszta to informacja: biblioteki
Pythona, Blender do pracy w tle (bryla_blender.py) i ODA File Converter dla DWG.
"""
import glob, importlib.util, os, re, shutil, socket, sys, xmlrpc.client
from pathlib import Path

def port(nr):
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect(("127.0.0.1", nr)); return True
    except OSError:
        return False
    finally:
        s.close()

def pierwszy(*kandydaci):
    for k in kandydaci:
        if k and Path(k).exists():
            return k
    return None

blender = port(9876)
freecad = port(9875)
print("Blender  9876:", "dziala" if blender else "nie odpowiada, odpal 'Blender z MCP.bat'")
if freecad:
    try:
        xmlrpc.client.ServerProxy("http://127.0.0.1:9875", allow_none=True).ping()
        print("FreeCAD  9875: dziala")
    except Exception as e:
        print("FreeCAD  9875: port otwarty, RPC nie odpowiada:", e)
else:
    print("FreeCAD  9875: nie odpowiada, uruchom FreeCAD")

print("\nInformacyjnie:")
brak = [m for m in ("fitz", "numpy", "cv2", "scipy", "PIL", "ezdxf", "shapely", "trimesh", "tzdata", "certifi")
        if importlib.util.find_spec(m) is None]
print("biblioteki Pythona:", "komplet" if not brak else "brak " + ", ".join(brak) + " (pip install -r requirements.txt)")

def blender_windows():
    """Najnowszy Blender w Program Files (Windows), posortowany numerycznie."""
    wersje = [(tuple(int(n) for n in re.findall(r"\d+", Path(p).parent.name)), p)
              for p in glob.glob("C:/Program Files/Blender Foundation/*/blender.exe")]
    return max(wersje)[1] if wersje else None

exe = pierwszy(shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender", blender_windows())
print("Blender do pracy w tle (bryla_blender.py):", exe or "nie znaleziony")
oda = pierwszy(os.environ.get("ODA_CONVERTER"), "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
               *sorted(glob.glob("C:/Program Files/ODA/ODAFileConverter*/ODAFileConverter.exe"), reverse=True))
print("ODA File Converter:", oda or "nie znaleziony (potrzebny tylko do DWG)")
sys.exit(0 if (blender and freecad) else 1)
