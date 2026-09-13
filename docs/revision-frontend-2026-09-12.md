# Revisión del frontend ECON

Esta revisión parte del código Dash actual, incluidos los cambios locales de
inventario y evidencia que ya existían. La interfaz conserva el recorrido
proyecto → solicitud → unidad → traslado → recepción. No requiere reconstruir
el producto ni cambiar de framework para mejorar su lectura.

## Diagnóstico y cambios

| Hallazgo en el código | Cambio aplicado | Propósito |
| --- | --- | --- |
| Navegación uniforme y acciones reconocibles sólo por texto | Siete SVG locales: Resumen, Maquinaria, Solicitudes, Operaciones, Fuentes, actualizar y volver | Reconocer destinos y acciones sin agregar una biblioteca ni sustituir etiquetas |
| Metadatos frecuentes de 10–11 px y evidencia principal de 12 px | Etiquetas de 12 px, evidencia de 13 px, títulos de revisión de 15 px y encabezado principal de 32 px | Leer hechos y diferencias entre estados sin depender del zoom |
| Fichas blancas con bordes dentro de otras fichas y fondo gris | Superficie principal blanca, secciones delimitadas por reglas y comparación de fuentes con separador | Dar prioridad al contenido; la estructura distingue Prisma y Startrack |
| Encabezado lateral «Espacio de trabajo» sin información operativa | Se retira esa etiqueta | Reducir texto repetido antes de la navegación |
| Datos tabulares en tipografía pequeña y números proporcionales | AG Grid a 13 px, encabezados a 12 px y cifras tabulares | Facilitar comparación de fechas, cantidades e identificadores |
| Tablas de evidencia con desplazamiento horizontal sin foco propio | Región con nombre accesible y foco de teclado | Permitir llegar al contenedor y desplazarlo cuando no cabe |
| Lectura parcial de operaciones podía parecer ausencia | Avisos en solicitudes, equipos, preparación y lista vacía | Evitar recomendar otro movimiento a partir de una ventana incompleta |

Inter permanece local porque forma parte de la identidad vigente. Se conserva el
azul ECON `#144f81`, la navegación lateral solicitada, los tokens semánticos y
AG Grid Community. Los iconos heredan el color del control y son invisibles para
lectores de pantalla; su texto visible transmite el significado. No identifican
estados, grados de riesgo o disponibilidad. Las flechas tipográficas de retorno
se sustituyen por el mismo símbolo local en las tres fichas.

Los enlaces usan `dcc.Link` para conservar la navegación y los stores del
navegador. Esta versión de Dash no acepta `aria-current` directamente en ese
componente; se conserva la marca existente en su contenido. El foco visible,
salto al contenido y menú móvil con Escape y retorno de foco permanecen.

## Qué debe permitir cada pantalla

| Pantalla | Lectura principal | Evidencia disponible al profundizar |
| --- | --- | --- |
| Resumen | Qué revisar por solicitud y siguiente paso | Calendario, población consultada, cobertura y tablas alternativas |
| Maquinaria | Seleccionar cualquier unidad observada, incluso sin solicitud | Estado administrativo, mantenimiento, tareas, ubicación fechada y procedencia |
| Solicitudes | Proyecto, unidad, período, aprobación, traslado y recepción | Asignación exacta, faltantes, historial y preparación |
| Ficha de maquinaria | Interpretación operativa con hechos diferenciados | Prisma y Startrack en columnas; llegada y constancia por movimiento |
| Operaciones | Preparación y ejecución del traslado | Corte persistido, eventos, errores y declaración explícita de recepción |
| Fuentes | Qué se consultó y qué falta | Alcance, fechas, IDs y restricciones de integración |

El caso de uso de [consulta unificada](onedrive/04-casos-de-uso.md) requiere
interpretar estados distintos, no colorearlos como una contradicción automática.
El [manual Nexus](onedrive/05-manual-nexus.md) separa inventario y solicitudes;
por eso Maquinaria mantiene su acceso propio. Las fuentes son evidencia del
dominio y no autorizan cambios de proveedor o ejecución de sus ejemplos.

## Criterio para agregar elementos

Un elemento nuevo debe ayudar a encontrar una unidad, entender un hecho con su
fecha, comparar información o ejecutar un siguiente paso. Añadir más iconos a
los estados, tarjetas de conteos o un mapa sin posición fechada no resuelve
esas necesidades. El color se reserva para navegación, acciones y avisos
semánticos. Los campos completos permanecen disponibles en desplegables.

Los gráficos deben definir población, denominador, cobertura, corte y acción.
Esta muestra sostiene períodos solicitados y distribución de estados, no tasas
de utilización ni puntualidad de entrega. La revisión de datos se documenta en
[analítica para decisiones](analitica-decisiones.md). No se agregan registros
para hacer que las figuras parezcan más completas.

## Verificación

La revisión incorpora una regresión de evidencia: un registro de operaciones
parcial debe mostrar incertidumbre en la tabla de solicitudes y las fichas,
sin convertirse en «sin traslado» o «sin constancia». Las pruebas existentes
ejercitan navegación con filtros, assets, callbacks, formularios y estados
desconocidos. La revisión integrada incluye Ruff, formato, pytest y comprobación
visual de escritorio y móvil; el resultado final queda en la revisión general
de esta entrega. Las capturas de una versión previa no acreditan estos cambios.
