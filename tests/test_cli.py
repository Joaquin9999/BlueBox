from typer.testing import CliRunner

from bluebox.cli.app import app


runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "BlueBox CLI" in result.stdout
