"""Entorno de ejecución y rutas conocidas.

Todo lo que depende del sistema (SO, variables, home, búsqueda de programas)
vive en `Env`, para poder simularlo en los tests sin tocar tu PC.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Env:
    system: str = field(default_factory=platform.system)
    environ: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    home: Path = field(default_factory=Path.home)
    which: Callable[[str], str | None] = shutil.which
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run

    @property
    def is_windows(self) -> bool:
        return self.system == "Windows"

    @property
    def local_appdata(self) -> Path:
        value = self.environ.get("LOCALAPPDATA")
        return Path(value) if value else self.home / "AppData" / "Local"


def _first_existing(candidates: list[Path]) -> Path:
    """Devuelve el primer candidato que exista; si ninguno, el primero."""
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def terminal_settings_candidates(env: Env) -> list[Path]:
    local = env.local_appdata
    return [
        # Windows Terminal instalado desde Microsoft Store / winget
        local
        / "Packages"
        / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
        / "LocalState"
        / "settings.json",
        # Windows Terminal Preview
        local
        / "Packages"
        / "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe"
        / "LocalState"
        / "settings.json",
        # Instalación sin empaquetar (portable)
        local / "Microsoft" / "Windows Terminal" / "settings.json",
    ]


def terminal_settings_path(env: Env) -> Path:
    return _first_existing(terminal_settings_candidates(env))


def powershell_profile_candidates(env: Env) -> list[Path]:
    name = Path("PowerShell") / "Microsoft.PowerShell_profile.ps1"
    return [
        env.home / "Documents" / name,
        # Si OneDrive redirige la carpeta Documentos
        env.home / "OneDrive" / "Documents" / name,
    ]


def powershell_profile_path(env: Env) -> Path:
    return _first_existing(powershell_profile_candidates(env))


def managed_files(env: Env) -> dict[str, Path]:
    """Archivos que termforge respalda y restaura, por nombre estable."""
    return {
        "windows-terminal": terminal_settings_path(env),
        "powershell-profile": powershell_profile_path(env),
    }


def backup_root(env: Env) -> Path:
    override = env.environ.get("TERMFORGE_HOME")
    if override:
        return Path(override) / "backups"
    if env.is_windows:
        return env.local_appdata / "termforge" / "backups"
    data_home = env.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else env.home / ".local" / "share"
    return base / "termforge" / "backups"
