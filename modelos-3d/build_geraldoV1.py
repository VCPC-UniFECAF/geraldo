"""G.E.R.A.L.D.O. v2 - modelo 3D a partir das imagens de referencia + especificacao do projeto.
(Gestor de Entregas e Reposicao Autonoma para Leitos e Dispensacao Otimizada)

Uso: blender -b --python build_geraldoV1.py
       VIEWS=hero,frente,traseira,lateral,topo,aerea   (quais vistas renderizar; padrao = todas)
       PREVIEW=1 PREVIEW_DIR=/pasta                     (renders rapidos, sem salvar)
Gera geraldoV1.blend, geraldoV1.glb, renders/geraldoV1_<vista>.png (hero, frente, traseira, lateral, aerea, topo).

Unidades em metros. Robo na origem: frente = +X, eixo das rodas = Y, base_link no chao (convencao ROS).
Pegada 0,70 x 0,50 m, rodas de tracao 0,20 m, rodizio traseiro 0,08 m (especificacao).
Cenario, luzes e cameras ficam sob `cenario_root`, que leva a pose do robo na cena ate a origem.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.environ.get("PREVIEW") == "1"
PREVIEW_DIR = os.environ.get("PREVIEW_DIR", OUT)
ALL_VIEWS = ["hero", "frente", "traseira", "lateral", "topo", "aerea"]
VIEWS = [v for v in os.environ.get("VIEWS", ",".join(ALL_VIEWS)).split(",") if v]
PI = math.pi

if not os.environ.get("NO_RESET"):     # no Blender ao vivo (MCP), resete a cena numa chamada anterior
    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)
scene = bpy.context.scene


# ---------- helpers ----------
def mat(name, color, rough=0.4, metal=0.0, coat=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def activate(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def smooth(o, angle=40):
    activate(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def link(o):
    bpy.context.view_layer.active_layer_collection.collection.objects.link(o)
    return o


def parent_keep(o, parent):
    """Parenteia mantendo a pose mundial atual de `o`."""
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def finish(o, name, material, parent=None, bevel=0.0, segs=4):
    o.name = name
    activate(o)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        bv = o.modifiers.new("Bevel", "BEVEL")
        bv.width, bv.segments = bevel, segs
        bpy.ops.object.modifier_apply(modifier=bv.name)
    smooth(o)
    if material:
        o.data.materials.append(material)
    if parent:
        parent_keep(o, parent)
    return o


def cyl(name, radius, depth, loc, material, parent=None, axis="Y", bevel=0.0, verts=64):
    rot = {"Y": (PI / 2, 0, 0), "X": (0, PI / 2, 0), "Z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc, rotation=rot)
    return finish(bpy.context.active_object, name, material, parent, bevel)


def slab(name, size, loc, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.scale = size
    return finish(o, name, material)


def shell(name, L, W, H, r_plan, r_edge, seg_p=12, seg_e=10):
    """Caixa arredondada: cantos verticais com raio r_plan, arestas de topo/base com raio r_edge."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = (v.co.x * L, v.co.y * W, v.co.z * H)
    vertical = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
    bmesh.ops.bevel(bm, geom=vertical, offset=r_plan, segments=seg_p, profile=0.5, affect="EDGES")
    h = H / 2
    rims = [e for e in bm.edges
            if all(abs(abs(v.co.z) - h) < 1e-6 for v in e.verts) and e.verts[0].co.z * e.verts[1].co.z > 0]
    bmesh.ops.bevel(bm, geom=rims, offset=r_edge, segments=seg_e, profile=0.5, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    link(o)
    return o


def pad(name, L, W, H, r_plan, r_edge, material):
    """Placa pequena e arredondada (sensores, slots, LEDs, parafusos). Espessura = eixo Z local."""
    o = shell(name, L, W, H, r_plan, r_edge, 6, 3)
    smooth(o)
    o.data.materials.append(material)
    return o


def stick(o, surface, origin, direction, lift):
    """Cola `o` em `surface` (raycast): Z local = normal, Y local = 'para cima'. Retorna a matriz mundial."""
    bpy.context.view_layer.update()
    inv = surface.matrix_world.inverted()
    ok, loc, nor, _ = surface.ray_cast(inv @ Vector(origin), (inv.to_3x3() @ Vector(direction)).normalized())
    assert ok, f"raycast falhou para {o.name}"
    n = (surface.matrix_world.to_3x3() @ nor).normalized()
    p = surface.matrix_world @ loc
    o.matrix_world = Matrix.Translation(p + n * lift) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    return o


def new_collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[name]
    return c


# ---------- materiais ----------
WHITE = mat("plastico_branco", (0.80, 0.80, 0.82), rough=0.32, coat=0.35)
SKIRT = mat("saia_cinza", (0.10, 0.105, 0.115), rough=0.5)
TIRE = mat("pneu", (0.025, 0.026, 0.028), rough=0.65)
HUB = mat("disco_roda", (0.075, 0.078, 0.085), rough=0.45, metal=0.2)
GLASS = mat("sensor_vidro", (0.003, 0.003, 0.004), rough=0.18)
LENS = mat("lente", (0.0, 0.006, 0.02), rough=0.05, coat=1.0)
LED = mat("led_ciano", (0.3, 0.85, 1.0), emit=(0.35, 0.9, 1.0), strength=10.0)
RED = mat("cruz_vermelha", (0.40, 0.07, 0.09), rough=0.5)
LABEL = mat("texto_cinza", (0.16, 0.17, 0.19), rough=0.6)
RECESS = mat("reentrancia", (0.52, 0.53, 0.55), rough=0.5)
METAL = mat("parafuso", (0.35, 0.36, 0.38), rough=0.35, metal=0.6)

# ---------- dimensoes (m) ----------
BL, BW, BH = 0.70, 0.50, 0.20          # chassi: comprimento, largura, altura
Z0 = 0.045                             # vao livre sob o chassi
ZT = Z0 + BH                           # topo do chassi
BZ = Z0 + BH / 2
R_PLAN, R_EDGE, SEG_E = 0.12, 0.05, 12
WR, WW, WX, WY = 0.10, 0.040, 0.10, 0.225  # roda de tracao: raio (0,20 m de diametro), largura, x (adiantada), y
CR, CX = 0.04, -0.30                       # rodizio traseiro: raio (0,08 m de diametro), x
BOXL, BOXW, BOXH, LIDH = 0.48, 0.40, 0.172, 0.048   # bau: comprimento, largura, altura da base, altura da tampa
BOXZ = ZT - 0.002                                   # base do bau
LIDAR = True                                        # disco de LiDAR 2D (opcional na especificacao)

# ---------- robo ----------
new_collection("GERALDO")
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
base = bpy.context.active_object
base.name = "base_link"

body = shell("chassi", BL, BW, BH, R_PLAN, R_EDGE, 14, SEG_E)
me = body.data
z_row = lambda k: -BH / 2 + R_EDGE * (1 - math.cos(k * PI / 2 / SEG_E))
for p in me.polygons:                  # saia escura (linhas 0..8 do chanfro) + filete de LED, exceto junto das rodas
    fz = max(me.vertices[i].co.z for i in p.vertices)
    if fz <= z_row(8) + 1e-5:
        p.material_index = 1
    elif fz <= z_row(10) + 1e-5:
        p.material_index = 1 if abs(p.center.x - WX) < 0.18 else 2
for v in me.vertices:                  # frente mais estreita, topo abaulado e em cunha (frente mais baixa)
    x, y, z = v.co
    t = min(max((x + 0.1) / (BL / 2 + 0.1), 0), 1)
    y *= 1 - 0.12 * t * t
    top = min(max(z / (BH / 2), 0), 1)
    z += top * (0.012 * max(0, 1 - (x / (BL / 2)) ** 2 - (y / (BW / 2)) ** 2) - 0.012 * x / (BL / 2))
    v.co = (x, y, z)
body.location = (0, 0, BZ)
for m in (WHITE, SKIRT, LED):
    me.materials.append(m)

# recortes: 2 rodas de tracao + rodizio traseiro (pocos escuros)
cutters = [(WR + 0.013, 0.12, (WX, s * (WY + 0.025), WR), "Y") for s in (1, -1)]
cutters.append((CR + 0.007, 0.07, (CX, 0, CR), "Y"))
for r_, depth, loc, axis in cutters:
    cut = cyl("corte", r_, depth, loc, None, axis=axis)
    for p in cut.data.polygons:
        p.material_index = 1
    mod = body.modifiers.new("corte", "BOOLEAN")
    mod.object, mod.operation, mod.solver = cut, "DIFFERENCE", "EXACT"
    activate(body)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cut)
