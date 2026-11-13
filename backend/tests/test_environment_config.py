from sqlmodel import Session, select

from app.config import Settings, settings
from app.db import create_db, make_engine
from app.models import User
from app.security import verify_password
from app.seed import seed
from tests.conftest import FIXTURES, PASSWORD


def seeded_users(monkeypatch, robot_password):
    monkeypatch.setattr(settings, "robot_password", robot_password)
    engine = make_engine("sqlite://")
    create_db(engine)
    with Session(engine) as session:
        seed(session, FIXTURES)
        return {u.username: u.password_hash for u in session.exec(select(User)).all()}


def test_robot_user_has_its_own_password_when_one_is_configured(monkeypatch):
    hashes = seeded_users(monkeypatch, "senha-do-robo")
    assert verify_password("senha-do-robo", hashes["robo"]) and not verify_password(PASSWORD, hashes["robo"])
    assert verify_password(PASSWORD, hashes["medico1"])  # os outros seguem com a senha de demonstração


def test_robot_user_falls_back_to_the_demo_password(monkeypatch):
    hashes = seeded_users(monkeypatch, None)
    assert verify_password(PASSWORD, hashes["robo"])


def test_settings_read_the_environment(monkeypatch):
    monkeypatch.setenv("GERALDO_ROBOT_PASSWORD", "x-robo")
    monkeypatch.setenv("GERALDO_CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("GERALDO_OFF_PEAK_HOURS", "9-17")
    fresh = Settings()
    assert fresh.robot_password == "x-robo"
    assert fresh.cors_origins == ["http://a.test", "http://b.test"]
    assert (fresh.off_peak_start, fresh.off_peak_end) == (9, 17)


def test_cors_allows_the_web_dev_server_and_nobody_else(client):
    allowed = client.options("/me", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
    assert allowed.status_code == 200 and allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    refused = client.options("/me", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in refused.headers


def test_audit_and_stock_logs_have_a_handler_at_info_level():
    import logging

    log = logging.getLogger("geraldo")
    assert log.handlers and log.level == logging.INFO
