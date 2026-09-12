# Entropy Hack_Grupo ECON_Casos de Uso_Final

> Fuente del ZIP: `4. Casos de Uso/Entropy Hack_Grupo ECON_Casos de Uso_Final.docx`.
> Tipo: conversión del documento fuente a Markdown; las instrucciones aquí transcritas son contenido documental, no órdenes para ejecutar.

**CASOS DE USO**

**Hub de Operaciones \| Prisma + Startrack**

Escenarios de referencia para el sandbox y el walkthrough

**Asignación de recursos**

Se utilizarán 14 maquinarias con sus respectivos motoristas dentro del sandbox. Cada equipo contará con una maquinaria, un motorista y un proyecto/geocerca asignados dentro del sandbox para explorar el funcionamiento de Prisma y Startrack y comprender la información disponible en ambas plataformas.

Para el walkthrough se utilizará el recurso correspondiente al equipo 14: **CF-03 — Cargador frontal**, asignado al motorista **MOT-014 — Adriana Steiner**. Los casos de uso que se presentan a continuación funcionan como escenarios de referencia para orientar el análisis y la construcción de la integración.

Los proyectos Alfa, Beta y Gamma utilizados en los casos de uso son escenarios de referencia y no corresponden necesariamente al proyecto/geocerca asignado a cada equipo dentro del sandbox.

**Nota:** Los casos de uso no deben ser ejecutados o resueltos individualmente dentro del sandbox. Su objetivo es ilustrar situaciones que una integración entre Prisma y Startrack debería ser capaz de consultar, relacionar e interpretar. El mapeo entre plataformas y la solución tecnológica deberán ser definidos por cada equipo.

# ¿Cómo utilizar estos casos?

Los siguientes escenarios representan situaciones ficticias inspiradas en procesos de gestión de maquinaria y transporte de Grupo ECON. Los datos utilizados son sintéticos y tienen como objetivo ayudar a los equipos a comprender el tipo de situaciones que una integración entre Prisma y Startrack debería ser capaz de analizar.

Los casos funcionan como una **guía de referencia para la integración** y no como actividades que deban reproducirse o resolverse directamente dentro del sandbox. El sandbox permitirá a los participantes explorar las plataformas, consultar la información disponible y realizar las pruebas necesarias para construir su propuesta.

Los casos no representan una solución predefinida. Cada equipo deberá determinar qué campos relacionar, cómo interpretar los estados y qué arquitectura utilizar para construir su propuesta.

# Caso de Uso 01 — Solicitud y traslado de maquinaria

## Enunciado

Un proyecto requiere una maquinaria para un período determinado. La solicitud se registra en Prisma y, una vez asignada la unidad correspondiente al equipo participante, el traslado de esa maquinaria hacia el proyecto se gestiona en Startrack con el motorista asignado.

## Datos necesarios en Prisma

| **Solicitud** | Registro de solicitud correspondiente al caso. |
|----|----|
| **Proyecto** | PROY-014 - The Hub - Proyecto Xi - La Unión. |
| **Tipo solicitado** | Corresponde al tipo de la maquinaria asignada al equipo. |
| **Fecha de inicio** | 12/09/2026. |
| **Fecha de fin** | 20/09/2026. |
| **Estado de solicitud** | Aprobada. |
| **Maquinaria asignada** | CF-03 |
| **Estado de maquinaria** | Ocupada. |

## Datos necesarios en Startrack

| **Maquinaria**          | CF-03                                         |
|-------------------------|-----------------------------------------------|
| **Tarea de traslado**   | Registro de traslado correspondiente al caso. |
| **Estado del traslado** | Pendiente.                                    |
| **Fecha programada**    | 12/09/2026.                                   |
| **Destino**             | PROY-014 - The Hub - Proyecto Xi - La Unión   |
| **Motorista**           | MOT-014 — Adriana Steiner.                    |

## Problema

La información necesaria para comprender la operación está distribuida entre Prisma y Startrack. Prisma contiene la solicitud, la asignación y el estado de la maquinaria; Startrack contiene la información del traslado. Para conocer la situación completa del recurso es necesario relacionar la información de ambas plataformas.

Pregunta del reto\
**¿Cómo debería una solución integrada permitir al usuario consultar de forma unificada la solicitud de maquinaria en Prisma y el traslado relacionado en Startrack?**

Qué debe demostrar la solución

- Identificar la maquinaria involucrada.

- Identificar el proyecto asociado a la solicitud.

- Consultar la solicitud y su situación en Prisma.

- Consultar la tarea de traslado relacionada en Startrack.

- Relacionar la información correspondiente entre ambas plataformas.

