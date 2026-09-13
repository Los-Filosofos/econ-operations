<!-- econ-audit:2026-09-12:durable-inbox -->

Existe historial operativo y una cola segura de salida, pero no un receptor desacoplado, inbox ni progreso durable del consumidor. El dibujo de integración y la propuesta local de eventos aún no se traducen en una entrada verificable. El contrato aportado de Prisma no publica webhooks; Startrack documenta alertas y ubicaciones, sin acreditar eventos generales de tareas.

**Prioridad:** P1. **Frente sugerido:** Arquitectura e integraciones. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/models/operations.py:16](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/models/operations.py#L16), [apps/api/app/models/operations.py:54](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/models/operations.py#L54), [apps/api/app/models/operations.py:74](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/models/operations.py#L74) y [apps/api/app/main.py:84](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/main.py#L84). Fuentes: [webhooks Startrack](https://support.gps-platform.com/admin/webhooks/), [configuración de reenvío](https://support.gps-platform.com/admin/api/webhooks/) y `econ-hackathon-openapi.json`.

## Criterios de aceptación

- [ ] Acordar un sobre versionado con fuente, cuenta, entorno, entidad/ID, identidad de evento o huella documentada, fecha del hecho, recepción y versión cuando exista.
- [ ] Implementar inbox transaccional en PostgreSQL y alimentación desde polling; añadir solo webhooks con contrato y mecanismo de autenticación efectivamente validados, aislados del dashboard.
- [ ] Confirmar entrega HTTP únicamente después de persistir; deduplicar atómicamente y conservar inválidos/ambiguos con causa, reintentos acotados y cola de revisión.
- [ ] Procesar hechos con checkpoint y orden por entidad; un replay reconstruye resultados locales sin repetir POST de tareas ni declaraciones de recepción.
- [ ] Verificar duplicado, desorden, caída después de persistir y antes/después de procesar, mensaje inválido y cambio de dispositivo.
- [ ] Validar unidades y formatos con muestras autorizadas: la documentación de alertas describe segundos pero ejemplifica valores de milisegundos; Json2 presenta coordenadas con escala no aclarada. No adivinar conversiones.
- [ ] Mantener polling de conciliación para Prisma y tareas; mantener defaults live deshabilitados y la conciliación unknown actual. Registrar ADR; incorporar broker solo si una prueba de carga demuestra necesidad.

## Relación con el backlog y alcance

Ampliación de arquitectura solicitada ahora, distinta del polling de [econ-protocol#7](https://github.com/Los-Filosofos/econ-protocol/issues/7) y del SDK de [econ-protocol#10](https://github.com/Los-Filosofos/econ-protocol/issues/10). La habilitación del proveedor continúa relacionada con [econ-protocol#2](https://github.com/Los-Filosofos/econ-protocol/issues/2). La primera entrega puede validarse con entradas controladas sin publicar un receptor.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
