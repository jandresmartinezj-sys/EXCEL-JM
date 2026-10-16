# Hoja de ruta

| Fase | Estado | Evidencia / pendiente |
|---|---|---|
| 0 · Auditoría | ✅ | El repositorio tenía estrategia, procedimientos, documentos legales y plantillas, sin software. Se reutilizan los procedimientos, los precios, las metas y el modelo del centro de control. |
| 1 · Fundamentos (orquestador, agentes, permisos, memoria, datos, auditoría, pruebas) | ✅ | 39 pruebas |
| 2 · Móvil y voz | 🟡 | PWA + voz web + Siri/Atajos implementados; **falta probar en un iPhone físico** |
| 3 · Núcleo empresarial (clientes, obligaciones, tareas, aprobaciones) | 🟡 | Falta: alta y edición de clientes, obligaciones y facturas desde la app (hoy por importación de Excel o API futura), carga de documentos |
| 4 · Agentes profesionales | 🟡 | 6 activos o parciales con capacidades reales; 5 planificados (ver AGENTS.md) |
| 5 · Inteligencia comercial | 🟡 | Pipeline, propuesta y oportunidades internas; faltan CAC, LTV y marketing |
| 6 · Automatizaciones | 🟡 | Flujos A, B, C, E y alertas; faltan las integraciones externas |
| 7 · Portal y centro de mando | 🟡 | API del portal aislada y probada; falta la interfaz del portal para clientes |
| 8 · Validación y despliegue | ⏳ | Requiere un servidor con HTTPS (decisión de costo del propietario) |

## Próximas prioridades (en orden)
1. **Desplegar con HTTPS** y probar la voz y Siri en tu iPhone (bloqueante para el uso real).
2. **Formularios de captura** en la app: clientes, obligaciones, facturas, horas (dejar de depender del Excel).
3. **Calendario tributario oficial** cargado por cliente según el último dígito del NIT (con la fuente de cada fecha).
4. **Web Push** para alertas en el teléfono.
5. Integración con **Google Calendar** y **correo** (con aprobación).
6. Agente tributario con **consulta normativa citada** (modo IA + web, con la vigencia verificada).
7. Flujo de caja a 13 semanas (agente de finanzas) e interfaz del portal de clientes.
