from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/contracts/openapi.yaml"

EXPECTED_OPERATIONS = {
    ("post", "/auth/login"),
    ("get", "/me"),
    ("get", "/locations"),
    ("get", "/stock"),
    ("post", "/deliveries"),
    ("get", "/deliveries"),
    ("get", "/deliveries/{id}"),
    ("post", "/deliveries/{id}/cancel"),
    ("post", "/deliveries/{id}/approve"),
    ("post", "/deliveries/{id}/confirm-receipt"),
    ("get", "/movements"),
    ("post", "/robot/next-task"),
    ("post", "/robot/events"),
    ("post", "/robot/telemetry"),
    ("post", "/robot/estop"),
    ("get", "/robot/estop"),
    ("get", "/telemetry"),
}


def load():
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def test_all_contract_operations_are_declared():
    paths = load()["paths"]
    declared = {(m, p) for p, ops in paths.items() for m in ops if m in {"get", "post", "put", "delete"}}
    assert declared == EXPECTED_OPERATIONS


def test_priority_enum_matches_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["Priority"]["enum"] == ["critica", "media", "rotina"]


def test_delivery_status_enum_matches_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["DeliveryStatus"]["enum"] == [
        "PENDENTE_APROVACAO",
        "NA_FILA",
        "EM_ROTA",
        "AGUARDANDO_RECEBIMENTO",
        "ENTREGUE",
        "CANCELADA",
        "FALHOU",
    ]


def test_movement_types_match_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["MovementType"]["enum"] == ["RESERVA", "BAIXA", "CREDITO", "ESTORNO"]


def test_roles_match_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["Role"]["enum"] == ["medico", "enfermeiro", "farmaceutico", "admin", "robo"]


def test_login_is_the_only_public_operation():
    paths = load()["paths"]
    public = [p for p, ops in paths.items() for op in ops.values() if isinstance(op, dict) and op.get("security") == []]
    assert public == ["/auth/login"]


def test_ros_and_jwt_docs_exist():
    for name in ("ros-interfaces.md", "jwt.md"):
        assert (ROOT / "docs/contracts" / name).stat().st_size > 500, name


def test_the_robot_may_read_a_delivery_to_wait_for_the_receipt():
    operation = load()["paths"]["/deliveries/{id}"]["get"]
    assert "robo" in operation["description"] and "somente leitura" in operation["description"]


def test_estop_is_set_by_the_panel_and_read_by_the_robot():
    spec = load()
    path = spec["paths"]["/robot/estop"]
    assert "admin" in path["post"]["description"] and "farmaceutico" in path["post"]["description"]
    assert "robo" in path["get"]["description"]
    assert set(path["post"]["responses"]) == {"204", "401", "403", "422"}
    assert set(path["get"]["responses"]) == {"200", "401", "403"}
    state = {"$ref": "#/components/schemas/EstopState"}
    assert path["post"]["requestBody"]["content"]["application/json"]["schema"] == state
    assert path["get"]["responses"]["200"]["content"]["application/json"]["schema"] == state
    schema = spec["components"]["schemas"]["EstopState"]
    assert schema["required"] == ["active"] and schema["properties"]["active"]["type"] == "boolean"


def test_telemetry_obstacles_are_at_most_20_circles():
    obstacles = load()["components"]["schemas"]["Telemetry"]["properties"]["obstacles"]
    assert obstacles["maxItems"] == 20
    assert obstacles["items"]["required"] == ["x", "y", "radius"]


def test_ros_interfaces_says_who_reads_the_estop_and_what_the_bridge_may_touch():
    text = (ROOT / "docs/contracts/ros-interfaces.md").read_text(encoding="utf-8")
    assert "GET /robot/estop" in text
    bridge = next(line for line in text.splitlines() if line.startswith("- `geraldo_bridge`"))
    for topic in ("/geraldo/estop", "/geraldo/state", "/geraldo/battery", "/amcl_pose", "/plan", "/scan", "/range/*"):
        assert topic in bridge, topic
    for topic in ("/camera/color/image_raw", "/camera/depth/image_raw", "/speed_limit"):
        assert topic in text, topic


def test_robot_protocol_fixes_the_estop_cadence_the_join_rule_and_the_obstacles_format():
    text = (ROOT / "docs/contracts/robot-protocol.md").read_text(encoding="utf-8")
    assert "`GET /robot/estop` a cada 1 s" in text
    assert "só sai da parada com as duas fontes desligadas" in text
    assert "até 20 itens `{x, y, radius}`" in text
    assert "sempre `[]`" not in text
