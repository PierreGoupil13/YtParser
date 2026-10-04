from typer.testing import CliRunner

from ytparser.cli import app

runner = CliRunner()


def test_hello() -> None:
    result = runner.invoke(app, ["hello"])

    assert result.exit_code == 0
    assert result.output == "Hello from YtParser!\n"


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "hello" in result.output


def test_unknown_command() -> None:
    result = runner.invoke(app, ["unknown"])

    assert result.exit_code != 0
    assert "No such command" in result.output
