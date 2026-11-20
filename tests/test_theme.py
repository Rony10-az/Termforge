from __future__ import annotations

import pytest

from termforge.env import powershell_profile_path
from termforge.theme import ThemeError, apply_theme, find_theme, list_themes, themes_path


def _write_themes(env, names: list[str]) -> None:
    root = themes_path(env)
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / f"{name}.omp.json").write_text("{}", encoding="utf-8")


def test_list_themes_sorted_case_insensitive(make_env):
    env = make_env({})
    _write_themes(env, ["dracula", "atomic", "Catppuccin"])

    themes = list_themes(env)

    assert [t.name for t in themes] == ["atomic", "Catppuccin", "dracula"]


def test_list_themes_empty_when_dir_missing(make_env):
    env = make_env({})
    assert list_themes(env) == []


def test_list_themes_ignores_non_theme_files(make_env):
    env = make_env({})
    root = themes_path(env)
    root.mkdir(parents=True)
    (root / "README.md").write_text("no es un tema", encoding="utf-8")
    _write_themes(env, ["atomic"])

    assert [t.name for t in list_themes(env)] == ["atomic"]


def test_themes_path_honors_env_override(make_env, tmp_path):
    override = tmp_path / "custom-themes"
    env = make_env({})
    env.environ = dict(env.environ, POSH_THEMES_PATH=str(override))

    assert themes_path(env) == override


def test_find_theme_by_number(make_env):
    env = make_env({})
    _write_themes(env, ["atomic", "dracula"])
    themes = list_themes(env)

    assert find_theme(themes, "2").name == "dracula"


def test_find_theme_by_exact_name_case_insensitive(make_env):
    env = make_env({})
    _write_themes(env, ["atomic", "dracula"])
    themes = list_themes(env)

    assert find_theme(themes, "Atomic").name == "atomic"


def test_find_theme_by_unique_prefix(make_env):
    env = make_env({})
    _write_themes(env, ["atomic", "dracula"])
    themes = list_themes(env)

    assert find_theme(themes, "drac").name == "dracula"


def test_find_theme_ambiguous_prefix_raises(make_env):
    env = make_env({})
    _write_themes(env, ["sonicboom_dark", "sonicboom_light"])
    themes = list_themes(env)

    with pytest.raises(ThemeError):
        find_theme(themes, "sonicboom")


def test_find_theme_unknown_name_raises(make_env):
    env = make_env({})
    _write_themes(env, ["atomic"])
    themes = list_themes(env)

    with pytest.raises(ThemeError):
        find_theme(themes, "no-existe")


def test_find_theme_out_of_range_number_raises(make_env):
    env = make_env({})
    _write_themes(env, ["atomic"])
    themes = list_themes(env)

    with pytest.raises(ThemeError):
        find_theme(themes, "5")


def test_apply_theme_creates_profile_without_backup(make_env, tmp_path):
    env = make_env({})
    _write_themes(env, ["atomic"])
    themes = list_themes(env)

    backup_info = apply_theme(env, themes[0], tmp_path / "backups")

    assert backup_info is None
    content = powershell_profile_path(env).read_text(encoding="utf-8")
    assert "atomic.omp.json" in content
    assert content.count("oh-my-posh init pwsh") == 1


def test_apply_theme_replaces_existing_line_and_backs_up(make_env, tmp_path):
    env = make_env({})
    profile = powershell_profile_path(env)
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "Set-Alias ll ls\noh-my-posh init pwsh | Invoke-Expression\n", encoding="utf-8"
    )
    _write_themes(env, ["atomic", "dracula"])
    dracula = find_theme(list_themes(env), "dracula")

    backup_info = apply_theme(env, dracula, tmp_path / "backups")

    content = profile.read_text(encoding="utf-8")
    assert content.count("oh-my-posh init pwsh") == 1
    assert "dracula.omp.json" in content
    assert "Set-Alias ll ls" in content
    assert backup_info is not None
    assert backup_info.label == "pre-theme"