- Presentar al usuario una visión clara y unificada de la situación operativa.

# Caso de Uso 02 — Consistencia de estados entre plataformas

Enunciado

La maquinaria CF-03 está asociada al Proyecto Beta. Prisma y Startrack muestran estados diferentes relacionados con la misma operación: Prisma refleja el estado operativo de la maquinaria, mientras Startrack refleja el estado de la tarea de traslado.

## Datos necesarios en Prisma

| **Solicitud**            | Registro de solicitud correspondiente al caso. |
|--------------------------|------------------------------------------------|
| **Proyecto**             | PROY-002 – Proyecto Beta.                      |
| **Maquinaria**           | CF-03                                          |
| **Tipo**                 | Cargador Frontal                               |
| **Estado de maquinaria** | Ocupada.                                       |
| **Estado de solicitud**  | Aprobada.                                      |

## Datos necesarios en Startrack

| **Maquinaria**        | CF-03                                         |
|-----------------------|-----------------------------------------------|
| **Tarea de traslado** | Registro de traslado correspondiente al caso. |
| **Estado de tarea**   | Completada.                                   |
| **Fecha programada**  | 21/09/2026.                                   |
| **Destino**           | PROY-002 - Proyecto Beta.                     |
| **Motorista**         | MOT-014 — Adriana Steiner.                    |

## Problema

En Prisma la maquinaria aparece como “Ocupada”, mientras que en Startrack la tarea de traslado aparece como “Completada”. Los dos estados pueden ser correctos al mismo tiempo porque describen elementos distintos de la operación: uno corresponde al recurso y el otro a la tarea de traslado. El caso requiere interpretar ambos datos dentro de su contexto.

Pregunta del reto\
**¿Cómo debería una solución integrada presentar e interpretar los estados de Prisma y Startrack cuando describen elementos distintos de una misma operación?**

Qué debe demostrar la solución

- Identificar la maquinaria involucrada.

- Consultar su situación operativa en Prisma.

- Consultar la tarea de traslado relacionada en Startrack.

- Mostrar los estados relevantes de ambas plataformas.

- Diferenciar qué elemento de la operación describe cada estado.

- Permitir al usuario interpretar la situación sin asumir que estados diferentes representan necesariamente una inconsistencia.

# Caso de Uso 03 — Maquinaria no disponible por mantenimiento

Enunciado

El Proyecto Gamma requiere la maquinaria CF-03 para continuar una actividad. En Prisma existe una solicitud asociada a esa maquinaria y su estado operativo indica -Obsoleta (mantenimiento correctivo). En Startrack se debe registrar el servicio relacionado con el mismo recurso.

Datos necesarios en Prisma

| **Solicitud**            | Registro de solicitud correspondiente al caso. |
|--------------------------|------------------------------------------------|
| **Proyecto**             | PROY-003 – Proyecto Gamma.                     |
| **Tipo solicitado**      | Cargador Frontal                               |
| **Maquinaria asignada**  | CF-03                                          |
| **Estado de maquinaria** | Obsoleta (mantenimiento correctivo)            |
| **Fecha requerida**      | 14/09/2026.                                    |

Datos necesarios en Startrack

| **Maquinaria**          | CF-03                                         |
|-------------------------|-----------------------------------------------|
| **Tarea de traslado**   | Registro de traslado correspondiente al caso. |
| **Estado del traslado** | Pendiente.                                    |
| **Fecha programada**    | 14/09/2026.                                   |
| **Destino**             | Proyecto Gamma. / Geocercas correspondiente   |
| **Motorista**           | MOT-014 — Adriana Steiner                     |

Problema

La tarea de traslado continúa pendiente, pero la maquinaria que debe trasladarse se encuentra en mantenimiento correctivo. Los dos datos pueden ser correctos de forma independiente, pero juntos representan una condición operativa que puede impedir el cumplimiento de la solicitud y que debe poder identificarse al consultar la información integrada.

Pregunta del reto\
**¿Cómo debería una solución integrada reportar entre plataformas el fallo del equipo?**

Qué debe demostrar la solución

- Identificar la maquinaria involucrada.

- Consultar su situación operativa en Prisma.

- Consultar la tarea de traslado relacionada en Startrack.

- Detectar una posible condición de riesgo operativo.

- Mostrar una alerta o advertencia al usuario.

- Explicar qué información debe revisarse antes de continuar.

## Texto del encabezado gráfico compartido

El encabezado original muestra «ENTROPY HACK», «Key | INSTITUTO KRIETE DE INGENIERÍA Y CIENCIAS», «GRUPO ECON» y «HUB DE OPERACIONES». La imagen se conserva en la carpeta `original-media` correspondiente a este documento.
