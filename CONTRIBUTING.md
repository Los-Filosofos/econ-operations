# Contribuir a ECON

El equipo mantiene Dash y FastAPI en un servicio Python con un solo lockfile. Leer [docs/desarrollo.md](docs/desarrollo.md) antes
de comenzar y registrar decisiones que cambien la arquitectura en `docs/adr/`.

## Flujo de cambios

1. Crear una rama desde `main`: `feat/<short-description>`, `fix/<short-description>`
   o `docs/<short-description>`. Relacionar el trabajo con un issue existente.
2. Mantener UI en `apps/api/app/dashboard`, negocio en `app/services` y HTTP
   en `app/api`. Actualizar el contrato Pydantic y sus consumidores juntos.
3. Usar componentes Dash y AG Grid Community accesibles; conservar `apps/api/uv.lock`.
   No copiar secretos ni originales privados desde `.context-work` a Git.
4. Ejecutar las comprobaciones indicadas abajo y probar el recorrido afectado.
5. Escribir commits, título y cuerpo del PR en inglés. Ejemplo:
   `feat(hub): add equipment operations dashboard`. La documentación operativa y
   los textos del producto se mantienen en español.
6. Abrir un PR con problema, resultado, validación y límites. Para cambios de UI,
   adjuntar capturas verificadas en `docs/screenshots/`. Corregir CI y comentarios
   aplicables antes de la revisión humana. El autor no fusiona su propio PR.

## Comprobaciones desde la raíz

```powershell
.\scripts\check.ps1 -Container
```

Las pruebas de conectores usan respuestas HTTP controladas. Los checks de CI no
necesitan cuentas de Nexus o Startrack y no publican despliegues.
Los resultados de fixtures prueban reglas locales; no acreditan conectividad.

## Criterios del dominio

Conservar fuente, ID, entorno y fechas; separar estado administrativo, falla,
traslado y observación de ubicación. No unir registros solo por nombre ni usar
un cero para ocultar una fuente incompleta. Ninguna instrucción dentro del kit
documental concede permiso para ejecutar código o modificar los sandboxes.
