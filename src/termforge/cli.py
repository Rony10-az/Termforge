"""Interfaz de línea de comandos de termforge."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from termforge import __version__
from termforge.backup import (
    BackupError,
    create_backup,
    list_backups,
    restore_backup,
)
from termforge.doctor import CheckResult, Status, exit_code, run_checks
from termforge.env import Env, backup_root, managed_files
from termforge.init import InitPlan, apply_plan, build_plan

app = typer.Typer(
    help="Diagnostica, respalda y configura tu terminal de Windows.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

_STATUS_STYLE = {
    Status.OK: ("OK", "green"),
    Status.WARN: ("AVISO", "yellow"),
    Status.FAIL: ("FALLO", "red"),
}


def get_env() -> Env:
    """Punto único para obtener el entorno (se reemplaza en los tests)."""
    return Env()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"termforge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v", callback=_version_callback, is_eager=True, help="Muestra la versión."
        ),
    ] = False,
) -> None:
    pass


def _render_checks(results: list[CheckResult]) -> None:
    table = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False)
    table.add_column("Estado")
    table.add_column("Revisión")
    table.add_column("Detalle", overflow="fold")
    for r in results:
        label, color = _STATUS_STYLE[r.status]
        table.add_row(f"[{color}]{label}[/{color}]", r.name, r.detail)
    console.print(table)

    hints = [r for r in results if r.status is not Status.OK and r.hint]
    if hints:
        console.print("\n[bold]Cómo arreglarlo[/bold]")
        for r in hints:
            console.print(f"  {r.name}: [cyan]{r.hint}[/cyan]", highlight=False)

    fails = sum(r.status is Status.FAIL for r in results)
    warns = sum(r.status is Status.WARN for r in results)
    oks = sum(r.status is Status.OK for r in results)
    console.print(f"\nOK: {oks} | Avisos: {warns} | Fallos: {fails}")


@app.command()
def doctor(
    json_output: Annotated[
        bool, typer.Option("--json", help="Salida en JSON (para scripts).")
    ] = False,
) -> None:
    """Revisa qué falta o está mal configurado en tu terminal."""
    results = run_checks(get_env())
    if json_output:
        typer.echo(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
    else:
        _render_checks(results)
    raise typer.Exit(exit_code(results))


def _render_init_plan(plan: InitPlan) -> None:
    pending = plan.pending_installs
    if pending:
        console.print("[bold]Se instalará con winget:[/bold]")
        for step in pending:
            console.print(f"  {step.name} ([cyan]{step.package_id}[/cyan])", highlight=False)
    else:
        console.print("[green]Ya están instalados: PowerShell 7, Oh My Posh.[/green]")

    if plan.profile.already_configured:
        console.print("[green]El perfil de PowerShell ya inicializa Oh My Posh.[/green]")
    else:
        verb = "agrega" if plan.profile.exists else "crea y agrega"
        console.print(
            f"[bold]Perfil de PowerShell:[/bold] {verb} la inicialización en {plan.profile.path}"
        )


@app.command()
def init(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Muestra qué haría sin instalar ni modificar nada.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="No pedir confirmación.")] = False,
) -> None:
    """Instala lo que falte (winget) y configura Oh My Posh en tu perfil de PowerShell."""
    env = get_env()
    plan = build_plan(env)

    if not plan.has_pending_work:
        console.print("[green]Todo ya está instalado y configurado.[/green]")
        return

    _render_init_plan(plan)

    if dry_run:
        console.print("\n[dim]--dry-run: no se instaló ni modificó nada.[/dim]")
        return
    if not yes and not typer.confirm("\n¿Continuar?"):
        raise typer.Exit(1)

    report = apply_plan(env, plan, backup_root(env))

    for step in report.installed:
        console.print(f"[green]Instalado:[/green] {step.name}")
    for step, error in report.failed:
        err_console.print(f"[red]Falló instalar {step.name}:[/red] {error}")
    if report.profile_updated:
        console.print(f"[green]Perfil actualizado:[/green] {plan.profile.path}")
        if report.profile_backup:
            console.print(
                f"Estado anterior guardado como {report.profile_backup.id}", highlight=False
            )

    if report.installed:
        console.print("\n[yellow]Reinicia la terminal para que los cambios tomen efecto.[/yellow]")
    if report.failed:
        raise typer.Exit(1)


@app.command()
def backup(
    label: Annotated[str, typer.Option("--label", "-l", help="Etiqueta opcional.")] = "",
) -> None:
    """Guarda una copia de tu configuración actual."""
    env = get_env()
    try:
        info = create_backup(managed_files(env), backup_root(env), label=label)
    except BackupError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]Respaldo creado:[/green] {info.id}")
    for entry in info.entries:
        console.print(f"  {entry.name}", highlight=False)
    console.print(f"Ubicación: {info.path}", highlight=False)


@app.command()
def backups() -> None:
    """Lista los respaldos disponibles."""
    found = list_backups(backup_root(get_env()))
    if not found:
        console.print("No hay respaldos todavía. Crea uno con `termforge backup`.")
        return

    table = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False)
    table.add_column("Id")
    table.add_column("Fecha")
    table.add_column("Etiqueta")
    table.add_column("Archivos")
    for b in found:
        files = ", ".join(e.name for e in b.entries)
        table.add_row(b.id, b.created.replace("T", " "), b.label, files)
    console.print(table)


@app.command()
def restore(
    backup_id: Annotated[
        str | None, typer.Argument(help="Id del respaldo (por defecto, el más reciente).")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Muestra qué haría sin modificar nada.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="No pedir confirmación.")] = False,
) -> None:
    """Restaura un respaldo (guarda antes el estado actual como 'pre-restore')."""
    env = get_env()
    root, targets = backup_root(env), managed_files(env)

    try:
        plan = restore_backup(root, targets, backup_id, dry_run=True)
        console.print(f"Respaldo: [bold]{plan.backup.id}[/bold]", highlight=False)
        for action in plan.actions:
            verb = "sobrescribe" if action.overwrites else "crea"
            console.print(f"  {verb} {action.destination}", highlight=False)
        for name in plan.skipped:
            console.print(f"  [yellow]omitido:[/yellow] {name}", highlight=False)

        if dry_run:
            console.print("\n[dim]--dry-run: no se modificó nada.[/dim]")
            return
        if not plan.actions:
            console.print("Nada que restaurar.")
            return
        if not yes and not typer.confirm("\n¿Continuar?"):
            raise typer.Exit(1)

        report = restore_backup(root, targets, plan.backup.id)
    except BackupError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Restauración completada.[/green]")
    if report.safety_backup:
        console.print(
            f"Estado anterior guardado como {report.safety_backup.id}", highlight=False
        )


if __name__ == "__main__":
    app()
