"""Configuración declarativa: describe el estado deseado de tu terminal en un YAML.

En vez de correr `init`, `theme` y `profiles` por separado, un archivo
`termforge.yaml` describe el resultado que quieres y `termforge apply` lo deja
así. Es complementario, igual que el resto de `termforge`: solo instala o
agrega lo que falte, nunca borra ni degrada algo que ya tenías.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from termforge.env import Env
from termforge.init import InitPlan, InitReport
from termforge.init import apply_plan as apply_init_plan
from termforge.init import build_plan as build_init_plan
from termforge.profiles import ProfileCandidate, ProfilesError
from termforge.profiles import apply_plan as apply_profiles_plan
from termforge.profiles import build_plan as build_profiles_plan
from termforge.theme import Theme, ThemeError, apply_theme, find_theme, list_themes

_KNOWN_KEYS = {"init", "theme", "profiles"}
_KNOWN_PROFILE_KINDS = {"git-bash", "wsl"}


class ConfigError(Exception):
    """Error esperado: YAML inválido, con campos desconocidos, o nada que aplicar."""


@dataclass
class TermforgeConfig:
    init: bool = False
    theme: str | None = None
    profiles: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.init and self.theme is None and not self.profiles


def load_config(path: Path) -> TermforgeConfig:
    """Lee y valida un archivo de configuración declarativa."""
    if not path.is_file():
        raise ConfigError(f"No se encontró el archivo de configuración: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML inválido en {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} debe describir un mapa (init, theme, profiles).")

    unknown = set(raw) - _KNOWN_KEYS
    if unknown:
        raise ConfigError(f"Clave(s) desconocida(s) en {path}: {', '.join(sorted(unknown))}")

    init_flag = raw.get("init", False)
    if not isinstance(init_flag, bool):
        raise ConfigError("'init' debe ser true o false.")

    theme = raw.get("theme")
    if theme is not None and not isinstance(theme, str):
        raise ConfigError("'theme' debe ser el nombre de un tema (texto).")

    profiles = raw.get("profiles", [])
    if not isinstance(profiles, list) or not all(isinstance(p, str) for p in profiles):
        raise ConfigError("'profiles' debe ser una lista de nombres (git-bash, wsl).")
    unknown_profiles = set(profiles) - _KNOWN_PROFILE_KINDS
    if unknown_profiles:
        valid = ", ".join(sorted(_KNOWN_PROFILE_KINDS))
        raise ConfigError(
            f"profiles desconocido(s): {', '.join(sorted(unknown_profiles))} (válidos: {valid})"
        )

    return TermforgeConfig(init=init_flag, theme=theme, profiles=profiles)


@dataclass
class ConfigReport:
    init_plan: InitPlan | None = None
    init_report: InitReport | None = None
    theme_applied: Theme | None = None
    theme_pending_install: bool = False
    profiles_status: list[ProfileCandidate] = field(default_factory=list)


def run_config(
    env: Env, config: TermforgeConfig, backup_root: Path, dry_run: bool = False
) -> ConfigReport:
    """Aplica (o, en `dry_run`, solo describe) el estado deseado en `config`.

    `init` se ejecuta antes de resolver `theme` a propósito: en una PC nueva,
    así `init` ya instaló Oh My Posh (y sus temas) para cuando se busca el
    tema pedido. En `--dry-run` nada se instala de verdad, así que si el tema
    todavía no se puede resolver pero `init` lo dejaría listo, se avisa en vez
    de fallar.
    """
    init_plan = build_init_plan(env) if config.init else None
    if init_plan and not dry_run and init_plan.has_pending_work:
        init_report = apply_init_plan(env, init_plan, backup_root)
    else:
        init_report = None

    theme_applied: Theme | None = None
    theme_pending_install = False
    if config.theme:
        themes = list_themes(env)
        if themes:
            try:
                theme_applied = find_theme(themes, config.theme)
            except ThemeError as exc:
                raise ConfigError(str(exc)) from exc
            if not dry_run:
                apply_theme(env, theme_applied, backup_root)
        elif dry_run and config.init:
            theme_pending_install = True
        else:
            raise ConfigError(
                f"No se encontraron temas de Oh My Posh instalados para aplicar '{config.theme}'. "
                "Agrega `init: true` a la configuración, o corre `termforge init` primero."
            )

    profiles_status: list[ProfileCandidate] = []
    if config.profiles:
        try:
            data, all_candidates = build_profiles_plan(env)
        except ProfilesError as exc:
            raise ConfigError(str(exc)) from exc
        wanted = set(config.profiles)
        profiles_status = [
            c
            for c in all_candidates
            if (c.key == "git-bash" and "git-bash" in wanted)
            or (c.key.startswith("wsl:") and "wsl" in wanted)
        ]
        pending = [c for c in profiles_status if not c.already_present]
        if not dry_run and pending:
            apply_profiles_plan(env, data, pending, backup_root)

    return ConfigReport(
        init_plan=init_plan,
        init_report=init_report,
        theme_applied=theme_applied,
        theme_pending_install=theme_pending_install,
        profiles_status=profiles_status,
    )
