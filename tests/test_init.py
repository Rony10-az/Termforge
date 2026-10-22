from __future__ import annotations

import subprocess

from termforge.env import powershell_profile_path
from termforge.init import OH_MY_POSH_INIT_LINE, apply_plan, build_plan


def _run_ok(cmd, **kwargs):
    return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")


def _run_fail(cmd, **kwargs):
    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no se encontró el paquete")


def test_plan_flags_missing_programs_and_profile(make_env):
    env = make_env({})

    plan = build_plan(env)

    assert plan.has_pending_work
    pending_ids = {s.id for s in plan.pending_installs}
    assert pending_ids == {"pwsh", "oh-my-posh"}
    assert not plan.profile.already_configured
    assert not plan.profile.exists


def test_plan_is_empty_when_everything_is_ready(make_env):
    env = make_env({"pwsh": "p", "oh-my-posh": "o"})
    profile = powershell_profile_path(env)
    profile.parent.mkdir(parents=True)
    profile.write_text(f"{OH_MY_POSH_INIT_LINE}\n", encoding="utf-8")

    plan = build_plan(env)

    assert not plan.has_pending_work
    assert plan.pending_installs == []


def test_apply_installs_missing_programs_and_writes_profile(make_env, tmp_path):
    env = make_env({}, run=_run_ok)
    plan = build_plan(env)

    report = apply_plan(env, plan, tmp_path / "backups")

    assert {s.id for s in report.installed} == {"pwsh", "oh-my-posh"}
    assert report.failed == []
    assert report.profile_updated
    assert report.profile_backup is None  # no existía, nada que respaldar

    profile = powershell_profile_path(env)
    assert OH_MY_POSH_INIT_LINE in profile.read_text(encoding="utf-8")


def test_apply_backs_up_existing_profile_before_appending(make_env, tmp_path):
    env = make_env({"pwsh": "p", "oh-my-posh": "o"})
    profile = powershell_profile_path(env)
    profile.parent.mkdir(parents=True)
    profile.write_text("Set-Alias ll ls", encoding="utf-8")

    plan = build_plan(env)
    report = apply_plan(env, plan, tmp_path / "backups")

    assert report.profile_backup is not None
    content = profile.read_text(encoding="utf-8")
    assert content.startswith("Set-Alias ll ls\n")
    assert OH_MY_POSH_INIT_LINE in content


def test_apply_records_failed_installs(make_env, tmp_path):
    env = make_env({}, run=_run_fail)
    plan = build_plan(env)

    report = apply_plan(env, plan, tmp_path / "backups")

    assert report.installed == []
    failed_ids = {s.id for s, _ in report.failed}
    assert failed_ids == {"pwsh", "oh-my-posh"}
    assert all("no se encontró" in error for _, error in report.failed)


def test_apply_skips_already_installed_programs(make_env, tmp_path):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    env = make_env({"pwsh": "p"}, run=run)
    plan = build_plan(env)

    apply_plan(env, plan, tmp_path / "backups")

    assert len(calls) == 1
    assert "JanDeDobbeleer.OhMyPosh" in calls[0]
