"""Exporta as 4 malhas do hospital para o Gazebo (OBJ + MTL).

Uso: blender -b modelos-3d/hospital.blend --python robot/scripts/export_hospital_mesh.py [-- pasta_de_saida]
Sem pasta de saída, grava em robot/ros2_ws/src/geraldo_description/meshes/hospital.

hospital_estrutura, hospital_mobiliario e hospital_obstaculos saem em coordenadas do mundo (origem no canto sudoeste).
A maca sai na origem e sem giro, porque o maca.sdf a posiciona (é spawnada em tempo de execução).
Eixos: forward="Y" e up="Z" deixam o arquivo igual à cena do Blender (mesma convenção do export_blender_mesh.py).
"""
import os
import sys

import bpy
from mathutils import Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(
    ROOT, "robot", "ros2_ws", "src", "geraldo_description", "meshes", "hospital"
)
PARTS = {
    "hospital_estrutura": "HOSPITAL_estrutura",
    "hospital_mobiliario": "HOSPITAL_mobiliario",
    "hospital_obstaculos": "HOSPITAL_obstaculos",
    "maca": "HOSPITAL_maca",
}

os.makedirs(OUT, exist_ok=True)
for name, collection in PARTS.items():
    meshes = [o for o in bpy.data.collections[collection].objects if o.type == "MESH"]
    assert meshes, f"nenhuma malha em {collection}"
    saved = {o: o.matrix_world.copy() for o in meshes} if name == "maca" else {}
    for o in saved:
        o.matrix_world = Matrix.Identity(4)
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
    for o, m in saved.items():
        o.matrix_world = m
    print("EXPORT_OK", name, len(meshes))
