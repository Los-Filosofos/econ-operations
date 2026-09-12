# ECON · Hub de Operaciones

Frontend de consulta en español con React, TypeScript, Vite, TanStack Router,
TanStack Query y shadcn/ui. La API FastAPI permanece en `../api`.

## Desarrollo

Requiere Node.js 24.19.0 y la API en el puerto 8000:

```sh
npm ci
npm run dev
```

Abrir `http://127.0.0.1:5173`. La consulta inicial usa ejemplos locales servidos
por la API. El navegador no incluye fixtures ni reemplaza una fuente caída por
datos de ejemplo. «Sandbox en vivo» muestra el estado de los conectores del backend.

Copiar `.env.example` a `.env.local` para ajustar el proxy de desarrollo con
`API_PROXY_TARGET`. Configurar `VITE_API_BASE_URL` con el origen HTTPS público
de la API antes de compilar para Cloudflare. Las variables `VITE_*` se publican
en el navegador y nunca deben contener credenciales.

## Estructura

- `src/routes`: rutas tipadas y partición automática del código.
- `src/features/hub/schema.ts`: validación del contrato remoto y parámetros de URL.
- `src/features/hub/api.ts`: transporte HTTP y validación de las respuestas.
- `src/features/hub/queries.ts`: opciones de caché y conexión de React Query con la URL.
- `src/features/hub/selectors.ts`: filtros y relaciones por identificadores, sin estado duplicado.
- `src/features/hub/components`: tablas, evidencia, indicadores y ficha de maquinaria.
- `src/features/hub/pages`: composición de las siete vistas del hub.
- `src/components/layout`: navegación, búsqueda, origen seleccionado y estado de lectura.
- `src/components/ui`: componentes añadidos con el CLI oficial de shadcn.
- `src/routeTree.gen.ts`: árbol generado por TanStack Router.
- `wrangler.jsonc`: activos estáticos en Workers y fallback de SPA.

Las vistas incluyen resumen, maquinaria y ficha, solicitudes, traslados,
atención y fuentes. `mode` y `q` conservan el origen y la búsqueda en la URL.
La búsqueda admite 100 caracteres y consulta la API. `filter` selecciona los
casos de los indicadores en maquinaria. Cada equipo conserva varios traslados;
sus estados administrativos, tareas, ubicación y mantenimiento están separados.

## Comprobaciones

```sh
npm run lint
npm run test
npm run build
npm run typecheck
npm run deploy:check
```

`build` genera las rutas, compila y comprueba los proyectos TypeScript.
`typecheck` usa `tsc -b`. `deploy:check` compila y ejecuta Wrangler con
`--dry-run`; no publica. `deploy` compila y publica en la cuenta configurada.

## Inicialización reproducible

Desde la raíz, con `apps` creado:

```sh
npx shadcn@latest init --preset b0 --template vite --name web --cwd apps --base base --no-monorepo --yes
```

El CLI resolvió `b0` como Base UI, `base-nova`, colores neutros, Inter y Lucide.
Por indicación del usuario, la apariencia se personalizó con la marca pública
de ECON: azul `#144f81`, logo oficial, esquinas rectas y Roboto Condensed en
encabezados. Inter se conserva para lectura de datos. Las fuentes y logos se
sirven localmente, y se preservan las primitivas accesibles de Base UI.
La [arquitectura del frontend](../../docs/frontend-architecture.md) registra
responsabilidades, decisiones, referencias y procedencia de estos activos.
El frontend tiene su propio lockfile; no necesita un workspace JavaScript ni
servidor SSR para desplegar activos.

Consultar [desarrollo](../../docs/desarrollo.md), la
[decisión de frontend](../../docs/adr/0001-web-platform.md), el
[despliegue Cloudflare](../../docs/deploy-cloudflare.md) y el
[modelo operativo](../../docs/modelo-operativo.md).
