# Registro de decisiones de arquitectura (ADR)

## ADR-001 · PWA + Siri/Atajos en lugar de una app nativa (2026-10-16)
**Contexto:** se busca una experiencia móvil por voz en el iPhone. **Opciones:** app nativa Swift, multiplataforma (React Native o Flutter), PWA.
**Decisión:** PWA ahora; Siri mediante Atajos para la activación por voz.
**Por qué:** sin App Store, sin cuenta de desarrollador de Apple (USD 99 al año) y sin Mac para compilar; un solo código; despliegue inmediato. La activación permanente por palabra clave no la ofrece iOS a terceros ni siquiera en una app nativa; Siri + Atajo es la vía real.
**Revisar cuando:** se necesite voz continua en segundo plano dentro de la app, widgets en vivo o push más rico → app nativa (SwiftUI + App Intents) sobre la misma API.

## ADR-002 · Monolito modular + SQLite (2026-10-16)
**Decisión:** FastAPI + SQLite (WAL) en un solo proceso. **Por qué:** un propietario y un equipo pequeño; cero costo operativo; respaldo con un archivo. **Revisar cuando:** haya más de un proceso, más de unos 10 usuarios concurrentes o se necesite búsqueda semántica → PostgreSQL (+ pgvector si se justifica).

## ADR-003 · Doble modo: reglas locales + Claude opcional (2026-10-16)
**Decisión:** el orquestador resuelve las intenciones conocidas sin LLM; Claude (`claude-opus-5-5`, esfuerzo `medium`, caché del prompt de sistema, alternativa del lado del servidor ante rechazos) solo para instrucciones libres. **Por qué:** costo predecible, respuesta inmediata, funciona sin clave y con el mismo control de permisos. **Riesgo:** el modo local entiende frases limitadas → se amplía con los casos reales registrados en `conversations`.

## ADR-004 · Bucle manual de herramientas (2026-10-16)
**Decisión:** bucle `stop_reason == "tool_use"` propio en lugar del Tool Runner beta. **Por qué:** control explícito de permisos y aprobaciones por herramienta, registro de uso por iteración, límite de pasos y conversión de errores en `tool_result` con `is_error`.

## ADR-005 · Auditoría encadenada por hash + triggers (2026-10-16)
**Decisión:** `audit_log` de solo inserción (triggers) y verificación de la cadena. **Por qué:** que ningún agente ni la aplicación puedan alterar su historial, y detectar manipulaciones directas sobre la BD.

## ADR-006 · Las integraciones externas no se simulan (2026-10-16)
**Decisión:** aprobar una acción externa sin integración la marca como "aprobada, ejecución manual requerida". **Por qué:** nunca afirmar que se envió, presentó o pagó algo que no ocurrió.
