from __future__ import annotations

import json
import subprocess

import pytest

from termforge.config import ConfigError, TermforgeConfig, load_config, run_config
from termforge.env import powershell_profile_path, terminal_settings_candidates
from termforge.theme import themes_path


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_valid(tmp_path):
    path = _write(
        tmp_path / "termforge.yaml",
        "init: true\ntheme: dracula\nprofiles: [git-bash, wsl]\n",
    )

    config = load_config(path)

    assert config == TermforgeConfig(init=True, theme="dracula", profiles=["git-bash", "wsl"])


def test_load_config_empty_file_is_empty_config(tmp_path):
    path = _write(tmp_path / "termforge.yaml", "")
    assert load_config(path).is_empty


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "no-existe.yaml")


def test_load_config_invalid_yaml_raises(tmp_path):
    path = _write(tmp_path / "termforge.yaml", "init: [true\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_not_a_mapping_raises(tmp_path):
    path = _write(tmp_path / "termforge.yaml", "- a\n- b\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_unknown_key_raises(tmp_path):
    path = _write(tmp_path / "termforge.yaml", "tema: dracula\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_unknown_profile_kind_raises(tmp_path):
    path = _write(tmp_path / "termforge.yaml", "profiles: [cmd]\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_run_config_installs_missing_programs(make_env, tmp_path):
    env = make_env({}, run=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="ok"))
    config = TermforgeConfig(init=True)

    report = run_config(env, config, tmp_path / "backups")

    assert {s.id for s in report.init_report.installed} == {"pwsh", "oh-my-posh"}
    profile = powershell_profile_path(env).read_text(encoding="utf-8")
    assert "oh-my-posh init pwsh" in profile


def test_run_config_dry_run_changes_nothing(make_env, tmp_path):
    env = make_env({}, run=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="ok"))
    config = TermforgeConfig(init=True)

    run_config(env, config, tmp_path / "backups", dry_run=True)

    assert not powershell_profile_path(env).exists()


def test_run_config_applies_theme_when_available(make_env, tmp_path):
    env = make_env({"oh-my-posh": "o"})
    theme_dir = themes_path(env)
    theme_dir.mkdir(parents=True)
    (theme_dir / "dracula.omp.json").write_text("{}", encoding="utf-8")
    config = TermforgeConfig(theme="dracula")

    report = run_config(env, config, tmp_path / "backups")

    assert report.theme_applied.name == "dracula"
    profile = powershell_profile_path(env).read_text(encoding="utf-8")
    assert "dracula.omp.json" in profile


def test_run_config_theme_without_oh_my_posh_raises(make_env, tmp_path):
    env = make_env({})
    config = TermforgeConfig(theme="dracula")

    with pytest.raises(ConfigError):
        run_config(env, config, tmp_path / "backups")


def test_run_config_theme_dry_run_defers_when_init_pending(make_env, tmp_path):
    env = make_env({})
    config = TermforgeConfig(init=True, theme="dracula")

    report = run_config(env, config, tmp_path / "backups", dry_run=True)

    assert report.theme_pending_install
    assert report.theme_applied is None


def test_run_config_adds_requested_profile_kinds(make_env, tmp_path):
    git_exe = tmp_path / "Git" / "mingw64" / "bin" / "git.exe"
    bash_exe = tmp_path / "Git" / "bin" / "bash.exe"
    bash_exe.parent.mkdir(parents=True)
    bash_exe.write_text("", encoding="utf-8")

    env = make_env(
        {"git": str(git_exe), "wsl": "w"},
        run=lambda cmd, **kw: subprocess.CompletedProcess(
            cmd, 0, stdout=b"Ubuntu\r\n" if cmd[0] == "wsl" else b""
        ),
    )
    settings = terminal_settings_candidates(env)[0]
    _write(settings, '{"profiles": {"list": []}}')

    config = TermforgeConfig(profiles=["git-bash"])
    report = run_config(env, config, tmp_path / "backups")

    assert [c.key for c in report.profiles_status] == ["git-bash"]
    data = json.loads(settings.read_text(encoding="utf-8"))
    names = {p["name"] for p in data["profiles"]["list"]}
    assert names == {"Git Bash"}  # wsl no se pidió, no se agrega


def test_run_config_empty_config_does_nothing(make_env, tmp_path):
    env = make_env({})
    report = run_config(env, TermforgeConfig(), tmp_path / "backups")
    assert report.init_plan is None
    assert report.theme_applied is None
    assert report.profiles_status == []
