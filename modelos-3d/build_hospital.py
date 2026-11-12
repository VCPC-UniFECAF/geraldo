"""Maquete 3D do hospital a partir de robot/hospital/hospital_layout.json (gerado por gen_hospital.py).

Uso: blender -b --python modelos-3d/build_hospital.py
       VIEWS=aerea,topo,corredor,...   (quais vistas renderizar; padrão = todas)
       NO_RENDER=1                      (só monta e salva o .blend)
       HOSPITAL_BLEND=/caminho.blend    (onde salvar; padrão modelos-3d/hospital.blend)
Gera hospital.blend e renders/hospital_<vista>.png.

Eixos: origem no canto sudoeste, x leste, y norte, z para cima (metros), como o mundo do Gazebo.
Coleções: HOSPITAL_estrutura, HOSPITAL_mobiliario, HOSPITAL_obstaculos, HOSPITAL_maca. Sem teto.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from hospital_pecas import Forma  # noqa: E402

ROOT = os.path.dirname(HERE)
LAYOUT = os.path.join(ROOT, "robot", "hospital", "hospital_layout.json")
BLEND = os.environ.get("HOSPITAL_BLEND", os.path.join(HERE, "hospital.blend"))
RENDERS = os.path.join(HERE, "renders")
PISO = {"reception": "piso_madeira"}   # demais salas: porcelanato; corredores: vinílico
VISTAS = {   # nome: (posição da câmera, alvo, lente em mm)
    "aerea": ((23, -34, 40), (23, 12, 0), 30),
    "topo": ((23, 15, 62), (23, 15, 0), 35),
    "corredor": ((2.5, 15, 1.5), (40, 15, 0.9), 28),
    "recepcao": ((11.5, 2.5, 2.2), (4, 6.5, 0.5), 24),
    "pronto_socorro": ((21, 13.4, 2.3), (4, 9.5, 0.6), 24),
    "consultorio": ((16.6, 7.5, 2.2), (13, 3, 0.6), 24),
    "farmacia": ((11.5, 27.5, 2.4), (4, 19, 1.0), 24),
    "banco_sangue": ((21.5, 27.5, 2.3), (14, 23, 0.8), 24),
    "centro_cirurgico": ((33.5, 27.5, 2.4), (28, 19.5, 0.7), 24),
    "uti": ((43.5, 27.5, 2.4), (36, 19, 0.7), 24),
    "enfermaria": ((33.5, 13.5, 2.4), (26, 5, 0.6), 24),
}
VIEWS = [v for v in os.environ.get("VIEWS", ",".join(VISTAS)).split(",") if v]

bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)
scene = bpy.context.scene


def colecao(nome):
    c = bpy.data.collections.new(nome)
    scene.collection.children.link(c)
    return c


def estrutura(layout, col):
    """Piso (vinílico + uma placa por sala), paredes com rodapé e faixa de proteção, batentes e vergas das portas."""
    t, h, dw = layout["wall_thickness"], layout["wall_height"], layout["door_width"]
    w, d = layout["size"]
    f = Forma()
    f.caixa((w, d, 0.006), (w / 2, d / 2, 0.003), "piso_vinilico")
    for r in layout["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        f.caixa((x1 - x0, y1 - y0, 0.008), ((x0 + x1) / 2, (y0 + y1) / 2, 0.004), PISO.get(r["kind"], "piso_porcelanato"))
    vistas = set()
    for x0, y0, x1, y1 in layout["walls"]:
        chave = tuple(round(v, 3) for v in (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        if chave in vistas or abs(x1 - x0) + abs(y1 - y0) < 1e-6:
            continue
        vistas.add(chave)
        horizontal = abs(y1 - y0) < 1e-9
        comp = abs(x1 - x0) if horizontal else abs(y1 - y0)
        sx, sy = (comp + t, t) if horizontal else (t, comp + t)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        f.caixa((sx, sy, h), (cx, cy, h / 2), "parede")
        f.caixa((sx + 0.01, sy + 0.01, 0.12), (cx, cy, 0.06), "rodape")
        f.caixa((sx + 0.01, sy + 0.01, 0.25), (cx, cy, 0.9), "faixa_protecao")
    for dr in layout["doors"]:
        x, y = dr["x"], dr["y"]
        along = dr["axis"] == "x"
        for s in (-1, 1):     # batentes: a parede termina exatamente na borda do vão
            off = s * (dw / 2 + 0.03)
            f.caixa((0.06, t + 0.04, 2.1) if along else (t + 0.04, 0.06, 2.1), (x + off, y, 1.05) if along else (x, y + off, 1.05), "laca_branca")
        f.caixa((dw + 0.12, t + 0.04, 0.4) if along else (t + 0.04, dw + 0.12, 0.4), (x, y, 2.3), "laca_branca")
    return f.objeto("estrutura", col)


def luz_e_mundo(layout):
    w, d = layout["size"]
    sol = bpy.data.lights.new("sol", "SUN")
    sol.energy = 3.0
    obj = bpy.data.objects.new("sol", sol)
    obj.location = (w / 2, d / 2, 30)
    obj.rotation_euler = (math.radians(35), math.radians(15), math.radians(20))
    scene.collection.objects.link(obj)
    mundo = bpy.data.worlds.new("mundo")
    mundo.use_nodes = True
    mundo.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.60, 0.68, 1)
    mundo.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = mundo


def renderizar(vistas):
    os.makedirs(RENDERS, exist_ok=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for nome in vistas:
        pos, alvo, lente = VISTAS[nome]
        cam_data.lens = lente
        cam.location = pos
        cam.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(RENDERS, f"hospital_{nome}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER_OK", nome)


def main():
    with open(LAYOUT, encoding="utf-8") as fh:
        layout = json.load(fh)
    cols = {nome: colecao(f"HOSPITAL_{nome}") for nome in ("estrutura", "mobiliario", "obstaculos", "maca")}
    estrutura(layout, cols["estrutura"])
    luz_e_mundo(layout)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    if os.environ.get("NO_RENDER") != "1":
        renderizar(VIEWS)


main()
