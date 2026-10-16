"""Registro de agentes: función, herramientas, fuentes, límites y estado real de implementación.

`status`:
- "activo": tiene capacidades implementadas y probadas en esta versión.
- "parcial": algunas capacidades implementadas; el resto figura en `pending`.
- "planificado": definido, sin capacidades ejecutables todavía. JARVIZ lo dice así, no lo simula.
"""
AGENTS = {
    "ceo": {
        "name": "CEO estratégico", "max_autonomy": 3, "status": "activo",
        "purpose": "Visión ejecutiva integral, prioridades y decisiones que requieren al propietario.",
        "capabilities": ["business_status", "weekly_priorities", "weekly_review"],
        "sources": ["kpis", "alerts", "pipeline", "obligations", "receivables"],
        "pending": ["Evaluación de nuevos mercados con fuentes externas (modo IA + web)"],
    },
    "mercado": {
        "name": "Inteligencia de mercado y oportunidades", "max_autonomy": 2, "status": "parcial",
        "purpose": "Detectar dónde crecer. Distingue hechos, hipótesis y estimaciones.",
        "capabilities": ["opportunities"],
        "sources": ["clients", "prospects", "time_entries", "estrategia/mapa-oportunidades.md"],
        "pending": ["Investigación externa con búsqueda web y citas (requiere clave API y aprobación de costo)"],
    },
    "marketing": {
        "name": "Marketing e inteligencia de marca", "max_autonomy": 2, "status": "planificado",
        "purpose": "Posicionamiento, contenido y campañas con retorno medible. Publicar requiere aprobación.",
        "capabilities": [], "sources": ["ecosistema/02-marketing.md"],
        "pending": ["Calendario editorial, borradores de publicaciones, medición por canal"],
    },
    "ventas": {
        "name": "Ventas y desarrollo comercial", "max_autonomy": 3, "status": "activo",
        "purpose": "Convertir oportunidades en ingresos: pipeline, propuestas, seguimiento.",
        "capabilities": ["pipeline", "draft_proposal", "new_prospect"],
        "sources": ["prospects", "comercial/kit-comercial.md"],
        "pending": ["CAC y LTV (requiere registrar gasto comercial)"],
    },
    "contabilidad": {
        "name": "Contabilidad", "max_autonomy": 3, "status": "parcial",
        "purpose": "Apoyar cierres: checklist SOP, documentos faltantes, tareas. No registra asientos definitivos.",
        "capabilities": ["close_checklist"], "sources": ["documents", "SOP-02"],
        "pending": ["Extracción de datos de facturas", "Conciliación bancaria asistida", "Integración con software contable"],
    },
    "tributario": {
        "name": "Tributario colombiano", "max_autonomy": 3, "status": "parcial",
        "purpose": "Control de obligaciones y vencimientos. Conclusiones normativas solo con fuente oficial citada.",
        "capabilities": ["obligations"], "sources": ["obligations", "fuentes oficiales (DIAN, SUIN-Juriscol, Diario Oficial)"],
        "pending": ["Consulta normativa con fuentes oficiales vigentes (modo IA + web)", "Carga automática del calendario DIAN"],
    },
    "legal": {
        "name": "Legal y cumplimiento", "max_autonomy": 2, "status": "planificado",
        "purpose": "Organizar contratos y cumplimiento; coordinar con abogado aliado. No se presenta como abogado.",
        "capabilities": [], "sources": ["legal/", "ecosistema/08-legal-cumplimiento.md"],
        "pending": ["Control de vencimientos contractuales", "Matriz de cumplimiento"],
    },
    "finanzas": {
        "name": "Finanzas y dirección financiera", "max_autonomy": 2, "status": "activo",
        "purpose": "Cartera, rentabilidad por cliente, MRR. Distingue real, presupuesto y proyección. Nunca paga ni transfiere.",
        "capabilities": ["receivables", "profitability"], "sources": ["invoices", "clients", "time_entries"],
        "pending": ["Flujo de caja a 13 semanas", "Presupuesto y escenarios"],
    },
    "operaciones": {
        "name": "Operaciones y prestación de servicios", "max_autonomy": 3, "status": "activo",
        "purpose": "Convertir cada servicio en tareas con responsable y fecha; detectar retrasos.",
        "capabilities": ["create_task", "close_checklist"], "sources": ["tasks", "obligations", "SOP"],
        "pending": ["Medición de productividad por proceso"],
    },
    "control": {
        "name": "Control interno, auditoría y riesgos", "max_autonomy": 1, "status": "activo",
        "purpose": "Riesgos, integridad de auditoría y excepciones. No modifica ni borra registros de auditoría.",
        "capabilities": ["risk_review"], "sources": ["audit_log", "kpis", "approvals"],
        "pending": ["Revisión de segregación de funciones con equipo"],
    },
    "cliente": {
        "name": "Experiencia del cliente y fidelización", "max_autonomy": 2, "status": "parcial",
        "purpose": "Riesgo de abandono, satisfacción y renovaciones. Nunca expone datos de un cliente a otro.",
        "capabilities": ["churn_risk"], "sources": ["clients", "invoices", "time_entries"],
        "pending": ["Bandeja de solicitudes del portal"],
    },
    "talento": {
        "name": "Recursos humanos y talento", "max_autonomy": 1, "status": "planificado",
        "purpose": "Perfiles, capacitación y cargas de trabajo. Sin decisiones laborales automatizadas.",
        "capabilities": [], "sources": ["ecosistema/09-talento.md"], "pending": ["Matriz de competencias"],
    },
    "tecnologia": {
        "name": "Tecnología, datos e IA", "max_autonomy": 1, "status": "parcial",
        "purpose": "Estado técnico, costos de IA y calidad de datos. No despliega ni toca credenciales.",
        "capabilities": ["system_status"], "sources": ["llm_usage", "audit_log"],
        "pending": ["Evaluación de calidad de respuestas"],
    },
    "documental": {
        "name": "Gestión documental y conocimiento", "max_autonomy": 3, "status": "planificado",
        "purpose": "Base de conocimiento con procedencia, versiones y permisos.",
        "capabilities": [], "sources": ["documents", "memory"], "pending": ["Carga y búsqueda de documentos por contenido"],
    },
    "competencia": {
        "name": "Inteligencia competitiva y benchmarking", "max_autonomy": 1, "status": "planificado",
        "purpose": "Benchmarking con fuentes públicas legítimas únicamente.",
        "capabilities": [], "sources": ["fuentes públicas"], "pending": ["Requiere modo IA con búsqueda web"],
    },
}


def summary() -> list[dict]:
    return [{"id": k, **{f: v[f] for f in ("name", "status", "max_autonomy", "purpose", "capabilities", "pending")}}
            for k, v in AGENTS.items()]