while me.materials and me.materials[-1] is None:   # o Boolean deixa slots vazios do cortador
    me.materials.pop(index=len(me.materials) - 1)
smooth(body)
parent_keep(body, base)

SENS_Z = ZT - 0.095                    # altura dos sensores (parte plana da parede)
FRONT_ORIGIN = (1, 0, SENS_Z)


def on_body(o, origin, direction, lift=0.004):
    stick(o, body, origin, direction, lift)
    return parent_keep(o, base)


def lens_on(parent_obj, name, radius, local_xy):
    lens = cyl(name, radius, 0.004, (0, 0, 0), LENS, axis="Z", verts=32)
    lens.matrix_world = parent_obj.matrix_world @ Matrix.Translation((local_xy[0], local_xy[1], 0.0065))
    return parent_keep(lens, base)


# frente: camera RGB-D (cavidade com 2 lentes) + sensor de proximidade central abaixo dela
cam_pill = pad("camera_rgbd", 0.120, 0.036, 0.012, 0.0175, 0.004, GLASS)
on_body(cam_pill, (1, 0, SENS_Z), (-1, 0, 0))
for dx in (-0.034, 0.034):
    lens_on(cam_pill, f"lente_camera_{dx}", 0.0105, (dx, 0))
on_body(pad("prox_frontal_0", 0.040, 0.013, 0.005, 0.0062, 0.0015, GLASS), (1, 0, SENS_Z - 0.032), (-1, 0, 0), 0.0005)

