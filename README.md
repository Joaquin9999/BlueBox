# BlueBox

`BlueBox` es una CLI para **CTFs** (especialmente forense/Blue Team) que te ayuda a:

- organizar casos de forma reproducible,
- preparar un entorno de trabajo con herramientas Blue Team,
- y dejar el workspace listo para trabajo eficiente con agentes (Codex/LLM).

Está pensada para reducir fricción operativa y reducir desperdicio de tokens en análisis asistido por IA.

## ¿Qué resuelve?

En vez de carpetas ad-hoc por reto, BlueBox crea un flujo estable:

- entrada de evidencia (`inbox/`),
- workspace de caso (`cases/<nombre>/`),
- reportes y salida final (`work/reports/`, `output/`),
- contexto compacto para agentes (`agent/context.md`, `agent/handoff.md`).

## Instalación rápida (recomendada con entorno virtual)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
bluebox --help
```

## Flujo recomendado (operador CTF / Blue Team)

```bash
bluebox wizard
bluebox setup --profile all
bluebox new
bluebox inspect
bluebox run --no-launch
bluebox info
bluebox next
```

Flujo corto para demo:

```bash
bluebox new --name "Safe Demo" --artifacts ./examples/safe-demo/artifacts --title "Safe Demo"
bluebox inspect
bluebox check
bluebox run --no-launch
bluebox report --allow-incomplete
```

## Comandos clave

### Product UX

- `bluebox new`: crea caso de forma segura.
- `bluebox check`: valida estructura y metadata del caso.
- `bluebox inspect`: clasifica el caso y propone dirección inicial.
- `bluebox run`: prepara/lanza flujo de agente.
- `bluebox info`: estado operativo enriquecido del caso.
- `bluebox report`: genera writeup final.
- `bluebox home`: dashboard rápido.
- `bluebox next`: sugiere siguiente acción.
- `bluebox handoff`: resumen corto para transferencia entre analistas/agentes.
- `bluebox summary`: resumen compacto del caso.
- `bluebox summarize <archivo>`: convierte salidas grandes en reportes compactos.

### Gestión de casos activos

- `bluebox cases list/current/use/open/clear/archive/clone`
- aliases cortos: `bluebox use`, `bluebox current`, `bluebox open`

### Tooling Blue Team / DFIR

- `bluebox tools profiles`
- `bluebox tools list`
- `bluebox tools check <profile>`
- `bluebox tools install <profile>`
- `bluebox tools install <profile> --apply`

Perfiles principales:

- `base`
- `forensics-core`
- `pcap`
- `windows-dfir`
- `memory`
- `malware`
- `ctf-blue`
- `all`

Cuando hay caso activo, `tools install` puede dejar reporte en:

- `cases/<case>/work/reports/tooling_status.md`

## Entorno virtual vs herramientas del sistema

- `bluebox` (paquete Python) vive donde lo instales (idealmente `.venv`).
- Las herramientas de `tools install --apply` se instalan en el **host** (brew/apt/pip según disponibilidad), no solo dentro del venv.

## Estructura de trabajo

```text
.bluebox/
  active_case.txt
  recent_cases.json
  settings.yaml
inbox/
cases/
exports/
profiles/
```

Cada caso incluye estructura orientada a investigación + agentes:

- `challenge/` (manifest, hashes, referencias)
- `work/` (reportes y derivados)
- `agent/` (contexto/prompt/handoff)
- `memory/` (log cronológico)
- `output/` (flag y writeups)

## Guías

- Uso operativo completo: `USAGE_GUIDE.md`
- Instalación y troubleshooting: `INSTALL.md`
- Ejemplo público seguro: `examples/README.md`

## Pruebas

```bash
source .venv/bin/activate
python -m pip install pytest
pytest -q
```

## Modelo de ramas

- `main`: rama de distribución (solo lo necesario para usuarios finales).
- `development`: integración de trabajo y evolución técnica.

## Objetivo del proyecto

BlueBox busca ser una plataforma CLI ligera para CTF/Blue Team que combine:

- disciplina de evidencia,
- automatización operativa,
- y colaboración fluida con agentes.