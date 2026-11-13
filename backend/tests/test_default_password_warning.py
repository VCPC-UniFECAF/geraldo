import logging

from fastapi.testclient import TestClient

from app import main
from app.config import DEFAULT_DEMO_PASSWORD, settings


def start(monkeypatch, engine, password, auto_seed=True):
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(settings, "demo_password", password)
    monkeypatch.setattr(settings, "auto_seed", auto_seed)
    with TestClient(main.app):
        pass


def test_seeding_with_the_default_password_warns_loudly_but_starts(monkeypatch, engine, caplog):
    caplog.set_level(logging.WARNING, logger="geraldo")
    start(monkeypatch, engine, DEFAULT_DEMO_PASSWORD)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "GERALDO_DEMO_PASSWORD" in warnings[0].getMessage() and "senha" in warnings[0].getMessage()


def test_a_chosen_password_does_not_warn(monkeypatch, engine, caplog):
    caplog.set_level(logging.WARNING, logger="geraldo")
    start(monkeypatch, engine, "outra-senha-de-teste")
    assert not caplog.records


def test_without_auto_seed_there_is_nothing_to_warn_about(monkeypatch, engine, caplog):
    caplog.set_level(logging.WARNING, logger="geraldo")
    start(monkeypatch, engine, DEFAULT_DEMO_PASSWORD, auto_seed=False)
    assert not caplog.records
