import os
import secrets

DEFAULT_DEMO_PASSWORD = "demo-only-change-me"  # valor público: serve só para a demonstração local


def parse_hours(text: str) -> tuple[int, int]:
    """'20-6' -> (20, 6). Erro claro em português se o formato ou a faixa (0 a 24) estiverem errados."""
    parts = text.split("-")
    if len(parts) == 2 and all(p.strip().isdigit() and 0 <= int(p) <= 24 for p in parts):
        return int(parts[0]), int(parts[1])
    raise ValueError(f"GERALDO_OFF_PEAK_HOURS inválido ({text!r}): use o formato inicio-fim, em horas de 0 a 24, por exemplo 20-6.")


class Settings:
    """Configuração lida do ambiente. Atributos mutáveis para os testes."""

    def __init__(self) -> None:
        self.database_url = os.environ.get("GERALDO_DATABASE_URL", "sqlite:///./geraldo.db")
        # sem segredo no ambiente, gera um aleatório (tokens deixam de valer ao reiniciar)
        self.jwt_secret = os.environ.get("GERALDO_JWT_SECRET") or secrets.token_hex(32)
        self.jwt_minutes = int(os.environ.get("GERALDO_JWT_MINUTES", "60"))
        self.demo_password = os.environ.get("GERALDO_DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
        # senha do usuário "robo" no seed; sem ela, vale a mesma senha de demonstração dos outros usuários
        self.robot_password = os.environ.get("GERALDO_ROBOT_PASSWORD") or None
        self.password_iterations = 200_000
        self.auto_seed = os.environ.get("GERALDO_AUTO_SEED", "1") == "1"
        # origens (separadas por vírgula) que o navegador pode usar para chamar a API: o Vite em desenvolvimento e em preview
        default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
        self.cors_origins = [o.strip() for o in os.environ.get("GERALDO_CORS_ORIGINS", default_origins).split(",") if o.strip()]
        # janela de baixo pico, "início-fim" em horas (padrão 20-6; "0-24" libera a rotina o dia todo, útil na demo)
        self.off_peak_start, self.off_peak_end = parse_hours(os.environ.get("GERALDO_OFF_PEAK_HOURS", "20-6"))


settings = Settings()
