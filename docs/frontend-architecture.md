# Arquitectura e identidad del frontend

Revisión del 12 de septiembre de 2026. Aplicación de consulta en `apps/web`,
con React 19, Vite, TypeScript, TanStack Router/Query y shadcn sobre Base UI.
La investigación de dominio que orienta las pantallas se conserva en
[manuales y diseño](investigacion-manuales-y-diseno.md).

## Responsabilidades

| Capa | Responsabilidad |
| --- | --- |
| `src/routes` | Declaración de rutas y validación de parámetros. El plugin genera `routeTree.gen.ts` y divide el código por ruta. |
| `components/app-shell.tsx` | Composición del marco de navegación, encabezado, contexto de consulta, contenido y pie. |
| `components/layout` | Navegación y cierre del panel móvil, borrador del buscador, cambio de origen, actualización manual y estado de las fuentes. |
| `features/hub/schema.ts` | Contrato remoto validado con Zod y tipos derivados; conserva nulabilidad, fuente, IDs y fechas. |
| `features/hub/api.ts` | Petición HTTP al backend, cancelación y validación de JSON, versión y modo solicitado. No conoce React ni el router. |
| `features/hub/queries.ts` | `queryOptions` y hook `useHub`: une el modo y búsqueda de la URL con la caché de React Query. |
| `features/hub/selectors.ts` | Derivaciones puras: filtro de maquinaria y relación solicitud–unidad–tarea por IDs. |
| `features/hub/components` | Componentes acotados: tabla de equipos, secuencia operativa, alertas, procedencia, fuentes, métricas, hechos del equipo y registros relacionados. |
| `features/hub/pages` | Composición de las siete vistas; evita un archivo común que importe todas las responsabilidades. |
| `components/ui` | Primitivas instaladas mediante el CLI oficial de shadcn, sin reemplazar su comportamiento accesible. |
| `src/index.css` | Tokens semánticos, tipografía, personalización de las primitivas y adaptación a pantallas. |

Se usan imports directos a componentes. El estado remoto permanece en React
Query; no se replica en un contexto global ni mediante efectos. El único
estado local de producto es el borrador del buscador y el filtro visual de
prioridad. Los conteos y las listas filtradas se derivan durante el render.
El panel de maquinaria recibe su lista y modo, sin construir una respuesta
HTTP artificial para representar un filtro local.

