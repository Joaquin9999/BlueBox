# BlueBox

`BlueBox` es una herramienta CLI en Python para flujos blue team/DFIR por fases.

## Quickstart (30 segundos)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
bluebox --help
```

Flujo mínimo de prueba:

```bash
bluebox start
bluebox doctor
bluebox init
# (modo interactivo: te pedirá challenge name, artifacts, title, context y base path)
bluebox classify
bluebox validate
```

## Estado actual

- Proyecto inicial con CLI funcional.
- Comando disponible: `bluebox --help`.
- Flujo de trabajo por ramas de fase activo.
- Modelo de workspace de caso y templates base implementados.
- Comando `bluebox init` implementado para inicializar casos desde artefactos.

## Guía de uso

- Consulta `USAGE_GUIDE.md` para flujo operativo completo paso a paso.

## Guía de instalación

- Consulta `INSTALL.md` para instalación desde cero, verificación y troubleshooting.

## Qué contiene el repositorio

- `bluebox/`: paquete Python principal y CLI (`bluebox.cli.app`).
- `bluebox/core/`: modelo de caso, sanitización, render y generador determinista de estructura.
- `cli/`, `core/`, `templates/`, `scripts/`, `tests/`: estructura base para evolución por fases.
- `examples/`: ejemplos públicos seguros y reproducibles.
- `pyproject.toml`: metadatos del paquete y entrypoint del comando `bluebox`.
- `Makefile`: helper mínimo para tareas futuras.

## Templates de caso incluidos

- `templates/case/notes/*`: `writeup.md`, `findings.md`, `changelog.md`, `hypotheses.md`, `writeup_final.md`.
- `templates/case/meta/*`: `solution_state.json`, `artifacts_inventory.json`, `hashes.json`, `evidence_summary.json`.
- `templates/case/.codex/*`: `prompt.txt`, `context.md`.

## Requisitos

- Python `>=3.12`.
- Entorno de consola en macOS, Linux o Windows.

## Instalación local (desarrollo)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

## Uso

```bash
bluebox --help
bluebox start
bluebox version
bluebox init
bluebox init --name "Suspicious Beaconing" --artifacts ./samples/beaconing --title "Suspicious Beaconing" --context "Initial context"
bluebox validate
bluebox classify
bluebox solve --no-launch
bluebox status
bluebox doctor
bluebox finalize --allow-incomplete
bluebox project show
bluebox project set ./suspicious-beaconing
bluebox project list
bluebox project list --existing-only
bluebox project clear
bluebox tools list
bluebox tools check base
bluebox tools install network
bluebox tools install network --apply
```

## Qué hace `bluebox init`

- Crea el folder del caso con nombre sanitizado.
- Genera la estructura canónica de carpetas y archivos de notas/meta.
- Copia artefactos a `original/` y `working/` (sin modificar los originales).
- Calcula hashes SHA-256 de `original/` y escribe `meta/hashes.json`.
- Construye inventario en `meta/artifacts_inventory.json`.
- Inicializa `meta/solution_state.json` con estado `initialized`.
- Escribe la primera entrada en `notes/changelog.md`.
- Guarda el proyecto activo en `.bluebox/active_case.txt` para usar otros comandos sin ruta explícita.

## Qué valida `bluebox validate`

- Estructura de carpetas requerida del caso.
- Archivos obligatorios en `notes/`, `meta/` y `.codex/`.
- JSON válido en archivos `meta/*.json` requeridos.
- Estado permitido en `meta/solution_state.json`.
- Retorna código `0` si el caso es válido y `1` si hay errores.

## Qué hace `bluebox classify`

- Lee `meta/artifacts_inventory.json` y detecta tipos de artefacto por extensión/nombre.
- Infiere categoría inicial (ej. `pcap/network forensics`, `windows dfir`, `phishing`, etc.).
- Infiere subcategorías cuando aplica.
- Propone una ruta inicial de análisis e hipótesis de trabajo (advisory).
- Actualiza:
  - `notes/hypotheses.md`
  - `notes/writeup.md`
  - `notes/changelog.md`
  - `meta/solution_state.json` (estado `classified`)

## Qué hace `bluebox solve`

- Valida el caso antes de iniciar solve.
- Construye `.codex/context.md` con título, contexto, categoría/subcategorías,
	resumen de inventario, hipótesis activas y estado actual.
- Copia el prompt principal de solver a `.codex/prompt.txt`.
- Registra acciones en `meta/commands.log`.
- Actualiza `meta/solution_state.json` a estado `solving`.
- Lanza `codex` en el directorio del caso (o prepara sin lanzar con `--no-launch`).

## Qué hace `bluebox status`

- Muestra resumen operativo del caso:
  - nombre del caso
  - título
  - estado actual
  - categoría
  - número de artefactos
  - cantidad de hipótesis activas
  - última actualización registrada en changelog

## Qué hace `bluebox doctor`

- Ejecuta diagnóstico rápido del entorno:
  - versión de Python en uso
  - plataforma del sistema
  - disponibilidad de `uv`
  - disponibilidad de `codex`
  - disponibilidad de `git`

## Qué hace `bluebox tools`

- `bluebox tools list`: lista perfiles de herramientas DFIR/Blue Team.
- `bluebox tools check <profile>`: verifica disponibilidad de herramientas del perfil.
- `bluebox tools install <profile>`: muestra comandos sugeridos (dry-run por defecto).
- `bluebox tools install <profile> --apply`: ejecuta comandos de instalación en tu sistema (brew/apt/pip según host).

## Qué hace `bluebox project`

- `bluebox project show`: muestra la ruta del proyecto activo en el workspace actual.
- `bluebox project set <case-path>`: cambia el proyecto activo para ejecutar comandos sin pasar ruta.
- `bluebox project list`: lista proyectos conocidos en el historial del workspace.
- `bluebox project list --existing-only`: muestra solo proyectos cuya ruta todavía existe.
- `bluebox project clear`: limpia el proyecto activo actual.

## Sobre entorno virtual y sistema

- BlueBox puede ejecutarse dentro de `.venv` (recomendado) o en Python global.
- El paquete `bluebox` sí vive en el entorno donde lo instales (venv o sistema).
- Las herramientas de `bluebox tools install --apply` son herramientas del host (no quedan encerradas solo en el venv, salvo comandos explícitos de `pip`).

## Qué hace `bluebox finalize`

- Lee documentación acumulada:
  - `notes/writeup.md`
  - `notes/findings.md`
  - `notes/changelog.md`
  - `notes/hypotheses.md`
  - `meta/evidence_summary.json`
  - `meta/solution_state.json`
- Genera `notes/writeup_final.md` fiel al contenido ya documentado.
- Si el caso está en `solved/finalized`, mueve estado a `finalized`.
- Si no está resuelto, aborta limpiamente por defecto.
- Puede generar versión incompleta explícita con `--allow-incomplete`.

## Ejecución de pruebas

```bash
source .venv/bin/activate
pip install pytest
pytest -q
```

## Ejemplos públicos seguros

- Demo incluida: `examples/safe-demo/`.
- Los artefactos del demo son sintéticos y aptos para repositorio público.
- Guía de ejecución rápida en `examples/README.md`.

## Flujo de ramas por fases

- `main` se mantiene estable.
- Cada fase se desarrolla en su rama: `phase/<numero>-<nombre>`.
- Se realizan commits pequeños y frecuentes.
- Al cerrar la fase, se integra a `main` con merge commit.

Ejemplo:

```bash
git checkout main
git checkout -b phase/2-case-model
# ... cambios de la fase ...
git add .
git commit -m "feat: implement case model"
git checkout main
git merge --no-ff phase/2-case-model -m "merge: integrate phase 2 case model"
```

## Despliegue a GitHub (publicación del repo)

Si el repo no aparece en GitHub, normalmente falta crear/configurar remoto y hacer `push`.

1) Crear el repositorio en GitHub (ejemplo: `BlueBox`).

2) Conectar remoto:

```bash
git remote add origin git@github.com:<tu-usuario>/BlueBox.git
# o HTTPS:
# git remote add origin https://github.com/<tu-usuario>/BlueBox.git
```

3) Subir `main`:

```bash
git push -u origin main
```

4) Subir ramas de fase cuando quieras compartir trabajo intermedio:

```bash
git push -u origin phase/rebrand-bluebox
```

## Verificación rápida de Git remoto

```bash
git remote -v
git branch -vv
```