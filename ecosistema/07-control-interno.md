# 07 · Control interno y gestión de riesgos

Marco de referencia: los 5 componentes de COSO (ambiente de control, evaluación de riesgos, actividades de
control, información y comunicación, supervisión), adaptados a una firma pequeña.

## Ambiente de control
- Código de ética: Ley 43 de 1990 (integridad, objetividad, independencia, confidencialidad, responsabilidad).
- Política de independencia: no prestar auditoría ni revisoría fiscal a un cliente al que se le lleva la contabilidad.
- Política de "no firmar lo no verificado".

## Matriz de riesgos

| # | Riesgo | Prob. | Impacto | Control | Responsable |
|---|---|---|---|---|---|
| R1 | Vencimiento tributario incumplido → sanción al cliente y reclamación | Media | Alto | Hoja **Obligaciones** con alertas a 5 días; revisión semanal los lunes | Contador titular |
| R2 | Error en una declaración | Media | Alto | Checklist de calidad + revisión cruzada + aprobación escrita del cliente | Contador titular |
| R3 | Cliente no paga | Media | Medio | Pago anticipado; suspensión a 15 días; contrato | Finanzas |
| R4 | Fuga o pérdida de información del cliente | Baja | Alto | Nube con 2FA, accesos mínimos, copias de seguridad, política de datos (Ley 1581) | Tecnología |
| R5 | Uso indebido de credenciales del cliente | Baja | Alto | Nada de contraseñas personales por chat; delegaciones formales; gestor de contraseñas | Contador titular |
| R6 | Dependencia del fundador (persona clave) | Alta | Alto | SOP documentados; calendario compartido; plan de contingencia con un colega aliado | Fundador |
| R7 | Responsabilidad profesional (demanda o investigación de la JCC) | Baja | Alto | Carta de encargo con alcance claro; evidencia de aprobaciones; **póliza de responsabilidad civil profesional** | Fundador |
| R8 | Lavado de activos o fraude del cliente | Baja | Alto | Conocimiento del cliente (KYC) al entrar: identificación, actividad y origen de fondos razonable; rechazar clientes con señales de alerta | Fundador |
| R9 | Concentración de ingresos | Media | Medio | Ningún cliente > 20% del ingreso | Finanzas |
| R10 | Sobrecarga de capacidad → baja calidad | Media | Medio | Contratar al llegar al 80% de capacidad; límites de volumen en los planes | Fundador |

Escala: probabilidad e impacto Baja/Media/Alta. Revisión **trimestral** de la matriz.

## Actividades de control clave
- **Segregación** (con equipo): quien registra no aprueba; quien prepara no presenta sin revisión.
- **Conciliaciones** mensuales: bancos, IVA, retenciones, nómina (ver el checklist en 04).
- **Bitácora** de presentación: fecha, formulario, número, quién preparó y quién revisó.
- **Accesos**: inventario de accesos por cliente; se revocan al terminar el contrato.
- **Copias de seguridad**: automáticas diarias en la nube + copia mensual externa.

## Información y comunicación
Aprobaciones del cliente siempre **por escrito** (correo o WhatsApp exportado a la carpeta del cliente).

## Supervisión
Autoevaluación trimestral: indicadores de calidad (errores, vencimientos), quejas y la matriz de riesgos actualizada.
Revisión de pares anual con un colega de confianza (muestra de 2 clientes).
