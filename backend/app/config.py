import os
import secrets


class Settings:
    """Configuração lida do ambiente. Atributos mutáveis para os testes."""

    def __init__(self) -> None:
        self.database_url = os.environ.get("GERALDO_DATABASE_URL", "sqlite:///./geraldo.db")
        # sem segredo no ambiente, gera um aleatório (tokens deixam de valer ao reiniciar)
        self.jwt_secret = os.environ.get("GERALDO_JWT_SECRET") or secrets.token_hex(32)
        self.jwt_minutes = int(os.environ.get("GERALDO_JWT_MINUTES", "60"))
        self.demo_password = os.environ.get("GERALDO_DEMO_PASSWORD", "demo-only-change-me")
        self.password_iterations = 200_000
        self.auto_seed = os.environ.get("GERALDO_AUTO_SEED", "1") == "1"


settings = Settings()
