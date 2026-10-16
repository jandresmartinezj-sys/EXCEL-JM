# Seguridad y gobernanza

## Controles implementados
| Control | Implementación | Probado |
|---|---|---|
| Contraseñas | scrypt (n=2^14) con sal; mínimo 10 caracteres | ✅ |
| Sesiones | token aleatorio de 256 bits; en la BD solo el hash SHA-256; expiración (12 h); cierre de sesión que revoca | ✅ |
| Token personal (Siri/Atajos) | solo el propietario lo crea; vence (≤ 365 días); revocable; se muestra una vez | ✅ |
| Roles | owner, staff, client; el cliente solo accede a `/api/portal` con su `client_id` | ✅ |
| Separación entre clientes | consultas del portal filtradas por el `client_id` del token; memoria de cliente por `client_id` | ✅ |
| Mínimo privilegio | autonomía efectiva = min(agente, global); nivel 4 siempre con aprobación | ✅ |
| Auditoría | solo inserción (triggers) + cadena de hash verificable (`/api/audit`) | ✅ |
| Límite de solicitudes | login 5/min por IP+usuario; comandos 30/min por usuario | ✅ |
| Validación de entradas | pydantic (longitudes y rangos); SQL siempre parametrizado | ✅ |
| Cabeceras | CSP `default-src 'self'` sin scripts en línea, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy | ✅ |
| Frontend | todo el texto de datos se inserta con `textContent` (sin HTML) | revisión de código |
| Secretos | solo variables de entorno; `.env` en `.gitignore`; `.env.example` sin valores | ✅ |
| Errores | mensajes sin trazas ni secretos | revisión |
| Datos en caché del teléfono | el service worker nunca guarda respuestas de `/api/` | revisión |
| Instrucciones maliciosas en documentos | el modo IA trata los datos como resultados de herramientas; las herramientas no permiten acciones externas ni cambiar permisos | ✅ (prueba con cliente simulado) |

## Matriz de permisos
| Acción | owner | staff | client | Nivel | Requiere aprobación |
|---|---|---|---|---|---|
| Consultar tablero, tareas, alertas, agentes | ✅ | ✅ | ❌ | 1 | — |
| Dar instrucciones a JARVIZ | ✅ | ✅ | ❌ | 1–3 | según el nivel |
| Borradores (propuestas, informes, checklists) | ✅ | ✅ | ❌ | 2 | si la autonomía < 2 |
| Crear tareas, prospectos, notas | ✅ | ✅ | ❌ | 3 | si la autonomía < 3 |
| Enviar mensajes o propuestas, presentar declaraciones, pagar, firmar, borrar datos, marcar una obligación como presentada | solicita | solicita | ❌ | 4 | **siempre** (decide el owner) |
| Decidir aprobaciones | ✅ | ❌ | ❌ | — | — |
| Cambiar la autonomía global | ✅ | ❌ | ❌ | — | auditado |
| Ver la auditoría | ✅ | ❌ | ❌ | — | — |
| Crear un token personal (Siri) | ✅ | ❌ | ❌ | — | auditado |
| Ver su propio portal | — | — | ✅ | 1 | — |

## Privacidad de la voz
- El audio **no llega a JARVIZ**: el reconocimiento lo hace el navegador (en iPhone, el servicio de dictado de Apple) y al servidor solo llega el texto.
- No se graban ni se guardan audios. El indicador "Escuchando…" y el botón rojo son visibles mientras el micrófono está activo.
- Historial de conversación: retención configurable (30 días por defecto, `run-scheduled` lo depura) y borrado por el usuario desde Ajustes.

## Pendiente (no implementado; no afirmar que existe)
- Cifrado en reposo de la BD → usar disco cifrado del servidor o SQLCipher (ver `docs/DEPLOY.md`).
- HTTPS → lo provee el proxy inverso o la plataforma de despliegue; **obligatorio** para usar el micrófono en el iPhone.
- 2FA para el propietario, bloqueo de cuenta persistente, límite de solicitudes distribuido (si hay varios procesos).
- Escaneo automático de dependencias (sugerido: `pip-audit` en CI).
