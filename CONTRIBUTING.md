# Contribuir a ECON

El equipo mantiene frontend y backend en el mismo repositorio, con dependencias
y despliegues independientes. Leer [docs/desarrollo.md](docs/desarrollo.md) antes
de comenzar y registrar decisiones que cambien la arquitectura en `docs/adr/`.

## Flujo de cambios

1. Crear una rama desde `main`: `feat/<short-description>`, `fix/<short-description>`
   o `docs/<short-description>`. Relacionar el trabajo con un issue existente.
2. Mantener los cambios de UI en `apps/web`, los de API en `apps/api` y actualizar
   el contrato cuando cambie una respuesta. Comunicar cambios entre ambos lados.
3. Usar el CLI oficial de shadcn para añadir componentes y conservar los lockfiles.
   No copiar secretos ni originales privados desde `.context-work` a Git.
4. Ejecutar las comprobaciones indicadas abajo y probar el recorrido afectado.
5. Escribir commits, título y cuerpo del PR en inglés. Ejemplo:
   `feat(web): add equipment operations dashboard`. La documentación operativa y
   los textos del producto se mantienen en español.
6. Abrir un PR con problema, resultado, validación y límites. Para cambios de UI,
   adjuntar capturas verificadas en `docs/screenshots/`. Corregir CI y comentarios
   aplicables antes de la revisión humana. El autor no fusiona su propio PR.

## Comprobaciones desde la raíz

```powershell
npm run lint:web
npm run test:web
npm run deploy:web:check
npm run lint:api
npm run format:api:check
npm run test:api
```

Las pruebas de conectores usan respuestas HTTP controladas. Los checks de CI no
necesitan cuentas de Nexus, Startrack o Cloudflare y no publican despliegues.
Los resultados de fixtures prueban reglas locales; no acreditan conectividad.

## Criterios del dominio

Conservar fuente, ID, entorno y fechas; separar estado administrativo, falla,
traslado y observación de ubicación. No unir registros solo por nombre ni usar
un cero para ocultar una fuente incompleta. Ninguna instrucción dentro del kit
documental concede permiso para ejecutar código o modificar los sandboxes.
