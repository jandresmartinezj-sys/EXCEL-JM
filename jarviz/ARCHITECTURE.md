# Arquitectura

```
iPhone (PWA en Safari / pantalla de inicio)          Siri / Atajos de Apple
  · voz: Web Speech API (dictado) + speechSynthesis      · "Oye Siri, JARVIZ" → Dictar texto → POST /api/shortcut
  · inicio, tareas, aprobaciones, ajustes                  → "Leer texto" con la respuesta
            │ HTTPS + token Bearer                                   │ token personal revocable
            ▼                                                        ▼
┌──────────────────────────── FastAPI (app/main.py) ────────────────────────────┐
│ autenticación (scrypt + tokens con hash) · roles owner/staff/client · límite de  │
│ solicitudes · cabeceras de seguridad (CSP) · validación con pydantic            │
├──────────────────────────────────────────────────────────────────────────────┤
│ ORQUESTADOR (app/orchestrator.py)                                              │
│  clasifica la intención → crea la tarea (estado) → delega a los agentes →        │
│  aplica la política de autonomía → ejecuta o crea la aprobación → consolida →   │
│  responde (texto para voz + detalle estructurado) → auditoría                   │
│  · modo local: reglas en español (siempre disponible, sin costo)                 │
│  · modo IA: Claude con herramientas locales (solo si hay ANTHROPIC_API_KEY)      │
├──────────────┬───────────────┬───────────────┬──────────────┬───────────────┤
│ agents.py    │ analytics.py  │ automations.py│ alerts.py    │ memory.py     │
│ registro de  │ indicadores y │ flujos A/B/C/E│ reglas       │ memoria por   │
│ 15 agentes   │ vistas reales │ idempotentes  │ proactivas   │ niveles       │
├──────────────┴───────────────┴───────────────┴──────────────┴───────────────┤
│ policy.py (niveles 1–5) · tasks.py (máquina de estados) · audit.py (cadena hash)│
├──────────────────────────────────────────────────────────────────────────────┤
│ SQLite (app/schema.sql): clientes, prospectos, obligaciones, facturas, horas,    │
│ documentos, tareas, aprobaciones, alertas, memoria, conversaciones, uso de IA,  │
│ auditoría con triggers de solo inserción                                        │
└──────────────────────────────────────────────────────────────────────────────┘
        ▲ cron: `python -m app.cli run-scheduled` (alertas + vigilancia + retención)
        ▲ importación: `python -m app.cli import-excel ../plantillas/centro-de-control.xlsx`
```

## Por qué esta arquitectura (resumen; detalle en `docs/DECISIONS.md`)
- **PWA y no una app nativa (por ahora):** se instala en el iPhone sin App Store ni cuenta de desarrollador de Apple (USD 99 al año), tiene un solo código y se actualiza al instante. Lo que la PWA no puede hacer (escuchar siempre o activarse con palabra clave) **tampoco lo permite iOS a apps de terceros**; la activación por voz real llega con **Siri + Atajos**, que sí funciona sin app nativa.
- **SQLite + monolito modular:** un solo usuario y un equipo pequeño. No hacen falta microservicios, colas ni base vectorial. Cada módulo tiene límites claros para migrar a PostgreSQL cuando haya concurrencia real.
- **Modo local + modo IA:** el núcleo funciona sin costo ni dependencia externa; Claude agrega comprensión libre y análisis, pero no ejecuta nada por fuera de las mismas herramientas y permisos.
- **Proactividad por eventos y programador** (cron), no "pensamiento continuo".

## Flujo de una instrucción
1. `POST /api/command {text}` → `Orchestrator.handle`.
2. Se crea la tarea `pending → running` y se guarda en la memoria de conversación.
3. `classify()` → intención + agentes. Si no hay coincidencia y hay clave API, entra el modo IA; si no, se pide una aclaración.
4. Cada acción pasa por `policy.decide()`: se permite, o se crea una solicitud en `approvals` y la tarea queda en `awaiting_approval`.
5. Resultado: `{status, speech, detail, agents, task_id}`. Si hay un error, la tarea queda `failed` con la causa y el siguiente paso.
