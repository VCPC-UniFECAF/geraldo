from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = ["AGENTS.md", "backend/AGENTS.md", "web/AGENTS.md", "robot/AGENTS.md", "security/AGENTS.md", "unity/AGENTS.md"]
PROMPTS = [f"docs/prompts/00-inicio-{n}.md" for n in ("samuel", "erik", "vieira", "pedro")]
PLAN_FOR = {
    "samuel": ["semana1-samuel-fundacao", "semana1-samuel-robo"],
    "erik": ["semana1-erik-backend"],
    "vieira": ["semana1-vieira-web"],
    "pedro": ["semana1-pedro-qualidade"],
}


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


def test_prompts_reference_agents_and_their_plans():
    for person, rel in zip(("samuel", "erik", "vieira", "pedro"), PROMPTS):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "AGENTS.md" in text, rel
        for plan in PLAN_FOR[person]:
            assert plan in text, f"{rel} deveria citar {plan}"
            assert (ROOT / f"docs/superpowers/plans/2026-11-05-{plan}.md").is_file(), plan


GUIDE = "docs/padroes-de-projeto.md"


def test_patterns_guide_exists_and_names_the_course_patterns():
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    for must in ("SOLID", "Factory Method", "Strategy", "Observer", "Adapter", "Builder", "DIP", "puras"):
        assert must in text or must.lower() in text.lower(), must


def test_every_agents_file_and_prompt_points_to_the_patterns_guide():
    for rel in AGENTS + PROMPTS:
        assert "padroes-de-projeto.md" in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_root_agents_has_the_patterns_rule():
    assert "Padrões de projeto" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_pull_request_template_has_the_patterns_checklist():
    text = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert "construtor" in text and "if/elif" in text
