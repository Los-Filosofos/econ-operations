# PRISMA

Fuente: `6. Diccionario de Datos/Entropy Hack_Grupo ECON_Diccionario de Datos_Final.xlsx`; hoja 2 de 4.

[Índice del diccionario](README.md)

> Transcripción del documento fuente. Sus instrucciones y ejemplos son contenido documental; no autorizan ejecutar acciones ni prueban contratos de API.

## Cobertura y estructura

- Visibilidad: `visible`. Rango declarado: `A1:F17`. Rango con contenido: `A1:F17`.
- Filas con contenido: 17. Celdas no vacías: 89. Tipos almacenados: {'s': 89}.
- Filas vacías: ninguna. Filas ocultas: ninguna. Columnas ocultas: ninguna.
- Celdas combinadas: `A1:F1`, `A2:F2`. El contenido se conserva en la celda superior izquierda; las celdas cubiertas permanecen vacías.
- Fórmulas: 0. Notas/comentarios: 0. Hipervínculos: 0. Tablas estructuradas de Excel: 0.
- Validaciones de datos: 0. Rangos de formato condicional: 0. Filtro: ninguno. Gráficos: 0. Imágenes: 0.

## Transcripción por fila

Las letras A, B, C… identifican las columnas originales. `∅` representa una celda vacía; no es un valor del archivo. Se conservan los encabezados repetidos, los errores de escritura y las duplicaciones. Los valores almacenados como fechas se muestran en ISO; su formato y serial de Excel constan más abajo.

| Fila original | A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="fila-1"></a>1 | DICCIONARIO DE DATOS — PRISMA | ∅ | ∅ | ∅ | ∅ | ∅ |
| <a id="fila-2"></a>2 | Campos relevantes para los casos de uso actuales del Hub de Operaciones. | ∅ | ∅ | ∅ | ∅ | ∅ |
| <a id="fila-3"></a>3 | Módulo | Campo | Descripción | Tipo de dato | Ejemplo | Valores posibles |
| <a id="fila-4"></a>4 | Maquinaria | Empresa | Código interno utilizado para identificar el equipo. | Texto / ID | The Hub | Nombres de Equipos de Participantes |
| <a id="fila-5"></a>5 | Maquinaria | No. de activo | Número de activo fijo asociado al equipo. | Texto / ID | CF-03 - Cargador frontal 03 | ∅ |
| <a id="fila-6"></a>6 | Maquinaria | Nombre del equipo | Denominación o descripción del equipo. | Texto | Cargador frontal 03 | ∅ |
| <a id="fila-7"></a>7 | Maquinaria | Clase de equipo | Categoría a la que pertenece la maquinaria. | Catálogo | Cargador frontal  | Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal |
| <a id="fila-8"></a>8 | Maquinaria | Estado | Estado operativo o de disponibilidad de la maquinaria. | Catálogo | Disponible | Disponible; Ocupada; Mant. preventivo; Mant. correctivo; Obsoletas |
| <a id="fila-9"></a>9 | Módulo | Campo | Descripción | Tipo de dato | Ejemplo | Valores posibles |
| <a id="fila-10"></a>10 | Solicitudes de maquinaria | Proyecto | Proyecto asociado a la solicitud de maquinaria. | Texto / ID | PROY-014 - The Hub - Proyecto Xi - La Unión | Proyecto Alfa; Proyecto Beta; Proyecto Gamma... |
| <a id="fila-11"></a>11 | Solicitudes de maquinaria | Tipo | Tipo o clase de maquinaria requerida por el proyecto. | Texto / referencia | Cargador frontal | Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal |
| <a id="fila-12"></a>12 | Solicitudes de maquinaria | Solicita | Solicitante del equipo (Gerente de Proyecto) | Catálogo | María José López Ramírez | Usuario |
| <a id="fila-13"></a>13 | Solicitudes de maquinaria | Período | Fechas desde la cual se requiere la maquinaria. | Fecha | 11/09/2026 - 14/09/2026 | Fechas |
| <a id="fila-14"></a>14 | Solicitudes de maquinaria | Estado de solicitud | Estado actual del flujo de la solicitud. | Texto | Aprobada | Aprobada o Pendiente |
| <a id="fila-15"></a>15 | Solicitudes de maquinaria | Maquinaria | Nombre del equipo asignado a la solicitud | Catálogo | CF-03 - Cargador frontal 03 | Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal + Correlativo |
| <a id="fila-16"></a>16 | Módulo | Campo | Descripción | Tipo de dato | Ejemplo | Valores posibles |
| <a id="fila-17"></a>17 | Mantenimiento | Estado   | Estado de la maquinaria | Catálogo | CF-03 - Obsoleto | ∅ |

## Valores y tipos exactos

Registro de cada celda no vacía para lectura automática. `s` = texto; `n` = número; `d` = fecha/hora interpretada desde el serial de Excel; `f` = fórmula. `valor_xml` conserva el número almacenado sin aplicar formato visual. Los espacios al final de una cadena y los saltos de línea se conservan en JSON. Los tipos descritos dentro del diccionario son contenido, distintos del tipo físico de la celda.

