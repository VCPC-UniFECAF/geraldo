import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.profiles import DEFAULT_PROFILE, PROFILES, profile_for  # noqa: E402


def test_profiles_cover_exactly_the_contract_priorities():
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
    assert list(PROFILES) == spec["components"]["schemas"]["Priority"]["enum"]


def test_critical_is_faster_and_squeezes_closer_than_routine():
    assert PROFILES["critica"].max_speed > PROFILES["media"].max_speed > PROFILES["rotina"].max_speed
    assert PROFILES["critica"].inflation_radius < PROFILES["media"].inflation_radius


def test_the_default_profile_matches_the_nav2_inflation_radius():
    params = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml").read_text())
    radius = params["local_costmap"]["local_costmap"]["ros__parameters"]["inflation_layer"]["inflation_radius"]
    assert DEFAULT_PROFILE is PROFILES["media"] and DEFAULT_PROFILE.inflation_radius == pytest.approx(radius)


def test_profile_for_picks_by_priority_and_rejects_unknown_ones():
    assert profile_for("critica") is PROFILES["critica"]
    with pytest.raises(ValueError, match="Prioridade desconhecida: urgente"):
        profile_for("urgente")
