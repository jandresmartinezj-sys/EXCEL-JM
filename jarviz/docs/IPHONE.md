# JARVIZ en el iPhone: instalación, voz y Siri

## Qué es posible en iOS (realista)
| Deseo | ¿Posible? | Cómo |
|---|---|---|
| Abrir JARVIZ como una app | ✅ | PWA: Safari → Compartir → **Agregar a pantalla de inicio** |
| Hablarle y que responda en voz | ✅ con condiciones | Botón 🎙 en la app (reconocimiento de voz del navegador + voz sintetizada). Si tu versión de iOS no lo permite en modo pantalla de inicio, usa el **micrófono del teclado** (dictado), que siempre funciona. |
| "Oye Siri, JARVIZ…" con la pantalla bloqueada | ✅ | **Atajo de Apple** llamado "JARVIZ" (abajo) |
| Palabra de activación propia escuchando siempre | ❌ | iOS no permite a apps de terceros (ni PWA ni nativas) escuchar de forma permanente. La alternativa real es Siri + Atajo. |
| Activación con un gesto | ✅ | Ajustes → Accesibilidad → Tocar → **Toque posterior** → doble toque = Atajo JARVIZ; o el **botón de Acción** (iPhone 15 Pro y posteriores) |
| Widget | ✅ | Widget de Atajos en la pantalla de inicio o de bloqueo |
| Notificaciones push | ⏳ | Web Push funciona en iOS 16.4+ con la PWA instalada (pendiente de implementar) |

**Requisito:** JARVIZ debe estar servido por **HTTPS** (el micrófono y la instalación lo exigen). Ver `DEPLOY.md`.

## 1. Instalar la app
1. En el iPhone abre Safari en `https://<tu-dominio-jarviz>`.
2. Inicia sesión con tu usuario de propietario.
3. Compartir → **Agregar a pantalla de inicio** → nombre "JARVIZ".
4. Abre JARVIZ desde el ícono. La primera vez que toques 🎙, iOS pedirá permiso de micrófono y de reconocimiento de voz: acéptalos.

## 2. Crear el Atajo de Siri "JARVIZ"
1. En la app JARVIZ: Más → Ajustes → **Generar token personal**. Cópialo (solo se muestra una vez).
2. Abre la app **Atajos** → **+** → nombre: **JARVIZ**.
3. Agrega estas acciones en orden:
   1. **Dictar texto** (idioma: español; "Dejar de escuchar": después de una pausa).
   2. **Obtener contenido de URL**:
      - URL: `https://<tu-dominio-jarviz>/api/shortcut`
      - Método: **POST**
      - Encabezados: `Authorization` = `Bearer <tu token>` · `Content-Type` = `application/json`
      - Cuerpo de la solicitud: **JSON** → campo `text` (texto) = variable **Texto dictado**
   3. **Leer texto** → "Contenido de la URL" (voz en español).
4. Prueba: "**Oye Siri, JARVIZ**" → espera el tono → "dame el estado general del negocio".

Si pierdes el teléfono: revoca el token (por ahora, cierra todas las sesiones desde el servidor; ver `DEPLOY.md` § Revocar tokens).

## 3. Lista de prueba manual de voz (pendiente de ejecutar en tu iPhone)
| # | Prueba | Resultado esperado |
|---|---|---|
| 1 | Tocar 🎙 y decir "dame el estado general del negocio" | Se ve "Escuchando…", aparece el texto transcrito, se envía y la respuesta se lee en voz alta |
| 2 | Tocar ■ mientras habla JARVIZ | La voz se detiene de inmediato |
| 3 | Decir "envía la propuesta a Ferretería El Progreso" | Responde que quedó en aprobaciones; aparece el contador en "Aprobar" |
| 4 | Negar el permiso de micrófono | Mensaje de cómo activarlo en Ajustes |
| 5 | Atajo "Oye Siri, JARVIZ" con el teléfono bloqueado | Siri dicta, envía y lee la respuesta |
| 6 | Ajustes → desactivar "Leer las respuestas en voz alta" | Las respuestas solo se muestran |

## Privacidad
El audio lo procesa el dictado de Apple; a JARVIZ solo llega texto. JARVIZ no graba ni guarda audio. El historial de texto se puede borrar desde Ajustes y se depura automáticamente según la retención configurada.
