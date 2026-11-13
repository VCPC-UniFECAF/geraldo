from dataclasses import dataclass


@dataclass(frozen=True)
class NavProfile:
    """Como o robô navega numa prioridade: velocidade máxima (m/s) e raio de inflação do costmap local (m)."""

    name: str
    max_speed: float
    inflation_radius: float  # menor = passa mais perto dos obstáculos (desvio mais agressivo)


# O contrato fixa as prioridades (OpenAPI Priority). A média usa o raio padrão do Nav2 (nav2_params.yaml).
PROFILES: dict[str, NavProfile] = {
    "critica": NavProfile("critica", max_speed=1.0, inflation_radius=0.55),
    "media": NavProfile("media", max_speed=0.8, inflation_radius=0.70),
    "rotina": NavProfile("rotina", max_speed=0.5, inflation_radius=0.70),
}
DEFAULT_PROFILE = PROFILES["media"]


def profile_for(priority: str) -> NavProfile:
    if priority not in PROFILES:
        raise ValueError(f"Prioridade desconhecida: {priority}. Use critica, media ou rotina.")
    return PROFILES[priority]