# 2 ovais diagonais na frente (+-45) e 2 na traseira (+-135); nada a 180
for ang, nome in ((45, "prox_frontal_esq_45"), (-45, "prox_frontal_dir_315"),
                  (135, "prox_traseiro_esq_135"), (-135, "prox_traseiro_dir_225")):
    d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
    arc = Vector((math.copysign(BL / 2 - R_PLAN, d.x), math.copysign(BW / 2 - R_PLAN - 0.02 * (d.x > 0), d.y), SENS_Z))
    o = pad(nome, 0.060, 0.028, 0.012, 0.0135, 0.004, GLASS)   # ray a partir do centro do arco do canto: normal = ang
    on_body(o, arc + d, -d)
    lens_on(o, f"lente_{nome}", 0.0065, (0.016 * (1 if ang < 0 else -1), 0))
for y in (0.13, -0.13):                # perfuracoes de microfone
    on_body(pad(f"mic_{y}", 0.011, 0.011, 0.004, 0.0053, 0.0015, GLASS), (1, y, SENS_Z), (-1, 0, 0), 0.0005)

# barras de luz verticais nas laterais, perto da traseira
for s, n in ((1, "esq"), (-1, "dir")):
    on_body(pad(f"barra_luz_{n}", 0.007, 0.055, 0.005, 0.0033, 0.0015, LED), (-0.22, s, SENS_Z), (0, -s, 0), 0.0005)

# traseira: painel de manutencao/bateria (moldura, placa, 4 parafusos, trava, porta)
frame = pad("painel_moldura", 0.186, 0.086, 0.004, 0.011, 0.0015, SKIRT)
on_body(frame, (-1, 0, SENS_Z), (1, 0, 0), 0.0005)
plate = pad("painel", 0.178, 0.078, 0.004, 0.009, 0.0015, WHITE)
on_body(plate, (-1, 0, SENS_Z), (1, 0, 0), 0.0015)
for sx in (-0.07, 0.07):
    for sy in (-0.027, 0.027):
        sc = cyl(f"parafuso_{sx}_{sy}", 0.0035, 0.003, (0, 0, 0), METAL, axis="Z", verts=16)
        sc.matrix_world = plate.matrix_world @ Matrix.Translation((sx, sy, 0.0025))
        parent_keep(sc, base)
