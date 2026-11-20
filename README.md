<div align="center">

# ⚒️ termforge

**Diagnostica, respalda y configura tu terminal de Windows**
*(Windows Terminal + PowerShell 7 + Oh My Posh), sin romper lo que ya tienes.*

[![CI](https://github.com/Rony10-az/Termforge/actions/workflows/ci.yml/badge.svg)](https://github.com/Rony10-az/Termforge/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/termforge.svg)](https://pypi.org/project/termforge/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Platform: Windows](https://img.shields.io/badge/platform-windows-0078D6.svg)](#)

![termforge doctor en acción](docs/doctor.png)

</div>

## Instala tu terminal en un comando

```powershell
pip install termforge
termforge init   # instala PowerShell 7 + Oh My Posh con winget y configura tu perfil
```

¿No tienes Python a mano? Descarga `termforge.exe` desde la
[última versión publicada](https://github.com/Rony10-az/Termforge/releases/latest) y úsalo
directo, sin instalar nada más.

Para desarrollar sobre el código (requiere Python 3.10+):

```powershell
git clone https://github.com/Rony10-az/Termforge.git
cd Termforge
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Eso es todo: `termforge init` detecta qué falta, lo instala con `winget` y deja tu perfil de
PowerShell inicializando Oh My Posh, sin que tengas que buscar instaladores ni editar nada a
mano. Si ya tenías algo instalado, `termforge` lo respeta y solo completa lo que falta.

¿Quieres repetir exactamente esta configuración en otra PC? Describe el resultado en un YAML
y aplícalo con un comando:

```yaml
# termforge.yaml
init: true
theme: jandedobbeleer
profiles: [git-bash, wsl]
```

```powershell
termforge apply
```

## Por qué

Dejar una terminal bien configurada toma horas: instalar programas, elegir una Nerd Font,
editar `settings.json`, tocar el perfil de PowerShell. `termforge` convierte ese proceso en
comandos repetibles y **reversibles**.

¿Quieres saber qué más instalar? [`docs/herramientas.md`](docs/herramientas.md) es una guía con
las herramientas populares para una buena terminal (zoxide, fzf, eza, lazygit, etc.) y soluciones
a problemas comunes.

## Comandos (v0.1)

| Comando | Qué hace |
|---|---|
| `termforge doctor` | Revisa qué falta o está mal (PowerShell 7, Windows Terminal, Oh My Posh, Nerd Font, Git, WSL, perfil) y muestra cómo arreglarlo. `--json` para scripts. |
| `termforge init [--dry-run] [-y]` | Instala con `winget` lo que falte (PowerShell 7, Oh My Posh) y agrega la inicialización de Oh My Posh al perfil de PowerShell. Respalda el perfil antes de modificarlo. |
| `termforge theme [número\|nombre] [--list]` | Lista los temas de Oh My Posh ya instalados y aplica el que elijas (por número, sin buscar el nombre exacto). Respalda el perfil antes de modificarlo. |
| `termforge profiles [--dry-run] [-y]` | Agrega Git Bash y los distros de WSL detectados como perfiles fijos en el menú de Windows Terminal (WSL normalmente solo aparece ahí de forma dinámica, sin quedar guardado). Respalda `settings.json` antes de modificarlo. |
| `termforge apply [-f archivo.yaml] [--dry-run] [-y]` | Deja tu terminal como la describe un YAML (`init`, `theme`, `profiles` en una sola corrida). Ver [`termforge.example.yaml`](termforge.example.yaml). |
| `termforge backup [-l etiqueta]` | Guarda una copia de `settings.json` y del perfil de PowerShell. |
| `termforge backups` | Lista los respaldos. |
| `termforge restore [id] [--dry-run] [-y]` | Restaura un respaldo (el más reciente por defecto). Antes guarda el estado actual como `pre-restore`. |

`doctor` termina con código `1` si hay fallos, así que sirve también en scripts y CI.

## Seguridad

- **Backup antes de modificar**: `restore` nunca sobrescribe sin guardar antes el estado actual.
- **`--dry-run`**: muestra qué haría sin tocar nada.
- Lee el `settings.json` de Windows Terminal aunque tenga comentarios y comas finales (JSONC).
- Los respaldos viven en `%LOCALAPPDATA%\termforge\backups` (se cambia con `TERMFORGE_HOME`).
- `profiles` sí **reescribe** `settings.json` (para agregar perfiles), así que pierde cualquier
  comentario manual que tengas ahí; por eso respalda el archivo antes de tocarlo.

## Desarrollo

```powershell
pytest -q        # tests
ruff check .     # lint

pip install pyinstaller
pyinstaller termforge.spec    # genera dist/termforge.exe
```

Estructura:

```
src/termforge/
├── cli.py       # comandos (Typer + Rich)
├── doctor.py    # diagnóstico
├── init.py      # instalación (winget) y configuración de Oh My Posh
├── theme.py     # listar y aplicar temas de Oh My Posh
├── profiles.py  # agregar Git Bash/WSL al menú de Windows Terminal
├── config.py    # configuración declarativa (termforge apply)
├── backup.py    # respaldo y restauración
├── env.py       # rutas y entorno (simulable en tests)
└── jsonc.py     # lector de JSON con comentarios
tests/           # corren en Windows y Linux (GitHub Actions)
```

Todo lo que depende del sistema pasa por `Env`, por eso los tests simulan una PC con Windows
sin tocar tu configuración real.

## Roadmap

- [x] `doctor`, `backup`, `restore`
- [x] `init`: instalar dependencias con winget y configurar Oh My Posh
- [x] `theme`: elegir y aplicar un tema de Oh My Posh de una lista
- [x] `profiles`: agregar Git Bash y WSL al menú de Windows Terminal
- [x] Configuración declarativa (`termforge apply -f termforge.yaml`)
- [x] Publicar en PyPI y empaquetar `.exe` (ver [`.github/workflows/release.yml`](.github/workflows/release.yml))

## Licencia

Distribuido bajo la licencia MIT. Ver [LICENSE](LICENSE) para el texto completo.
