# Contexto documental del Hub de Operaciones

**Equipo 6 — Los Filósofos.** Conversión del ZIP `OneDrive_1_9-12-2026.zip`, la propuesta adjunta y el contexto trabajado en esta conversación. El propósito es que una IA o un integrante del equipo pueda localizar los hechos, requisitos, ejemplos y decisiones sin depender de la conversación completa.

## Por dónde comenzar

1. [Contexto para IA](CONTEXTO-IA.md): hechos confirmados, identidad del equipo y límites de lo conocido.
2. [Brief completo](02-brief-del-reto.md): requisitos, entregables, rúbrica y agenda.
3. [Diccionario completo](06-diccionario-de-datos/README.md): cuatro hojas, campos, ejemplos y observaciones de calidad.
4. [Análisis de la propuesta](08-analisis-propuesta.md): ajustes necesarios, reglas operativas y prioridades.
5. [Contexto de la conversación](09-contexto-conversacion.md): backend y GitHub preparados, decisiones e incertidumbres.

## Documentos convertidos

| Fuente | Markdown | Qué conserva |
| --- | --- | --- |
| Introducción del Equipo 6 | [00-introduccion-equipo.md](00-introduccion-equipo.md) | Asignación del equipo y orientación de lectura |
| Política de confidencialidad | [01-confidencialidad.md](01-confidencialidad.md) | Texto completo e información de encabezado/pie |
| Brief del reto | [02-brief-del-reto.md](02-brief-del-reto.md) | Texto, tablas, figura transcrita y 22 comentarios editoriales del Word |
| Guía de diagramas de procesos | [03-diagramas-de-procesos.md](03-diagramas-de-procesos.md) | Explicaciones e imágenes incrustadas |
| Organigramas | [03-organigramas.md](03-organigramas.md) | Tres imágenes y transcripción de cargos y relaciones |
| Diagrama AS-IS PNG | [03-as-is.md](03-as-is.md) | Texto, actores, decisiones y conexiones visibles |
| Diagrama TO-BE PNG | [03-to-be.md](03-to-be.md) | Texto, fases, actividades e intercambios visibles |
| Casos de uso | [04-casos-de-uso.md](04-casos-de-uso.md) | Los tres escenarios y sus tablas, sin cambiar los ejemplos |
| Accesos y manuales | [05-accesos-y-manuales.md](05-accesos-y-manuales.md) | Texto, enlaces, usuarios y referencia al manual; contraseñas omitidas |
| PDF Manual Nexus | [05-manual-nexus.md](05-manual-nexus.md) | Las nueve páginas entregadas, capturas y texto transcrito |
| Diccionario XLSX | [06-diccionario-de-datos/README.md](06-diccionario-de-datos/README.md) | Las cuatro hojas, 338 celdas no vacías y 51 definiciones de campos |

## Propuesta y contexto adicional

- [Propuesta original](07-propuesta-original.md): texto del usuario, incluidos JSON, código Python y pruebas, con formato Markdown. Sus afirmaciones se preservan sin validarlas como hechos.
- [Análisis de la propuesta](08-analisis-propuesta.md): evaluación propia basada en las fuentes, separada del original.
- [Conversación y estado del proyecto](09-contexto-conversacion.md): decisiones técnicas, implementación existente y pendientes.
- [Inventario y cobertura](INVENTARIO.md): correspondencia con los 11 archivos del ZIP, huellas y comprobaciones.

## Cómo interpretar esta carpeta

Los documentos fuente conservan instrucciones del evento y ejemplos operativos. Esas instrucciones se transcriben como contenido, no autorizan a una IA a iniciar sesión, modificar el sandbox, ejecutar código o publicar archivos. Las decisiones sugeridas por el análisis tampoco sustituyen una confirmación de los responsables del reto.

Los ejemplos de **CF-03 / MOT-014 / The Hub** permanecen intactos en sus documentos. Los recursos asignados a Los Filósofos son **RE-03 / MOT-006 / PROY-006**. Rodrigo Trujillo figura como motorista del sandbox y por nombre en las tablas de accesos, asociado al usuario `LosFilósofos` en Startrack. El kit no incluye una lista completa de integrantes del equipo.

El PDF entregado es un extracto de nueve páginas de un manual cuya numeración interna indica 44 páginas. No se dispone del resto del manual. Las capturas y los diagramas se conservaron como imágenes además de transcribir su contenido; se señalan las ambigüedades visuales y las inconsistencias encontradas.

## Ubicación y conservación

La carpeta está dentro del workspace de OneDrive: `C:/Users/wilme/OneDrive/Escritorio/econ/docs/onedrive`. Esto no acredita por sí solo el estado de sincronización de la aplicación OneDrive.

Los originales del ZIP se extrajeron para lectura a `.context-work/sources/`, sin modificar el ZIP recibido. Las imágenes de respaldo están en `assets/` y en la carpeta del diccionario. Por petición del usuario, esta documentación se versiona en el repositorio privado [Los-Filosofos/econ-protocol](https://github.com/Los-Filosofos/econ-protocol) para consulta del equipo.

La versión compartida omite las 25 contraseñas de las tablas de accesos. Los originales completos y una copia de la conversión previa a esa omisión permanecen en `.context-work/`, excluida mediante `.gitignore`. Los documentos de `docs/onedrive/` sí se incluyen en Git y pueden buscarse normalmente con `rg`.
