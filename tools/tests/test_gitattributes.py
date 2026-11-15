from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rules() -> list[str]:
    return (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()


def test_text_files_are_checked_out_with_lf():
    for pattern in ("*.sh", "*.py", "*.mjs", "*.cjs", "*.ts", "*.tsx", "*.json", "*.yaml", "*.yml", "*.md"):
        assert f"{pattern} text eol=lf" in rules(), pattern


def test_images_are_binary():
    assert "*.png binary" in rules()
    assert "*.pgm binary" in rules()