Esta separación aplica la recomendación de React de delimitar componentes y
mantener solamente el estado mínimo necesario. Los valores derivados se
calculan a partir de los datos existentes. [React: Thinking in React](https://react.dev/learn/thinking-in-react).

## Consulta, URL y errores

La clave de caché es `['hub', mode, q]`. Distintos orígenes o búsquedas nunca
comparten resultados. Los consumidores del marco y la página reutilizan esa
consulta. Se transmite `AbortSignal`, se omiten credenciales del navegador,
la frescura es de 60 segundos, no hay reintentos automáticos ni actualización
por foco de ventana. El botón **Actualizar** hace explícita una nueva lectura.
No se emplean datos anteriores como placeholder al cambiar modo o búsqueda.

`queryOptions` centraliza clave, función y política para mantener inferencia
de tipos y evitar configuraciones divergentes. [TanStack Query: Query Options](https://tanstack.com/query/latest/docs/framework/react/guides/query-options).

El router valida `mode` (`fixture` o `live`) y `q` (texto recortado, máximo 100
caracteres). La lista de maquinaria añade su filtro validado. Los controles
de búsqueda y origen preservan los demás parámetros al navegar. El borrador
del buscador se reinicia con `key={q}` al cambiar la URL, por ejemplo con
Atrás/Adelante, sin un efecto que copie estado remoto. Un modo inválido produce
el error de ruta; no se convierte en una demostración. [TanStack Router: Search Params](https://tanstack.com/router/latest/docs/guide/search-params).

`HubBoundary` presenta carga, error con reintento y aviso de cobertura parcial.
Una respuesta incompatible o de otro modo se rechaza antes del render.
El marco oculta datos conservados en caché si la nueva lectura produce error.
Los valores desconocidos permanecen nulos y se muestran como ausencia de
información, no como cero. La API es la única fuente de fixtures: no existe
fallback entre ejemplos locales y sandbox.

## Jerarquía operativa

La vista general comienza con indicadores del alcance y una tabla que sigue
**proyecto/solicitud → unidad asignada → tarea de traslado → evidencia**.
Cada tarea de esa tabla debe tener el mismo `request_id` que la solicitud.
Un vínculo confirmado de la maquinaria no acredita otra solicitud del mismo
equipo. Si no hay tarea coincidente, la fila dice **Traslado por vincular**.
Los tests cubren varias tareas de una solicitud, otra solicitud de la misma
unidad, falta de asignación y equipo fuera de la consulta.

El estado administrativo, mantenimiento, estado de tarea y ubicación se
presentan por separado. La ficha conserva la clave logística y el número de
activo contable como campos diferentes, además de la procedencia de equipo,
solicitudes, tareas y ubicación. El cierre de una tarea y una geocerca no se
convierten en evidencia de recepción física. No se infieren categorías de
estados personalizados de Startrack sin el catálogo validado del proveedor.

Los enlaces externos de Fuentes abren los sandboxes y los manuales oficiales
en otra pestaña con `noopener noreferrer`. No se inventan enlaces profundos
a registros ni acciones de modificación. Esta etapa no añade login ni cambia
la habilitación del modo live.

## Identidad visual y accesibilidad

Se revisó visualmente el [sitio público de ECON](https://econ.com.sv/) y sus
activos el **12/09/2026**. Su cabecera usa la marca blanca sobre azul, y el CSS
del sitio repite `#144f81`, `#9E9884` y las familias Roboto Condensed e Inter.
Estos son referentes observados; no constituyen un manual de marca aprobado.
El tema del hub adapta esos referentes con superficies claras, bordes rectos,
encabezados condensados y texto de lectura Inter. Evita fotografías de obras
que podrían confundirse con datos operativos.

El preset `b0` queda documentado como punto de partida. La solicitud explícita
del usuario autoriza personalizar su apariencia: `--radius: 0`, tokens ECON,
tablas y navegación propias. Se mantienen `Button`, `ToggleGroup`, `Sidebar`,
`Alert`, `Empty`, `Table`, `Field` y otras primitivas generadas. Se consultaron
los comandos `shadcn docs` y la documentación Base UI antes de componerlas.
[shadcn: Theming](https://ui.shadcn.com/docs/theming),
[shadcn: Sidebar](https://ui.shadcn.com/docs/components/base/sidebar),
[shadcn: Button](https://ui.shadcn.com/docs/components/base/button).

La jerarquía usa texto operativo de 13 px, metadatos de 11–12 px, indicadores
tabulares y fuentes locales. En móvil la búsqueda usa 16 px. La navegación
usa el panel accesible de shadcn, las tablas conservan desplazamiento
horizontal, los focos permanecen visibles y se respeta movimiento reducido.

### Activos preservados

Descargas directas, sin edición de los PNG, realizadas el **12/09/2026**.
Se sirven desde `apps/web/public/brand`, sin hotlinks al sitio corporativo.
La marca pertenece a Grupo ECON.

| Archivo | Fuente oficial | SHA-256 |
| --- | --- | --- |
| `econ-white.png` | [Logo blanco](https://econ.com.sv/wp-content/uploads/2025/01/LOGOS_ECON_VERSION-BLANCO-01.png) | `3dc975d787e2b5144d6908fd17300bdbad03451b066e82397539f5869618a897` |
| `econ-color.png` | [Logo a color](https://econ.com.sv/wp-content/uploads/2024/09/LOGO1_ECON.png) | `f4299912e5967fdafa32cfc531fc63c5206e074f80a7c521a6b610a7a95fe212` |
| `econ-icon.png` | [Favicon corporativo](https://econ.com.sv/wp-content/uploads/2025/01/cropped-logo_Mesa-de-trabajo-1-1-32x32.png) | `eab8457fef6decac21496ad79f2d3ee2f8fd35b9d9e954b95c8ddefa8d12c326` |

Inter y Roboto Condensed se distribuyen con los paquetes Fontsource Variable
5.3.0, licencia OFL-1.1 incluida en los paquetes. Se cargan únicamente sus
archivos WOFF2 latinos. La tipografía no genera solicitudes a Google Fonts.
[Fontsource: Roboto Condensed](https://fontsource.org/fonts/roboto-condensed).

## Verificación

Los tests de contrato verifican ausencia de fallback, separación de caché,
modo devuelto, cancelación, parámetros inválidos y métricas desconocidas.
Los tests de relaciones verifican que las tareas pertenecen a la solicitud
exacta. Ejecutar `npm run lint`, `npm run test`, `npm run build` y
`npm run deploy:check` en `apps/web`. El último es una comprobación local de
Wrangler con `--dry-run`; no publica el sitio.
