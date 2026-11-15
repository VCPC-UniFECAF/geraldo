from pathlib import Path

import yaml

from robot.scripts.make_nav2_params import CRUISE_SPEED, FOOTPRINT, INITIAL_POSE, MPPI_TUNING, patch_params

ROOT = Path(__file__).resolve().parents[3]


def fake_defaults():
    return {
        "amcl": {"ros__parameters": {"set_initial_pose": False, "base_frame_id": "base_footprint"}},
        "local_costmap": {"local_costmap": {"ros__parameters": {"robot_radius": 0.22, "plugins": ["voxel_layer"]}}},
        "global_costmap": {"global_costmap": {"ros__parameters": {"robot_radius": 0.22}}},
        "controller_server": {"ros__parameters": {"FollowPath": {"vx_max": 0.5, "vx_min": -0.35, "wz_max": 1.9}}},
        "velocity_smoother": {"ros__parameters": {"max_velocity": [0.5, 0.0, 2.0], "min_velocity": [-0.5, 0.0, -2.0]}},
    }


def test_costmaps_use_the_70_by_50_footprint_and_drop_robot_radius():
    out = patch_params(fake_defaults())
    for name in ("local_costmap", "global_costmap"):
        p = out[name][name]["ros__parameters"]
        assert p["footprint"] == FOOTPRINT
        assert "robot_radius" not in p
    assert FOOTPRINT == "[[0.35, 0.25], [0.35, -0.25], [-0.35, -0.25], [-0.35, 0.25]]"


def test_amcl_starts_at_the_robot_base_and_uses_base_link():
    p = patch_params(fake_defaults())["amcl"]["ros__parameters"]
    assert p["set_initial_pose"] is True
    assert p["initial_pose"] == INITIAL_POSE == {"x": 6.5, "y": 26.5, "z": 0.0, "yaw": -1.5708}
    assert p["base_frame_id"] == "base_link"


def test_amcl_trusts_the_simulated_odometry_and_the_lidar_range():
    p = patch_params(fake_defaults())["amcl"]["ros__parameters"]
    assert all(p[f"alpha{i}"] == 0.05 for i in range(1, 6))
    assert p["laser_max_range"] == 12.0 and p["z_hit"] > p["z_rand"]


def test_no_node_keeps_looking_for_base_footprint():
    defaults = fake_defaults()
    defaults["collision_monitor"] = {"ros__parameters": {"base_frame_id": "base_footprint", "nested": [{"frame": "base_footprint"}]}}
    out = patch_params(defaults)
    assert "base_footprint" not in str(out)
    assert out["collision_monitor"]["ros__parameters"]["base_frame_id"] == "base_link"


def test_global_costmap_keeps_the_lidar_layer_so_the_planner_detours_around_new_obstacles():
    defaults = fake_defaults()
    defaults["global_costmap"]["global_costmap"]["ros__parameters"]["plugins"] = ["static_layer", "obstacle_layer", "inflation_layer"]
    out = patch_params(defaults)
    assert out["global_costmap"]["global_costmap"]["ros__parameters"]["plugins"] == ["static_layer", "obstacle_layer", "inflation_layer"]
    assert out["local_costmap"]["local_costmap"]["ros__parameters"]["plugins"] == ["voxel_layer"]


def test_robot_cruises_at_0_8_m_s_in_both_the_controller_and_the_velocity_smoother():
    out = patch_params(fake_defaults())
    assert out["controller_server"]["ros__parameters"]["FollowPath"]["vx_max"] == CRUISE_SPEED == 1.0
    assert out["velocity_smoother"]["ros__parameters"]["max_velocity"][0] == CRUISE_SPEED


def test_reverse_and_turn_rate_stay_as_they_were():
    out = patch_params(fake_defaults())
    follow = out["controller_server"]["ros__parameters"]["FollowPath"]
    assert (follow["vx_min"], follow["wz_max"]) == (-0.35, 1.9)
    smoother = out["velocity_smoother"]["ros__parameters"]
    assert smoother["max_velocity"][1:] == [0.0, 2.0] and smoother["min_velocity"] == [-0.5, 0.0, -2.0]


def test_other_parameters_are_preserved():
    out = patch_params(fake_defaults())
    assert out["local_costmap"]["local_costmap"]["ros__parameters"]["plugins"] == ["voxel_layer"]


def test_the_mppi_horizon_fits_the_local_costmap_and_the_pruned_path_at_cruise_speed():
    # teto de velocidade = meia janela do costmap local (ou prune_distance) / (time_steps x model_dt): com 56 passos (2,8 s)
    # e janela de 3 m o robô não passava de 0,54 m/s (investigação de 15/11/2026)
    defaults = fake_defaults()
    defaults["controller_server"]["ros__parameters"]["FollowPath"].update({"time_steps": 56, "model_dt": 0.05, "prune_distance": 1.7, "vx_std": 0.2})
    defaults["local_costmap"]["local_costmap"]["ros__parameters"].update({"width": 3, "height": 3})
    out = patch_params(defaults)
    follow = out["controller_server"]["ros__parameters"]["FollowPath"]
    window = out["local_costmap"]["local_costmap"]["ros__parameters"]["width"]
    horizon = follow["time_steps"] * follow["model_dt"]
    assert window / 2 / horizon >= CRUISE_SPEED and follow["prune_distance"] / horizon >= CRUISE_SPEED
    assert (follow["time_steps"], follow["vx_std"]) == (MPPI_TUNING["time_steps"], MPPI_TUNING["vx_std"]) == (28, 0.4)


def test_the_generated_yaml_has_the_mppi_tuning_and_a_horizon_that_fits_the_real_window():
    params = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml").read_text(encoding="utf-8"))
    follow = params["controller_server"]["ros__parameters"]["FollowPath"]
    window = params["local_costmap"]["local_costmap"]["ros__parameters"]["width"]
    assert {k: follow[k] for k in MPPI_TUNING} == MPPI_TUNING
    horizon = follow["time_steps"] * follow["model_dt"]
    assert window / 2 / horizon >= CRUISE_SPEED and follow["prune_distance"] / horizon >= CRUISE_SPEED
