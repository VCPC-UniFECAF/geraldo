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
