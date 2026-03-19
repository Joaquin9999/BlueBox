from typer.testing import CliRunner

from bluehunt.cli.app import app


runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "BlueHunt CLI" in result.stdout
