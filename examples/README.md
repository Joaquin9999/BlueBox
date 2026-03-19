# BlueBox Examples

Este directorio contiene ejemplos **públicos y seguros** para demostrar flujo del CLI.

## Contenido

- `safe-demo/`: artefactos sintéticos sin datos sensibles.
- Formatos demo versionados: `.txt` (compatibles con reglas de `.gitignore` actuales).

## Flujo recomendado

```bash
bluebox init --name "Safe Demo" --artifacts ./examples/safe-demo/artifacts --title "Safe Demo"
bluebox classify ./safe-demo
bluebox validate ./safe-demo
bluebox solve ./safe-demo --no-launch
bluebox status ./safe-demo
bluebox finalize ./safe-demo --allow-incomplete
```

> Nota: estos datos son ficticios y solo de demostración.
