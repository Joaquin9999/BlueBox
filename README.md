# BlueBox

`BlueBox` es una herramienta CLI en Python para flujos blue team/DFIR por fases.

## Estado actual

- Proyecto inicial con CLI funcional.
- Comando disponible: `bluebox --help`.
- Flujo de trabajo por ramas de fase activo.
- Modelo de workspace de caso y templates base implementados.

## Qué contiene el repositorio

- `bluebox/`: paquete Python principal y CLI (`bluebox.cli.app`).
- `bluebox/core/`: modelo de caso, sanitización, render y generador determinista de estructura.
- `cli/`, `core/`, `templates/`, `scripts/`, `tests/`: estructura base para evolución por fases.
- `pyproject.toml`: metadatos del paquete y entrypoint del comando `bluebox`.
- `Makefile`: helper mínimo para tareas futuras.

## Templates de caso incluidos

- `templates/case/notes/*`: `writeup.md`, `findings.md`, `changelog.md`, `hypotheses.md`, `writeup_final.md`.
- `templates/case/meta/*`: `solution_state.json`, `artifacts_inventory.json`, `hashes.json`, `evidence_summary.json`.
- `templates/case/.codex/*`: `prompt.txt`, `context.md`.

## Requisitos

- Python `>=3.12`.
- Entorno Unix-like (probado en macOS; enfoque compatible con Ubuntu/Debian).

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
bluebox version
```

## Ejecución de pruebas

```bash
source .venv/bin/activate
pip install pytest
pytest -q
```

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