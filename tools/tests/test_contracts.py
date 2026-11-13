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
