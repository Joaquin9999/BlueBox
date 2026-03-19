# BlueBox — Guía de Uso

Esta guía resume el uso operativo de BlueBox de punta a punta.

## 1) Requisitos

- Python `>=3.12`
- Entorno de consola en macOS, Linux o Windows
- Repositorio clonado localmente

## 2) Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

## 3) Verificación inicial

```bash
bluebox --help
bluebox start
bluebox wizard
bluebox home
bluebox version
bluebox doctor
```

## 4) Flujo recomendado por caso

### 4.1 Inicializar caso

Modo recomendado vNext (seguro):

```bash
bluebox new
```

Modo interactivo (recomendado):

```bash
bluebox init
```

Modo no interactivo (script/CI):

```bash
bluebox init --name "Suspicious Beaconing" \
  --artifacts ./input_artifacts \
  --title "Suspicious Beaconing" \
  --context "Initial triage context"
```

Resultado esperado:
- Carpeta de caso sanitizada en `cases/<nombre-caso>/` (ej. `cases/suspicious-beaconing/`)
- Estructura estándar compatible: `notes/`, `meta/`, `.codex/` + árbol vNext (`challenge/`, `agent/`, `memory/`, `output/`)
- `hashes.json`, `artifacts_inventory.json`, `solution_state.json`
- Proyecto activo guardado en `.bluebox/active_case.txt`
- Recientes guardados en `.bluebox/recent_cases.json`
- Config por defecto en `.bluebox/settings.yaml`

### 4.2 Clasificar caso

```bash
bluebox classify
```

Resultado esperado:
- Estado a `classified`
- Categoría/subcategorías inferidas
- Actualización de `notes/hypotheses.md`, `notes/writeup.md`, `notes/changelog.md`

### 4.3 Validar integridad

```bash
bluebox validate
```

Resultado esperado:
- Código `0` si estructura/JSON/status son válidos
- Código `1` y errores claros si hay problemas

### 4.4 Preparar solve con Codex

```bash
bluebox solve --no-launch
```

Modo real (si tienes `codex` instalado):

```bash
bluebox solve
```

Resultado esperado:
- `.codex/context.md` actualizado
- `.codex/prompt.txt` actualizado
- `meta/commands.log` con eventos
- Estado a `solving`

### 4.5 Consultar estado operativo

```bash
bluebox status
```

Muestra:
- case, title, status, category
- artifacts count
- active hypotheses count
- latest changelog entry

### 4.6 Generar writeup final

Caso resuelto (`status=solved`):

```bash
bluebox finalize
```

Caso no resuelto (incompleto explícito):

```bash
bluebox finalize --allow-incomplete
```

Resultado esperado:
- `notes/writeup_final.md` generado
- Si estaba en `solved`, pasa a `finalized`

## 5) Ejemplo público seguro

Puedes usar los artefactos sintéticos incluidos:

```bash
bluebox init --name "Safe Demo" \
  --artifacts ./examples/safe-demo/artifacts \
  --title "Safe Demo"

bluebox classify
bluebox validate
bluebox solve --no-launch
bluebox status
bluebox finalize --allow-incomplete
```

## 6) Comandos de referencia rápida

```bash
bluebox version
bluebox doctor
bluebox setup --mode all
bluebox setup --mode tool --tool jq
bluebox tools list
bluebox tools check base
bluebox tools install network
bluebox tools install network --apply
bluebox project show
bluebox project set <case-path>
bluebox project list
bluebox project list --existing-only
bluebox project list --compact
bluebox project prune-missing
bluebox project clear
bluebox cases list
bluebox cases current
bluebox cases use <case-name|case-path>
bluebox cases open [<case-name|case-path>]
bluebox cases clear
bluebox cases archive <case-name|case-path>
bluebox cases clone <case-name|case-path> <new-name>
bluebox use <case-name|case-path>
bluebox current
bluebox open [<case-name|case-path>]
bluebox check [<case-path>]
bluebox inspect [<case-path>]
bluebox run [<case-path>] [--no-launch]
bluebox info [<case-path>]
bluebox home
bluebox handoff [<case-path>] [--no-write]
bluebox summary [<case-path>]
bluebox summarize <source-file> [--case-path <case-path>] [--output-name <name.md>]
bluebox report [<case-path>] [--allow-incomplete]
bluebox wizard [--base-path <path>] [--create-case --name <name> --artifacts <path> --title <title>]
bluebox next [<case-path>]
bluebox init --name <name> --artifacts <path> --title <title>
bluebox new --name <name> --artifacts <path> --title <title> [--evidence-mode reference-only|lightweight-copy|full-copy]
bluebox classify [<case-path>]
bluebox validate [<case-path>]
bluebox solve [<case-path>] [--no-launch]
bluebox status [<case-path>]
bluebox finalize [<case-path>] [--allow-incomplete]
```

## 6.1 Perfiles de herramientas opcionales

BlueBox permite gestionar herramientas comunes de forense/blue team por perfil.

- `base`
- `network`
- `windows-dfir`
- `linux-dfir`
- `malware`

Primero revisa qué tienes instalado:

```bash
bluebox tools list
bluebox tools check network
```

Si quieres instalar faltantes:

```bash
bluebox tools install network      # dry-run (solo sugerencias)
bluebox tools install network --apply
```

Nota: con `--apply`, BlueBox ejecuta comandos de instalación del sistema (por ejemplo `brew` o `apt`).

## 7) Errores comunes

- `Case validation failed ...`
  - Ejecuta `bluebox validate <case-path>` y corrige faltantes.

- `Codex CLI not found in PATH`
  - Usa `bluebox solve --no-launch` o instala `codex` en tu entorno.

- `Case is not solved ... finalize`
  - Usa `--allow-incomplete` o marca el caso como resuelto antes de finalizar.

## 8) Buenas prácticas para repo público

- No incluir secretos ni datos sensibles.
- Mantener ejemplos sintéticos en `examples/`.
- Usar commits pequeños por fase.
- Ejecutar `pytest -q` antes de merge/tag.

## 9) Compatibilidad

- BlueBox funciona sobre Python `3.12+` en macOS, Linux y Windows.
- Para validar tu host actual (Python, plataforma y binarios requeridos), ejecuta:

```bash
bluebox doctor
```
