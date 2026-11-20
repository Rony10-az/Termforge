# Guía de herramientas para una buena terminal en Windows

`termforge` se enfoca en Windows Terminal + PowerShell 7 + Oh My Posh, pero una
terminal cómoda suele apoyarse en más piezas. Esta guía las junta en un solo
lugar: qué hace cada una, por qué vale la pena, y el comando para instalarla
con `winget` (todas corren bien en PowerShell 7).

> ¿Falta una herramienta que usas todos los días? Abre un PR agregándola a la
> tabla que le corresponda.

## Shell

| Herramienta | Para qué sirve | Instalación |
|---|---|---|
| [PowerShell 7](https://github.com/PowerShell/PowerShell) | El shell que usa `termforge`; multiplataforma, más rápido y compatible que Windows PowerShell 5.1. | `winget install --id Microsoft.PowerShell` |
| [WSL](https://learn.microsoft.com/windows/wsl/) | Un Linux real dentro de Windows, para cuando una tarea es más simple con herramientas de Linux (`grep`, `make`, contenedores). | `wsl --install` |
| [Git Bash](https://git-scm.com/) | Un shell tipo bash, útil si vienes de Linux/Mac o necesitas scripts `.sh`. Se instala junto con Git. | `winget install --id Git.Git` |

## Prompt e iconos

| Herramienta | Para qué sirve | Instalación |
|---|---|---|
| [Oh My Posh](https://ohmyposh.dev/) | Prompt personalizable con temas (Git, duración de comandos, contexto de la nube, etc). `termforge init`/`termforge theme` lo configuran por ti. | `winget install JanDeDobbeleer.OhMyPosh -s winget` |
| Nerd Font (p. ej. [CascadiaCode NF](https://www.nerdfonts.com/)) | Fuente con los iconos que usan los temas de Oh My Posh y `eza`/`lsd`. Sin ella ves cuadros o símbolos raros. | `oh-my-posh font install CascadiaCode` |
| [Terminal-Icons](https://github.com/devblackops/Terminal-Icons) | Agrega iconos a la salida de `Get-ChildItem` (`ls`) en PowerShell. | `Install-Module -Name Terminal-Icons -Repository PSGallery` |

## Navegación y búsqueda

| Herramienta | Para qué sirve | Instalación |
|---|---|---|
| [zoxide](https://github.com/ajeetdsouza/zoxide) | Un `cd` con memoria: `z proyecto` te lleva a la carpeta que más usas con ese nombre. | `winget install ajeetdsouza.zoxide` |
| [fzf](https://github.com/junegunn/fzf) | Buscador difuso interactivo: filtra historial, archivos o cualquier lista mientras escribes. | `winget install fzf` |
| [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | Buscar texto en archivos, mucho más rápido que `grep`/`Select-String` en proyectos grandes. | `winget install BurntSushi.ripgrep.MSVC` |
| [fd](https://github.com/sharkdp/fd) | Buscar archivos por nombre, con una sintaxis más simple que `Get-ChildItem -Recurse`. | `winget install sharkdp.fd` |

## Listar y ver archivos

| Herramienta | Para qué sirve | Instalación |
|---|---|---|
| [eza](https://github.com/eza-community/eza) | Reemplazo de `ls` con colores, iconos (necesita una Nerd Font) y vista de árbol. | `winget install eza-community.eza` |
| [bat](https://github.com/sharkdp/bat) | Reemplazo de `cat`/`Get-Content` con resaltado de sintaxis y números de línea. | `winget install sharkdp.bat` |

## Git

| Herramienta | Para qué sirve | Instalación |
|---|---|---|
| [lazygit](https://github.com/jesseduffield/lazygit) | Interfaz de texto para Git (stage, commit, branches, rebase interactivo) sin salir de la terminal. | `winget install JesseDuffield.lazygit` |
| [posh-git](https://github.com/dahlbyk/posh-git) | Autocompletado de comandos de Git y estado del repo en el prompt de PowerShell (si no usas Oh My Posh para esto). | `Install-Module posh-git -Scope CurrentUser` |

## Solución de problemas comunes

- **No veo iconos, veo cuadros o signos de interrogación**: te falta instalar una Nerd Font y configurarla como fuente de Windows Terminal. `termforge doctor` lo detecta.
- **`oh-my-posh`/`zoxide`/etc. "no se reconoce como un comando"** justo después de instalarlo con winget: abre una terminal nueva. Winget actualiza el `PATH`, pero las terminales ya abiertas no se enteran.
- **"no se puede cargar el archivo ... porque la ejecución de scripts está deshabilitada"**: tu política de ejecución bloquea el perfil de PowerShell. Corre `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` (como usuario, no hace falta administrador).
- **Instalé un tema de Oh My Posh pero no cambió nada**: revisa que el perfil de PowerShell realmente lo cargue (`termforge doctor` lo valida) y reinicia la terminal.
