"""Buduje bryle w Blenderze z par scian i slupow. Uruchamiac w tle:

    blender -b --python bryla_blender.py -- sciany_pary.json slupy.json 3.50 wynik.blend

Kazda para to prostopadloscian sciany, kazdy slup to prostopadloscian pionowy.
Wysokosc podaje sie w metrach, bo w rzucie jej nie ma; bierze sie ja z przekroju
albo z elewacji.
"""
import bpy, sys, json, math, os

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
plik_scian, plik_slupow, wysokosc, wynik = argv[0], argv[1], float(argv[2]), argv[3]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

def bryly(nazwa, czworokaty, h, kolor):
    verts, faces = [], []
    for r in czworokaty:
        i = len(verts)
        verts += [(x, y, 0.0) for x, y in r] + [(x, y, h) for x, y in r]
        faces += [(i, i+1, i+2, i+3), (i+4, i+5, i+6, i+7), (i, i+1, i+5, i+4),
                  (i+1, i+2, i+6, i+5), (i+2, i+3, i+7, i+6), (i+3, i, i+4, i+7)]
    me = bpy.data.meshes.new(nazwa); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(nazwa, me); bpy.context.collection.objects.link(ob)
    m = bpy.data.materials.new(nazwa); m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = kolor
    p.inputs["Roughness"].default_value = 0.75
    ob.data.materials.append(m)
    return ob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sciany_z_rzutu import prostokat

czw = [prostokat(a, b, d) for a, b, d in json.load(open(plik_scian))]
bryly("Sciany", [c for c in czw if c], wysokosc, (0.86, 0.85, 0.83, 1))

slupy = json.load(open(plik_slupow))
bryly("Slupy", [[(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)]
                for x, y, w, h in slupy], wysokosc, (0.74, 0.73, 0.70, 1))

bpy.ops.object.light_add(type="SUN", location=(0, 0, 40))
s = bpy.context.active_object
s.data.energy = 3.4
s.rotation_euler = (math.radians(48), 0, math.radians(210))
w = bpy.context.scene.world
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.62, 0.68, 0.80, 1)
bg.inputs[1].default_value = 0.55

bpy.ops.wm.save_as_mainfile(filepath=wynik)
print("SCIAN %d, SLUPOW %d, WYSOKOSC %.2f m" % (len(czw), len(slupy), wysokosc))
