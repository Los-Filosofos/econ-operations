# STARTRACK

Fuente: `6. Diccionario de Datos/Entropy Hack_Grupo ECON_Diccionario de Datos_Final.xlsx`; hoja 3 de 4.

[Índice del diccionario](README.md)

> Transcripción del documento fuente. Sus instrucciones y ejemplos son contenido documental; no autorizan ejecutar acciones ni prueban contratos de API.

## Cobertura y estructura

- Visibilidad: `visible`. Rango declarado: `A1:F45`. Rango con contenido: `A1:F45`.
- Filas con contenido: 42. Celdas no vacías: 208. Tipos almacenados: {'s': 197, 'n': 9, 'd': 2}.
- Filas vacías: 15, 22, 34. Filas ocultas: ninguna. Columnas ocultas: ninguna.
- Celdas combinadas: `A15:F15`, `A1:F1`, `A22:F22`, `A2:F2`, `A34:F34`. El contenido se conserva en la celda superior izquierda; las celdas cubiertas permanecen vacías.
- Fórmulas: 0. Notas/comentarios: 0. Hipervínculos: 0. Tablas estructuradas de Excel: 0.
- Validaciones de datos: 0. Rangos de formato condicional: 0. Filtro: ninguno. Gráficos: 0. Imágenes: 0.

## Transcripción por fila

Las letras A, B, C… identifican las columnas originales. `∅` representa una celda vacía; no es un valor del archivo. Se conservan los encabezados repetidos, los errores de escritura y las duplicaciones. Los valores almacenados como fechas se muestran en ISO; su formato y serial de Excel constan más abajo.

