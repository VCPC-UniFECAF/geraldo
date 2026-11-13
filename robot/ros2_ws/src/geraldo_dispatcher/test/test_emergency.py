import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402


def test_it_starts_released_and_follows_engage_and_release():
    estop = EmergencyStop()
    assert estop.active is False
    estop.engage()
    assert estop.active is True
    estop.release()
    assert estop.active is False
