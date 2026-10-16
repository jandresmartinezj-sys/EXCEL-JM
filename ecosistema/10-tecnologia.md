# 10 · Tecnología y automatización

## Herramientas básicas (fase 1: barato y suficiente)

| Necesidad | Herramienta | Nota |
|---|---|---|
| Contabilidad de clientes | El software del cliente (Siigo, Alegra, World Office, ContaPyme, Manager…) | Diferenciador: multiplataforma |
| Contabilidad propia y facturación | Alegra o Siigo (plan básico) | Factura electrónica desde el primer cliente |
| Archivos | Google Drive / OneDrive con 2FA | Estructura estándar de carpetas (ver 04) |
| Comunicación | WhatsApp Business + correo con dominio propio | Etiquetas por cliente y etapa |
| Comercial, operación y finanzas | **`centro-de-control.xlsx`** | Migrar a un CRM (p. ej., HubSpot gratis) al pasar de 30 clientes |
| Contraseñas | Gestor de contraseñas (Bitwarden, 1Password) | Nunca contraseñas en chats ni en Excel |
| Firma de documentos | Firma electrónica (proveedor certificado) | Contratos y aprobaciones |
| Agenda | Google Calendar + enlace de reservas | Diagnósticos en autoservicio |

## Automatizaciones prioritarias

| # | Proceso | Cómo | Ahorro |
|---|---|---|---|
| A1 | Alertas de vencimientos | Hoja **Obligaciones** (días restantes + semáforo); exportar al calendario | Riesgo R1 |
| A2 | Diagnóstico y propuesta | Plantilla `diagnostico-financiero-pyme.xlsx` | ~2 h por prospecto |
| A3 | Informe mensual del cliente | Reutilizar la hoja Diagnóstico con las cifras del mes | ~1 h por cliente |
| A4 | Recordatorios de soportes y cobro | Mensajes programados en WhatsApp Business o correo | Cobro a tiempo |
| A5 | Conciliación bancaria | Importar el extracto a Excel + cruce con la contabilidad (BUSCARX) | ~1–2 h por cliente |
| A6 | Uso de IA | Borradores de respuestas a requerimientos, resúmenes de normas, análisis de cifras. **Siempre** con revisión profesional; nunca subir datos personales de clientes a herramientas sin un acuerdo de confidencialidad | Tiempo de investigación |

## Seguridad de la información
- 2FA en todas las cuentas · cifrado del disco del computador · copia de seguridad diaria.
- Principio de mínimo privilegio en los accesos a los sistemas de los clientes.
- Al terminar un contrato: devolver la información, revocar accesos y conservar solo lo legalmente exigido.
