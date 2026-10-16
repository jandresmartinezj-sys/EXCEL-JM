# Integraciones

Estado honesto: **solo la API de Claude está implementada** (y probada con un cliente simulado, no contra el servicio real). Ninguna otra integración está conectada; JARVIZ no simula que lo esté.

| Integración | Para qué (necesidad) | Estado | Datos y permisos | Costo | Seguridad y recuperación |
|---|---|---|---|---|---|
| **API de Claude** (`claude-opus-5-5`) | Entender instrucciones libres y analizar con herramientas locales | ✅ código + pruebas simuladas; requiere `ANTHROPIC_API_KEY` | Se envían el texto de la instrucción, las últimas 10 vueltas de conversación y los resultados de las herramientas (cifras de la firma). **No** se envían documentos. | Por tokens (Opus 5.5: USD 4 entrada / 20 salida por millón; las lecturas de caché cuestan menos). Se registra en `llm_usage`. | Clave en el entorno. Alternativa de modelo del lado del servidor habilitada (`fallbacks: "default"`) para rechazos. Los errores dejan la tarea en `failed` con la causa. Sin clave → modo local. |
| Siri / Atajos de Apple | Activar por voz desde el iPhone | ✅ endpoint `/api/shortcut`; sin probar en un dispositivo | Token personal revocable | 0 | Revocar el token si se pierde el teléfono |
| Google Calendar | Llevar los vencimientos al calendario | ⏳ pendiente | OAuth (calendar.events) | 0 | Exportar .ics como primer paso (sin OAuth) |
| Gmail / correo transaccional | Enviar propuestas y recordatorios aprobados | ⏳ pendiente | OAuth (gmail.send) o un proveedor SMTP | 0–bajo | Solo tras aprobación (nivel 4); registrar el ID del mensaje |
| Google Drive / OneDrive | Expedientes documentales | ⏳ pendiente | OAuth con el alcance mínimo (archivo por carpeta) | 0 | Hash y versión en `documents` |
| Software contable (Siigo, Alegra…) | Leer movimientos y saldos de clientes | ⏳ pendiente; depende de la API de cada proveedor y del permiso del cliente | Token del cliente (por cliente) | Según el plan del proveedor | Solo lectura al inicio |
| Facturación electrónica | Emitir las facturas de la firma | ⏳ pendiente (hoy se registran a mano) | API del proveedor tecnológico | Por documento | Nunca automática sin aprobación |
| Firma electrónica | Contratos | ⏳ pendiente | API del proveedor certificado | Por firma | Nivel 4 |
| Notificaciones push | Alertas al teléfono | ⏳ pendiente: Web Push funciona en iOS 16.4+ con la PWA instalada; requiere claves VAPID y HTTPS | Suscripción del navegador | 0 | — |
| Fuentes oficiales (DIAN, SUIN-Juriscol, Diario Oficial) | Base normativa con fuente y vigencia | ⏳ pendiente (modo IA + búsqueda web con citas; nunca convertir una noticia en regla) | Lectura pública | Tokens | Cada conclusión debe guardar URL, fecha y vigencia |

**Orden recomendado** (por valor y riesgo): 1) Google Calendar (vencimientos) → 2) correo con aprobación → 3) Drive (expedientes) → 4) Web Push → 5) software contable.
