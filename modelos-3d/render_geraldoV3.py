"""G.E.R.A.L.D.O. V3: renders do robo num corredor hospitalar.

Uso: blender -b modelos-3d/geraldoV3.blend --python modelos-3d/render_geraldoV3.py
       VIEWS=hero,frente,traseira,lateral,topo,aerea   (quais vistas renderizar; padrao = todas)
       PREVIEW=1 PREVIEW_DIR=/pasta                     (renders rapidos de teste)
Gera renders/geraldoV3_<vista>.png ao lado deste script. NAO salva o .blend: as malhas do Gazebo saem dele
(robot/scripts/export_blender_mesh.py) e o cenario e as cameras so existem durante o render.

Robo na origem: frente = +X, eixo das rodas = Y, base_link no chao. O corredor corre ao longo de X; as cores vem
de hospital_paleta.PALETA, as mesmas da maquete do hospital.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from hospital_paleta import PALETA  # noqa: E402

PREVIEW = os.environ.get("PREVIEW") == "1"
PREVIEW_DIR = os.environ.get("PREVIEW_DIR", HERE)
ALL_VIEWS = ["hero", "frente", "traseira", "lateral", "topo", "aerea"]
VIEWS = [v for v in os.environ.get("VIEWS", ",".join(ALL_VIEWS)).split(",") if v]
PI = math.pi
scene = bpy.context.scene

# o .blend traz uma camera e uma luz padrao; saem para nao competir com as do render
for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
    bpy.data.objects.remove(o)

# os cortes booleanos (corte_roda, corte_rodizio) ficam com o olho desligado no viewport mas ligados no render, e
# tampariam as rodas; o render passa a seguir o olho do viewport
for o in bpy.data.objects:
    if o.hide_get():
        o.hide_render = True

MATS = {}


def mat(name):
    if name not in MATS:
        color, rough, metal = PALETA[name]
        m = bpy.data.materials.new(f"cenario_{name}")
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        MATS[name] = m
    return MATS[name]


def slab(name, size, loc, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name, o.scale = name, size
    o.data.materials.append(mat(material))
    return o


# ---------- cenario: corredor de 3,6 m de largura, sem teto (vistas de cima) ----------
HALF = 1.8
LENGTH = 12.0
slab("piso", (LENGTH, 2 * HALF, 0.1), (0, 0, -0.05), "piso_vinilico")
slab("faixa_piso", (LENGTH, 0.08, 0.002), (0, 0, 0.001), "amarelo_sinal")
for side, sign in (("esq", 1), ("dir", -1)):
    y = sign * (HALF + 0.05)
    slab(f"parede_{side}", (LENGTH, 0.1, 3.0), (0, y, 1.5), "parede")
    slab(f"rodape_{side}", (LENGTH, 0.03, 0.1), (0, sign * (HALF - 0.015), 0.05), "rodape")
    slab(f"faixa_protecao_{side}", (LENGTH, 0.04, 0.22), (0, sign * (HALF - 0.02), 0.95), "faixa_protecao")
slab("batente", (0.08, 0.04, 2.25), (-2.9, HALF - 0.02, 1.125), "laca_branca")
slab("batente_b", (0.08, 0.04, 2.25), (-1.7, HALF - 0.02, 1.125), "laca_branca")
slab("batente_c", (1.2, 0.04, 0.08), (-2.3, HALF - 0.02, 2.2), "laca_branca")
slab("porta", (1.0, 0.04, 2.1), (-2.3, HALF - 0.04, 1.05), "madeira_clara")
slab("placa_cruz_v", (0.05, 0.02, 0.2), (-2.3, HALF - 0.04, 2.45), "vermelho_cruz")
slab("placa_cruz_h", (0.2, 0.02, 0.05), (-2.3, HALF - 0.04, 2.45), "vermelho_cruz")
for i, x in enumerate((1.6, 4.0, -4.6)):
    slab(f"janela_{i}", (1.4, 0.03, 1.2), (x, -HALF + 0.02, 1.7), "vidro_azul")
    slab(f"janela_{i}_moldura", (1.5, 0.02, 1.3), (x, -HALF + 0.015, 1.7), "laca_branca")
slab("banco", (1.2, 0.4, 0.45), (3.4, HALF - 0.3, 0.225), "tecido_azul")
slab("tela_aviso", (0.6, 0.02, 0.35), (-4.2, HALF - 0.04, 1.6), "tela_preta")

# ---------- luzes e cameras ----------
target = bpy.data.objects.new("alvo", None)
scene.collection.objects.link(target)
target.location = Vector((0.0, 0.0, 0.24))


def track(o):
    c = o.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"


def add_camera(name, lens, loc, dof=False, down=False):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.dof.use_dof = dof
    if dof:
        cd.dof.focus_object, cd.dof.aperture_fstop = target, 4.0
    cam = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    if down:  # vista de topo: sem TRACK_TO (singular); frente do robo para a direita da imagem
        cam.rotation_euler = (0, 0, -PI / 2)
    else:
        track(cam)
    return cam


cams = {
    "hero": add_camera("cam_hero", 32, (1.75, -1.35, 0.5), dof=True),
    "frente": add_camera("cam_frente", 38, (1.9, 0, 0.26)),
    "traseira": add_camera("cam_traseira", 38, (-1.9, 0, 0.30)),
    "lateral": add_camera("cam_lateral", 45, (0, 1.65, 0.24)),
    "aerea": add_camera("cam_aerea", 38, (1.5, 1.1, 1.1)),
    "topo": add_camera("cam_topo", 45, (0, 0, 2.7), down=True),
}
for name, loc, energy, size in (("luz_teto", (0.0, 0.0, 3.0), 380, 5.0), ("luz_fundo", (-1.0, -1.4, 1.6), 90, 3.0), ("luz_frente", (2.4, 0.9, 1.4), 60, 2.5)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = energy, size
    o = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(o)
    o.location = loc
    track(o)

world = bpy.data.worlds.new("mundo")
scene.world = world
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.92, 0.94, 0.98, 1)
bg.inputs["Strength"].default_value = 0.45

# ---------- render ----------
r = scene.render
r.engine = "CYCLES"
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "AgX"
r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGB"
r.image_settings.compression = 100


def render(view, path, res, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.camera = cams[view]
    r.resolution_x, r.resolution_y = res
    scene.cycles.samples = samples
    r.filepath = path
    bpy.ops.render.render(write_still=True)


for v in VIEWS:
    hero = v == "hero"
    if PREVIEW:
        render(v, os.path.join(PREVIEW_DIR, f"p_{v}.png"), (960, 540), 24)
    else:
        render(v, os.path.join(HERE, "renders", f"geraldoV3_{v}.png"), (1920, 1080) if hero else (1280, 720), 128 if hero else 64)
print("OK", VIEWS)
