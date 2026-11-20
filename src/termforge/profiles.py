"""Agrega Git Bash y los distros de WSL detectados al menú de Windows Terminal.

WSL y PowerShell Core aparecen en el menú "+" de Windows Terminal como perfiles
dinámicos (generados en caliente, sin quedar guardados en `settings.json`), así
que `termforge backup`/`restore` no los cubre y desaparecen si Windows Terminal
cambia cómo los genera. Este módulo agrega una entrada explícita y persistente
para cada uno, solo si todavía no existe.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from termforge import jsonc
from termforge.backup import BackupInfo, create_backup
from termforge.env import Env, terminal_settings_path

_IGNORED_DISTROS = {"docker-desktop", "docker-desktop-data"}


class ProfilesError(Exception):
    """Error esperado: sin settings.json o con un formato inesperado."""


@dataclass
class ProfileCandidate:
    key: str
    name: str
    commandline: str
    already_present: bool


def detect_git_bash(env: Env) -> Path | None:
    """Ruta de `bash.exe` de Git for Windows, derivada de dónde está `git.exe`."""
    git = env.which("git")
    if not git:
        return None
    for ancestor in Path(git).parents:
        candidate = ancestor / "bin" / "bash.exe"
        if candidate.is_file():
            return candidate
    return None


def detect_wsl_distros(env: Env) -> list[str]:
    """Nombres de distros de WSL instaladas (sin las internas de Docker Desktop)."""
    if env.which("wsl") is None:
        return []
    try:
        result = env.run(["wsl", "--list", "--quiet"], capture_output=True)
    except OSError:
        return []
    if result.returncode != 0:
        return []

    raw = result.stdout
    # `wsl.exe` siempre escribe su salida en UTF-16LE en Windows, sin BOM.
    text = raw.decode("utf-16-le", errors="ignore") if isinstance(raw, bytes) else raw
    names = [line.strip() for line in text.splitlines() if line.strip()]
    return [n for n in names if n.lower() not in _IGNORED_DISTROS]


def _existing_commandlines(data: dict) -> list[str]:
    profiles = data.get("profiles")
    profile_list = profiles.get("list", []) if isinstance(profiles, dict) else []
    return [
        p.get("commandline", "").lower()
        for p in profile_list
        if isinstance(p, dict) and p.get("commandline")
    ]


def build_plan(env: Env) -> tuple[dict, list[ProfileCandidate]]:
    """Qué perfiles de Git Bash/WSL faltan en `settings.json` de Windows Terminal."""
    path = terminal_settings_path(env)
    if not path.exists():
        raise ProfilesError("No se encontró settings.json de Windows Terminal.")
    try:
        data = jsonc.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ProfilesError(f"settings.json inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfilesError("settings.json no tiene el formato esperado.")

    existing = _existing_commandlines(data)
    candidates: list[ProfileCandidate] = []

    bash = detect_git_bash(env)
    if bash:
        commandline = f'"{bash}" -i -l'
        # No comparamos la ruta resuelta: el perfil existente puede usar
        # `%PROGRAMFILES%` sin expandir y no calzaría como texto.
        present = any("bash.exe" in cmd for cmd in existing)
        candidates.append(ProfileCandidate("git-bash", "Git Bash", commandline, present))

    for distro in detect_wsl_distros(env):
        commandline = f"wsl.exe -d {distro}"
        present = any(
            cmd.startswith("wsl") and distro.lower() in cmd for cmd in existing
        )
        candidates.append(ProfileCandidate(f"wsl:{distro}", distro, commandline, present))

    return data, candidates


def apply_plan(
    env: Env, data: dict, pending: list[ProfileCandidate], backup_root: Path
) -> BackupInfo:
    """Agrega los perfiles pendientes a `settings.json`, respaldándolo antes."""
    path = terminal_settings_path(env)
    backup_info = create_backup({"windows-terminal": path}, backup_root, label="pre-profiles")

    profiles = data.setdefault("profiles", {})
    profile_list = profiles.setdefault("list", [])
    for candidate in pending:
        profile_list.append(
            {
                "guid": f"{{{uuid.uuid4()}}}",
                "name": candidate.name,
                "commandline": candidate.commandline,
            }
        )

    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return backup_info
