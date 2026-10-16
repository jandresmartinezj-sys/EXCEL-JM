# Modelo de datos (v1)

Esquema: `app/schema.sql` (SQLite). La versión se registra en `schema_version`.

| Tabla | Propósito | Claves y relaciones |
|---|---|---|
| `users` | owner, staff, client | `client_id` obligatorio si el rol es client |
| `tokens` | sesiones y tokens personales (solo hash) | → users |
| `clients` | clientes y su plan, honorario, estado, riesgo y satisfacción (NPS) | `is_demo` |
| `prospects` | pipeline comercial (8 etapas del ecosistema) | `dedupe_key` única (flujo A) |
| `obligations` | vencimientos tributarios por cliente; `source_note` = procedencia de la fecha | → clients |
| `invoices` | facturación y cobro de la firma | → clients |
| `time_entries` | horas por cliente (rentabilidad) | → clients |
| `documents` | metadatos documentales con procedencia, hash y versión | → clients |
| `tasks` | unidad de trabajo con estado e `idempotency_key` única | → clients |
| `approvals` | solicitudes de aprobación (nivel, carga, decisión) | → tasks |
| `alerts` | alertas proactivas; `fingerprint` única (sin duplicados) | → clients |
| `memory` | memoria por niveles: work, business, client, decision, preference; procedencia y vencimiento; borrado lógico | client exige `client_id` |
| `conversations` | memoria de conversación (retención corta) | → users |
| `settings` | autonomía global, etc. | — |
| `llm_usage` | tokens por llamada al modelo (costo de IA) | — |
| `audit_log` | auditoría encadenada; triggers que impiden UPDATE y DELETE | — |

Correspondencia con el centro de control de Excel: Clientes → `clients`, Pipeline → `prospects`, Obligaciones → `obligations`, Facturacion → `invoices`, Horas → `time_entries` (`app/importer.py`).

## Migraciones y reversión
- v1: creación completa (`CREATE TABLE IF NOT EXISTS`; idempotente).
- Las migraciones futuras deben ir en `app/db.py::migrate` con `ALTER TABLE` incrementales y un `schema_version` nuevo.
- **Reversión:** antes de migrar, copia la BD con `sqlite3 data/jarviz.db ".backup data/backup-<fecha>.db"`. Para revertir, restaura esa copia (SQLite no tiene down-migrations automáticas).
