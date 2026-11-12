"""Catálogo das peças do hospital: tamanho e grupo. Fonte única das dimensões (o Blender desenha dentro delas)."""
from __future__ import annotations

from dataclasses import dataclass

MOBILIARIO, OBSTACULO = "mobiliario", "obstaculo"


@dataclass(frozen=True)
class Piece:
    size: tuple[float, float, float]  # largura (x local), profundidade (y local), altura, em metros
    group: str = MOBILIARIO
    z: float = 0.0                    # altura do pé (peças de parede)
    walkable: bool = False            # marcação no piso: o robô pode passar por cima


PIECES: dict[str, Piece] = {
    # mobiliário (só visual)
    "banco": Piece((1.6, 0.4, 0.45)),
    "balcao": Piece((3.0, 0.7, 1.1)),
    "tv": Piece((1.2, 0.1, 0.7), z=1.3),
    "planta": Piece((0.4, 0.4, 1.0)),
    "mesa": Piece((1.4, 0.7, 0.75)),
    "cadeira": Piece((0.45, 0.45, 0.9)),
    "maca": Piece((2.0, 0.8, 0.9)),
    "armario": Piece((0.9, 0.4, 1.9)),
    "pia": Piece((0.6, 0.5, 1.0)),
    "cortina": Piece((0.1, 1.8, 2.0)),
    "carrinho_emergencia": Piece((0.7, 0.5, 1.0)),
    "carrinho": Piece((0.9, 0.6, 1.0)),
    "estante": Piece((2.0, 0.5, 2.0)),
    "doca": Piece((0.9, 0.9, 0.02), walkable=True),
    "geladeira": Piece((0.8, 0.7, 1.9)),
    "bancada": Piece((3.0, 0.6, 0.9)),
    "poltrona_coleta": Piece((0.8, 0.9, 1.0)),
    "mesa_cirurgica": Piece((2.0, 0.8, 0.9)),
    "foco": Piece((0.6, 0.6, 2.0)),
    "mesa_instrumentos": Piece((1.2, 0.6, 0.9)),
    "leito": Piece((2.0, 0.95, 0.95)),
    "monitor": Piece((0.45, 0.45, 1.5)),
    "mesa_cabeceira": Piece((0.45, 0.45, 0.6)),
    "posto_enfermagem": Piece((2.0, 0.8, 1.5)),
    "extintor": Piece((0.2, 0.2, 0.7), z=0.9),
    "placa": Piece((0.6, 0.05, 0.3), z=1.9),
    # obstáculos de corredor (colisão e mapa do Nav2)
    "cadeira_rodas": Piece((0.7, 0.7, 0.95), OBSTACULO),
    "carrinho_medicacao": Piece((0.9, 0.6, 1.0), OBSTACULO),
    "piso_molhado": Piece((0.4, 0.4, 0.65), OBSTACULO),
    "carrinho_lencois": Piece((0.8, 0.6, 1.1), OBSTACULO),
}
