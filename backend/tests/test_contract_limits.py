"""Os limites de entrada do contrato (minimum, maximum, maxItems...) são os mesmos do código, campo a campo.

Contract-first: se o código recusa (422) algo que o contrato permite, o robô e o painel quebram sem aviso.
"""
from pathlib import Path

import pytest
import yaml

from app.main import app

SPEC = yaml.safe_load((Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
LIMITS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems")
# schema do contrato -> schema de entrada no código
PAIRS = {"Telemetry": "TelemetryIn", "LoginRequest": "LoginRequest", "DeliveryCreate": "DeliveryCreate"}


def flatten(node: dict, schemas: dict, path: str = "") -> dict[str, dict]:
    """caminho do campo -> seus limites, seguindo $ref, properties e items."""
    if "$ref" in node:
        return flatten(schemas[node["$ref"].rsplit("/", 1)[1]], schemas, path)
    for branch in node.get("anyOf", []):  # campo opcional: o pydantic escreve anyOf [tipo, null]
        if branch.get("type") != "null":
            return flatten(branch, schemas, path)
    limits = {k: node[k] for k in LIMITS if k in node}
    if node.get("type") == "integer" and "exclusiveMinimum" in limits:  # gt=0 e minimum: 1 são o mesmo limite
        limits["minimum"] = limits.pop("exclusiveMinimum") + 1
    found = {path: limits}
    for name, child in node.get("properties", {}).items():
        found |= flatten(child, schemas, f"{path}.{name}")
    if "items" in node:
        found |= flatten(node["items"], schemas, f"{path}[]")
    return found


@pytest.mark.parametrize("contract_name, code_name", PAIRS.items())
def test_input_limits_in_the_contract_match_the_code(contract_name, code_name):
    contract = flatten(SPEC["components"]["schemas"][contract_name], SPEC["components"]["schemas"])
    code = flatten(app.openapi()["components"]["schemas"][code_name], app.openapi()["components"]["schemas"])
    for field in contract.keys() | code.keys():
        assert contract.get(field, {}) == code.get(field, {}), f"{contract_name}{field}: contrato {contract.get(field)} x código {code.get(field)}"
