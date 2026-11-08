import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "design-system/DESIGN_SYSTEM.md"
TOKENS = ROOT / "design-system/tokens/tokens.json"

COMPONENTS = [
    "PriorityBadge", "StatusBadge", "StatCard", "RobotStatusCard", "DeliveryQueueRow",
    "StockLevelBar", "MovementLogRow", "AlertBanner", "TelemetryPanel", "RequestForm",
]


def token_hexes() -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", node):
            found.add(node.upper())
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(json.loads(TOKENS.read_text(encoding="utf-8")))
    return found


def test_doc_starts_with_the_nine_golden_rules():
    text = DOC.read_text(encoding="utf-8")
    section = text.split("## Regras de ouro")[1].split("\n## ")[0]
    assert len(re.findall(r"^\d+\. ", section, re.M)) == 9


def test_every_hex_in_the_doc_exists_in_the_tokens():
    text = DOC.read_text(encoding="utf-8")
    hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", text)}
    assert hexes, "o guia deveria citar ao menos as cores principais"
    assert hexes <= token_hexes(), f"cores fora dos tokens: {hexes - token_hexes()}"


def test_doc_points_to_the_sources_of_truth():
    text = DOC.read_text(encoding="utf-8")
    for needle in ("tokens.json", "build.mjs", "tailwind.preset.cjs", "tokens.css", "GeraldoTokens.cs"):
        assert needle in text, needle


def test_doc_lists_every_domain_component():
    text = DOC.read_text(encoding="utf-8")
    missing = [c for c in COMPONENTS if c not in text]
    assert not missing, missing
