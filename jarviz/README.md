# JARVIZ v0.1

Cerebro empresarial de la firma: un orquestador central que interpreta instrucciones por voz o texto, las delega a agentes especializados, aplica niveles de autonomía y aprobaciones, y deja todo registrado en una auditoría verificable. Se usa desde el iPhone como aplicación web instalable (PWA), por voz y con Siri mediante Atajos.

**No parte de cero.** Reutiliza el ecosistema del repositorio: los procedimientos (`../ecosistema/`), la oferta y los precios (`../comercial/`), las metas y el modelo de datos del centro de control (`../plantillas/centro-de-control.xlsx`, que se puede importar).

## Qué funciona hoy (probado)

| Capacidad | Estado | Evidencia |
|---|---|---|
| Orquestador con 18 intenciones en español y delegación a agentes | ✅ | `tests/test_core.py` |
| Estados de tarea (pendiente → en ejecución → completada / fallida / esperando aprobación / cancelada) | ✅ | prueba de máquina de estados |
| Niveles de autonomía 1–5; acciones externas siempre requieren aprobación | ✅ | `test_policy_*`, `test_external_action_*` |
| Bandeja de aprobaciones (solo el propietario decide) | ✅ | `test_staff_cannot_approve_*` |
| Auditoría de solo inserción, encadenada por hash y verificable | ✅ | `test_audit_*` |
| Memoria persistente por niveles con retención y borrado | ✅ | `test_memory_*` |
| Tablero: 20 indicadores con definición, fórmula, fuente, meta, semáforo y "no disponible" | ✅ | `test_kpis_*` |
| Alertas proactivas deduplicadas (obligaciones, cartera, seguimiento, concentración, riesgo) | ✅ | `test_scheduled_alerts_deduplicate` |
| Flujos A (prospecto), B (cierre), C (obligaciones), E (revisión semanal), sin duplicados | ✅ | `test_*_flow*` |
| Portal de clientes aislado (cada cliente ve solo lo suyo) | ✅ | `test_client_portal_isolation` |
| Importación del centro de control de Excel | ✅ | `test_import_excel_is_idempotent` |
| App web para iPhone: inicio, voz, tareas, aprobaciones, clientes, alertas, agentes, auditoría, ajustes | ✅ | prueba en navegador real (Chromium, pantalla de iPhone 13), sin errores de JavaScript |
| Modo IA con Claude (tool use, aprobaciones, registro de costos) | ✅ con cliente simulado · ⚠️ sin probar contra la API real (no hay clave en este entorno) | `tests/test_llm.py` |
| Voz en un iPhone físico, Siri y Atajos | ⚠️ implementado y documentado, **sin probar en un dispositivo** | `docs/IPHONE.md` |

## Inicio rápido (local)

```bash
cd jarviz
python3 -m pip install -r requirements.txt
cp .env.example .env               # opcional: ANTHROPIC_API_KEY para el modo IA
python3 -m app.cli create-user tu_usuario --role owner
python3 -m app.cli seed-demo       # opcional: datos de DEMOSTRACIÓN (el tablero los marca)
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Abre `http://localhost:8000`. Para usarlo desde el iPhone ver `docs/IPHONE.md`. Para desplegar ver `docs/DEPLOY.md`.

Pruebas: `python3 -m pytest -q` (39 pruebas).

## Comandos de voz o texto (ejemplos)
"Dame el estado general del negocio" · "¿Qué debería priorizar esta semana?" · "Identifica oportunidades de negocio" ·
"¿Qué obligaciones vencen pronto?" · "¿Cómo está la cartera?" · "Rentabilidad por cliente" · "Revisa los riesgos" ·
"Prepara una propuesta para <empresa>" · "Registra un nuevo prospecto llamado <nombre>" · "Prepara el cierre de <cliente>" ·
"Crea una tarea <texto>" · "Anota que <texto>" · "Revisión semanal" · "Envía la propuesta a <empresa>" (→ aprobación).

## Documentación
`ARCHITECTURE.md` · `AGENTS.md` · `DATA_MODEL.md` · `AUTOMATIONS.md` · `SECURITY.md` (incluye la matriz de permisos) ·
`INTEGRATIONS.md` · `TESTING.md` · `ROADMAP.md` · `docs/IPHONE.md` · `docs/DEPLOY.md` · `docs/DECISIONS.md`.
