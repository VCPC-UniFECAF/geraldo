import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from robot.scripts.contract_examples import EXAMPLES, event_examples, telemetry_examples  # noqa: E402
from robot.scripts.openapi_check import validate  # noqa: E402

SPEC = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]
TELEMETRY = {"robot_state": "IDLE", "pose": {"x": 1.0, "y": 2.0, "yaw": 0.0}, "battery": 80.0, "updated_at": "2026-11-13T12:00:00+00:00"}


def test_there_is_one_telemetry_example_per_state_and_all_follow_the_contract():
    examples = telemetry_examples()
    assert list(examples) == SCHEMAS["Telemetry"]["properties"]["robot_state"]["enum"]
    for state, body in examples.items():
        assert validate(body, SCHEMAS["Telemetry"], SPEC) == [], state
        assert body["robot_state"] == state


def test_every_event_example_follows_the_contract():
    for name, events in event_examples().items():
        for event in events:
            assert validate(event, SCHEMAS["RobotEvent"], SPEC) == [], name


def test_the_event_sequences_are_the_documented_ones():
    examples = event_examples()
    assert [e["event"] for e in examples["entrega_concluida"]] == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert [e["event"] for e in examples["falha_na_origem"]] == ["FAILED"]
    assert [e["event"] for e in examples["entrega_cancelada"]] == ["LOADED", "ARRIVED", "FAILED"]
    assert [e["event"] for e in examples["recebimento_nao_confirmado"]] == ["LOADED", "ARRIVED", "FAILED"]
    assert examples["falha_na_origem"][0]["reason"] == "não chegou à origem"


def test_the_example_files_are_up_to_date():
    assert json.loads((EXAMPLES / "robot-telemetry.json").read_text(encoding="utf-8")) == telemetry_examples()
    assert json.loads((EXAMPLES / "robot-events.json").read_text(encoding="utf-8")) == event_examples()


def test_the_validator_accepts_a_valid_body_and_nullable_fields():
    assert validate({**TELEMETRY, "delivery_id": None}, SCHEMAS["Telemetry"], SPEC) == []


def test_the_validator_catches_each_kind_of_violation():
    schema = SCHEMAS["Telemetry"]
    assert any("fora de" in e for e in validate({**TELEMETRY, "robot_state": "VOANDO"}, schema, SPEC))
    assert any("falta battery" in e for e in validate({k: v for k, v in TELEMETRY.items() if k != "battery"}, schema, SPEC))
    assert any("maior" in e for e in validate({**TELEMETRY, "battery": 120.0}, schema, SPEC))
    assert any("esperado number" in e for e in validate({**TELEMETRY, "battery": "cheia"}, schema, SPEC))
    assert any("esperado number" in e for e in validate({**TELEMETRY, "battery": True}, schema, SPEC))
    assert any("data/hora" in e for e in validate({**TELEMETRY, "updated_at": "ontem"}, schema, SPEC))
    assert any("nulo" in e for e in validate({**TELEMETRY, "battery": None}, schema, SPEC))