| Fila original | A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="fila-1"></a>1 | DICCIONARIO DE DATOS — STARTRACK | ∅ | ∅ | ∅ | ∅ | ∅ |
| <a id="fila-2"></a>2 | Campos relevantes de vehículos, tareas y geocercas para el Hub de Operaciones. | ∅ | ∅ | ∅ | ∅ | ∅ |
| <a id="fila-3"></a>3 | Módulo | Campo | Descripción | Tipo de dato | Ejemplo | Valores posibles |
| <a id="fila-4"></a>4 | Vehículos | Descripción | Nombre o descripción con la que se identifica el activo en Startrack. | Texto | CF-03 | ∅ |
| <a id="fila-5"></a>5 | Vehículos | Estado | Estado actual mostrado para el activo en Startrack. | Catálogo | Normal | ∅ |
| <a id="fila-6"></a>6 | Vehículos | Tipo | Tipo de vehículo o maquinaria. | Catálogo | Cargador frontal | ∅ |
| <a id="fila-7"></a>7 | Vehículos | Año | Año del vehículo. | Texto | 2013 | ∅ |
| <a id="fila-8"></a>8 | Vehículos | Color | Color del vehículo. | Texto | Amarillo | ∅ |
| <a id="fila-9"></a>9 | Vehículos | Marca | Marca del activo. | Texto | Caterpillar | ∅ |
| <a id="fila-10"></a>10 | Vehículos | Modelo | Modelo del activo. | Texto | 950H | ∅ |
| <a id="fila-11"></a>11 | Vehículos | Grupo | Grupo del vehículo. | Catálogo | Vehículos-Hackathon | ∅ |
| <a id="fila-12"></a>12 | Vehículos | Etiquetas | Etiquetas del vehículo. | Catálogo | Equipo 14 - The Hub | ∅ |
| <a id="fila-13"></a>13 | Vehículos | Conductor | Conductor o motorista asignado al activo. | Usuario / referencia | MOT-014 - Adriana Steiner | ∅ |
| <a id="fila-14"></a>14 | Vehículos | ID remoto | Identificador utilizado por la organización para relacionar el activo con reportes o integraciones. | Texto / ID | 78093 | ∅ |
| <a id="fila-16"></a>16 | Geocercas | geocerca_id | Identificador de la geocerca dentro del ejercicio. | Texto / ID | GEO-014 | ∅ |
| <a id="fila-17"></a>17 | Geocercas | Nombre | Nombre con el que se identifica la geocerca. | Texto | PROY-014 - The Hub - Proyecto Xi - La Unión | ∅ |
| <a id="fila-18"></a>18 | Geocercas | Grupo | Grupo de Geocercas. | Catálogo | Geocercas-Hackathon | Personalizable |
| <a id="fila-19"></a>19 | Geocercas | Margen Adicional | Referencia del radio del lugar. | Texto | 1000 | ∅ |
| <a id="fila-20"></a>20 | Geocercas | Latitud | Ubicación de la geocerca expresada mediante coordenadas geográficas. | Coordenada | 133376152 | Asociada a: Geocercas y Puntos de Referencia |
| <a id="fila-21"></a>21 | Geocercas | Longitud | Ubicación de la geocerca expresada mediante coordenadas geográficas. | Coordenada | -878486967 | Asociada a: Geocercas y Puntos de Referencia |
| <a id="fila-23"></a>23 | Tareas | tarea_id | Identificador de la tarea dentro del ejercicio. | Texto / ID | 24 | ∅ |
| <a id="fila-24"></a>24 | Tareas | Título | Nombre principal de la tarea. | TAR-014 | Traslado de cargador frontal CF-03 | ∅ |
| <a id="fila-25"></a>25 | Tareas | Descripción | Información adicional sobre el objetivo de la tarea. | Texto largo | Traslado de cargador frontal | ∅ |
| <a id="fila-26"></a>26 | Tareas | Tipo | Categoría de la tarea. | Catálogo | Trasalado | Personalizable |
| <a id="fila-27"></a>27 | Tareas | Estado | Situación actual de la tarea. | Catálogo | Pendiente | Pendiente; Completada; Cancelada; estados personalizados |
| <a id="fila-28"></a>28 | Tareas | Fecha programada | Fecha programada para la tarea. | Fecha | 12/09/2026 | ∅ |
| <a id="fila-29"></a>29 | Tareas | Origen | Dirección de Origen. | Catálogo | PLANTA ORIGEN | Personalizable: Geocercas y Puntos de Referencia |
| <a id="fila-30"></a>30 | Tareas | Destino | Dirección de Destino. | Catálogo | PROY-014 - The Hub - Proyecto Xi - La Unión | Personalizable: Geocercas y Puntos de Referencia |
| <a id="fila-31"></a>31 | Tareas | Latitud | Ubicación de la geocerca expresada mediante coordenadas geográficas. | Coordenada | 133376152 | Asociada a: Geocercas y Puntos de Referencia |
| <a id="fila-32"></a>32 | Tareas | Longitud | Ubicación de la geocerca expresada mediante coordenadas geográficas. | Coordenada | -878486967 | Asociada a: Geocercas y Puntos de Referencia |
| <a id="fila-33"></a>33 | Tareas | Asignar | Usuario o motorista asignado a realizar la tarea. | Usuario / referencia | MOT-014 — Adriana Steiner | ∅ |
| <a id="fila-35"></a>35 | Mantenimiento  | Vehículo | Nombre o descripción con la que se identifica el activo en Startrack. | Vehículo / referencia | CF-03 | ∅ |
| <a id="fila-36"></a>36 | Mantenimiento  | Referencia | Información adicional sobre el objetivo del mantenimiento. | Texto | Reparación de falla reportada | ∅ |
| <a id="fila-37"></a>37 | Mantenimiento  | Fecha de servicio(s) | Fecha programada para el mantenimiento. | Fecha | 2026-09-12T00:00:00 | ∅ |
| <a id="fila-38"></a>38 | Mantenimiento  | Odometro | Mide la distancia recorrida por el equipo. | numero/Km | 25.52 | ∅ |
| <a id="fila-39"></a>39 | Mantenimiento  | Hora | Hora del mantenimiento. | Hora | 23:46:00 | ∅ |
| <a id="fila-40"></a>40 | Mantenimiento  | Horometro | Mide las horas que una máquina o equipo ha estado funcionando. | numero/h | 257748 | ∅ |
| <a id="fila-41"></a>41 | Mantenimiento  | Motivo de reparación | Información adicional sobre el objetivo del mantenimiento. | Catálogo | Emergencia | ∅ |
| <a id="fila-42"></a>42 | Mantenimiento  | Proveedor | Suministra el mantenimiento. | Proveedor / referencia | ∅ | ∅ |
| <a id="fila-43"></a>43 | Mantenimiento  | Mecanico | Encargado de realizar el mantenimiento. | Usuario / referencia | ∅ | ∅ |
| <a id="fila-44"></a>44 | Mantenimiento  | Anadir tipo de servicio | Categoría del mantenimiento. | Catálogo | ∅ | ∅ |
| <a id="fila-45"></a>45 | Mantenimiento  | Anadir tipo de servicio | Categoría del mantenimiento. | catalogo | ∅ | ∅ |