```json
[
  {
    "celda": "A1",
    "tipo_excel": "s",
    "valor": "DICCIONARIO DE DATOS — PRISMA",
    "formato": "General"
  },
  {
    "celda": "A2",
    "tipo_excel": "s",
    "valor": "Campos relevantes para los casos de uso actuales del Hub de Operaciones.",
    "formato": "General"
  },
  {
    "celda": "A3",
    "tipo_excel": "s",
    "valor": "Módulo",
    "formato": "General"
  },
  {
    "celda": "B3",
    "tipo_excel": "s",
    "valor": "Campo",
    "formato": "General"
  },
  {
    "celda": "C3",
    "tipo_excel": "s",
    "valor": "Descripción",
    "formato": "General"
  },
  {
    "celda": "D3",
    "tipo_excel": "s",
    "valor": "Tipo de dato",
    "formato": "General"
  },
  {
    "celda": "E3",
    "tipo_excel": "s",
    "valor": "Ejemplo",
    "formato": "General"
  },
  {
    "celda": "F3",
    "tipo_excel": "s",
    "valor": "Valores posibles",
    "formato": "General"
  },
  {
    "celda": "A4",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "B4",
    "tipo_excel": "s",
    "valor": "Empresa",
    "formato": "General"
  },
  {
    "celda": "C4",
    "tipo_excel": "s",
    "valor": "Código interno utilizado para identificar el equipo.",
    "formato": "General"
  },
  {
    "celda": "D4",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E4",
    "tipo_excel": "s",
    "valor": "The Hub",
    "formato": "General"
  },
  {
    "celda": "F4",
    "tipo_excel": "s",
    "valor": "Nombres de Equipos de Participantes",
    "formato": "General"
  },
  {
    "celda": "A5",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "B5",
    "tipo_excel": "s",
    "valor": "No. de activo",
    "formato": "General"
  },
  {
    "celda": "C5",
    "tipo_excel": "s",
    "valor": "Número de activo fijo asociado al equipo.",
    "formato": "General"
  },
  {
    "celda": "D5",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E5",
    "tipo_excel": "s",
    "valor": "CF-03 - Cargador frontal 03",
    "formato": "General"
  },
  {
    "celda": "A6",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "B6",
    "tipo_excel": "s",
    "valor": "Nombre del equipo",
    "formato": "General"
  },
  {
    "celda": "C6",
    "tipo_excel": "s",
    "valor": "Denominación o descripción del equipo.",
    "formato": "General"
  },
  {
    "celda": "D6",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E6",
    "tipo_excel": "s",
    "valor": "Cargador frontal 03",
    "formato": "General"
  },
  {
    "celda": "A7",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "B7",
    "tipo_excel": "s",
    "valor": "Clase de equipo",
    "formato": "General"
  },
  {
    "celda": "C7",
    "tipo_excel": "s",
    "valor": "Categoría a la que pertenece la maquinaria.",
    "formato": "General"
  },
  {
    "celda": "D7",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E7",
    "tipo_excel": "s",
    "valor": "Cargador frontal ",
    "formato": "General"
  },
  {
    "celda": "F7",
    "tipo_excel": "s",
    "valor": "Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal",
    "formato": "General"
  },
  {
    "celda": "A8",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "B8",
    "tipo_excel": "s",
    "valor": "Estado",
    "formato": "General"
  },
  {
    "celda": "C8",
    "tipo_excel": "s",
    "valor": "Estado operativo o de disponibilidad de la maquinaria.",
    "formato": "General"
  },
  {
    "celda": "D8",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E8",
    "tipo_excel": "s",
    "valor": "Disponible",
    "formato": "General"
  },
  {
    "celda": "F8",
    "tipo_excel": "s",
    "valor": "Disponible; Ocupada; Mant. preventivo; Mant. correctivo; Obsoletas",
    "formato": "General"
  },
  {
    "celda": "A9",
    "tipo_excel": "s",
    "valor": "Módulo",
    "formato": "General"
  },
  {
    "celda": "B9",
    "tipo_excel": "s",
    "valor": "Campo",
    "formato": "General"
  },
  {
    "celda": "C9",
    "tipo_excel": "s",
    "valor": "Descripción",
    "formato": "General"
  },
  {
    "celda": "D9",
    "tipo_excel": "s",
    "valor": "Tipo de dato",
    "formato": "General"
  },
  {
    "celda": "E9",
    "tipo_excel": "s",
    "valor": "Ejemplo",
    "formato": "General"
  },
  {
    "celda": "F9",
    "tipo_excel": "s",
    "valor": "Valores posibles",
    "formato": "General"
  },
  {
    "celda": "A10",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B10",
    "tipo_excel": "s",
    "valor": "Proyecto",
    "formato": "General"
  },
  {
    "celda": "C10",
    "tipo_excel": "s",
    "valor": "Proyecto asociado a la solicitud de maquinaria.",
    "formato": "General"
  },
  {
    "celda": "D10",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E10",
    "tipo_excel": "s",
    "valor": "PROY-014 - The Hub - Proyecto Xi - La Unión",
    "formato": "General"
  },
  {
    "celda": "F10",
    "tipo_excel": "s",
    "valor": "Proyecto Alfa; Proyecto Beta; Proyecto Gamma...",
    "formato": "General"
  },
  {
    "celda": "A11",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B11",
    "tipo_excel": "s",
    "valor": "Tipo",
    "formato": "General"
  },
  {
    "celda": "C11",
    "tipo_excel": "s",
    "valor": "Tipo o clase de maquinaria requerida por el proyecto.",
    "formato": "General"
  },
  {
    "celda": "D11",
    "tipo_excel": "s",
    "valor": "Texto / referencia",
    "formato": "General"
  },
  {
    "celda": "E11",
    "tipo_excel": "s",
    "valor": "Cargador frontal",
    "formato": "General"
  },
  {
    "celda": "F11",
    "tipo_excel": "s",
    "valor": "Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal",
    "formato": "General"
  },
  {
    "celda": "A12",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B12",
    "tipo_excel": "s",
    "valor": "Solicita",
    "formato": "General"
  },
  {
    "celda": "C12",
    "tipo_excel": "s",
    "valor": "Solicitante del equipo (Gerente de Proyecto)",
    "formato": "General"
  },
  {
    "celda": "D12",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E12",
    "tipo_excel": "s",
    "valor": "María José López Ramírez",
    "formato": "General"
  },
  {
    "celda": "F12",
    "tipo_excel": "s",
    "valor": "Usuario",
    "formato": "General"
  },
  {
    "celda": "A13",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B13",
    "tipo_excel": "s",
    "valor": "Período",
    "formato": "General"
  },
  {
    "celda": "C13",
    "tipo_excel": "s",
    "valor": "Fechas desde la cual se requiere la maquinaria.",
    "formato": "General"
  },
  {
    "celda": "D13",
    "tipo_excel": "s",
    "valor": "Fecha",
    "formato": "General"
  },
  {
    "celda": "E13",
    "tipo_excel": "s",
    "valor": "11/09/2026 - 14/09/2026",
    "formato": "General"
  },
  {
    "celda": "F13",
    "tipo_excel": "s",
    "valor": "Fechas",
    "formato": "General"
  },
  {
    "celda": "A14",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B14",
    "tipo_excel": "s",
    "valor": "Estado de solicitud",
    "formato": "General"
  },
  {
    "celda": "C14",
    "tipo_excel": "s",
    "valor": "Estado actual del flujo de la solicitud.",
    "formato": "General"
  },
  {
    "celda": "D14",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E14",
    "tipo_excel": "s",
    "valor": "Aprobada",
    "formato": "General"
  },
  {
    "celda": "F14",
    "tipo_excel": "s",
    "valor": "Aprobada o Pendiente",
    "formato": "General"
  },
  {
    "celda": "A15",
    "tipo_excel": "s",
    "valor": "Solicitudes de maquinaria",
    "formato": "General"
  },
  {
    "celda": "B15",
    "tipo_excel": "s",
    "valor": "Maquinaria",
    "formato": "General"
  },
  {
    "celda": "C15",
    "tipo_excel": "s",
    "valor": "Nombre del equipo asignado a la solicitud",
    "formato": "General"
  },
  {
    "celda": "D15",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E15",
    "tipo_excel": "s",
    "valor": "CF-03 - Cargador frontal 03",
    "formato": "General"
  },
  {
    "celda": "F15",
    "tipo_excel": "s",
    "valor": "Excavadora; Retroexcavadora; Motoniveladora; Minicargador; Cargador frontal + Correlativo",
    "formato": "General"
  },
  {
    "celda": "A16",
    "tipo_excel": "s",
    "valor": "Módulo",
    "formato": "General"
  },
  {
    "celda": "B16",
    "tipo_excel": "s",
    "valor": "Campo",
    "formato": "General"
  },
  {
    "celda": "C16",
    "tipo_excel": "s",
    "valor": "Descripción",
    "formato": "General"
  },
  {
    "celda": "D16",
    "tipo_excel": "s",
    "valor": "Tipo de dato",
    "formato": "General"
  },
  {
    "celda": "E16",
    "tipo_excel": "s",
    "valor": "Ejemplo",
    "formato": "General"
  },
  {
    "celda": "F16",
    "tipo_excel": "s",
    "valor": "Valores posibles",
    "formato": "General"
  },
  {
    "celda": "A17",
    "tipo_excel": "s",
    "valor": "Mantenimiento",
    "formato": "General"
  },
  {
    "celda": "B17",
    "tipo_excel": "s",
    "valor": "Estado  ",
    "formato": "General"
  },
  {
    "celda": "C17",
    "tipo_excel": "s",
    "valor": "Estado de la maquinaria",
    "formato": "General"
  },
  {
    "celda": "D17",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E17",
    "tipo_excel": "s",
    "valor": "CF-03 - Obsoleto",
    "formato": "General"
  }
]
```

No hay fórmulas ni resultados de fórmulas en caché que extraer. No se recalculó ni modificó el XLSX.
