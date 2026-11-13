"""Validador mínimo de corpos contra os schemas do docs/contracts/openapi.yaml (sem dependência nova).

Cobre só o que o contrato usa: $ref, nullable, enum, type, format date-time, minimum, maximum, maxItems, required, properties e items.
"""
from datetime import datetime

TYPES = {"string": str, "boolean": bool, "integer": int, "number": (int, float), "object": dict, "array": list}


def validate(value, schema: dict, spec: dict, path: str = "$") -> list[str]:
    """Devolve a lista de violações de `value` contra `schema` (vazia = válido)."""
    if "$ref" in schema:
        node = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node[part]
        return validate(value, node, spec, path)
    if value is None:
        return [] if schema.get("nullable") else [f"{path}: nulo não é permitido"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} fora de {schema['enum']}")
    kind = schema.get("type")
    if kind and (not isinstance(value, TYPES[kind]) or (kind in ("integer", "number") and isinstance(value, bool))):
        return errors + [f"{path}: esperado {kind}, veio {type(value).__name__}"]
    if kind == "string" and schema.get("format") == "date-time":
        try:
            datetime.fromisoformat(value)
        except ValueError:
            errors.append(f"{path}: data/hora inválida: {value!r}")
    if kind in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} menor que {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} maior que {schema['maximum']}")
    if kind == "object":
        errors += [f"{path}: falta {name}" for name in schema.get("required", []) if name not in value]
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                errors += validate(value[name], sub, spec, f"{path}.{name}")
    if kind == "array":
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: {len(value)} itens, no máximo {schema['maxItems']}")
        for index, item in enumerate(value):
            errors += validate(item, schema.get("items", {}), spec, f"{path}[{index}]")
    return errors