trava = pad("painel_trava", 0.030, 0.012, 0.004, 0.0055, 0.0015, WHITE)
trava.matrix_world = plate.matrix_world @ Matrix.Translation((0, 0.040, 0.002))
parent_keep(trava, base)
porta = pad("painel_porta", 0.036, 0.022, 0.004, 0.0045, 0.0015, GLASS)
porta.matrix_world = plate.matrix_world @ Matrix.Translation((0, -0.026, 0.0025))
parent_keep(porta, base)

# rodas de tracao: malha ao longo de Y, origem no centro (gira em torno de Y)
for s, n in ((1, "esq"), (-1, "dir")):
    y = s * WY
    w = cyl(f"roda_{n}_link", WR, WW, (WX, y, WR), TIRE, base, bevel=0.01)
    cyl(f"disco_{n}", 0.073, 0.004, (WX, y + s * (WW / 2 + 0.0005), WR), HUB, w, bevel=0.0015)
    cyl(f"tampa_{n}", 0.026, 0.008, (WX, y + s * (WW / 2 + 0.003), WR), TIRE, w, bevel=0.003)

# rodizio traseiro (embutido no recorte da saia) + garfo
cyl("rodizio_traseiro", CR, 0.022, (CX, 0, CR), TIRE, base, bevel=0.004)
cyl("rodizio_eixo", 0.008, 0.052, (CX, 0, CR), METAL, base)
for s in (1, -1):
    slab(f"rodizio_garfo_{s}", (0.05, 0.004, 0.065), (CX, s * 0.017, CR + 0.025), SKIRT)
    parent_keep(bpy.context.active_object, base)

# LiDAR 2D (disco no topo do chassi, a frente do bau)
if LIDAR:
    cyl("lidar_base", 0.036, 0.008, (0.275, 0, ZT - 0.004), SKIRT, base, axis="Z")
    cyl("lidar", 0.030, 0.028, (0.275, 0, ZT + 0.014), GLASS, base, axis="Z", bevel=0.003)

# bau de medicamentos (base + vedacao + tampa)
bw = shell("bau", BOXL, BOXW, BOXH, 0.05, 0.03, 10, 8)
bw.location = (0, 0, BOXZ + BOXH / 2)
seal = shell("vedacao", BOXL - 0.02, BOXW - 0.02, 0.012, 0.045, 0.003, 10, 2)
seal.location = (0, 0, BOXZ + BOXH + 0.001)
lid = shell("tampa", BOXL + 0.01, BOXW + 0.01, LIDH, 0.055, 0.02, 10, 8)
lid.location = (0, 0, BOXZ + BOXH + 0.004 + LIDH / 2)
for o, m in ((bw, WHITE), (seal, SKIRT), (lid, WHITE)):
    smooth(o)
    o.data.materials.append(m)
    parent_keep(o, base)

LID_Z = BOXZ + BOXH + 0.004 + LIDH * 0.40
for s in (1, -1):                      # cruz, texto e pegada nas duas laterais longas
    face_y = s * (BOXW / 2 + 0.0008)
    for nm, size, dy in (("v", (0.022, 0.003, 0.068), 0), ("h", (0.068, 0.003, 0.022), s * 0.0005)):
        slab(f"cruz_{nm}_{s}", size, (0, face_y + dy, BOXZ + 0.11), RED)
        parent_keep(bpy.context.active_object, base)
    bpy.ops.object.text_add(location=(0, s * (BOXW / 2 + 0.0015), BOXZ + 0.053), rotation=(PI / 2, 0, 0 if s < 0 else PI))
    t = bpy.context.active_object
    t.data.body, t.data.size, t.data.extrude = "MEDICINE DELIVERY", 0.0245, 0.0004
    t.data.align_x, t.data.align_y = "CENTER", "CENTER"
    bpy.ops.object.convert(target="MESH")
    t.name = f"texto_{s}"
    t.data.materials.append(LABEL)
    parent_keep(t, base)
    g = pad(f"pegada_lat_{s}", 0.10, 0.013, 0.004, 0.0062, 0.0015, RECESS)
    stick(g, lid, (0, s, LID_Z), (0, -s, 0), 0.0005)
    parent_keep(g, base)
