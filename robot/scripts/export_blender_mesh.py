"""Exporta as 5 malhas do G.E.R.A.L.D.O. (V3) para o Gazebo (OBJ + MTL), em coordenadas do base_link.

Uso: blender -b modelos-3d/geraldoV3.blend --python robot/scripts/export_blender_mesh.py [-- pasta_de_saida]
Sem pasta de saída, grava em robot/ros2_ws/src/geraldo_description/meshes.

Cada junta do URDF tem a sua malha: o corpo (tudo que é fixo), as duas rodas grandes e as duas partes do rodízio
(o garfo, que gira no pino em Z, e a roda pequena, que rola em Y). Os cortadores dos vãos ficam fora da coleção do robô.
Eixos: com forward="Y" e up="Z" o arquivo fica igual à cena do Blender (frente = +X, Z para cima); com NEGATIVE_Y
o corpo saía girado 180 graus e aparecia de costas para as rodas e o rodízio no Gazebo.
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(
    ROOT, "robot", "ros2_ws", "src", "geraldo_description", "meshes"
)

PARTS = {
    "geraldo_body": lambda: list(bpy.data.collections["GERALDO_corpo"].objects),
    "roda_esq": lambda: [bpy.data.objects["roda_esq"]],
    "roda_dir": lambda: [bpy.data.objects["roda_dir"]],
    "rodizio_garfo": lambda: [bpy.data.objects["rodizio_garfo"]],
    "rodizio_roda": lambda: [bpy.data.objects["rodizio_roda"]],
}

os.makedirs(OUT, exist_ok=True)
for name, pick in PARTS.items():
    meshes = [o for o in pick() if o.type == "MESH"]   # Empties (pivôs, dobradiças) não entram no .obj
    assert meshes, f"nenhuma malha para {name}"
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.ops.wm.obj_export(
        filepath=os.path.join(OUT, f"{name}.obj"),
        export_selected_objects=True,
        apply_modifiers=True,
        export_materials=True,
        forward_axis="Y",
        up_axis="Z",
        global_scale=1.0,
    )
    print("EXPORT_OK", name, len(meshes))
