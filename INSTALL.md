# BlueBox — Guía de Instalación

Esta guía cubre instalación local para uso de desarrollo y operación CLI.

## Requisitos

- Python `>=3.12`
- `git`
- Terminal en macOS, Linux o Windows

## 1) Clonar repositorio

```bash
git clone https://github.com/Joaquin9999/BlueBox.git
cd BlueBox
```

## 2) Crear entorno virtual

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Instalar BlueBox

```bash
python -m pip install --upgrade pip
python -m pip install .
```

## 4) Verificar instalación

```bash
bluebox --help
bluebox start
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

## 6.1) Instalar herramientas opcionales DFIR/Blue Team

BlueBox incluye perfiles de herramientas opcionales.

Ver perfiles y estado:

```bash
bluebox tools list
bluebox tools check base
bluebox tools check network
```

Instalación (segura por defecto):

```bash
bluebox tools install network
```

El comando anterior no instala nada: solo muestra sugerencias (dry-run).

Ejecución real de instalación:

```bash
bluebox tools install network --apply
```

Con `--apply`, BlueBox ejecuta comandos del sistema operativo (ej. `brew`, `apt`, `pip`) para herramientas faltantes.
Estas herramientas se instalan en tu host según el gestor usado, no exclusivamente dentro del entorno virtual.

## 7) Instalación editable (modo desarrollo)

Si vas a modificar código activamente:

```bash
python -m pip install -e .
```

## Proyecto activo (flujo sin rutas largas)

Después de `bluebox init`, se guarda un proyecto activo en `.bluebox/active_case.txt`.
Por eso puedes ejecutar:

```bash
bluebox classify
bluebox validate
bluebox solve --no-launch
bluebox status
bluebox finalize --allow-incomplete
```

Si prefieres, también puedes pasar ruta explícita en cada comando.

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

### `Agent CLI not found in PATH`

- `bluebox solve` puede ejecutarse sin lanzar el agente usando:

```bash
bluebox solve <case-path> --no-launch
```

### Error de versión de Python

- Comprueba versión actual:

```bash
python --version
```

- Usa Python 3.12+ para evitar incompatibilidades.

## Compatibilidad esperada

- BlueBox es una CLI Python pura y se distribuye como paquete estándar.
- Matriz de validación automatizada definida en `.github/workflows/ci.yml` para:
	- Ubuntu (Linux)
	- Windows
	- macOS
	- Python 3.12 y 3.13
- Arquitecturas distintas a runners estándar (por ejemplo 32-bit) se consideran best-effort; valida con `bluebox doctor` y una ejecución de smoke test.
