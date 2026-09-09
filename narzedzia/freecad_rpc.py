"""Steruje FreeCAD-em przez jego serwer RPC, bez konektora MCP.

    python freecad_rpc.py --dxf rysunek.dxf --doc Projekt --zapisz model.FCStd
    python freecad_rpc.py --kod "print(len(FreeCAD.ActiveDocument.Objects))"

Wtyczka FreeCADMCP wystawia XML-RPC na porcie 9875. Jesli w ustawieniach
dodatku wlaczysz Auto-Start Server, serwer wstaje razem z programem.
"""
import argparse, textwrap, xmlrpc.client

def polacz(host="127.0.0.1", port=9875):
    s = xmlrpc.client.ServerProxy("http://%s:%d" % (host, port), allow_none=True)
    s.ping()
    return s

IMPORT = r'''
import FreeCAD, FreeCADGui
pg = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
pg.SetBool("dxfUseLegacyImporter", False)
pg.SetBool("dxfCreatePart", True)
pg.SetBool("groupLayers", True)
pg.SetBool("dxfGetOriginalColors", True)
pg.SetBool("dxfShowDialog", False)
doc = FreeCAD.newDocument("%(doc)s")
FreeCAD.setActiveDocument(doc.Name)
import importDXF
importDXF.insert(r"%(dxf)s", doc.Name)
doc.recompute()
FreeCADGui.activeDocument().activeView().viewTop()
FreeCADGui.SendMsgToActiveView("ViewFit")
print("OBIEKTOW:", len(doc.Objects))
'''

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dxf"); ap.add_argument("--doc", default="Import")
    ap.add_argument("--kod"); ap.add_argument("--zapisz")
    ap.add_argument("--zrzut", help="sciezka PNG widoku z gory")
    a = ap.parse_args()
    s = polacz()
    if a.dxf:
        print(s.execute_code(IMPORT % {"doc": a.doc, "dxf": a.dxf}))
    if a.kod:
        print(s.execute_code(a.kod))
    if a.zrzut:
        print(s.execute_code(textwrap.dedent(r'''
            import FreeCADGui
            v = FreeCADGui.activeDocument().activeView()
            v.viewTop(); FreeCADGui.SendMsgToActiveView("ViewFit")
            v.saveImage(r"%s", 1600, 2000, "White")
            print("ZRZUT OK")
        ''') % a.zrzut))
    if a.zapisz:
        print(s.execute_code('import FreeCAD; FreeCAD.ActiveDocument.saveAs(r"%s"); print("ZAPISANE")' % a.zapisz))
