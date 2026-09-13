# 📁 Entregables Oficiales · Hackathon Grupo ECON 2026
**Equipo**: Los Filósofos  
**Fecha y Hora de Entrega**: Domingo 13 de Septiembre, 10:00 AM  
**Repositorio**: [https://github.com/Los-Filosofos/econ-operations](https://github.com/Los-Filosofos/econ-operations)  

Esta carpeta reúne de manera centralizada y explícita todos los entregables obligatorios solicitados en el reto, en sus formatos de reporte oficial **PDF**, hojas de cálculo estructuradas (**Excel/CSV**) y documentación técnica (**Markdown**).

> **Formato de las tablas.** Cada `.csv` y cada `.xlsx` contiene la misma matriz que el entregable cuyo nombre lleva. Los CSV son **UTF-8 con BOM**, fin de línea **CRLF** y separador **coma** (RFC 4180): el BOM hace que Excel muestre los acentos al abrir el archivo con doble clic, y la coma mantiene el archivo apto para ingesta automatizada. Para revisar las matrices en Excel, el archivo indicado es el `.xlsx`: lleva cabecera fija y filtrable, ancho de columna calculado y ajuste de texto.
> Los CSV y los libros se generan desde el Markdown de cada entregable con `scripts/docs/exportar_entregables.py`; `scripts/check.sh` verifica que no se desfasen. La procedencia y el SHA-256 de cada archivo están en [`MANIFEST-TABLAS.md`](./MANIFEST-TABLAS.md).

---

## 📑 Índice Rápido de Entregables

### [1. Matriz de Mapeo de Campos](./1-Matriz-de-Mapeo-de-Campos.pdf)
Conecta los campos de Prisma y Startrack, identificando de manera explícita aquellos que no tienen un equivalente directo.
- 📕 [Reporte Oficial en PDF](./1-Matriz-de-Mapeo-de-Campos.pdf)
- 📊 [Libro Excel](./1-Matriz-de-Mapeo-de-Campos.xlsx): hoja *Mapeo consolidado* con la matriz de este entregable, seguida de las 17 tablas de detalle del repositorio (18 hojas)
- 📄 [CSV de la matriz consolidada](./1-Matriz-de-Mapeo-de-Campos.csv) (14 filas × 5 columnas)
- 📄 [CSV de detalle: formulario de tarea completo](./1-Matriz-de-Mapeo-de-Campos-Detalle-Formulario.csv) (37 filas × 6 columnas)
- 📝 [Versión Markdown](./1-Matriz-de-Mapeo-de-Campos.md)

---

### [2. Matriz de Responsabilidades (RACI)](./2-Matriz-de-Responsabilidades-RACI.pdf)
Tabla estructurada en formato RACI que define quién es Responsable, quién Aprueba, a quién se Consulta y a quién se Informa sobre el estado de un equipo, cubriendo Mantenimiento, Logística y Equipos, Técnica de Proyectos y Control de Costos.
- 📕 [Reporte Oficial en PDF](./2-Matriz-de-Responsabilidades-RACI.pdf)
- 📊 [Libro Excel](./2-Matriz-de-Responsabilidades-RACI.xlsx): hoja *RACI por gerencia* y hoja *RACI propuesta* con el desglose por decisión
- 📄 [CSV de la RACI por gerencia](./2-Matriz-de-Responsabilidades-RACI.csv) (9 filas × 5 columnas)
- 📄 [CSV de detalle: RACI propuesta por decisión](./2-Matriz-de-Responsabilidades-RACI-Detalle.csv) (9 filas × 5 columnas)
- 📝 [Versión Markdown](./2-Matriz-de-Responsabilidades-RACI.md)

---

### [3. Prototipo o Mockup Navegable & Guía de Demo](./3-Prototipo-Navegable-y-Guia-de-Demo.pdf)
Dashboard web interactivo con instrucciones de acceso para la demostración en vivo y los scripts de arranque para la consulta unificada (estado y ubicación combinando ambas plataformas).
- 📕 [Reporte Oficial en PDF](./3-Prototipo-Navegable-y-Guia-de-Demo.pdf)
- 📝 [Guía de Acceso y Demo en Markdown](./3-Prototipo-Navegable-y-Guia-de-Demo.md)
- 🌐 **Acceso Web en Vivo**: `http://localhost:5173/` (SPA Web) y `http://localhost:8050/docs` (API REST)

---

### [4. Diagramas de Arquitectura & Dónde Vive Cada Estado](./4-Diagrama-de-Arquitectura-y-Dossier-Visual.pdf)
Documento y esquemas visuales que muestran los componentes del sistema, el flujo de datos entre Prisma, Startrack y ECON Hub, y la ubicación precisa de cada estado del equipo.
- 📕 [Dossier Visual y Diagramas en PDF](./4-Diagrama-de-Arquitectura-y-Dossier-Visual.pdf) (16 páginas)
- 🖼️ [Diagrama de Componentes de Arquitectura](./4-Diagrama-Arquitectura-Componentes.png)
- 🖼️ [Diagrama «Dónde Vive Cada Estado»](./4-Diagrama-Donde-Vive-Cada-Estado.png)
- 🖼️ [Diagrama de Flujo Operativo](./4-Diagrama-Flujo-Operativo.png)

---

### [5. Documento de Decisiones Técnicas (2 Páginas)](./5-Documento-de-Decisiones-Tecnicas.pdf)
Informe técnico ejecutivo de exactamente 2 páginas que detalla qué campos se mapearon, qué elementos se dejaron fuera de alcance y la justificación técnica de dichas decisiones.
- 📕 [Reporte Oficial en PDF (2 páginas)](./5-Documento-de-Decisiones-Tecnicas.pdf)
- 📝 [Versión Markdown](./5-Documento-de-Decisiones-Tecnicas.md)

---

### [6. Presentación Final (10 Diapositivas & Pitch)](./6-Presentacion-Final-10-Slides-y-Pitch.pdf)
Síntesis de 10 diapositivas que cubre el problema, la solución, la arquitectura, las matrices, el valor de negocio generado para Grupo ECON y la reflexión sobre el aprendizaje del equipo, acompañado del guion de pitch ejecutivo.
- 📕 [Reporte Oficial en PDF](./6-Presentacion-Final-10-Slides-y-Pitch.pdf)
- 📝 [Guion de Presentación y Pitch en Markdown](./6-Presentacion-Final-10-Slides-y-Pitch.md)
