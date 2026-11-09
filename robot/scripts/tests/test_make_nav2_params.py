from robot.scripts.make_nav2_params import FOOTPRINT, INITIAL_POSE, patch_params


def fake_defaults():
    return {
        "amcl": {"ros__parameters": {"set_initial_pose": False, "base_frame_id": "base_footprint"}},
        "local_costmap": {"local_costmap": {"ros__parameters": {"robot_radius": 0.22, "plugins": ["voxel_layer"]}}},
        "global_costmap": {"global_costmap": {"ros__parameters": {"robot_radius": 0.22}}},
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


def test_other_parameters_are_preserved():
    out = patch_params(fake_defaults())
    assert out["local_costmap"]["local_costmap"]["ros__parameters"]["plugins"] == ["voxel_layer"]
