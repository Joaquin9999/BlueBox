# BlueHunt

Repositorio base para construir **BlueHunt** por fases.

CLI actual: esqueleto funcional de Fase 1.

## Flujo de trabajo

- `main` se mantiene estable.
- Cada fase se desarrolla en su propia rama: `phase/<numero>-<nombre>`.
- Al completar una fase, se integra a `main` mediante merge.

## Convención sugerida

- `phase/0-bootstrap`
- `phase/1-cli-skeleton`
- `phase/2-case-model`

## Inicio rápido (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
bluehunt --help
```

## Estructura inicial

- `bluehunt/`: paquete Python y CLI (`bluehunt.cli.app`)
- `cli/`, `core/`, `templates/`, `scripts/`, `tests/`: carpetas base del proyecto
- `pyproject.toml`: metadatos, dependencias y entrypoint `bluehunt`