from dataclasses import dataclass


@dataclass(frozen=True)
class NavProfile:
    """Como o robô navega numa prioridade: só o raio de inflação do costmap local (m). A velocidade é 3,0 m/s para todas."""

    name: str
    inflation_radius: float  # menor = passa mais perto dos obstáculos (desvio mais agressivo)


# O contrato fixa as prioridades (OpenAPI Priority). A média e a rotina usam o raio padrão do Nav2 (nav2_params.yaml).
PROFILES: dict[str, NavProfile] = {
    "critica": NavProfile("critica", inflation_radius=0.55),
    "media": NavProfile("media", inflation_radius=0.70),
    "rotina": NavProfile("rotina", inflation_radius=0.70),
}
DEFAULT_PROFILE = PROFILES["media"]


def profile_for(priority: str) -> NavProfile:
    if priority not in PROFILES:
        raise ValueError(f"Prioridade desconhecida: {priority}. Use critica, media ou rotina.")
    return PROFILES[priority]
