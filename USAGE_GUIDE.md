# BlueBox — Guía de Uso

Esta guía resume el uso operativo de BlueBox de punta a punta.

## 1) Requisitos

- Python `>=3.12`
- Entorno Unix-like (macOS/Linux)
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
bluebox version
bluebox doctor
```

## 4) Flujo recomendado por caso

### 4.1 Inicializar caso

```bash
bluebox init "Suspicious Beaconing" \
  --artifacts ./input_artifacts \
  --title "Suspicious Beaconing" \
  --context "Initial triage context"
```

Resultado esperado:
- Carpeta de caso sanitizada (ej. `suspicious-beaconing/`)
- Estructura estándar de `notes/`, `meta/`, `.codex/`
- `hashes.json`, `artifacts_inventory.json`, `solution_state.json`

### 4.2 Clasificar caso

```bash
bluebox classify ./suspicious-beaconing
```

Resultado esperado:
- Estado a `classified`
- Categoría/subcategorías inferidas
- Actualización de `notes/hypotheses.md`, `notes/writeup.md`, `notes/changelog.md`

### 4.3 Validar integridad

```bash
bluebox validate ./suspicious-beaconing
```

Resultado esperado:
- Código `0` si estructura/JSON/status son válidos
- Código `1` y errores claros si hay problemas

### 4.4 Preparar solve con Codex

```bash
bluebox solve ./suspicious-beaconing --no-launch
```

Modo real (si tienes `codex` instalado):

```bash
bluebox solve ./suspicious-beaconing
```

Resultado esperado:
- `.codex/context.md` actualizado
- `.codex/prompt.txt` actualizado
- `meta/commands.log` con eventos
- Estado a `solving`

### 4.5 Consultar estado operativo

```bash
bluebox status ./suspicious-beaconing
```

Muestra:
- case, title, status, category
- artifacts count
- active hypotheses count
- latest changelog entry

### 4.6 Generar writeup final

Caso resuelto (`status=solved`):

```bash
bluebox finalize ./suspicious-beaconing
```

Caso no resuelto (incompleto explícito):

```bash
bluebox finalize ./suspicious-beaconing --allow-incomplete
```

Resultado esperado:
- `notes/writeup_final.md` generado
- Si estaba en `solved`, pasa a `finalized`

## 5) Ejemplo público seguro

Puedes usar los artefactos sintéticos incluidos:

```bash
bluebox init "Safe Demo" \
  --artifacts ./examples/safe-demo/artifacts \
  --title "Safe Demo"

bluebox classify ./safe-demo
bluebox validate ./safe-demo
bluebox solve ./safe-demo --no-launch
bluebox status ./safe-demo
bluebox finalize ./safe-demo --allow-incomplete
```

## 6) Comandos de referencia rápida

```bash
bluebox version
bluebox doctor
bluebox tools list
bluebox tools check base
bluebox tools install network
bluebox tools install network --apply
bluebox init <name> --artifacts <path> --title <title>
bluebox classify <case-path>
bluebox validate <case-path>
bluebox solve <case-path> [--no-launch]
bluebox status <case-path>
bluebox finalize <case-path> [--allow-incomplete]
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
