import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.emergency import BACKEND, TOPIC, EmergencyStop  # noqa: E402


def test_it_starts_released_and_follows_engage_and_release():
    estop = EmergencyStop()
    assert estop.active is False
    estop.engage()
    assert estop.active is True
    estop.release()
    assert estop.active is False


def test_it_stays_engaged_until_every_source_is_off():
    estop = EmergencyStop()
    estop.engage()
    estop.set_source(BACKEND, True)
    estop.release()                       # o tópico solta, o painel ainda segura
    assert estop.active is True
    estop.set_source(BACKEND, False)
    assert estop.active is False
    estop.set_source(BACKEND, True)       # e o contrário
    assert estop.active is True and TOPIC != BACKEND
