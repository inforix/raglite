from pathlib import Path


def test_spec_marked_approved():
    spec_path = Path("specs/000-raglite-spec.md")
    content = spec_path.read_text(encoding="utf-8")
    assert "Approved" in content

