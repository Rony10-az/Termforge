import json

import pytest
from typer.testing import CliRunner

from termforge import __version__, cli

runner = CliRunner()

PROGRAMS = {
    "winget": "w",
    "pwsh": "p",
    "oh-my-posh": "o",
    "git": "g",
    "wsl": "s",
}


@pytest.fixture
def use_env(monkeypatch, make_env):
    def _use(programs=None, run=None):
        env = make_env(PROGRAMS if programs is None else programs, run=run)
        monkeypatch.setattr(cli, "get_env", lambda: env)
        return env

    return _use


def test_version():
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help():
    result = runner.invoke(cli.app, [])
    assert "doctor" in result.output and "backup" in result.output


def test_doctor_json_reports_failures(use_env):
    use_env({})  # sin programas instalados

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    statuses = {item["name"]: item["status"] for item in data}
    assert statuses["PowerShell 7"] == "fail"


def test_doctor_table_output(use_env, settings_file):
    env = use_env()
    settings_file(env)

    result = runner.invoke(cli.app, ["doctor"])

    assert "PowerShell 7" in result.output
    assert "Fallos:" in result.output


def test_backup_without_files_fails(use_env):
    use_env()
    result = runner.invoke(cli.app, ["backup"])
    assert result.exit_code == 1


def test_backup_list_restore_flow(use_env, settings_file):
    env = use_env()
    path = settings_file(env, '{"a": 1}')

    created = runner.invoke(cli.app, ["backup", "--label", "inicial"])
    assert created.exit_code == 0, created.output
    assert "Respaldo creado" in created.output

    listed = runner.invoke(cli.app, ["backups"])
    assert "inicial" in listed.output

    path.write_text('{"a": 2}', encoding="utf-8")

    dry = runner.invoke(cli.app, ["restore", "--dry-run"])
    assert dry.exit_code == 0
    assert path.read_text(encoding="utf-8") == '{"a": 2}'

    declined = runner.invoke(cli.app, ["restore"], input="n\n")
    assert declined.exit_code == 1
    assert path.read_text(encoding="utf-8") == '{"a": 2}'

    restored = runner.invoke(cli.app, ["restore", "--yes"])
    assert restored.exit_code == 0, restored.output
    assert path.read_text(encoding="utf-8") == '{"a": 1}'
    assert "pre-restore" in runner.invoke(cli.app, ["backups"]).output


def test_restore_without_backups_fails(use_env):
    use_env()
    result = runner.invoke(cli.app, ["restore", "--yes"])
    assert result.exit_code == 1


def test_init_dry_run_changes_nothing(use_env):
    env = use_env({})
    result = runner.invoke(cli.app, ["init", "--dry-run"])
    assert result.exit_code == 0
    assert "Se instalará con winget" in result.output
    assert not env.home.joinpath(
        "Documents", "PowerShell", "Microsoft.PowerShell_profile.ps1"
    ).exists()


def test_init_installs_and_configures_profile(use_env):
    import subprocess

    use_env({}, run=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="ok"))

    result = runner.invoke(cli.app, ["init", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Instalado: PowerShell 7" in result.output
    assert "Perfil actualizado" in result.output


def test_init_nothing_pending(use_env):
    env = use_env({"pwsh": "p", "oh-my-posh": "o"})
    profile_dir = env.home / "Documents" / "PowerShell"
    profile_dir.mkdir(parents=True)
    (profile_dir / "Microsoft.PowerShell_profile.ps1").write_text(
        "oh-my-posh init pwsh | Invoke-Expression\n", encoding="utf-8"
    )

    result = runner.invoke(cli.app, ["init"])

    assert result.exit_code == 0
    assert "Todo ya está instalado y configurado" in result.output
