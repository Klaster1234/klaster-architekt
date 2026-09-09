"""Startuje serwer MCP w Blenderze zaraz po wczytaniu interfejsu."""
import bpy

def _start():
    try:
        bpy.ops.blendermcp.start_server()
        print("BLENDERMCP: serwer wystartowal na porcie 9876")
    except Exception as e:
        print("BLENDERMCP: start nieudany:", e)
    return None

bpy.app.timers.register(_start, first_interval=2.0)
