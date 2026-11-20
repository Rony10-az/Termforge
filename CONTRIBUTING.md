# Contribuir a termforge

Gracias por querer mejorar `termforge`. Esta guía explica el flujo para proponer un cambio,
cómo está armado el código y qué revisa el CI antes de aceptar un PR.

## Antes de empezar

- Para un bug o una idea nueva, abre primero un [issue](https://github.com/Rony10-az/Termforge/issues)
  describiendo el problema o la propuesta, salvo que sea algo obvio (un typo, una línea de
  `docs/herramientas.md`).
- Si vas a trabajar en algo de la sección ["Qué sigue"](README.md#qué-sigue) del README,
  coméntalo en el issue para evitar que dos personas hagan lo mismo.
- Sé respetuoso en issues y PRs. Nada más que agregar.

## Flujo para contribuir

1. Haz fork del repo y clónalo.
2. Crea una rama descriptiva: `git checkout -b agrega-theme-random`.
3. Prepara el entorno (ver abajo) y haz tu cambio, con sus tests.
4. Corre `pytest -q` y `ruff check .` localmente — ambos deben pasar limpio.
5. Haz commit con un mensaje que diga el *por qué*, no solo el *qué* (ver
   [convenciones de commits](#convenciones-de-commits)).
6. Abre el PR contra `main`. El [CI](.github/workflows/ci.yml) corre los tests en
   Windows y Linux, con Python 3.10/3.12/3.13 — todos deben pasar.

## Entorno de desarrollo

Requiere Python 3.10 o superior.

```powershell
git clone https://github.com/<tu-usuario>/Termforge.git
cd Termforge
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

pytest -q
ruff check .
```

## Cómo está armado el código

```
src/termforge/
├── cli.py       # comandos (Typer + Rich) — delgado, sin lógica
├── env.py       # Env: todo lo que depende del sistema pasa por aquí
├── doctor.py    # diagnóstico
├── init.py      # instalación (winget) y configuración de Oh My Posh
├── theme.py     # listar y aplicar temas de Oh My Posh
├── profiles.py  # agregar Git Bash/WSL al menú de Windows Terminal
├── config.py    # configuración declarativa (termforge apply)
├── backup.py    # respaldo y restauración
└── jsonc.py     # lector de JSON con comentarios
```

Cada módulo de lógica (`init.py`, `theme.py`, `profiles.py`...) sigue el mismo patrón:

- Recibe un `Env` (sistema operativo, variables, `which`, `run`) en vez de leer `os.environ` o
  llamar `subprocess.run` directamente. Así los tests simulan una PC de Windows sin tocar la
  tuya — mira `tests/conftest.py` (fixture `make_env`).
- Separa **planear** de **aplicar**: una función `build_plan(env)` que solo lee y decide qué
  falta, y otra `apply_plan(env, plan, ...)` que ejecuta los cambios. Eso es lo que hace
  posible el `--dry-run` en casi todos los comandos.
- Si modifica un archivo del usuario (perfil de PowerShell, `settings.json`), llama a
  `backup.create_backup(...)` antes de escribir.
- `cli.py` solo arma el comando de Typer, muestra el resultado con Rich y llama a las funciones
  del módulo — no tiene lógica propia que valga la pena testear por separado.

### Agregar un comando nuevo

1. Crea `src/termforge/tu_modulo.py` siguiendo el patrón de arriba.
2. Agrega sus tests en `tests/test_tu_modulo.py` (unitarios, sin CLI) usando `make_env`.
3. Conecta el comando en `cli.py` y agrega 2-3 tests en `tests/test_cli.py` que lo prueben
   de punta a punta con `CliRunner`.
4. Documenta el comando en la tabla de [Comandos](README.md#comandos) del README.

### Agregar una herramienta a la guía

Para sumar algo a [`docs/herramientas.md`](docs/herramientas.md): una fila en la tabla que le
corresponda (Shell, Prompt, Navegación...), con qué hace y el comando `winget install`
correspondiente. No hace falta tocar código para esto.

## Convenciones de commits

Seguimos un estilo simple: `tipo: resumen corto`, donde `tipo` es `feat`, `fix`, `docs`, `test`
o `refactor`. El resumen dice qué cambia; el cuerpo del commit (si hace falta) explica el
*por qué*. Ejemplo real de este repo:

```
fix: evitar que Rich envuelva el mensaje de 'apply' sin nada que hacer

En Linux CI, el path temporal de pytest es largo y Rich envolvía la
línea en 80 columnas justo en medio de "no pide nada", rompiendo el
test ahí (no en Windows, por eso pasaba inadvertido).
```

## Checklist antes de abrir el PR

- [ ] `pytest -q` pasa.
- [ ] `ruff check .` pasa sin avisos.
- [ ] Si tocaste un comando, el README (tabla de comandos) está al día.
- [ ] Si agregaste un comando que modifica algo del sistema, tiene `--dry-run` y respalda
      antes de escribir (ver [Seguridad y reversibilidad](README.md#seguridad-y-reversibilidad)).
