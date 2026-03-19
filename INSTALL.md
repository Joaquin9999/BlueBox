# BlueBox — Guía de Instalación

Esta guía cubre instalación local para uso de desarrollo y operación CLI.

## Requisitos

- Python `>=3.12`
- `git`
- Sistema Unix-like (macOS/Linux)

## 1) Clonar repositorio

```bash
git clone https://github.com/Joaquin9999/BlueBox.git
cd BlueBox
```

## 2) Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3) Instalar BlueBox

```bash
python -m pip install --upgrade pip
python -m pip install .
```

## 4) Verificar instalación

```bash
bluebox --help
bluebox version
bluebox doctor
```

## 5) Ejecutar pruebas (recomendado)

```bash
python -m pip install pytest
pytest -q
```

## 6) Actualizar a última versión del repo

```bash
git pull --ff-only
python -m pip install .
```

## 7) Instalación editable (modo desarrollo)

Si vas a modificar código activamente:

```bash
python -m pip install -e .
```

## Troubleshooting

### `bluebox: command not found`

- Verifica que el entorno virtual esté activo:

```bash
source .venv/bin/activate
```

- Reinstala el paquete:

```bash
python -m pip install .
```

### `Codex CLI not found in PATH`

- `bluebox solve` puede ejecutarse sin lanzar codex usando:

```bash
bluebox solve <case-path> --no-launch
```

### Error de versión de Python

- Comprueba versión actual:

```bash
python --version
```

- Usa Python 3.12+ para evitar incompatibilidades.
