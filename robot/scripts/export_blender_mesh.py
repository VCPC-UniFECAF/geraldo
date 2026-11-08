"""Exporta a malha do corpo do G.E.R.A.L.D.O. para o Gazebo (OBJ).

Uso: blender -b modelos-3d/geraldoV1.blend --python robot/scripts/export_blender_mesh.py
Rodas e rodízio ficam de fora: o URDF as descreve com primitivas para poderem girar.
"""
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "robot", "ros2_ws", "src", "geraldo_description", "meshes")
SKIP_PREFIXES = ("roda_", "disco_", "tampa_", "rodizio_")

os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
count = 0
for obj in bpy.data.collections["GERALDO"].objects:
    if obj.type == "MESH" and not obj.name.startswith(SKIP_PREFIXES):
        obj.select_set(True)
        count += 1
assert count > 20, f"poucos objetos selecionados: {count}"

bpy.ops.wm.obj_export(
    filepath=os.path.join(OUT, "geraldo_body.obj"),
    export_selected_objects=True,
    apply_modifiers=True,
    export_materials=True,
    # a "frente" do exportador é o -Y do Blender; com NEGATIVE_Y e Z os eixos do arquivo ficam idênticos aos da cena (frente = +X)
    forward_axis="NEGATIVE_Y",
    up_axis="Z",
    global_scale=1.0,
)
print("EXPORT_OK", count)
