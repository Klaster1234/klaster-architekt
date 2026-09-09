"""Sprawdza, czy serwery Blendera i FreeCAD-a odpowiadaja.

    python instalacja/sprawdz.py
"""
import socket, sys, xmlrpc.client

def port(nr):
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect(("127.0.0.1", nr)); return True
    except OSError:
        return False
    finally:
        s.close()

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
sys.exit(0 if (blender and freecad) else 1)
