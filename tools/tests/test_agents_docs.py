from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = ["AGENTS.md", "backend/AGENTS.md", "web/AGENTS.md", "robot/AGENTS.md", "security/AGENTS.md", "unity/AGENTS.md"]


def test_agents_files_exist_and_are_not_trivial():
    for rel in AGENTS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert len(text) > 300, rel


def test_root_agents_has_the_hard_rules():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for must in ("Contrato primeiro", "Movimentacao", "Nada na `main`", "segredo", "diga o plano"):
        assert must in text, must


def test_tool_pointers_reference_agents_md():
    for rel in ("CLAUDE.md", ".github/copilot-instructions.md"):
        assert "AGENTS.md" in (ROOT / rel).read_text(encoding="utf-8"), rel


GUIDE = "docs/padroes-de-projeto.md"


def test_patterns_guide_exists_and_names_the_course_patterns():
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    for must in ("SOLID", "Factory Method", "Strategy", "Observer", "Adapter", "Builder", "DIP", "puras"):
        assert must in text or must.lower() in text.lower(), must


def test_every_agents_file_points_to_the_patterns_guide():
    for rel in AGENTS:
        assert "padroes-de-projeto.md" in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_root_agents_has_the_patterns_rule():
    assert "Padrões de projeto" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_pull_request_template_has_the_patterns_checklist():
    text = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert "construtor" in text and "if/elif" in text


def test_robot_agents_describes_the_speed_by_priority_and_the_week_3_pieces():
    text = (ROOT / "robot/AGENTS.md").read_text(encoding="utf-8")
    for piece in ("crítica 1,0 m/s", "média 0,8 m/s", "rotina 0,5 m/s", "BackendEstopPoller", "detect_obstacles", "camera_link",
                  "demo.sh", "measure_speed.py", "Tentativa a 3 m/s"):
        assert piece in text, piece
    for stale in ("3,0 m/s sempre", "só o raio de inflação", "curve_limiter"):
        assert stale not in text, stale