for s, n in ((1, "frente"), (-1, "traseira")):   # pegada frontal e dobradicas atras
    if s == 1:
        g = pad("pegada_frontal", 0.09, 0.013, 0.004, 0.0062, 0.0015, RECESS)
        stick(g, lid, (1, 0, LID_Z), (-1, 0, 0), 0.0005)
        parent_keep(g, base)
    else:
        for i, y in enumerate((-0.09, -0.03, 0.03, 0.09)):
            h = pad(f"dobradica_{i}", 0.054, 0.012, 0.005, 0.0055, 0.0015, RECESS)
            stick(h, lid, (-1, y, BOXZ + BOXH + 0.004 + LIDH * 0.2), (1, 0, 0), 0.0005)
            parent_keep(h, base)

# luz de "underglow" ciano (reflexo no piso)
ld = bpy.data.lights.new("underglow", "AREA")
ld.energy, ld.size, ld.size_y, ld.color = 2, 0.6, 0.35, (0.3, 0.85, 1.0)
glow = link(bpy.data.objects.new("underglow", ld))
glow.location = (0, 0, 0.035)
glow.parent = base

robot = list(bpy.data.collections["GERALDO"].objects)

# ---------- cenario: corredor hospitalar ----------
new_collection("Cenario")
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
root = bpy.context.active_object
root.name = "cenario_root"
scenery = []

WALL = mat("parede", (0.78, 0.79, 0.81), rough=0.7)
RAIL = mat("corrimao", (0.60, 0.61, 0.63), rough=0.5)
DARKW = mat("rodape", (0.35, 0.36, 0.38), rough=0.6)
DOOR = mat("porta", (0.58, 0.59, 0.61), rough=0.5)
FRAME = mat("batente", (0.62, 0.63, 0.65), rough=0.5)
GLASSW = mat("janela", (0.38, 0.39, 0.41), rough=0.2)

floor_m = mat("piso", (0.5, 0.5, 0.52), rough=0.12)
nt = floor_m.node_tree
brick = nt.nodes.new("ShaderNodeTexBrick")
brick.offset = 0
brick.inputs["Color1"].default_value = (0.34, 0.35, 0.37, 1)
brick.inputs["Color2"].default_value = (0.32, 0.33, 0.35, 1)
brick.inputs["Mortar"].default_value = (0.2, 0.21, 0.22, 1)
brick.inputs["Scale"].default_value = 24
brick.inputs["Mortar Size"].default_value = 0.01
brick.inputs["Mortar Smooth"].default_value = 0.5
brick.inputs["Bias"].default_value = 0.0
brick.inputs["Brick Width"].default_value = 1.0
brick.inputs["Row Height"].default_value = 1.0
nt.links.new(brick.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])

bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
f = bpy.context.active_object
f.name = "piso"
f.data.materials.append(floor_m)
scenery.append(f)

W_Y = 3.4
scenery += [
    slab("parede_fundo", (11.4, 0.1, 3.0), (-3.3, W_Y, 1.5), WALL),
    slab("corrimao_faixa", (11.4, 0.04, 0.22), (-3.3, W_Y - 0.07, 0.95), RAIL),
    slab("corrimao", (11.4, 0.07, 0.04), (-3.3, W_Y - 0.085, 1.08), RAIL),
    slab("rodape", (11.4, 0.03, 0.1), (-3.3, W_Y - 0.06, 0.05), DARKW),
    slab("batente", (1.2, 0.04, 2.25), (1.1, W_Y - 0.06, 1.125), FRAME),
    slab("porta", (1.0, 0.04, 2.1), (1.1, W_Y - 0.085, 1.05), DOOR),
    slab("placa_fundo", (0.48, 0.02, 0.5), (0.35, W_Y - 0.06, 1.55), FRAME),
    slab("parede_dir", (0.1, 9, 3.0), (2.45, W_Y - 4.5, 1.5), WALL),
    slab("corrimao_dir", (0.07, 9, 0.22), (2.38, W_Y - 4.5, 0.95), RAIL),
    slab("rodape_dir", (0.03, 9, 0.1), (2.39, W_Y - 4.5, 0.05), DARKW),
]
for i, yy in enumerate((1.6, 0.0)):
    scenery.append(slab(f"janela_{i}", (0.03, 1.1, 1.3), (2.39, yy, 1.85), GLASSW))
    scenery.append(slab(f"janela_{i}_moldura", (0.02, 0.04, 1.3), (2.38, yy, 1.85), FRAME))
