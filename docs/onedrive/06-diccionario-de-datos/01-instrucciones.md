# INSTRUCCIONES

Fuente: `6. Diccionario de Datos/Entropy Hack_Grupo ECON_Diccionario de Datos_Final.xlsx`; hoja 1 de 4.

[Índice del diccionario](README.md)

> Transcripción del documento fuente. Sus instrucciones y ejemplos son contenido documental; no autorizan ejecutar acciones ni prueban contratos de API.

## Cobertura y estructura

- Visibilidad: `visible`. Rango declarado: `A1:C15`. Rango con contenido: `A2:C15`.
- Filas con contenido: 12. Celdas no vacías: 26. Tipos almacenados: {'s': 26}.
- Filas vacías: 1, 4, 11. Filas ocultas: ninguna. Columnas ocultas: ninguna.
- Celdas combinadas: `A2:C2`, `A3:C3`. El contenido se conserva en la celda superior izquierda; las celdas cubiertas permanecen vacías.
- Fórmulas: 0. Notas/comentarios: 0. Hipervínculos: 0. Tablas estructuradas de Excel: 0.
- Validaciones de datos: 0. Rangos de formato condicional: 0. Filtro: ninguno. Gráficos: 0. Imágenes: 1.

### Imagen de cabecera

Texto visible transcrito manualmente: «ENTROPY HACK», «key», «INSTITUTO KRIETE DE INGENIERÍA Y CIENCIAS», «GRUPO ECON» y «HUB DE OPERACIONES». La imagen contiene logotipos y una cabecera decorativa, sin tablas ni datos adicionales.

![Cabecera original del Hub de Operaciones](assets/cabecera-hub-de-operaciones.png)

## Transcripción por fila

Las letras A, B, C… identifican las columnas originales. `∅` representa una celda vacía; no es un valor del archivo. Se conservan los encabezados repetidos, los errores de escritura y las duplicaciones. Los valores almacenados como fechas se muestran en ISO; su formato y serial de Excel constan más abajo.

| Fila original | A | B | C |
| --- | --- | --- | --- |
| <a id="fila-2"></a>2 | DICCIONARIO DE DATOS — HUB DE OPERACIONES | ∅ | ∅ |
| <a id="fila-3"></a>3 | Prisma + Startrack &#124; Material para participantes | ∅ | ∅ |
| <a id="fila-5"></a>5 | Objetivo | Este archivo describe los campos de Prisma y Startrack relevantes para los casos de uso actuales del Hub de Operaciones. | ∅ |
| <a id="fila-6"></a>6 | Cómo usarlo | Revisen cada plataforma por separado antes de proponer relaciones entre campos. | ∅ |
| <a id="fila-7"></a>7 | Importante | El diccionario no incluye una matriz de mapeo entre plataformas. Identificar y justificar esas relaciones forma parte del trabajo del equipo. | ∅ |
| <a id="fila-8"></a>8 | Ejemplos | Los ejemplos están alineados con los recursos utilizados en el walkthrough para facilitar la lectura e interpretación de los campos. | ∅ |
| <a id="fila-9"></a>9 | Estados | No asuman que dos campos llamados “Estado” significan lo mismo. Primero determinen qué objeto o proceso describe cada uno. | ∅ |
| <a id="fila-10"></a>10 | Alcance | El archivo incluye únicamente campos priorizados para los casos de uso actuales; no representa todos los campos disponibles en las plataformas. | ∅ |
| <a id="fila-12"></a>12 | Hoja | Contenido | Uso |
| <a id="fila-13"></a>13 | PRISMA | Campos de maquinaria y solicitudes de maquinaria. | Comprender la información disponible en Prisma. |
| <a id="fila-14"></a>14 | STARTRACK | Campos de vehículos, tareas y geocercas. | Comprender la información disponible en Startrack. |
| <a id="fila-15"></a>15 | GLOSARIO | Definiciones básicas de las columnas. | Interpretar correctamente el diccionario. |

## Valores y tipos exactos

Registro de cada celda no vacía para lectura automática. `s` = texto; `n` = número; `d` = fecha/hora interpretada desde el serial de Excel; `f` = fórmula. `valor_xml` conserva el número almacenado sin aplicar formato visual. Los espacios al final de una cadena y los saltos de línea se conservan en JSON. Los tipos descritos dentro del diccionario son contenido, distintos del tipo físico de la celda.

