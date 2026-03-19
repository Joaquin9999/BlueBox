# BlueBox Release Checklist

## Objetivo

Checklist mínimo para cortes estables del proyecto en GitHub.

## Pre-release

- Estar en `main` sincronizado con `origin/main`.
- Verificar working tree limpio (`git status`).
- Ejecutar suite completa:
  - `python -m pip install .`
  - `pytest -q`
- Ejecutar smoke de flujo base:
  - `bluebox init`
  - `bluebox classify`
  - `bluebox validate`
  - `bluebox solve --no-launch`
  - `bluebox status`
  - `bluebox finalize --allow-incomplete`

## Seguridad para repo público

- No incluir secretos, tokens o credenciales.
- No incluir artefactos privados o sensibles.
- Revisar archivos nuevos en `examples/` para asegurar que son sintéticos.

## Tag y publicación

- Crear tag anotado:
  - `git tag -a vX.Y.Z -m "release: vX.Y.Z"`
- Publicar `main` y tag:
  - `git push origin main`
  - `git push origin vX.Y.Z`

## Post-release

- Verificar presencia del tag en remoto:
  - `git ls-remote --tags origin`
- (Opcional) Crear release en GitHub con resumen de cambios por fase.
