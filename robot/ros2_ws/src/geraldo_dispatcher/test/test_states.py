import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.states import State, StateMachine  # noqa: E402

DELIVERY = [
    State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.CHEGOU,
    State.AGUARDANDO_RETIRADA, State.VOLTANDO, State.IDLE,
]


def test_state_values_match_the_openapi_contract():
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
    assert [s.value for s in State] == spec["components"]["schemas"]["Telemetry"]["properties"]["robot_state"]["enum"]


def test_a_whole_delivery_is_a_valid_path():
    machine = StateMachine()
    for state in DELIVERY:
        machine.go(state)
    assert machine.state is State.IDLE


@pytest.mark.parametrize("stuck", [State.A_CAMINHO, State.AGUARDANDO_RETIRADA])
def test_a_failure_can_send_the_robot_back_home_from_the_trip_and_from_the_wait(stuck):
    machine = StateMachine(initial=stuck)
    machine.go(State.VOLTANDO)
    machine.go(State.IDLE)
    assert machine.state is State.IDLE


def test_invalid_transition_says_what_was_attempted():
    machine = StateMachine()
    with pytest.raises(ValueError, match="IDLE.*CHEGOU"):
        machine.go(State.CHEGOU)
    assert machine.state is State.IDLE


def test_listeners_hear_every_transition_in_order_and_not_the_subscription():
    machine, heard = StateMachine(), []
    machine.subscribe(heard.append)
    assert heard == []
    machine.go(State.A_CAMINHO)
    machine.go(State.CARREGANDO)
    assert heard == [State.A_CAMINHO, State.CARREGANDO]


def test_a_rejected_transition_does_not_notify():
    machine, heard = StateMachine(), []
    machine.subscribe(heard.append)
    with pytest.raises(ValueError):
        machine.go(State.IDLE)
    assert heard == []
