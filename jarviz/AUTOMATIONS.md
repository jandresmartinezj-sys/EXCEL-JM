# Automatizaciones

Todas registran en la auditoría, usan claves de idempotencia (no duplican) y dejan la tarea en `failed` con la causa si algo falla.

| Flujo | Activación | Pasos implementados | Idempotencia | Permisos | Externo |
|---|---|---|---|---|---|
| **A · Nuevo prospecto** | "registra un nuevo prospecto llamado X" | registrar → clasificar segmento → plan recomendado → preguntas de diagnóstico → borrador de propuesta → tarea de contacto a 2 días | nombre normalizado + contacto | nivel 3 | enviar la propuesta = aprobación nivel 4 |
| **B · Cierre contable** | "prepara el cierre de <cliente> [AAAA-MM]" | checklist SOP-02 → documentos faltantes → 9 tareas | cliente + periodo + paso | nivel 3 | ninguno; requiere validación profesional |
| **C · Vigilancia de obligaciones** | programador diario o `/api/scheduled/run` | obligaciones a ≤ 15 días → tarea de preparación 5 días antes | obligación + "prep" | nivel 3 | presentar = aprobación nivel 4 |
| **D · Nueva oportunidad** | "identifica oportunidades" | solo datos internos: subir de plan, cierres avanzados, segmento más rentable | — (consulta) | nivel 1 | la investigación externa requiere el modo IA con web (pendiente) |
| **E · Revisión semanal** | "revisión semanal" o programador | consolidar → comparar con metas → prioridades → guardar en memoria de trabajo | año + semana ISO | nivel 3 | ninguno |
| **Alertas** | cada carga del tablero + programador | obligaciones ≤ 5 días o vencidas, oportunidades sin seguimiento, facturas con > 15 días, concentración > 20%, cliente en riesgo alto | huella por regla y objeto | nivel 3 | ninguno |

## Programador (cron)
```cron
# todos los días a las 6:50 a. m. (hora Colombia, servidor en UTC-5)
50 6 * * * cd /ruta/jarviz && /usr/bin/python3 -m app.cli run-scheduled >> data/scheduled.log 2>&1
```
`run-scheduled` = alertas + flujo C + depuración de conversaciones según la retención.

## Recuperación
- Ejecutar un flujo dos veces es seguro (idempotente).
- Una tarea `failed` puede volver a `pending` (transición permitida) y reintentarse.
- Para detener la automatización: baja la autonomía global a 1 o 2 en Ajustes (las acciones de nivel 3 pasan a requerir aprobación) y quita la línea del cron.
