from termforge.doctor import Status, exit_code, run_checks
from termforge.env import powershell_profile_path

ALL_PROGRAMS = {
    "winget": r"C:\winget.exe",
    "pwsh": r"C:\pwsh.exe",
    "oh-my-posh": r"C:\oh-my-posh.exe",
    "git": r"C:\git.exe",
    "wsl": r"C:\wsl.exe",
}


def by_name(results):
    return {r.name: r for r in results}


def fonts_with_nerd(env):
    return ["Segoe UI (TrueType)", "CaskaydiaCove Nerd Font Regular (TrueType)"]


def test_everything_ok(make_env, settings_file):
    env = make_env(ALL_PROGRAMS)
    settings_file(env)
    profile = powershell_profile_path(env)
    profile.parent.mkdir(parents=True)
    profile.write_text("oh-my-posh init pwsh | Invoke-Expression\n", encoding="utf-8")

    results = run_checks(env, fonts=fonts_with_nerd)

    assert all(r.status is Status.OK for r in results), [
        (r.name, r.status.value, r.detail) for r in results if r.status is not Status.OK
    ]
    assert exit_code(results) == 0
    assert "2 perfiles" in by_name(results)["Windows Terminal"].detail


def test_missing_programs_fail_with_hints(make_env):
    env = make_env({})
    results = by_name(run_checks(env, fonts=lambda e: []))

    assert results["PowerShell 7"].status is Status.FAIL
    assert "winget install" in results["PowerShell 7"].hint
    assert results["Oh My Posh"].status is Status.FAIL
    assert results["Windows Terminal"].status is Status.FAIL
    assert results["Git"].status is Status.WARN  # opcional: solo aviso
    assert results["WSL"].status is Status.WARN
    assert exit_code(list(results.values())) == 1


def test_invalid_settings_json_is_a_failure(make_env, settings_file):
    env = make_env(ALL_PROGRAMS)
    settings_file(env, "{esto no es json")

    result = by_name(run_checks(env, fonts=fonts_with_nerd))["Windows Terminal"]

    assert result.status is Status.FAIL
    assert "inválido" in result.detail


def test_no_nerd_font_warns(make_env):
    env = make_env(ALL_PROGRAMS)
    result = by_name(run_checks(env, fonts=lambda e: ["Arial (TrueType)"]))["Nerd Font instalada"]
    assert result.status is Status.WARN


def test_nerd_font_short_names_detected(make_env):
    env = make_env(ALL_PROGRAMS)
    fonts = lambda e: ["JetBrainsMono NFM Regular (TrueType)"]  # noqa: E731
    result = by_name(run_checks(env, fonts=fonts))["Nerd Font instalada"]
    assert result.status is Status.OK


def test_profile_without_oh_my_posh_warns(make_env):
    env = make_env(ALL_PROGRAMS)
    profile = powershell_profile_path(env)
    profile.parent.mkdir(parents=True)
    profile.write_text("Set-Alias ll ls\n", encoding="utf-8")

    result = by_name(run_checks(env, fonts=fonts_with_nerd))["Perfil de PowerShell"]

    assert result.status is Status.WARN
    assert "oh-my-posh init" in result.hint


def test_non_windows_warns_but_does_not_crash(make_env):
    env = make_env({}, system="Linux")
    results = by_name(run_checks(env))

    assert results["Sistema operativo"].status is Status.WARN
    assert results["Nerd Font instalada"].status is Status.WARN
