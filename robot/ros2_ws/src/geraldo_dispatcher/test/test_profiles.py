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


def test_only_the_inflation_radius_depends_on_the_priority():
    assert [(p.name, p.inflation_radius) for p in PROFILES.values()] == [("critica", 0.55), ("media", 0.70), ("rotina", 0.70)]
    assert not any(hasattr(p, "max_speed") for p in PROFILES.values())  # a velocidade é 3,0 m/s para todas


def test_the_default_profile_matches_the_nav2_inflation_radius():
    params = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml").read_text())
    radius = params["local_costmap"]["local_costmap"]["ros__parameters"]["inflation_layer"]["inflation_radius"]
    assert DEFAULT_PROFILE is PROFILES["media"] and DEFAULT_PROFILE.inflation_radius == pytest.approx(radius)


def test_profile_for_picks_by_priority_and_rejects_unknown_ones():
    assert profile_for("critica") is PROFILES["critica"]
    with pytest.raises(ValueError, match="Prioridade desconhecida: urgente"):
        profile_for("urgente")
