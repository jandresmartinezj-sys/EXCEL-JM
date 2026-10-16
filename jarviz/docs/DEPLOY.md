# Instalación, despliegue y recuperación

## Opción recomendada para empezar: privada con Tailscale (sin costo, sin exponer datos a internet)
Los datos de tus clientes no quedan publicados en internet: solo tus dispositivos acceden.
1. En un computador que esté encendido (o en un mini PC):
   ```bash
   git clone <repo> && cd EXCEL-JM/jarviz
   python3 -m pip install -r requirements.txt
   cp .env.example .env
   python3 -m app.cli create-user <tu_usuario> --role owner
   python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Instala Tailscale en el computador y en el iPhone (misma cuenta).
3. En el computador: `tailscale serve --bg 8000` → JARVIZ queda disponible con **HTTPS** en `https://<equipo>.<tu-tailnet>.ts.net` solo dentro de tu red privada.
4. En el iPhone (con Tailscale activo) abre esa URL y sigue `IPHONE.md`.

Limitación: si el computador se apaga, JARVIZ no responde.

## Opción servidor (VPS, ~USD 5–6 al mes; requiere tu aprobación del gasto)
- Ubuntu + `uvicorn` como servicio systemd detrás de **Caddy** (HTTPS automático con Let's Encrypt).
- Restringe el acceso: Caddy con lista de IPs o Tailscale en el servidor.
- Disco cifrado del proveedor (cifrado en reposo).

Ejemplo de Caddyfile:
```
jarviz.tudominio.com {
  reverse_proxy 127.0.0.1:8000
}
```

## Procesos programados (cron)
```cron
50 6 * * *  cd /ruta/jarviz && python3 -m app.cli run-scheduled >> data/scheduled.log 2>&1
15 23 * * * cd /ruta/jarviz && sqlite3 data/jarviz.db ".backup data/backups/jarviz-$(date +\%F).db"
```

## Copias de seguridad y recuperación
- Copia diaria con `.backup` (consistente aunque la app esté en uso) + copia semanal cifrada fuera del equipo (por ejemplo, `age` o `gpg` a tu nube).
- **Restaurar:** detén el servicio → copia el respaldo como `data/jarviz.db` → inicia → verifica con Más → Auditoría ("Cadena íntegra").
- Si la auditoría muestra la cadena rota: alguien modificó la BD por fuera de la app → restaura el último respaldo íntegro e investiga los accesos al servidor.

## Revocar tokens
Mientras no exista la pantalla de gestión de tokens:
```bash
sqlite3 data/jarviz.db "UPDATE tokens SET revoked = 1 WHERE kind = 'personal';"   # tokens de Siri
sqlite3 data/jarviz.db "UPDATE tokens SET revoked = 1;"                            # todas las sesiones
```
*(Es la única escritura directa permitida; no afecta la auditoría.)*

## Datos reales
```bash
python3 -m app.cli purge-demo                                        # quita la demostración
python3 -m app.cli import-excel ../plantillas/centro-de-control.xlsx  # importa tus datos (sin --demo)
```
Antes de importar, borra las filas de ejemplo de la plantilla.

## Verificación tras desplegar
1. `curl https://<url>/api/health` → `{"ok": true}`
2. `python3 -m pytest -q` en el servidor → todas las pruebas pasan.
3. Inicia sesión desde el iPhone y ejecuta la lista de `IPHONE.md` § 3.
