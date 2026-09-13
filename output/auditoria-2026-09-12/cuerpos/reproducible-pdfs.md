<!-- econ-audit:2026-09-12:reproducible-pdfs -->

output/pdf contiene decisiones (2 páginas), dossier visual (15) y diccionario/mapeo/manual (34). Los scripts documentados solo construyen y comprueban los dos primeros; no aparece el generador del manual completo. El diccionario de modelos sí tiene --check funcional. Los scripts y PDFs son archivos locales aún no versionados en la rama auditada.

**Prioridad:** P2. **Frente sugerido:** Documentación y herramientas. Asignación personal pendiente de reparto del equipo.

## Evidencia

Trabajo local: `docs/entregables-visuales.md:15` y `:155`; `scripts/docs/generar_dossier.py:890` solo llama build_dossier/build_decisions, mientras `:838` referencia el tercer PDF. [scripts/check.ps1:6](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/scripts/check.ps1#L6) limita Ruff a apps/api.

## Criterios de aceptación

- [ ] Incorporar el generador del manual/matriz completo y documentar un comando que regenere los tres PDFs desde fuentes editables.
- [ ] Documentar dependencias y fuentes tipográficas para una máquina limpia sin paths personales ni llamadas a proveedores.
- [ ] Verificar existencia, restricciones de páginas aplicables, contenido requerido, referencias y relación con el inventario actualizado.
- [ ] Añadir comprobación apropiada para scripts/artefactos documentales y revisión visual del resultado; mantener --check del diccionario.
- [ ] Dejar el conjunto listo para versionado y revisión, sin alterar fuentes originales ni mezclar evidencias locales con entregas ya publicadas.

## Relación con el backlog y alcance

Brecha nueva de reproducibilidad del paquete documental local; no declara ausentes los PDFs que ya existen.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
