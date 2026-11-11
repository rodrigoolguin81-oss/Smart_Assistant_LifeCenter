**Proyecto Final Bootcamp AI Engineering**

# Smart Assistant - LifeCenter

LifeCenter es una clínica dental que va a construir **Smart Assistant**, un asistente de Telegram que atiende a los pacientes 24/7 y descarga a recepción de las consultas repetitivas.

Stakeholders identificados:

| Stakeholder | Rol | Lo que quiere | Lo que no dice |
| --- | --- | --- | --- |
| Rossana Riquelme | Directora de LifeCenter (sponsor) | Atender más pacientes sin contratar más personal en recepción, cumpliendo el RGPD | Le preocupa la imagen de la clínica si el bot responde mal |
| Prince Calderon | Odontóloga | Agenda ordenada, sin huecos vacíos ni dobles reservas | No quiere que el bot opine sobre tratamientos ni síntomas |
| Pacientes | Usuarios finales | Respuesta rápida y pedir cita sin llamar | Nadie les ha preguntado si usan o prefieren Telegram |

## 1. Problema

Recepción dedica gran parte de su tiempo a responder siempre las mismas preguntas (precios, horarios, seguros, preparación de tratamientos) y a gestionar citas por teléfono. Fuera de horario las llamadas y mensajes quedan sin respuesta, y parte de esos pacientes no vuelve a contactar. Además, las citas no presentadas dejan huecos en la agenda que no se recuperan.

(Datos reales pendientes: hasta confirmarlos con LifeCenter, el PRD trabaja con cifras estimadas.)

## 2. Objetivo

Reducir la carga de consultas repetitivas en recepción y el número de citas perdidas, atendiendo a los pacientes por Telegram a cualquier hora.

## 3. Alcance — fuera

- Modificaciones e integraciones con el software de gestión clínica en producción.
- Diagnóstico, consejo clínico o recomendación de medicamentos.
- Acceso a la historia clínica del paciente.
- Cobros y pagos por Telegram.
- Integración con WhatsApp en esta fase (la arquitectura queda preparada para añadirlo después).
- Reducción de la plantilla de recepción.
- Contacto proactivo con pacientes con fines comerciales (campañas, promociones).
- Varias sedes y otros idiomas distintos del español.

## 4. Alcance — dentro

- Base de conocimiento de LifeCenter: tratamientos, precios, horarios, seguros y cuidados pre y post tratamiento.
- PoC del asistente por Telegram que responde preguntas frecuentes con fuente, mediante RAG sobre la base de conocimiento (sin base de datos vectorial).
- Arquitectura independiente del canal: el agente, la base de conocimiento y la agenda no dependen de Telegram, para poder sumar WhatsApp en una fase posterior.
- Solicitud, cambio y cancelación de citas sobre una agenda propia del proyecto.
- Recordatorio de cita 24 h antes.
- Derivación a recepción de urgencias, quejas y consultas sin respuesta en la base.
- Panel mínimo para que recepción vea las conversaciones derivadas.

## 5. Criterios de éxito

Los valores objetivo son una propuesta inicial que se deberá confirmar con datos reales de la clínica LifeCenter.

| Métrica | Valor objetivo | Plazo | Cómo se mide |
| --- | --- | --- | --- |
| Llamadas a recepción por consultas frecuentes | Reducción del 30 % mínimo | Fin del piloto (90 días) | Registro de llamadas de recepción antes y durante el piloto |
| Mensajes fuera de horario respondidos en menos de 1 minuto | 95 % mínimo | Fin del piloto | Telemetría del bot (hora de llegada y de respuesta) |
| PoC asistente | Validación de respuesta en 90 % | PoC | Evaluación y tests sobre un banco de preguntas reales |
| Consejos clínicos emitidos por el bot | 0 (100 % de casos derivados) | PoC | Eval con mensajes de síntomas y revisión de conversaciones |
| Coste medio de inferencia por conversación | 0,01 € máximo | PoC | Telemetría de uso de la API |
| Citas gestionadas por Telegram | 20 % mínimo del total | Fin del piloto | Citas creadas por el bot / citas totales en la agenda |
| Citas no presentadas | Reducción del 20 % mínimo | Fin del piloto | Tasa de ausencias antes y después de activar recordatorios |

## 6. Riesgos principales

Dueños: DIR = Directora de LifeCenter, ODO = Odontóloga, PO = Product Owner del proyecto. Cada riesgo se detalla en el PRD §8 con el mismo orden (R-01 a R-07).

| Riesgo | Probabilidad | Impacto | Respuesta y mitigación | Dueño |
| --- | --- | --- | --- | --- |
| Alucinación en precios o tratamientos | Alta | Alto | Mitigar. Responder solo con la base de conocimiento, citar la fuente y derivar a recepción si no hay evidencia. | PO |
| Consejo clínico o urgencia mal gestionada | Media | Alto | Mitigar. Guardrails en el prompt, detección de urgencias y derivación inmediata; eval al 100 %. | ODO |
| Baja adopción de Telegram entre los pacientes | Alta | Alto | Mitigar. Difundir el bot con código QR y enlace en recepción y en la web; mantener el teléfono; arquitectura preparada para sumar WhatsApp. | PO |
| Base de conocimiento desactualizada o incompleta | Media | Alto | Mitigar. Un responsable de mantener tarifas y FAQ, con fecha de vigencia en cada documento. | ODO |
| Doble reserva del mismo hueco | Baja | Medio | Mitigar. Bloqueo de la agenda al reservar y test de concurrencia. | PO |
| Incumplimiento RGPD con datos de salud | Media | Alto | Mitigar. Consentimiento en el primer mensaje, mínimos datos en prompts, seudonimización de logs y borrado a los 30 días. | DIR |
| Rechazo de los pacientes al nuevo canal | Media | Medio | Mitigar. Mantener el teléfono, ofrecer siempre "hablar con una persona" y pedir feedback. | DIR |

## 7. Supuestos

- LifeCenter puede crear y gestionar un bot oficial de Telegram con el nombre de la clínica.
- La información de tarifas, horarios, seguros y cuidados existe por escrito o se puede redactar antes del piloto.
- Una parte suficiente de los pacientes acepta usar Telegram para consultas, citas y recordatorios.
- Recepción revisa las conversaciones derivadas durante su horario.
- Para el PoC basta con una agenda propia del proyecto, sin tocar el software de gestión clínica.
- Se cargarán primero los documentos que cubren las preguntas más frecuentes.

## 8. Qué no sabemos todavía

- ¿Qué software de agenda usa LifeCenter y si ofrece una API para integrarlo después del PoC?
- ¿Cuántas llamadas y mensajes recibe recepción al día, y qué parte llega fuera de horario?
- ¿Los precios se pueden publicar tal cual o dependen siempre de una valoración previa?
- ¿Quién mantendrá actualizada la base de conocimiento cuando cambien tarifas o tratamientos?
- ¿LifeCenter tiene DPO propio o asesoría externa, y qué base legal usa para tratar datos de salud?
- ¿Qué porcentaje de pacientes de LifeCenter usa Telegram o estaría dispuesto a instalarlo?
