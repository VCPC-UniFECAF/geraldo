from robot.scripts.make_nav2_params import CRUISE_SPEED, FOOTPRINT, INITIAL_POSE, patch_params


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


def test_global_costmap_ignores_lidar_marks_but_the_local_one_keeps_them():
    defaults = fake_defaults()
    defaults["global_costmap"]["global_costmap"]["ros__parameters"]["plugins"] = ["static_layer", "obstacle_layer", "inflation_layer"]
    out = patch_params(defaults)
    assert out["global_costmap"]["global_costmap"]["ros__parameters"]["plugins"] == ["static_layer", "inflation_layer"]
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
