from pathlib import Path

from lineageai.scenarios import build_scenarios, main


def test_scenarios_cover_the_three_demo_flows() -> None:
    names = [scenario.name for scenario in build_scenarios()]

    assert names == ["happy_path", "self_healing", "complex_lineage"]


def test_runner_executes_all_scenarios_and_writes_examples(tmp_path: Path) -> None:
    exit_code = main(["--write-examples", "--examples-root", str(tmp_path)])

    assert exit_code == 0
    for name in ("happy_path", "self_healing", "complex_lineage"):
        directory = tmp_path / name
        assert (directory / "prompt.md").exists()
        assert list(directory.glob("*.sql")), f"missing SQL in {name}"
        assert list(directory.glob("*.yml")), f"missing YAML in {name}"
        assert (directory / "validation.log").exists()

    healing_log = (tmp_path / "self_healing" / "validation.log").read_text()
    assert "attempt 1: failure" in healing_log
    assert "attempt 2: success" in healing_log
