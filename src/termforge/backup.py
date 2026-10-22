"""Respaldo y restauración de los archivos de configuración de la terminal."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MANIFEST = "manifest.json"
MANIFEST_VERSION = 1


class BackupError(Exception):
    """Error esperado (nada que respaldar, respaldo inexistente, etc.)."""


@dataclass
class BackupEntry:
    name: str
    stored: str
    original: str


@dataclass
class BackupInfo:
    id: str
    path: Path
    created: str
    label: str
    entries: list[BackupEntry]


@dataclass
class RestoreAction:
    name: str
    destination: Path
    overwrites: bool


@dataclass
class RestoreReport:
    backup: BackupInfo
    actions: list[RestoreAction]
    skipped: list[str]
    safety_backup: BackupInfo | None
    dry_run: bool


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40]


def _unique_dir(root: Path, base_id: str) -> tuple[str, Path]:
    candidate, counter = base_id, 1
    while (root / candidate).exists():
        counter += 1
        candidate = f"{base_id}-{counter}"
    return candidate, root / candidate


def create_backup(
    targets: Mapping[str, Path],
    root: Path,
    label: str = "",
    now: datetime | None = None,
) -> BackupInfo:
    """Copia los archivos existentes de `targets` a una carpeta con fecha."""
    existing = {name: path for name, path in targets.items() if path.is_file()}
    if not existing:
        raise BackupError("No hay archivos de configuración para respaldar.")

    now = now or datetime.now()
    base_id = now.strftime("%Y%m%d-%H%M%S")
    if label:
        base_id = f"{base_id}-{_slug(label)}".rstrip("-")

    root.mkdir(parents=True, exist_ok=True)
    backup_id, backup_dir = _unique_dir(root, base_id)
    backup_dir.mkdir()

    entries: list[BackupEntry] = []
    for name, path in existing.items():
        stored = f"{name}{path.suffix}"
        shutil.copy2(path, backup_dir / stored)
        entries.append(BackupEntry(name=name, stored=stored, original=str(path)))

    manifest = {
        "version": MANIFEST_VERSION,
        "id": backup_id,
        "created": now.isoformat(timespec="seconds"),
        "label": label,
        "entries": [e.__dict__ for e in entries],
    }
    (backup_dir / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return BackupInfo(backup_id, backup_dir, manifest["created"], label, entries)


def _load(backup_dir: Path) -> BackupInfo | None:
    manifest_path = backup_dir / MANIFEST
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = [BackupEntry(**e) for e in data["entries"]]
        return BackupInfo(
            id=backup_dir.name,
            path=backup_dir,
            created=data["created"],
            label=data.get("label", ""),
            entries=entries,
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def list_backups(root: Path) -> list[BackupInfo]:
    """Respaldos válidos, del más reciente al más antiguo."""
    if not root.is_dir():
        return []
    found = [info for d in root.iterdir() if d.is_dir() and (info := _load(d))]
    return sorted(found, key=lambda b: b.id, reverse=True)


def get_backup(root: Path, backup_id: str | None = None) -> BackupInfo:
    """Busca un respaldo por id; sin id devuelve el más reciente."""
    if backup_id is None or backup_id == "latest":
        backups = list_backups(root)
        if not backups:
            raise BackupError("No hay respaldos. Crea uno con `termforge backup`.")
        return backups[0]

    # Evita rutas como "../x": el id debe ser un nombre de carpeta simple.
    if Path(backup_id).name != backup_id or backup_id in {".", ".."}:
        raise BackupError(f"Id de respaldo inválido: {backup_id!r}")
    info = _load(root / backup_id)
    if info is None:
        raise BackupError(f"No existe el respaldo {backup_id!r}.")
    return info


def restore_backup(
    root: Path,
    targets: Mapping[str, Path],
    backup_id: str | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> RestoreReport:
    """Restaura un respaldo. Antes de sobrescribir guarda el estado actual."""
    backup = get_backup(root, backup_id)

    actions: list[RestoreAction] = []
    skipped: list[str] = []
    for entry in backup.entries:
        stored = backup.path / entry.stored
        # Solo nombres de archivo simples y destinos conocidos.
        if Path(entry.stored).name != entry.stored or not stored.is_file():
            skipped.append(entry.name)
            continue
        if entry.name not in targets:
            skipped.append(entry.name)
            continue
        destination = targets[entry.name]
        actions.append(RestoreAction(entry.name, destination, destination.exists()))

    if dry_run:
        return RestoreReport(backup, actions, skipped, None, dry_run=True)

    current = {a.name: a.destination for a in actions if a.overwrites}
    safety = create_backup(current, root, label="pre-restore", now=now) if current else None

    entries = {e.name: e for e in backup.entries}
    for action in actions:
        action.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup.path / entries[action.name].stored, action.destination)

    return RestoreReport(backup, actions, skipped, safety, dry_run=False)
