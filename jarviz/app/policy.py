"""Niveles de autonomía y catálogo de acciones.

Nivel 1 Consulta · 2 Preparación · 3 Ejecución interna · 4 Ejecución externa aprobada ·
5 Automatización recurrente supervisada.
Reglas: una acción de nivel > autonomía efectiva NO se ejecuta, se convierte en solicitud de
aprobación. Las acciones de nivel 4 SIEMPRE requieren aprobación humana. Los agentes no pueden
cambiar estos valores: solo el propietario, por la API de configuración, con auditoría.
"""
from .db import one

ACTIONS = {
    # nivel 1: consulta
    "read": 1,
    # nivel 2: borradores
    "draft.proposal": 2, "draft.report": 2, "draft.checklist": 2,
    # nivel 3: ejecución interna no crítica
    "internal.create_task": 3, "internal.create_prospect": 3, "internal.save_memory": 3,
    "internal.update_obligation_progress": 3, "internal.run_alerts": 3,
    # nivel 4: externo / irreversible / con obligación legal o financiera
    "external.send_message": 4, "external.send_proposal": 4, "external.file_declaration": 4,
    "external.payment": 4, "external.sign_document": 4, "internal.mark_obligation_filed": 4,
    "internal.delete_data": 4,
}
ALWAYS_APPROVAL = {a for a, lvl in ACTIONS.items() if lvl >= 4}


def global_autonomy(conn, default: int) -> int:
    r = one(conn, "SELECT value FROM settings WHERE key = 'max_autonomy'")
    try:
        return max(1, min(5, int(r["value"]))) if r else default
    except (TypeError, ValueError):
        return default


def decide(conn, action: str, agent_max: int, default_global: int) -> dict:
    """Devuelve {'allowed': bool, 'needs_approval': bool, 'level': int, 'reason': str}."""
    if action not in ACTIONS:
        return {"allowed": False, "needs_approval": False, "level": None, "reason": f"Acción desconocida: {action}"}
    level = ACTIONS[action]
    effective = min(agent_max, global_autonomy(conn, default_global))
    if action in ALWAYS_APPROVAL:
        return {"allowed": False, "needs_approval": True, "level": level,
                "reason": "Acción de nivel 4: requiere aprobación humana siempre."}
    if level > effective:
        return {"allowed": False, "needs_approval": True, "level": level,
                "reason": f"Nivel {level} supera la autonomía efectiva ({effective})."}
    return {"allowed": True, "needs_approval": False, "level": level, "reason": "Permitida"}
