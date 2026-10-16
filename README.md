# EXCEL-JM · Ecosistema de la firma contable, tributaria y financiera

Sistema operativo completo del negocio: estrategia, áreas, procesos, control, documentos legales y herramientas.
**Empieza por** `ecosistema/00-arquitectura.md` y `ecosistema/12-hoja-de-ruta.md`.

**JARVIZ** (`jarviz/`): el cerebro empresarial del ecosistema. Es una app para iPhone con voz, agentes, aprobaciones, auditoría y tablero. Ver `jarviz/README.md`.

| Carpeta | Contenido |
|---|---|
| `jarviz/` | Asistente empresarial: servidor, app web para iPhone, agentes, pruebas y documentación técnica |
| `ecosistema/` | 13 documentos por área: estrategia y marca, marketing, comercial, operaciones (SOP), servicio, finanzas internas, control interno y riesgos, legal, talento, tecnología, indicadores y hoja de ruta |
| `legal/` | Contrato de prestación de servicios, carta de encargo, política de tratamiento de datos (modelos para revisar con un abogado) |
| `comercial/` | Kit comercial: oferta, precios, mensajes de prospección, preguntas de diagnóstico |
| `estrategia/` | Mapa de oportunidades, evidencia de mercado, decisiones |
| `plantillas/` | Herramientas Excel |
| `scripts/` | Generadores de las plantillas (`python3 scripts/<archivo>.py`, requiere `openpyxl`) |

## Plantillas
- `centro-de-control.xlsx`: **herramienta diaria de la firma**. Tablero de 21 indicadores con semáforo, pipeline comercial, clientes y rentabilidad, obligaciones tributarias con alertas, registro de horas y facturación con cartera por edades.
- `diagnostico-financiero-pyme.xlsx`: diagnóstico de 1 página (13 indicadores, semáforo, puntaje) + propuesta comercial automática.
- `cartera-por-edades-deterioro.xlsx`: cartera por edades con deterioro e indicadores.
