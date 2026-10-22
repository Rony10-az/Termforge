from __future__ import annotations

from pathlib import Path

import pytest

from termforge.env import Env

SETTINGS_JSONC = """\
{
    // Comentario típico de Windows Terminal
    "defaultProfile": "{guid}",
    "profiles": {
        "defaults": {
            "font": { "face": "CaskaydiaCove Nerd Font" }, // fuente
        },
        "list": [
            { "name": "PowerShell", }, /* bloque */
            { "name": "Git Bash" },
        ],
    },
}
"""


@pytest.fixture
def make_env(tmp_path: Path):
    """Crea un Env de Windows simulado dentro de tmp_path."""

    def _make(programs: dict[str, str] | None = None, system: str = "Windows", run=None) -> Env:
        home = tmp_path / "home"
        local = home / "AppData" / "Local"
        local.mkdir(parents=True, exist_ok=True)
        found = programs or {}
        kwargs = {} if run is None else {"run": run}
        return Env(
            system=system,
            environ={"LOCALAPPDATA": str(local), "TERMFORGE_HOME": str(tmp_path / "tf")},
            home=home,
            which=lambda name: found.get(name),
            **kwargs,
        )

    return _make


@pytest.fixture
def settings_file(make_env):
    """Escribe un settings.json de Windows Terminal (con comentarios) y devuelve su ruta."""

    def _write(env: Env, content: str = SETTINGS_JSONC) -> Path:
        from termforge.env import terminal_settings_candidates

        path = terminal_settings_candidates(env)[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write
