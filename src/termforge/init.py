"""Instalación de dependencias (winget) y configuración de Oh My Posh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from termforge.backup import BackupInfo, create_backup
from termforge.env import Env, powershell_profile_path

OH_MY_POSH_INIT_LINE = "oh-my-posh init pwsh | Invoke-Expression"
_MARKER = "# Agregado por termforge init"

_REQUIRED_PROGRAMS = [
    ("pwsh", "PowerShell 7", "Microsoft.PowerShell"),
    ("oh-my-posh", "Oh My Posh", "JanDeDobbeleer.OhMyPosh"),
]


@dataclass
class InstallStep:
    id: str
    name: str
    package_id: str
    installed: bool
    command: list[str]


@dataclass
class ProfileStep:
    path: Path
    exists: bool
    already_configured: bool


@dataclass
class InitPlan:
    install_steps: list[InstallStep]
    profile: ProfileStep

    @property
    def pending_installs(self) -> list[InstallStep]:
        return [s for s in self.install_steps if not s.installed]

    @property
    def has_pending_work(self) -> bool:
        return bool(self.pending_installs) or not self.profile.already_configured


@dataclass
class InitReport:
    installed: list[InstallStep]
    failed: list[tuple[InstallStep, str]]
    profile_updated: bool
    profile_backup: BackupInfo | None


def _winget_install_command(package_id: str) -> list[str]:
    return [
        "winget",
        "install",
        "--id",
        package_id,
        "-e",
        "--source",
        "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]


def build_plan(env: Env) -> InitPlan:
    """Qué falta instalar y si el perfil de PowerShell ya inicializa Oh My Posh."""
    steps = [
        InstallStep(
            id=cmd,
            name=name,
            package_id=package_id,
            installed=env.which(cmd) is not None,
            command=_winget_install_command(package_id),
        )
        for cmd, name, package_id in _REQUIRED_PROGRAMS
    ]

    path = powershell_profile_path(env)
    exists = path.exists()
    content = path.read_text(encoding="utf-8-sig") if exists else ""
    already_configured = "oh-my-posh" in content.lower()
    profile = ProfileStep(path=path, exists=exists, already_configured=already_configured)

    return InitPlan(install_steps=steps, profile=profile)


def apply_plan(env: Env, plan: InitPlan, backup_root: Path) -> InitReport:
    """Ejecuta los `winget install` pendientes y agrega la inicialización al perfil."""
    installed: list[InstallStep] = []
    failed: list[tuple[InstallStep, str]] = []

    for step in plan.pending_installs:
        try:
            result = env.run(step.command, capture_output=True, text=True)
        except OSError as exc:
            failed.append((step, str(exc)))
            continue
        if result.returncode == 0:
            installed.append(step)
        else:
            fallback = f"código de salida {result.returncode}"
            error = (result.stderr or result.stdout or fallback).strip()
            failed.append((step, error))

    profile_updated = False
    profile_backup = None
    if not plan.profile.already_configured:
        if plan.profile.exists:
            profile_backup = create_backup(
                {"powershell-profile": plan.profile.path}, backup_root, label="pre-init"
            )
        plan.profile.path.parent.mkdir(parents=True, exist_ok=True)
        needs_leading_newline = plan.profile.exists and plan.profile.path.stat().st_size > 0
        with plan.profile.path.open("a", encoding="utf-8") as f:
            if needs_leading_newline:
                f.write("\n")
            f.write(f"{_MARKER}\n{OH_MY_POSH_INIT_LINE}\n")
        profile_updated = True

    return InitReport(
        installed=installed,
        failed=failed,
        profile_updated=profile_updated,
        profile_backup=profile_backup,
    )