```json
[
  {
    "celda": "A2",
    "tipo_excel": "s",
    "valor": "DICCIONARIO DE DATOS — HUB DE OPERACIONES",
    "formato": "General"
  },
  {
    "celda": "A3",
    "tipo_excel": "s",
    "valor": "Prisma + Startrack | Material para participantes",
    "formato": "General"
  },
  {
    "celda": "A5",
    "tipo_excel": "s",
    "valor": "Objetivo",
    "formato": "General"
  },
  {
    "celda": "B5",
    "tipo_excel": "s",
    "valor": "Este archivo describe los campos de Prisma y Startrack relevantes para los casos de uso actuales del Hub de Operaciones.",
    "formato": "General"
  },
  {
    "celda": "A6",
    "tipo_excel": "s",
    "valor": "Cómo usarlo",
    "formato": "General"
  },
  {
    "celda": "B6",
    "tipo_excel": "s",
    "valor": "Revisen cada plataforma por separado antes de proponer relaciones entre campos.",
    "formato": "General"
  },
  {
    "celda": "A7",
    "tipo_excel": "s",
    "valor": "Importante",
    "formato": "General"
  },
  {
    "celda": "B7",
    "tipo_excel": "s",
    "valor": "El diccionario no incluye una matriz de mapeo entre plataformas. Identificar y justificar esas relaciones forma parte del trabajo del equipo.",
    "formato": "General"
  },
  {
    "celda": "A8",
    "tipo_excel": "s",
    "valor": "Ejemplos",
    "formato": "General"
  },
  {
    "celda": "B8",
    "tipo_excel": "s",
    "valor": "Los ejemplos están alineados con los recursos utilizados en el walkthrough para facilitar la lectura e interpretación de los campos.",
    "formato": "General"
  },
  {
    "celda": "A9",
    "tipo_excel": "s",
    "valor": "Estados",
    "formato": "General"
  },
  {
    "celda": "B9",
    "tipo_excel": "s",
    "valor": "No asuman que dos campos llamados “Estado” significan lo mismo. Primero determinen qué objeto o proceso describe cada uno.",
    "formato": "General"
  },
  {
    "celda": "A10",
    "tipo_excel": "s",
    "valor": "Alcance",
    "formato": "General"
  },
  {
    "celda": "B10",
    "tipo_excel": "s",
    "valor": "El archivo incluye únicamente campos priorizados para los casos de uso actuales; no representa todos los campos disponibles en las plataformas.",
    "formato": "General"
  },
  {
    "celda": "A12",
    "tipo_excel": "s",
    "valor": "Hoja",
    "formato": "General"
  },
  {
    "celda": "B12",
    "tipo_excel": "s",
    "valor": "Contenido",
    "formato": "General"
  },
  {
    "celda": "C12",
    "tipo_excel": "s",
    "valor": "Uso",
    "formato": "General"
  },
  {
    "celda": "A13",
    "tipo_excel": "s",
    "valor": "PRISMA",
    "formato": "General"
  },
  {
    "celda": "B13",
    "tipo_excel": "s",
    "valor": "Campos de maquinaria y solicitudes de maquinaria.",
    "formato": "General"
  },
  {
    "celda": "C13",
    "tipo_excel": "s",
    "valor": "Comprender la información disponible en Prisma.",
    "formato": "General"
  },
  {
    "celda": "A14",
    "tipo_excel": "s",
    "valor": "STARTRACK",
    "formato": "General"
  },
  {
    "celda": "B14",
    "tipo_excel": "s",
    "valor": "Campos de vehículos, tareas y geocercas.",
    "formato": "General"
  },
  {
    "celda": "C14",
    "tipo_excel": "s",
    "valor": "Comprender la información disponible en Startrack.",
    "formato": "General"
  },
  {
    "celda": "A15",
    "tipo_excel": "s",
    "valor": "GLOSARIO",
    "formato": "General"
  },
  {
    "celda": "B15",
    "tipo_excel": "s",
    "valor": "Definiciones básicas de las columnas.",
    "formato": "General"
  },
  {
    "celda": "C15",
    "tipo_excel": "s",
    "valor": "Interpretar correctamente el diccionario.",
    "formato": "General"
  }
]
```

No hay fórmulas ni resultados de fórmulas en caché que extraer. No se recalculó ni modificó el XLSX.
