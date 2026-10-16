# EXCEL-JM

Negocio de servicios contables, financieros y tributarios + herramientas en Excel.

| Carpeta | Contenido |
|---|---|
| `estrategia/` | Mapa de oportunidades, plan de 30 días, decisiones |
| `comercial/` | Oferta, precios, mensajes de prospección, propuesta, indicadores |
| `plantillas/` | Herramientas Excel listas para usar |
| `scripts/` | Generadores de plantillas (`python3 scripts/generar_cartera.py`, requiere `openpyxl`) |

## Plantillas
- `cartera-por-edades-deterioro.xlsx`: cartera por edades (de no vencida a más de 360 días), deterioro por rango, indicadores y alertas.
- `diagnostico-financiero-pyme.xlsx`: diagnóstico de 1 página con 13 indicadores (márgenes, liquidez, ciclo de caja, deuda, meses de caja, cumplimiento tributario), semáforo, puntaje de salud financiera y acciones recomendadas. Genera: `python3 scripts/generar_diagnostico.py`.