## Valores y tipos exactos

Registro de cada celda no vacía para lectura automática. `s` = texto; `n` = número; `d` = fecha/hora interpretada desde el serial de Excel; `f` = fórmula. `valor_xml` conserva el número almacenado sin aplicar formato visual. Los espacios al final de una cadena y los saltos de línea se conservan en JSON. Los tipos descritos dentro del diccionario son contenido, distintos del tipo físico de la celda.

```json
[
  {
    "celda": "A1",
    "tipo_excel": "s",
    "valor": "DICCIONARIO DE DATOS — STARTRACK",
    "formato": "General"
  },
  {
    "celda": "A2",
    "tipo_excel": "s",
    "valor": "Campos relevantes de vehículos, tareas y geocercas para el Hub de Operaciones.",
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
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B4",
    "tipo_excel": "s",
    "valor": "Descripción",
    "formato": "General"
  },
  {
    "celda": "C4",
    "tipo_excel": "s",
    "valor": "Nombre o descripción con la que se identifica el activo en Startrack.",
    "formato": "General"
  },
  {
    "celda": "D4",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E4",
    "tipo_excel": "s",
    "valor": "CF-03",
    "formato": "General"
  },
  {
    "celda": "A5",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B5",
    "tipo_excel": "s",
    "valor": "Estado",
    "formato": "General"
  },
  {
    "celda": "C5",
    "tipo_excel": "s",
    "valor": "Estado actual mostrado para el activo en Startrack.",
    "formato": "General"
  },
  {
    "celda": "D5",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E5",
    "tipo_excel": "s",
    "valor": "Normal",
    "formato": "General"
  },
  {
    "celda": "A6",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B6",
    "tipo_excel": "s",
    "valor": "Tipo",
    "formato": "General"
  },
  {
    "celda": "C6",
    "tipo_excel": "s",
    "valor": "Tipo de vehículo o maquinaria.",
    "formato": "General"
  },
  {
    "celda": "D6",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E6",
    "tipo_excel": "s",
    "valor": "Cargador frontal",
    "formato": "General"
  },
  {
    "celda": "A7",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B7",
    "tipo_excel": "s",
    "valor": "Año",
    "formato": "General"
  },
  {
    "celda": "C7",
    "tipo_excel": "s",
    "valor": "Año del vehículo.",
    "formato": "General"
  },
  {
    "celda": "D7",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E7",
    "tipo_excel": "n",
    "valor": 2013,
    "formato": "General",
    "valor_xml": "2013",
    "tipo_xml": "n"
  },
  {
    "celda": "A8",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B8",
    "tipo_excel": "s",
    "valor": "Color",
    "formato": "General"
  },
  {
    "celda": "C8",
    "tipo_excel": "s",
    "valor": "Color del vehículo.",
    "formato": "General"
  },
  {
    "celda": "D8",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E8",
    "tipo_excel": "s",
    "valor": "Amarillo",
    "formato": "General"
  },
  {
    "celda": "A9",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B9",
    "tipo_excel": "s",
    "valor": "Marca",
    "formato": "General"
  },
  {
    "celda": "C9",
    "tipo_excel": "s",
    "valor": "Marca del activo.",
    "formato": "General"
  },
  {
    "celda": "D9",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E9",
    "tipo_excel": "s",
    "valor": "Caterpillar",
    "formato": "General"
  },
  {
    "celda": "A10",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B10",
    "tipo_excel": "s",
    "valor": "Modelo",
    "formato": "General"
  },
  {
    "celda": "C10",
    "tipo_excel": "s",
    "valor": "Modelo del activo.",
    "formato": "General"
  },
  {
    "celda": "D10",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E10",
    "tipo_excel": "s",
    "valor": "950H",
    "formato": "General"
  },
  {
    "celda": "A11",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B11",
    "tipo_excel": "s",
    "valor": "Grupo",
    "formato": "General"
  },
  {
    "celda": "C11",
    "tipo_excel": "s",
    "valor": "Grupo del vehículo.",
    "formato": "General"
  },
  {
    "celda": "D11",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E11",
    "tipo_excel": "s",
    "valor": "Vehículos-Hackathon",
    "formato": "General"
  },
  {
    "celda": "A12",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B12",
    "tipo_excel": "s",
    "valor": "Etiquetas",
    "formato": "General"
  },
  {
    "celda": "C12",
    "tipo_excel": "s",
    "valor": "Etiquetas del vehículo.",
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
    "valor": "Equipo 14 - The Hub",
    "formato": "General"
  },
  {
    "celda": "A13",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B13",
    "tipo_excel": "s",
    "valor": "Conductor",
    "formato": "General"
  },
  {
    "celda": "C13",
    "tipo_excel": "s",
    "valor": "Conductor o motorista asignado al activo.",
    "formato": "General"
  },
  {
    "celda": "D13",
    "tipo_excel": "s",
    "valor": "Usuario / referencia",
    "formato": "General"
  },
  {
    "celda": "E13",
    "tipo_excel": "s",
    "valor": "MOT-014 - Adriana Steiner",
    "formato": "General"
  },
  {
    "celda": "A14",
    "tipo_excel": "s",
    "valor": "Vehículos",
    "formato": "General"
  },
  {
    "celda": "B14",
    "tipo_excel": "s",
    "valor": "ID remoto",
    "formato": "General"
  },
  {
    "celda": "C14",
    "tipo_excel": "s",
    "valor": "Identificador utilizado por la organización para relacionar el activo con reportes o integraciones.",
    "formato": "General"
  },
  {
    "celda": "D14",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E14",
    "tipo_excel": "n",
    "valor": 78093,
    "formato": "General",
    "valor_xml": "78093",
    "tipo_xml": "n"
  },
  {
    "celda": "A16",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B16",
    "tipo_excel": "s",
    "valor": "geocerca_id",
    "formato": "General"
  },
  {
    "celda": "C16",
    "tipo_excel": "s",
    "valor": "Identificador de la geocerca dentro del ejercicio.",
    "formato": "General"
  },
  {
    "celda": "D16",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E16",
    "tipo_excel": "s",
    "valor": "GEO-014",
    "formato": "General"
  },
  {
    "celda": "A17",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B17",
    "tipo_excel": "s",
    "valor": "Nombre",
    "formato": "General"
  },
  {
    "celda": "C17",
    "tipo_excel": "s",
    "valor": "Nombre con el que se identifica la geocerca.",
    "formato": "General"
  },
  {
    "celda": "D17",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E17",
    "tipo_excel": "s",
    "valor": "PROY-014 - The Hub - Proyecto Xi - La Unión",
    "formato": "General"
  },
  {
    "celda": "A18",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B18",
    "tipo_excel": "s",
    "valor": "Grupo",
    "formato": "General"
  },
  {
    "celda": "C18",
    "tipo_excel": "s",
    "valor": "Grupo de Geocercas.",
    "formato": "General"
  },
  {
    "celda": "D18",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E18",
    "tipo_excel": "s",
    "valor": "Geocercas-Hackathon",
    "formato": "General"
  },
  {
    "celda": "F18",
    "tipo_excel": "s",
    "valor": "Personalizable",
    "formato": "General"
  },
  {
    "celda": "A19",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B19",
    "tipo_excel": "s",
    "valor": "Margen Adicional",
    "formato": "General"
  },
  {
    "celda": "C19",
    "tipo_excel": "s",
    "valor": "Referencia del radio del lugar.",
    "formato": "General"
  },
  {
    "celda": "D19",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E19",
    "tipo_excel": "n",
    "valor": 1000,
    "formato": "General",
    "valor_xml": "1000",
    "tipo_xml": "n"
  },
  {
    "celda": "A20",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B20",
    "tipo_excel": "s",
    "valor": "Latitud",
    "formato": "General"
  },
  {
    "celda": "C20",
    "tipo_excel": "s",
    "valor": "Ubicación de la geocerca expresada mediante coordenadas geográficas.",
    "formato": "General"
  },
  {
    "celda": "D20",
    "tipo_excel": "s",
    "valor": "Coordenada",
    "formato": "General"
  },
  {
    "celda": "E20",
    "tipo_excel": "n",
    "valor": 133376152,
    "formato": "#,##0",
    "valor_xml": "133376152",
    "tipo_xml": "n"
  },
  {
    "celda": "F20",
    "tipo_excel": "s",
    "valor": "Asociada a: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A21",
    "tipo_excel": "s",
    "valor": "Geocercas",
    "formato": "General"
  },
  {
    "celda": "B21",
    "tipo_excel": "s",
    "valor": "Longitud",
    "formato": "General"
  },
  {
    "celda": "C21",
    "tipo_excel": "s",
    "valor": "Ubicación de la geocerca expresada mediante coordenadas geográficas.",
    "formato": "General"
  },
  {
    "celda": "D21",
    "tipo_excel": "s",
    "valor": "Coordenada",
    "formato": "General"
  },
  {
    "celda": "E21",
    "tipo_excel": "n",
    "valor": -878486967,
    "formato": "#,##0",
    "valor_xml": "-878486967",
    "tipo_xml": "n"
  },
  {
    "celda": "F21",
    "tipo_excel": "s",
    "valor": "Asociada a: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A23",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B23",
    "tipo_excel": "s",
    "valor": "tarea_id",
    "formato": "General"
  },
  {
    "celda": "C23",
    "tipo_excel": "s",
    "valor": "Identificador de la tarea dentro del ejercicio.",
    "formato": "General"
  },
  {
    "celda": "D23",
    "tipo_excel": "s",
    "valor": "Texto / ID",
    "formato": "General"
  },
  {
    "celda": "E23",
    "tipo_excel": "n",
    "valor": 24,
    "formato": "General",
    "valor_xml": "24",
    "tipo_xml": "n"
  },
  {
    "celda": "A24",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B24",
    "tipo_excel": "s",
    "valor": "Título",
    "formato": "General"
  },
  {
    "celda": "C24",
    "tipo_excel": "s",
    "valor": "Nombre principal de la tarea.",
    "formato": "General"
  },
  {
    "celda": "D24",
    "tipo_excel": "s",
    "valor": "TAR-014",
    "formato": "General"
  },
  {
    "celda": "E24",
    "tipo_excel": "s",
    "valor": "Traslado de cargador frontal CF-03",
    "formato": "General"
  },
  {
    "celda": "A25",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B25",
    "tipo_excel": "s",
    "valor": "Descripción",
    "formato": "General"
  },
  {
    "celda": "C25",
    "tipo_excel": "s",
    "valor": "Información adicional sobre el objetivo de la tarea.",
    "formato": "General"
  },
  {
    "celda": "D25",
    "tipo_excel": "s",
    "valor": "Texto largo",
    "formato": "General"
  },
  {
    "celda": "E25",
    "tipo_excel": "s",
    "valor": "Traslado de cargador frontal",
    "formato": "General"
  },
  {
    "celda": "A26",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B26",
    "tipo_excel": "s",
    "valor": "Tipo",
    "formato": "General"
  },
  {
    "celda": "C26",
    "tipo_excel": "s",
    "valor": "Categoría de la tarea.",
    "formato": "General"
  },
  {
    "celda": "D26",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E26",
    "tipo_excel": "s",
    "valor": "Trasalado",
    "formato": "General"
  },
  {
    "celda": "F26",
    "tipo_excel": "s",
    "valor": "Personalizable",
    "formato": "General"
  },
  {
    "celda": "A27",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B27",
    "tipo_excel": "s",
    "valor": "Estado",
    "formato": "General"
  },
  {
    "celda": "C27",
    "tipo_excel": "s",
    "valor": "Situación actual de la tarea.",
    "formato": "General"
  },
  {
    "celda": "D27",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E27",
    "tipo_excel": "s",
    "valor": "Pendiente",
    "formato": "General"
  },
  {
    "celda": "F27",
    "tipo_excel": "s",
    "valor": "Pendiente; Completada; Cancelada; estados personalizados",
    "formato": "General"
  },
  {
    "celda": "A28",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B28",
    "tipo_excel": "s",
    "valor": "Fecha programada",
    "formato": "General"
  },
  {
    "celda": "C28",
    "tipo_excel": "s",
    "valor": "Fecha programada para la tarea.",
    "formato": "General"
  },
  {
    "celda": "D28",
    "tipo_excel": "s",
    "valor": "Fecha",
    "formato": "General"
  },
  {
    "celda": "E28",
    "tipo_excel": "s",
    "valor": "12/09/2026",
    "formato": "General"
  },
  {
    "celda": "A29",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B29",
    "tipo_excel": "s",
    "valor": "Origen",
    "formato": "General"
  },
  {
    "celda": "C29",
    "tipo_excel": "s",
    "valor": "Dirección de Origen.",
    "formato": "General"
  },
  {
    "celda": "D29",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E29",
    "tipo_excel": "s",
    "valor": "PLANTA ORIGEN",
    "formato": "General"
  },
  {
    "celda": "F29",
    "tipo_excel": "s",
    "valor": "Personalizable: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A30",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B30",
    "tipo_excel": "s",
    "valor": "Destino",
    "formato": "General"
  },
  {
    "celda": "C30",
    "tipo_excel": "s",
    "valor": "Dirección de Destino.",
    "formato": "General"
  },
  {
    "celda": "D30",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E30",
    "tipo_excel": "s",
    "valor": "PROY-014 - The Hub - Proyecto Xi - La Unión",
    "formato": "General"
  },
  {
    "celda": "F30",
    "tipo_excel": "s",
    "valor": "Personalizable: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A31",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B31",
    "tipo_excel": "s",
    "valor": "Latitud",
    "formato": "General"
  },
  {
    "celda": "C31",
    "tipo_excel": "s",
    "valor": "Ubicación de la geocerca expresada mediante coordenadas geográficas.",
    "formato": "General"
  },
  {
    "celda": "D31",
    "tipo_excel": "s",
    "valor": "Coordenada",
    "formato": "General"
  },
  {
    "celda": "E31",
    "tipo_excel": "n",
    "valor": 133376152,
    "formato": "#,##0",
    "valor_xml": "133376152",
    "tipo_xml": "n"
  },
  {
    "celda": "F31",
    "tipo_excel": "s",
    "valor": "Asociada a: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A32",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B32",
    "tipo_excel": "s",
    "valor": "Longitud",
    "formato": "General"
  },
  {
    "celda": "C32",
    "tipo_excel": "s",
    "valor": "Ubicación de la geocerca expresada mediante coordenadas geográficas.",
    "formato": "General"
  },
  {
    "celda": "D32",
    "tipo_excel": "s",
    "valor": "Coordenada",
    "formato": "General"
  },
  {
    "celda": "E32",
    "tipo_excel": "n",
    "valor": -878486967,
    "formato": "#,##0",
    "valor_xml": "-878486967",
    "tipo_xml": "n"
  },
  {
    "celda": "F32",
    "tipo_excel": "s",
    "valor": "Asociada a: Geocercas y Puntos de Referencia",
    "formato": "General"
  },
  {
    "celda": "A33",
    "tipo_excel": "s",
    "valor": "Tareas",
    "formato": "General"
  },
  {
    "celda": "B33",
    "tipo_excel": "s",
    "valor": "Asignar",
    "formato": "General"
  },
  {
    "celda": "C33",
    "tipo_excel": "s",
    "valor": "Usuario o motorista asignado a realizar la tarea.",
    "formato": "General"
  },
  {
    "celda": "D33",
    "tipo_excel": "s",
    "valor": "Usuario / referencia",
    "formato": "General"
  },
  {
    "celda": "E33",
    "tipo_excel": "s",
    "valor": "MOT-014 — Adriana Steiner",
    "formato": "General"
  },
  {
    "celda": "A35",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B35",
    "tipo_excel": "s",
    "valor": "Vehículo",
    "formato": "General"
  },
  {
    "celda": "C35",
    "tipo_excel": "s",
    "valor": "Nombre o descripción con la que se identifica el activo en Startrack.",
    "formato": "General"
  },
  {
    "celda": "D35",
    "tipo_excel": "s",
    "valor": "Vehículo / referencia",
    "formato": "General"
  },
  {
    "celda": "E35",
    "tipo_excel": "s",
    "valor": "CF-03",
    "formato": "General"
  },
  {
    "celda": "A36",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B36",
    "tipo_excel": "s",
    "valor": "Referencia",
    "formato": "General"
  },
  {
    "celda": "C36",
    "tipo_excel": "s",
    "valor": "Información adicional sobre el objetivo del mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D36",
    "tipo_excel": "s",
    "valor": "Texto",
    "formato": "General"
  },
  {
    "celda": "E36",
    "tipo_excel": "s",
    "valor": "Reparación de falla reportada",
    "formato": "General"
  },
  {
    "celda": "A37",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B37",
    "tipo_excel": "s",
    "valor": "Fecha de servicio(s)",
    "formato": "General"
  },
  {
    "celda": "C37",
    "tipo_excel": "s",
    "valor": "Fecha programada para el mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D37",
    "tipo_excel": "s",
    "valor": "Fecha",
    "formato": "General"
  },
  {
    "celda": "E37",
    "tipo_excel": "d",
    "valor": "2026-09-12T00:00:00",
    "formato": "mm-dd-yy",
    "tipo_python": "datetime",
    "valor_xml": "46277",
    "tipo_xml": "n"
  },
  {
    "celda": "A38",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B38",
    "tipo_excel": "s",
    "valor": "Odometro",
    "formato": "General"
  },
  {
    "celda": "C38",
    "tipo_excel": "s",
    "valor": "Mide la distancia recorrida por el equipo.",
    "formato": "General"
  },
  {
    "celda": "D38",
    "tipo_excel": "s",
    "valor": "numero/Km",
    "formato": "General"
  },
  {
    "celda": "E38",
    "tipo_excel": "s",
    "valor": "25.52",
    "formato": "General"
  },
  {
    "celda": "A39",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B39",
    "tipo_excel": "s",
    "valor": "Hora",
    "formato": "General"
  },
  {
    "celda": "C39",
    "tipo_excel": "s",
    "valor": "Hora del mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D39",
    "tipo_excel": "s",
    "valor": "Hora",
    "formato": "General"
  },
  {
    "celda": "E39",
    "tipo_excel": "d",
    "valor": "23:46:00",
    "formato": "h:mm",
    "tipo_python": "time",
    "valor_xml": "0.99027777777777781",
    "tipo_xml": "n"
  },
  {
    "celda": "A40",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B40",
    "tipo_excel": "s",
    "valor": "Horometro",
    "formato": "General"
  },
  {
    "celda": "C40",
    "tipo_excel": "s",
    "valor": "Mide las horas que una máquina o equipo ha estado funcionando.",
    "formato": "General"
  },
  {
    "celda": "D40",
    "tipo_excel": "s",
    "valor": "numero/h",
    "formato": "General"
  },
  {
    "celda": "E40",
    "tipo_excel": "n",
    "valor": 257748,
    "formato": "#,##0",
    "valor_xml": "257748",
    "tipo_xml": "n"
  },
  {
    "celda": "A41",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B41",
    "tipo_excel": "s",
    "valor": "Motivo de reparación",
    "formato": "General"
  },
  {
    "celda": "C41",
    "tipo_excel": "s",
    "valor": "Información adicional sobre el objetivo del mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D41",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "E41",
    "tipo_excel": "s",
    "valor": "Emergencia",
    "formato": "General"
  },
  {
    "celda": "A42",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B42",
    "tipo_excel": "s",
    "valor": "Proveedor",
    "formato": "General"
  },
  {
    "celda": "C42",
    "tipo_excel": "s",
    "valor": "Suministra el mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D42",
    "tipo_excel": "s",
    "valor": "Proveedor / referencia",
    "formato": "General"
  },
  {
    "celda": "A43",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B43",
    "tipo_excel": "s",
    "valor": "Mecanico",
    "formato": "General"
  },
  {
    "celda": "C43",
    "tipo_excel": "s",
    "valor": "Encargado de realizar el mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D43",
    "tipo_excel": "s",
    "valor": "Usuario / referencia",
    "formato": "General"
  },
  {
    "celda": "A44",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B44",
    "tipo_excel": "s",
    "valor": "Anadir tipo de servicio",
    "formato": "General"
  },
  {
    "celda": "C44",
    "tipo_excel": "s",
    "valor": "Categoría del mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D44",
    "tipo_excel": "s",
    "valor": "Catálogo",
    "formato": "General"
  },
  {
    "celda": "A45",
    "tipo_excel": "s",
    "valor": "Mantenimiento ",
    "formato": "General"
  },
  {
    "celda": "B45",
    "tipo_excel": "s",
    "valor": "Anadir tipo de servicio",
    "formato": "General"
  },
  {
    "celda": "C45",
    "tipo_excel": "s",
    "valor": "Categoría del mantenimiento.",
    "formato": "General"
  },
  {
    "celda": "D45",
    "tipo_excel": "s",
    "valor": "catalogo",
    "formato": "General"
  }
]
```

No hay fórmulas ni resultados de fórmulas en caché que extraer. No se recalculó ni modificó el XLSX.
