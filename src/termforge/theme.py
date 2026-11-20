"""Selección y aplicación de temas de Oh My Posh, sin teclear el nombre exacto."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from termforge.backup import BackupInfo, create_backup
from termforge.env import Env, powershell_profile_path

_THEME_SUFFIXES = (".omp.json", ".omp.yaml", ".omp.yml", ".omp.toml")
_INIT_LINE_PREFIX = "oh-my-posh init pwsh"
_MARKER = "# Agregado por termforge theme"


class ThemeError(Exception):
    """Error esperado: sin temas, selección ambigua o inexistente."""


@dataclass
class Theme:
    name: str
    path: Path


def themes_path(env: Env) -> Path:
    """Carpeta de temas de Oh My Posh (variable de entorno, o la ruta por defecto de winget)."""
    override = env.environ.get("POSH_THEMES_PATH")
    if override:
        return Path(override)
    return env.local_appdata / "Programs" / "oh-my-posh" / "themes"


def _theme_name(path: Path) -> str:
    name = path.name
    for suffix in _THEME_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def list_themes(env: Env) -> list[Theme]:
    """Temas disponibles (los que ya trae instalado Oh My Posh), por nombre."""
    root = themes_path(env)
    if not root.is_dir():
        return []
    found = [
        Theme(name=_theme_name(p), path=p)
        for p in root.iterdir()
        if p.is_file() and any(p.name.lower().endswith(s) for s in _THEME_SUFFIXES)
    ]
    return sorted(found, key=lambda t: t.name.lower())


def find_theme(themes: list[Theme], selector: str) -> Theme:
    """Busca por número de la lista (1-based) o por nombre (exacto o prefijo único)."""
    selector = selector.strip()
    if selector.isdigit():
        index = int(selector)
        if 1 <= index <= len(themes):
            return themes[index - 1]
        raise ThemeError(f"No hay un tema con el número {index}.")

    lowered = selector.lower()
    exact = [t for t in themes if t.name.lower() == lowered]
    if exact:
        return exact[0]

    matches = [t for t in themes if t.name.lower().startswith(lowered)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(t.name for t in matches[:5])
        raise ThemeError(f"'{selector}' es ambiguo, coincide con: {names}")
    raise ThemeError(f"No se encontró el tema '{selector}'.")


def build_init_line(theme: Theme) -> str:
    config = str(theme.path).replace("\\", "/")
    return f'oh-my-posh init pwsh --config "{config}" | Invoke-Expression'


def apply_theme(env: Env, theme: Theme, backup_root: Path) -> BackupInfo | None:
    """Escribe la línea de init con el tema elegido en el perfil de PowerShell.

    Reemplaza una línea `oh-my-posh init pwsh ...` existente si la hay; si no,
    la agrega al final. Respalda el perfil antes de tocarlo si ya existía.
    """
    path = powershell_profile_path(env)
    content = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    lines = content.splitlines()

    new_line = build_init_line(theme)
    updated = [
        new_line if line.strip().lower().startswith(_INIT_LINE_PREFIX) else line
        for line in lines
    ]
    if new_line not in updated:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(_MARKER)
        updated.append(new_line)

    backup_info = None
    if path.exists():
        backup_info = create_backup({"powershell-profile": path}, backup_root, label="pre-theme")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return backup_info
