# Pruebas y criterios de aceptación

`python3 -m pytest -q` → **39 pruebas, todas pasan** (2026-10-16). Prueba de navegador: `docs/DEPLOY.md` § Verificación.

| Criterio de aceptación | Estado | Prueba |
|---|---|---|
| El agente central delega y consolida | ✅ | `test_orchestrator_delegates_and_consolidates` |
| La memoria conserva el contexto entre sesiones | ✅ | `test_memory_persists_and_isolates_clients` (nueva conexión) |
| Nadie accede a información ajena | ✅ | `test_client_portal_isolation`, `test_memory_*` |
| Una acción no autorizada se bloquea | ✅ | `test_external_action_is_blocked_pending_approval`, `test_staff_cannot_approve_or_change_autonomy`, `test_low_autonomy_*` |
| Una tarea fallida tiene un estado identificable | ✅ | `test_failed_task_has_identifiable_state`, `test_llm_refusal_marks_task_failed` |
| La auditoría permite reconstruir las acciones y detecta manipulación | ✅ | `test_audit_*`, `test_owner_approves_and_audit_reconstructs` |
| Las automatizaciones no duplican | ✅ | `test_idempotency_*`, `test_new_prospect_flow_is_idempotent`, `test_close_and_obligation_flows_do_not_duplicate`, `test_weekly_review_once_per_week`, `test_scheduled_alerts_deduplicate` |
| El tablero usa datos reales o marca la demostración | ✅ | `test_kpis_use_real_data_and_flag_demo`, `test_kpis_empty_db_report_not_available` |
| Interpretación de las instrucciones del enunciado | ✅ | `test_intent_classification` (9 casos) |
| Modo IA: bucle de herramientas, aprobaciones, registro de costos | ✅ simulado | `tests/test_llm.py` |
| Utilizable desde el iPhone | ✅ en emulación (Chromium con perfil de iPhone 13): login, tablero, comando, aprobación, auditoría, 0 errores JS · ⚠️ falta un dispositivo físico | script e2e |
| Transcripción de voz correcta | ⚠️ **no verificable aquí** (sin micrófono ni Safari). Prueba manual en `docs/IPHONE.md` | — |
| Las respuestas normativas se rastrean a sus fuentes | ⚠️ no aplica aún: el agente tributario no emite conclusiones normativas (pendiente con fuentes oficiales) | — |
| Integraciones con credenciales reales | ⚠️ ninguna configurada | — |
| Instalación en un entorno limpio | ✅ `pip install -r requirements.txt` + pasos del README en este contenedor | — |
