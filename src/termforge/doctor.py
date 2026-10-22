"""Diagnóstico del entorno de terminal."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum

from termforge import jsonc
from termforge.env import Env, powershell_profile_path, terminal_settings_path


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str
    hint: str = ""

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


_NERD_FONT = re.compile(r"nerd font|\bNF[MP]?\b", re.IGNORECASE)


def installed_fonts(env: Env) -> list[str] | None:
    """Nombres de fuentes instaladas (registro de Windows). None si no se puede leer."""
    if not env.is_windows:
        return None
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return None

    names: list[str] = []
    locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    ]
    for root, subkey in locations:
        try:
            with winreg.OpenKey(root, subkey) as key:
                count = winreg.QueryInfoKey(key)[1]
                names.extend(winreg.EnumValue(key, i)[0] for i in range(count))
        except OSError:
            continue
    return names


def _program(env: Env, name: str, label: str, hint: str, status_if_missing: Status) -> CheckResult:
    path = env.which(name)
    if path:
        return CheckResult(label, Status.OK, path)
    return CheckResult(label, status_if_missing, "no encontrado", hint)


def _check_os(env: Env) -> CheckResult:
    if env.is_windows:
        return CheckResult("Sistema operativo", Status.OK, "Windows")
    return CheckResult(
        "Sistema operativo",
        Status.WARN,
        f"{env.system or 'desconocido'}: termforge está pensado para Windows",
        "Ejecútalo en Windows para un diagnóstico completo",
    )


def _check_terminal_settings(env: Env) -> list[CheckResult]:
    path = terminal_settings_path(env)
    install_hint = "winget install --id Microsoft.WindowsTerminal"
    if not path.exists():
        missing = "settings.json no encontrado"
        return [CheckResult("Windows Terminal", Status.FAIL, missing, install_hint)]

    try:
        data = jsonc.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return [
            CheckResult(
                "Windows Terminal",
                Status.FAIL,
                f"settings.json inválido: {exc}",
                "Restaura un respaldo con `termforge restore` o corrige el JSON",
            )
        ]

    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    profile_list = profiles.get("list", []) if isinstance(profiles, dict) else []
    results = [
        CheckResult("Windows Terminal", Status.OK, f"{len(profile_list)} perfiles en {path}")
    ]

    defaults = profiles.get("defaults", {}) if isinstance(profiles, dict) else {}
    font = defaults.get("font", {}) if isinstance(defaults, dict) else {}
    face = font.get("face") if isinstance(font, dict) else None
    face = face or (defaults.get("fontFace") if isinstance(defaults, dict) else None)
    if face:
        results.append(CheckResult("Fuente del terminal", Status.OK, str(face)))
    else:
        results.append(
            CheckResult(
                "Fuente del terminal",
                Status.WARN,
                "sin fuente definida en profiles.defaults",
                "Define una Nerd Font para ver iconos y ligaduras",
            )
        )
    return results


def _check_nerd_font(env: Env, fonts: Callable[[Env], list[str] | None]) -> CheckResult:
    names = fonts(env)
    hint = "oh-my-posh font install"
    if names is None:
        return CheckResult("Nerd Font instalada", Status.WARN, "no se pudo verificar", hint)
    matches = sorted({n for n in names if _NERD_FONT.search(n)})
    if matches:
        return CheckResult("Nerd Font instalada", Status.OK, matches[0])
    return CheckResult("Nerd Font instalada", Status.WARN, "ninguna detectada", hint)


def _check_profile(env: Env) -> CheckResult:
    path = powershell_profile_path(env)
    if not path.exists():
        return CheckResult(
            "Perfil de PowerShell",
            Status.WARN,
            "no existe",
            "Se creará al configurar Oh My Posh",
        )
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return CheckResult("Perfil de PowerShell", Status.FAIL, f"no se pudo leer: {exc}")
    if "oh-my-posh" in content.lower():
        return CheckResult("Perfil de PowerShell", Status.OK, f"inicializa Oh My Posh ({path})")
    return CheckResult(
        "Perfil de PowerShell",
        Status.WARN,
        "existe pero no inicializa Oh My Posh",
        "Agrega: oh-my-posh init pwsh | Invoke-Expression",
    )


def run_checks(
    env: Env,
    fonts: Callable[[Env], list[str] | None] = installed_fonts,
) -> list[CheckResult]:
    results: list[CheckResult] = [_check_os(env)]
    results.append(
        _program(
            env,
            "winget",
            "winget",
            "Instala 'App Installer' desde Microsoft Store",
            Status.WARN,
        )
    )
    results.append(
        _program(
            env,
            "pwsh",
            "PowerShell 7",
            "winget install --id Microsoft.PowerShell",
            Status.FAIL,
        )
    )
    results.extend(_check_terminal_settings(env))
    results.append(
        _program(
            env,
            "oh-my-posh",
            "Oh My Posh",
            "winget install JanDeDobbeleer.OhMyPosh -s winget",
            Status.FAIL,
        )
    )
    results.append(_check_nerd_font(env, fonts))
    results.append(_check_profile(env))
    results.append(_program(env, "git", "Git", "winget install --id Git.Git", Status.WARN))
    results.append(_program(env, "wsl", "WSL", "wsl --install", Status.WARN))
    return results


def exit_code(results: list[CheckResult]) -> int:
    """1 si hay algún fallo; las advertencias no cuentan como error."""
    return 1 if any(r.status is Status.FAIL for r in results) else 0
