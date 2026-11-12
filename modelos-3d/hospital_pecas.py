"""Biblioteca de peças do hospital. Cada função registrada com @peca("tipo") desenha a peça dentro da caixa (w, d, h):
centrada em x e y, com o pé em z = 0. Os tamanhos vêm de robot/hospital/pieces.py (fonte única)."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from hospital_paleta import PALETA

PECAS = {}


def peca(tipo):
    def registra(fn):
        PECAS[tipo] = fn
        return fn
    return registra


def material(nome):
    m = bpy.data.materials.get(nome)
    if m:
        return m
    cor, rugosidade, metal = PALETA[nome]
    m = bpy.data.materials.new(nome)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*cor, 1)
    b.inputs["Roughness"].default_value = rugosidade
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*cor, 1)
    return m


class Forma:
    """Acumula caixas e cilindros (coordenadas locais) numa malha só, com um slot de material por nome da PALETA."""

    def __init__(self):
        self.bm = bmesh.new()
        self.slots = []

    def _atribui(self, verts, mat):
        if mat not in self.slots:
            self.slots.append(mat)
        idx = self.slots.index(mat)
        for face in {f for v in verts for f in v.link_faces}:
            face.material_index = idx

    def caixa(self, tam, pos, mat):
        """Caixa de tamanho `tam` (x, y, z) com o centro em `pos`."""
        verts = bmesh.ops.create_cube(self.bm, size=1.0)["verts"]
        bmesh.ops.scale(self.bm, vec=Vector(tam), verts=verts)
        bmesh.ops.translate(self.bm, vec=Vector(pos), verts=verts)
        self._atribui(verts, mat)

    def cilindro(self, raio, alt, pos, mat, eixo="z", seg=16):
        """Cilindro de raio `raio` e altura `alt` ao longo de `eixo`, com o centro em `pos`."""
        verts = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=raio, radius2=raio, depth=alt)["verts"]
        if eixo != "z":
            giro = Matrix.Rotation(math.pi / 2, 3, "Y" if eixo == "x" else "X")
            bmesh.ops.rotate(self.bm, cent=(0, 0, 0), matrix=giro, verts=verts)
        bmesh.ops.translate(self.bm, vec=Vector(pos), verts=verts)
        self._atribui(verts, mat)

    def objeto(self, nome, colecao, loc=(0, 0, 0), yaw=0.0):
        me = bpy.data.meshes.new(nome)
        self.bm.to_mesh(me)
        self.bm.free()
        for nome_mat in self.slots:
            me.materials.append(material(nome_mat))
        obj = bpy.data.objects.new(nome, me)
        obj.location = loc
        obj.rotation_euler = (0, 0, math.radians(yaw))
        colecao.objects.link(obj)
        return obj


# ---------- mobiliário ----------
@peca("banco")
def banco(f, w, d, h):
    f.caixa((w, d, 0.06), (0, 0, h - 0.03), "plastico_cinza")
    for sx in (-1, 1):
        f.caixa((0.05, d - 0.06, h - 0.06), (sx * (w / 2 - 0.12), 0, (h - 0.06) / 2), "inox")


@peca("balcao")
def balcao(f, w, d, h):
    f.caixa((w, d - 0.1, h - 0.04), (0, -0.05, (h - 0.04) / 2), "laca_branca")
    f.caixa((w, d, 0.04), (0, 0, h - 0.02), "madeira_clara")


@peca("tv")
def tv(f, w, d, h):
    f.caixa((w, d, h), (0, 0, h / 2), "tela_preta")


@peca("planta")
def planta(f, w, d, h):
    f.cilindro(0.15, 0.3, (0, 0, 0.15), "plastico_cinza")
    f.cilindro(w / 2, h - 0.3, (0, 0, 0.3 + (h - 0.3) / 2), "folha_verde", seg=8)


@peca("mesa")
def mesa(f, w, d, h):
    f.caixa((w, d, 0.04), (0, 0, h - 0.02), "madeira_clara")
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.caixa((0.05, 0.05, h - 0.04), (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), (h - 0.04) / 2), "inox")


@peca("cadeira")
def cadeira(f, w, d, h):
    f.caixa((w, d, 0.05), (0, 0, 0.45), "tecido_azul")
    f.caixa((w, 0.05, 0.4), (0, d / 2 - 0.025, 0.7), "tecido_azul")
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.caixa((0.03, 0.03, 0.45), (sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), 0.225), "inox")


@peca("maca")
def maca(f, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.2), sy * (d / 2 - 0.08)
            f.cilindro(0.06, 0.04, (x, y, 0.06), "borracha_preta", eixo="y")
            f.caixa((0.04, 0.04, 0.38), (x, y, 0.31), "inox")
    f.caixa((w - 0.2, d - 0.1, 0.05), (0, 0, 0.5), "inox")
    f.caixa((w, d, 0.12), (0, 0, 0.585), "lencol")
    f.caixa((0.4, d - 0.2, 0.1), (-(w / 2 - 0.3), 0, 0.695), "lencol")
    f.caixa((w * 0.55, d - 0.02, 0.04), (w / 2 - w * 0.275, 0, 0.665), "tecido_azul")
    for sy in (-1, 1):
        f.caixa((w * 0.6, 0.03, 0.2), (0, sy * (d / 2 - 0.015), 0.745), "inox")


@peca("armario")
def armario(f, w, d, h):
    f.caixa((w, d - 0.02, h), (0, 0.01, h / 2), "laca_branca")
    for sx in (-1, 1):
        f.caixa((0.02, 0.02, 0.4), (sx * 0.05, -d / 2 + 0.01, 1.0), "inox")


@peca("pia")
def pia(f, w, d, h):
    f.caixa((w, d, 0.8), (0, 0, 0.4), "laca_branca")
    f.caixa((w, d, 0.05), (0, 0, 0.825), "inox")
    f.cilindro(0.015, 0.12, (0, d / 2 - 0.08, 0.92), "inox", seg=8)


@peca("cortina")
def cortina(f, w, d, h):
    f.caixa((w, d, 1.5), (0, 0, 1.25), "tecido_azul")
    f.caixa((0.04, d, 0.04), (0, 0, h - 0.02), "inox")
    for sy in (-1, 1):
        f.cilindro(0.015, h, (0, sy * (d / 2 - 0.02), h / 2), "inox", seg=8)


@peca("carrinho_emergencia")
def carrinho_emergencia(f, w, d, h):
    f.caixa((w, d, 0.7), (0, 0, 0.5), "vermelho_cruz")
    f.caixa((w, d, 0.04), (0, 0, 0.87), "inox")
    f.caixa((0.3, 0.25, 0.1), (0, 0, 0.94), "plastico_cinza")
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.cilindro(0.05, 0.03, (sx * (w / 2 - 0.08), sy * (d / 2 - 0.06), 0.05), "borracha_preta", eixo="y", seg=10)


@peca("carrinho")
def carrinho(f, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.03), sy * (d / 2 - 0.03)
            f.caixa((0.04, 0.04, 0.85), (x, y, 0.525), "inox")
            f.cilindro(0.05, 0.03, (x, y, 0.05), "borracha_preta", eixo="y", seg=10)
    f.caixa((w - 0.06, d - 0.06, 0.04), (0, 0, 0.25), "inox")
    f.caixa((w - 0.06, d - 0.06, 0.5), (0, 0, 0.72), "lencol")


@peca("estante")
def estante(f, w, d, h):
    for sx in (-1, 1):
        f.caixa((0.04, d, h), (sx * (w / 2 - 0.02), 0, h / 2), "inox")
    f.caixa((w - 0.08, 0.02, h), (0, d / 2 - 0.01, h / 2), "plastico_cinza")
    for k, z in enumerate((0.05, 0.55, 1.05, 1.55, h - 0.015)):
        f.caixa((w - 0.08, d - 0.02, 0.03), (0, 0, z), "inox")
        if k < 4:
            for i in range(7):
                cor = ("laca_branca", "amarelo_sinal", "tecido_azul")[(i + k) % 3]
                f.caixa((0.2, 0.28, 0.2), (-0.78 + i * 0.26, -0.03, z + 0.115), cor)


@peca("doca")
def doca(f, w, d, h):
    f.caixa((w, d, h), (0, 0, h / 2), "amarelo_sinal")
    f.caixa((w - 0.12, d - 0.12, h + 0.001), (0, 0, (h + 0.001) / 2), "plastico_cinza")


@peca("geladeira")
def geladeira(f, w, d, h):
    f.caixa((w, d - 0.02, h), (0, 0.01, h / 2), "inox")
    f.caixa((0.03, 0.03, 0.6), (w / 2 - 0.1, -d / 2 + 0.01, 1.1), "plastico_cinza")
    f.caixa((0.3, 0.01, 0.1), (0, -d / 2 + 0.005, 1.6), "tela_preta")


@peca("bancada")
def bancada(f, w, d, h):
    f.caixa((w, d, h - 0.04), (0, 0, (h - 0.04) / 2), "laca_branca")
    f.caixa((w, d, 0.04), (0, 0, h - 0.02), "inox")


@peca("poltrona_coleta")
def poltrona_coleta(f, w, d, h):
    f.caixa((w - 0.2, d - 0.2, 0.3), (0, 0, 0.15), "plastico_cinza")
    f.caixa((0.6, 0.6, 0.15), (0, 0.05, 0.45), "tecido_azul")
    f.caixa((0.6, 0.12, 0.6), (0, d / 2 - 0.2, 0.8), "tecido_azul")
    for sx in (-1, 1):
        f.caixa((0.1, 0.5, 0.1), (sx * 0.35, 0.05, 0.65), "plastico_cinza")
    f.caixa((0.5, 0.25, 0.08), (0, -d / 2 + 0.15, 0.3), "tecido_azul")


@peca("mesa_cirurgica")
def mesa_cirurgica(f, w, d, h):
    f.caixa((0.8, 0.5, 0.08), (0, 0, 0.04), "inox")
    f.cilindro(0.1, 0.7, (0, 0, 0.43), "inox")
    f.caixa((w, d, 0.06), (0, 0, 0.84), "inox")
    f.caixa((w - 0.1, d - 0.1, 0.03), (0, 0, 0.885), "tecido_azul")


@peca("foco")
def foco(f, w, d, h):
    f.cilindro(0.28, 0.05, (0, 0, 0.025), "plastico_cinza")
    f.cilindro(0.03, 1.6, (0, 0, 0.85), "inox", seg=8)
    f.cilindro(0.25, 0.08, (0, 0, h - 0.1), "laca_branca")


@peca("mesa_instrumentos")
def mesa_instrumentos(f, w, d, h):
    f.caixa((w, d, 0.03), (0, 0, h - 0.015), "inox")
    f.caixa((w - 0.1, d - 0.1, 0.02), (0, 0, 0.2), "inox")
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.caixa((0.03, 0.03, h - 0.03), (sx * (w / 2 - 0.04), sy * (d / 2 - 0.04), (h - 0.03) / 2), "inox")
    for i in range(4):
        f.caixa((0.12, 0.05, 0.02), (-0.4 + i * 0.27, 0, h), "plastico_cinza")


@peca("leito")
def leito(f, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.cilindro(0.05, 0.04, (sx * (w / 2 - 0.2), sy * (d / 2 - 0.1), 0.05), "borracha_preta", eixo="y", seg=10)
    f.caixa((w - 0.1, d - 0.1, 0.2), (0, 0, 0.3), "plastico_cinza")
    f.caixa((w - 0.1, d - 0.1, 0.18), (0, 0, 0.49), "lencol")
    f.caixa((0.06, d, 0.5), (-(w / 2 - 0.03), 0, 0.7), "madeira_clara")
    f.caixa((0.06, d, 0.3), (w / 2 - 0.03, 0, 0.6), "madeira_clara")
    f.caixa((0.35, d - 0.3, 0.1), (-(w / 2 - 0.35), 0, 0.63), "lencol")
    f.caixa((0.9, d - 0.12, 0.04), (0.35, 0, 0.6), "tecido_azul")


@peca("monitor")
def monitor(f, w, d, h):
    f.cilindro(0.22, 0.04, (0, 0, 0.02), "plastico_cinza")
    f.cilindro(0.02, 1.4, (0, 0, 0.74), "inox", seg=8)
    f.caixa((0.4, 0.05, 0.3), (0, 0, 1.3), "tela_preta")
    f.caixa((0.2, 0.15, 0.3), (0, 0, 0.95), "laca_branca")


@peca("mesa_cabeceira")
def mesa_cabeceira(f, w, d, h):
    f.caixa((w, d, h - 0.03), (0, 0, (h - 0.03) / 2), "laca_branca")
    f.caixa((w, d, 0.03), (0, 0, h - 0.015), "madeira_clara")


@peca("posto_enfermagem")
def posto_enfermagem(f, w, d, h):
    f.caixa((w, d - 0.1, 1.05), (0, -0.05, 0.525), "laca_branca")
    f.caixa((w, d, 0.05), (0, 0, 1.075), "madeira_clara")
    f.caixa((0.4, 0.03, 0.3), (0.5, 0, 1.25), "tela_preta")


@peca("extintor")
def extintor(f, w, d, h):
    f.cilindro(0.09, 0.5, (0, 0, 0.25), "vermelho_cruz")
    f.cilindro(0.03, 0.1, (0, 0, 0.55), "borracha_preta", seg=8)


@peca("placa")
def placa(f, w, d, h):
    f.caixa((w, d, h), (0, 0, h / 2), "laca_branca")
    f.caixa((w - 0.04, d, 0.08), (0, -0.001, h - 0.06), "tecido_azul")


# ---------- obstáculos de corredor ----------
@peca("cadeira_rodas")
def cadeira_rodas(f, w, d, h):
    f.caixa((0.45, 0.45, 0.05), (0, 0.02, 0.48), "tecido_azul")
    f.caixa((0.45, 0.05, 0.4), (0, 0.24, 0.72), "tecido_azul")
    for sx in (-1, 1):
        f.cilindro(0.3, 0.04, (sx * 0.3, 0.05, 0.3), "borracha_preta", eixo="x")
        f.cilindro(0.06, 0.03, (sx * 0.22, -0.3, 0.06), "borracha_preta", eixo="x", seg=10)
        f.caixa((0.03, 0.4, 0.03), (sx * 0.23, 0.05, 0.65), "inox")
        f.caixa((0.03, 0.03, 0.3), (sx * 0.23, 0.31, 0.95 - 0.15), "inox")


@peca("carrinho_medicacao")
def carrinho_medicacao(f, w, d, h):
    f.caixa((w, d, 0.7), (0, 0, 0.5), "laca_branca")
    f.caixa((w, d, 0.04), (0, 0, 0.87), "inox")
    f.caixa((0.5, 0.3, 0.05), (0, 0, 0.915), "amarelo_sinal")
    for sz in (0.35, 0.5, 0.65):
        f.caixa((w - 0.1, 0.01, 0.1), (0, -d / 2 + 0.005, sz), "inox")
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.cilindro(0.05, 0.03, (sx * (w / 2 - 0.08), sy * (d / 2 - 0.06), 0.05), "borracha_preta", eixo="y", seg=10)


@peca("piso_molhado")
def piso_molhado(f, w, d, h):
    f.caixa((w, d, 0.03), (0, 0, 0.015), "amarelo_sinal")
    for i in range(5):
        prof = (d - 0.04) * (1 - i / 5)
        f.caixa((w - 0.08, prof, 0.12), (0, 0, 0.03 + 0.12 * i + 0.06), "amarelo_sinal")
    f.caixa((w - 0.14, 0.02, 0.1), (0, -0.02, 0.35), "vermelho_cruz")


@peca("carrinho_lencois")
def carrinho_lencois(f, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.03), sy * (d / 2 - 0.03)
            f.caixa((0.04, 0.04, 1.0), (x, y, 0.55), "inox")
            f.cilindro(0.05, 0.03, (x, y, 0.05), "borracha_preta", eixo="y", seg=10)
    f.caixa((w - 0.06, d - 0.06, 0.04), (0, 0, 0.25), "inox")
    f.caixa((w - 0.06, d - 0.06, 0.5), (0, 0, 0.8), "lencol")
