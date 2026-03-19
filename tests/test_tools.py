from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def test_tools_list_outputs_profiles() -> None:
    result = runner.invoke(app, ["tools", "list"])

    assert result.exit_code == 0
    assert "base" in result.stdout
    assert "network" in result.stdout or "pcap" in result.stdout


def test_tools_check_unknown_profile_fails() -> None:
    result = runner.invoke(app, ["tools", "check", "unknown-profile"])

    assert result.exit_code == 1
    assert "Unknown profile" in result.stdout


def test_tools_install_unknown_profile_fails() -> None:
    result = runner.invoke(app, ["tools", "install", "unknown-profile"])

    assert result.exit_code == 1
    assert "Unknown profile" in result.stdout


def test_tools_install_dry_run_base_profile() -> None:
    result = runner.invoke(app, ["tools", "install", "base"])

    assert result.exit_code in {0, 1}
    assert "base" not in result.stdout  # command outputs per-tool lines only
    assert "command:" in result.stdout or "already available" in result.stdout


def test_setup_all_dry_run_runs() -> None:
    result = runner.invoke(app, ["setup", "--mode", "all"])

    assert result.exit_code in {0, 1}
    assert "Setup mode" in result.stdout


def test_setup_unknown_tool_fails() -> None:
    result = runner.invoke(app, ["setup", "--mode", "tool", "--tool", "nonexistent-tool"])

    assert result.exit_code == 1
    assert "Unknown tool" in result.stdout