bpy.ops.object.text_add(location=(0.35, W_Y - 0.075, 2.0), rotation=(PI / 2, 0, 0))
sign = bpy.context.active_object
sign.name = "placa_ala"
sign.data.body, sign.data.size, sign.data.align_x = "WARD 214", 0.075, "CENTER"
sign.data.materials.append(DARKW)
scenery.append(sign)

# pose do robo no cenario (x, y, rumo)
POSE = Matrix.Translation((0.25, 0.4, 0)) @ Matrix.Rotation(math.radians(222), 4, "Z")

target = link(bpy.data.objects.new("alvo", None))
target.location = POSE @ Vector((0, 0, 0.24))
scenery.append(target)


def add_camera(name, lens, loc_S=None, loc_robot=None, dof=False, down=False):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.dof.use_dof = dof
    if dof:
        cd.dof.focus_object, cd.dof.aperture_fstop = target, 4.0
    cam = link(bpy.data.objects.new(name, cd))
    cam.location = loc_S if loc_S is not None else POSE @ Vector(loc_robot)
    if down:                                         # vista de topo: sem TRACK_TO (singular), frente do robo para cima
        cam.rotation_euler = (0, 0, POSE.to_euler().z - PI / 2)
    else:
        c = cam.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    scenery.append(cam)
    return cam


cams = {
    "hero": add_camera("cam_hero", 30, loc_S=Vector((0.30, -1.35, 0.36)), dof=True),
    "frente": add_camera("cam_frente", 38, loc_robot=(1.9, 0, 0.26)),
    "traseira": add_camera("cam_traseira", 38, loc_robot=(-1.9, 0, 0.30)),
    "lateral": add_camera("cam_lateral", 50, loc_robot=(0, 2.4, 0.24)),
    "aerea": add_camera("cam_aerea", 38, loc_robot=(1.5, 1.3, 1.1)),
    "topo": add_camera("cam_topo", 45, loc_robot=(0, 0, 2.7), down=True),
}
for name, loc, energy, size in (("luz_teto", (0.0, 0.8, 3.0), 320, 5.0), ("luz_fundo", (-1.0, -1.5, 1.6), 70, 3.0)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = energy, size
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    c = o.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    scenery.append(o)

for o in scenery:
    o.parent = root
root.matrix_world = POSE.inverted()
scene.camera = cams["hero"]

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


def render(view, path, res, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.camera = cams[view]
    r.resolution_x, r.resolution_y = res
    scene.cycles.samples = samples
    r.filepath = path
    bpy.ops.render.render(write_still=True)


if PREVIEW:
    for v in VIEWS:
        render(v, os.path.join(PREVIEW_DIR, f"p_{v}.png"), (960, 528), 24)
    raise SystemExit(0)

for v in VIEWS:
    hero = v == "hero"
    render(v, os.path.join(OUT, "renders", f"geraldoV1_{v}.png"),
           (1920, 1056) if hero else (1280, 704), 128 if hero else 48)
scene.camera = cams["hero"]

# ---------- salva e exporta ----------
if not os.environ.get("NO_SAVE"):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "geraldoV1.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for o in robot:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "geraldoV1.glb"), export_format="GLB", use_selection=True)
print("OK", len([o for o in robot if o.type == "MESH"]), "meshes")
