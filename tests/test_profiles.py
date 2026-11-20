from __future__ import annotations

import json
import subprocess

import pytest

from termforge.env import terminal_settings_candidates
from termforge.profiles import (
    ProfilesError,
    apply_plan,
    build_plan,
    detect_git_bash,
    detect_wsl_distros,
)


def _write_git_bash(tmp_path):
    git_exe = tmp_path / "Tools" / "Git" / "mingw64" / "bin" / "git.exe"
    bash_exe = tmp_path / "Tools" / "Git" / "bin" / "bash.exe"
    bash_exe.parent.mkdir(parents=True)
    bash_exe.write_text("", encoding="utf-8")
    return git_exe, bash_exe


def _wsl_run(stdout_text: str, returncode: int = 0):
    def _run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout_text.encode("utf-16-le"))

    return _run


def _write_settings(env, profiles_list):
    path = terminal_settings_candidates(env)[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"profiles": {"list": profiles_list}}), encoding="utf-8")
    return path


def test_detect_git_bash_walks_up_from_git_exe(make_env, tmp_path):
    git_exe, bash_exe = _write_git_bash(tmp_path)
    env = make_env({"git": str(git_exe)})

    assert detect_git_bash(env) == bash_exe


def test_detect_git_bash_none_when_bash_missing(make_env, tmp_path):
    env = make_env({"git": str(tmp_path / "Tools" / "Git" / "mingw64" / "bin" / "git.exe")})
    assert detect_git_bash(env) is None


def test_detect_git_bash_none_without_git(make_env):
    env = make_env({})
    assert detect_git_bash(env) is None


def test_detect_wsl_distros_decodes_utf16_and_filters_docker(make_env):
    env = make_env(
        {"wsl": "w"}, run=_wsl_run("Ubuntu\r\ndocker-desktop\r\ndocker-desktop-data\r\n")
    )
    assert detect_wsl_distros(env) == ["Ubuntu"]


def test_detect_wsl_distros_empty_without_wsl_binary(make_env):
    env = make_env({})
    assert detect_wsl_distros(env) == []


def test_detect_wsl_distros_empty_on_failure(make_env):
    env = make_env({"wsl": "w"}, run=_wsl_run("", returncode=1))
    assert detect_wsl_distros(env) == []


def test_build_plan_without_settings_raises(make_env):
    env = make_env({})
    with pytest.raises(ProfilesError):
        build_plan(env)


def test_build_plan_flags_missing_git_bash_and_wsl(make_env, tmp_path):
    git_exe, bash_exe = _write_git_bash(tmp_path)
    env = make_env({"git": str(git_exe), "wsl": "w"}, run=_wsl_run("Ubuntu\r\n"))
    _write_settings(env, [{"name": "PowerShell", "commandline": "pwsh.exe"}])

    _, candidates = build_plan(env)

    by_key = {c.key: c for c in candidates}
    assert not by_key["git-bash"].already_present
    assert not by_key["wsl:Ubuntu"].already_present


def test_build_plan_detects_already_present_entries(make_env, tmp_path):
    git_exe, bash_exe = _write_git_bash(tmp_path)
    env = make_env({"git": str(git_exe), "wsl": "w"}, run=_wsl_run("Ubuntu\r\n"))
    _write_settings(
        env,
        [
            {"name": "Git Bash", "commandline": f'"{bash_exe}" -i -l'},
            {"name": "Ubuntu", "commandline": "wsl.exe -d Ubuntu"},
        ],
    )

    _, candidates = build_plan(env)

    assert all(c.already_present for c in candidates)


def test_apply_plan_appends_profiles_and_backs_up(make_env, tmp_path):
    git_exe, bash_exe = _write_git_bash(tmp_path)
    env = make_env({"git": str(git_exe), "wsl": "w"}, run=_wsl_run("Ubuntu\r\n"))
    path = _write_settings(env, [{"name": "PowerShell", "commandline": "pwsh.exe"}])

    data, candidates = build_plan(env)
    pending = [c for c in candidates if not c.already_present]
    backup_info = apply_plan(env, data, pending, tmp_path / "backups")

    assert backup_info.label == "pre-profiles"
    written = json.loads(path.read_text(encoding="utf-8"))
    names = {p["name"] for p in written["profiles"]["list"]}
    assert names == {"PowerShell", "Git Bash", "Ubuntu"}
    assert all("guid" in p for p in written["profiles"]["list"][1:])
