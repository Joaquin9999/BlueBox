from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "BlueBox CLI" in result.stdout


def test_start_runs() -> None:
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0
    assert "BlueBox Quick Start" in result.stdout


def test_tools_without_subcommand_shows_help() -> None:
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 0
    assert "tools" in result.stdout.lower()


def test_project_show_fails_without_active_project(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["project", "show"])

    assert result.exit_code == 1
    assert "No active project set" in result.stdout


def test_project_set_and_show(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Project Set Demo",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Project Set Demo",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    case_path = tmp_path / "cases" / "project-set-demo"

    set_result = runner.invoke(app, ["project", "set", str(case_path)])
    assert set_result.exit_code == 0
    assert "Set active project" in set_result.stdout

    show_result = runner.invoke(app, ["project", "show"])
    assert show_result.exit_code == 0
    assert "Active project" in show_result.stdout
    assert "project-set-demo" in show_result.stdout


def test_project_list_empty_history(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["project", "list"])

    assert result.exit_code == 0
    assert "No projects in history yet" in result.stdout


def test_project_clear_removes_active_pointer(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Project Clear Demo",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Project Clear Demo",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    clear_result = runner.invoke(app, ["project", "clear"])
    assert clear_result.exit_code == 0
    assert "Cleared active project" in clear_result.stdout

    show_result = runner.invoke(app, ["project", "show"])
    assert show_result.exit_code == 1
    assert "No active project set" in show_result.stdout


def test_project_list_marks_active_project(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Project List Demo",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Project List Demo",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    list_result = runner.invoke(app, ["project", "list"])
    assert list_result.exit_code == 0
    assert "Known projects" in list_result.stdout
    assert "project-list-demo" in list_result.stdout
    assert "active" in list_result.stdout


def test_project_list_existing_only_filters_missing_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Existing Project",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Existing Project",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    missing_case = tmp_path / "missing-case"
    history_file = tmp_path / ".bluebox" / "projects_history.txt"
    history_content = history_file.read_text(encoding="utf-8")
    history_file.write_text(f"{missing_case}\n{history_content}", encoding="utf-8")

    list_result = runner.invoke(app, ["project", "list", "--existing-only"])
    assert list_result.exit_code == 0
    assert "existing-project" in list_result.stdout
    assert "missing-case" not in list_result.stdout


def test_project_list_existing_only_when_none_exist(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    history_file = tmp_path / ".bluebox" / "projects_history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(f"{tmp_path / 'missing-case'}\n", encoding="utf-8")

    result = runner.invoke(app, ["project", "list", "--existing-only"])
    assert result.exit_code == 0
    assert "No existing projects found in history" in result.stdout


def test_project_list_compact_outputs_plain_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Compact Project",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Compact Project",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    result = runner.invoke(app, ["project", "list", "--compact"])
    assert result.exit_code == 0
    assert "Known projects" not in result.stdout
    assert "(active)" not in result.stdout
    assert "compact-project" in result.stdout


def test_project_prune_missing_removes_missing_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifacts_file = tmp_path / "artifact.txt"
    artifacts_file.write_text("abc", encoding="utf-8")

    init_result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Prune Existing",
            "--artifacts",
            str(artifacts_file),
            "--title",
            "Prune Existing",
            "--base-path",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    missing_case = tmp_path / "missing-case"
    history_file = tmp_path / ".bluebox" / "projects_history.txt"
    history_content = history_file.read_text(encoding="utf-8")
    history_file.write_text(f"{missing_case}\n{history_content}", encoding="utf-8")

    prune_result = runner.invoke(app, ["project", "prune-missing"])
    assert prune_result.exit_code == 0
    assert "removed=1" in prune_result.stdout

    list_result = runner.invoke(app, ["project", "list"])
    assert "missing-case" not in list_result.stdout
    assert "prune-existing" in list_result.stdout


