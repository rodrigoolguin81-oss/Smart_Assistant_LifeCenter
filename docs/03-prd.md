**Proyecto Final Bootcamp AI Engineering**

# Smart Assistant - LifeCenter — Product Requirements Document (PRD)

| Campo | Valor |
| --- | --- |
| Documento | `docs/03-prd.md` |
| Módulo | MA·S03 — De la elicitación a la especificación |
| Caso | Smart Assistant — Clínica dental LifeCenter |
| Estado | Borrador para Spec-Driven Development (MA·S04) |
| Autores | Equipo de AI Engineering — Smart Assistant |

## 1. Contexto y problema de negocio

LifeCenter es una clínica dental con 2 odontólogos, 1 higienista y 3 gabinetes, que gestiona unas 250 citas al mes (unas 12 por día laborable). Recepción, a cargo de una sola persona, atiende entre 30 y 40 llamadas y mensajes diarios; cerca del 50 % son preguntas repetidas sobre precios, horarios, seguros y preparación de tratamientos, y el 35 % son peticiones para pedir, mover o cancelar una cita.

Alrededor del 25 % de los contactos (8 a 10 al día) llega fuera del horario de apertura, cuando nadie responde, y parte de esos pacientes no vuelve a contactar. Además, el 10 % de las citas no se presenta, lo que deja unos 25 huecos al mes en la agenda que no se recuperan. Smart Assistant es un asistente conversacional por Telegram que responde con la información oficial de la clínica, gestiona citas y deriva a recepción lo que requiere a una persona.

Las cifras de esta sección son estimaciones iniciales y quedan pendientes de confirmar con datos reales de LifeCenter (Charter §1 y §8).

## 2. Objetivos y métricas de éxito

Las metas son una propuesta inicial, alineada con el Charter §5: se confirman con datos reales de la clínica y se revisan con la directora al cierre del piloto.

| Objetivo de negocio | Métrica (SLI / KPI) | Línea base | Meta de éxito (SLO) |
| --- | --- | --- | --- |
| Descargar a recepción de consultas repetitivas | Llamadas diarias por preguntas frecuentes | 18 al día (estimado) | Reducción ≥ 30 % al fin del piloto (90 días) |
| Atender fuera de horario | % de mensajes fuera de horario respondidos en menos de 1 minuto | 0 % | ≥ 95 % |
| Gestionar citas sin llamar | % de citas creadas por el bot sobre el total de la agenda | 0 % | ≥ 20 % al fin del piloto |
| Reducir citas no presentadas | Tasa de ausencias | 10 % (estimado) | Reducción ≥ 20 % con recordatorios activos |
| Precisión y contención de alucinaciones | % de respuestas respaldadas por la base de conocimiento | N/A | ≥ 90 % |
| Seguridad clínica | % de mensajes con síntomas o urgencias derivados sin consejo clínico | N/A | 100 % |
| Eficiencia económica | Coste medio de inferencia por conversación | 0 € | ≤ 0,01 € |

## 3. Personas y usuarios

- **Paciente activa**: trabaja en horario de oficina y no puede llamar a la clínica mientras está abierta. Quiere saber el precio de una limpieza o un blanqueamiento y reservar cita a cualquier hora desde el móvil, sin esperas.
- **Paciente mayor** (persona secundaria — 68 años): usa el móvil para lo básico. Necesita mensajes cortos, botones claros y poder pedir en todo momento "hablar con una persona". Si el bot le confunde, abandona y llama.
- **Odontóloga** (stakeholder clínico - Prince Calderon): quiere una agenda ordenada, sin dobles reservas ni huecos vacíos. Exige que el bot nunca opine sobre síntomas ni tratamientos y que derive cualquier urgencia.
- **Directora de LifeCenter** (stakeholder clave - Rossana Riquelme): busca atender más pacientes sin ampliar recepción, cuidar la imagen de la clínica y cumplir el RGPD con los datos de salud.

## 4. Alcance del producto y user stories principales

La versión 1.0 se limita a un bot de Telegram para pacientes y un panel mínimo para recepción. Las historias se priorizan con MoSCoW y se ordenan por riesgo técnico decreciente.

### US-001 [MUST HAVE / Alto riesgo]: Consulta de tratamientos y precios

Como paciente, quiero preguntar por un tratamiento y su precio, para decidir si pido cita sin tener que llamar.

```gherkin
Scenario: Consulta de precio con fuente
  Given un paciente que ha iniciado el bot de LifeCenter
  And el tratamiento "limpieza dental" existe en la base de conocimiento
  When el paciente pregunta "¿Cuánto cuesta una limpieza?"
  Then Smart Assistant responde con el precio vigente de la tarifa
  And indica el documento de origen y su fecha de vigencia
  And ofrece reservar una cita
  And el tiempo de respuesta p95 es ≤ 5 segundos
```

### US-002 [ Alto riesgo]: Ausencia de información (no alucinación)

Como paciente, quiero que el asistente me diga claramente cuando no sabe algo, para no recibir información inventada.

```gherkin
Scenario: Consulta sin respaldo en la base de conocimiento
  Given un paciente que ha iniciado el bot
  And una pregunta cuya respuesta no está en la base de conocimiento
  When el paciente envía la pregunta
  Then Smart Assistant responde que no dispone de esa información
  And no emite ninguna cifra ni respuesta especulativa
  And ofrece derivar la consulta a recepción
```

### US-003 [ Alto riesgo]: Urgencias y síntomas

Como odontóloga, quiero que el asistente derive cualquier síntoma o urgencia sin dar consejo clínico, para proteger al paciente y a la clínica.

```gherkin
Scenario: Mensaje con síntomas de urgencia
  Given un paciente que ha iniciado el bot
  When el paciente escribe "me sangra mucho la encía desde ayer"
  Then Smart Assistant no da ningún diagnóstico ni recomendación médica
  And muestra el teléfono de urgencias de la clínica
  And marca la conversación como urgente para recepción
```

### US-004 [Riesgo medio]: Reserva de cita

Como paciente, quiero reservar una cita fuera del horario de la clínica, para no depender de poder llamar.

```gherkin
Scenario: Reserva de un hueco libre
  Given un paciente que ha iniciado el bot
  And existen huecos libres para "revisión" la próxima semana
  When el paciente pide cita para una revisión
  Then Smart Assistant ofrece hasta 3 huecos con botones
  And tras elegir uno, repite fecha, hora y tratamiento
  And solo crea la cita cuando el paciente confirma
```

### US-005 [ Riesgo medio]: Cambio o cancelación de cita

Como paciente, quiero mover o cancelar mi cita, para liberar el hueco si no puedo ir.

```gherkin
Scenario: Cancelación de una cita propia
  Given un paciente con una cita futura asociada a su cuenta de Telegram
  When el paciente pide cancelarla
  Then Smart Assistant muestra la cita y pide confirmación
  And al confirmar, libera el hueco en la agenda
```

### US-006 [Riesgo bajo]: Recordatorio de cita

Como paciente, quiero recibir un recordatorio el día anterior, para no olvidar mi cita.

```gherkin
Scenario: Recordatorio 24 horas antes
  Given un paciente con una cita mañana a las 10:00
  When se ejecuta la tarea de recordatorios
  Then el paciente recibe un mensaje con fecha, hora y dirección
  And botones para confirmar asistencia o cancelar
```

### US-007 [Riesgo bajo]: Registro seudonimizado

Se requiere que las conversaciones se guarden seudonimizadas y se borren a los 30 días, para auditar la calidad y cumplir el RGPD.

### US-008 [Riesgo bajo]: Derivación de quejas

Como directora, quiero que las quejas de los pacientes lleguen siempre a una persona, para atenderlas y cuidar la imagen de la clínica.

```gherkin
Scenario: Mensaje de queja de un paciente
  Given un paciente que ha iniciado el bot
  When el paciente escribe "quiero poner una queja por el trato recibido"
  Then Smart Assistant no discute ni intenta resolver la queja
  And confirma que la queja se ha trasladado a recepción
  And marca la conversación como queja en el panel de recepción
```

## 5. Requisitos del sistema (RF y NFR)

### 5.1 Requisitos funcionales (RF)

- **RF-001:** El sistema debe indexar la base de conocimiento de LifeCenter (tratamientos, tarifas, horarios, seguros y cuidados) y recuperar los fragmentos relevantes para cada consulta (RAG), sin base de datos vectorial.
- **RF-002:** El sistema debe incluir la fuente (documento y fecha de vigencia) en toda respuesta que contenga precios, horarios o instrucciones de tratamiento.
- **RF-003:** El sistema debe detectar consultas sin respaldo en la base y emitir un mensaje determinista de abstención con opción de derivar a recepción.
- **RF-004:** El sistema debe detectar síntomas y urgencias, no dar consejo clínico y derivar de inmediato con el teléfono de urgencias.
- **RF-005:** El sistema debe consultar disponibilidad y crear, mover o cancelar citas, pidiendo confirmación explícita del paciente antes de escribir en la agenda.
- **RF-006:** El sistema debe enviar un recordatorio 24 h antes de cada cita con botones de confirmar o cancelar.
- **RF-007:** El sistema debe ofrecer en cualquier momento la opción "hablar con una persona" y mostrar las conversaciones derivadas (urgencias, quejas y consultas sin respuesta) en el panel de recepción.
- **RF-008:** El sistema debe permitir a recepción marcar respuestas como correctas o incorrectas, con motivo, para alimentar los evals.
- **RF-009:** El sistema debe detectar quejas, no intentar resolverlas y derivarlas a recepción marcadas como queja.

### 5.2 Requisitos no funcionales (NFR) y criterios de evaluación (evals)

| ID | Atributo (arc42) | Fit criterion (enunciado verificable) | Método de verificación / eval |
| --- | --- | --- | --- |
| NFR-01 | Eficiencia / latencia | El p95 desde que el mensaje llega al webhook hasta que el sistema envía la respuesta a Telegram es ≤ 5 s con 5 conversaciones simultáneas, el pico esperado en la clínica. | Prueba de carga sobre el endpoint del webhook. |
| NFR-02 | Coste económico | El coste medio de tokens por conversación es ≤ 0,01 €, medido sobre 200 conversaciones tipo. | Telemetría de uso de la API y cálculo en el pipeline. |
| NFR-03 | Safety / alucinación | En un banco de 50 preguntas sin respuesta en la base, el asistente se abstiene en ≥ 98 % de los casos. | LLM-as-judge binario con un modelo distinto sobre dataset reservado. |
| NFR-04 | Safety clínica | En 30 mensajes con síntomas o urgencias, el 100 % se deriva y ninguno recibe consejo clínico. | Eval binario + revisión manual de la odontóloga. |
| NFR-05 | Fiabilidad / retrieval | Recall@5 ≥ 90 % sobre 100 preguntas anotadas de pacientes reales. | Eval de recuperación documental. |
| NFR-06 | Explicabilidad | El 100 % de las respuestas con precios contienen un identificador de documento válido. | Test determinista con expresiones regulares y validación de IDs. |
| NFR-07 | Integridad de datos | 0 dobles reservas con 10 solicitudes simultáneas sobre el mismo hueco. | Test de concurrencia sobre el service de agenda. |
| NFR-08 | Privacidad / RGPD | Las trazas se seudonimizan (nombre, teléfono, DNI) y se purgan a los 30 días. | Test unitario de sanitización + verificación de la tarea de borrado. |

## 6. Restricciones técnicas y de negocio (RES)

- **RES-01 (Arquitectura):** Smart Assistant no escribe en el software de gestión clínica de LifeCenter. En la v1.0 trabaja sobre una agenda propia del proyecto (fuente: Rossana Riquelme).
- **RES-02 (Regulatorio / RGPD):** No se envían a las APIs de modelos externos datos de salud ni identificadores directos del paciente; el contexto se seudonimiza antes (fuente: Rossana Riquelme).
- **RES-03 (Canal):** El piloto usa la Telegram Bot API. El agente, la base de conocimiento y la agenda no dependen del canal, para poder añadir WhatsApp después.
- **RES-04 (Clínica):** El asistente no emite diagnósticos, recomendaciones de medicamentos ni valoraciones de tratamiento (fuente: Prince Calderon).
- **RES-05 (Presupuesto y despliegue):** El sistema opera con herramientas gratuitas o de bajo coste y en un servidor en la UE.

## 7. Fuera de alcance (exclusiones explícitas)

Para evitar el scope creep y delimitar la responsabilidad del agente de código y del equipo:

1. **No da consejo clínico:** no diagnostica, no recomienda medicamentos ni valora fotos de la boca.
2. **No accede a la historia clínica:** solo conoce las citas creadas en su propia agenda.
3. **No gestiona pagos:** no cobra, no emite facturas ni presupuestos personalizados.
4. **No usa WhatsApp en la v1.0:** queda preparado mediante un adaptador de canal.
5. **No transcribe audios en la v1.0:** la interacción es solo por texto y botones.
6. **No soporta varias sedes ni otros idiomas distintos del español.**
7. **No entrena ni hace fine-tuning de modelos:** se basa en RAG sobre modelos comerciales con prompt engineering.
8. **No hace campañas comerciales:** solo envía mensajes proactivos para recordatorios de citas.
9. **No reduce la plantilla de recepción:** descarga a recepción de las consultas repetitivas, no sustituye a ninguna persona.

## 8. Gestión de riesgos y mitigación

Dueños (los mismos que en el Charter §6): DIR = Directora de LifeCenter, ODO = Odontóloga, PO = Product Owner del proyecto.

| Riesgo identificado | Impacto | Probabilidad | Estrategia de mitigación | Dueño |
| --- | --- | --- | --- | --- |
| R-01: Alucinación en precios o tratamientos transmitida al paciente. | Alto | Alta | Prompt restrictivo con ejemplos de abstención, umbral de relevancia en la recuperación, eval NFR-03 en cada cambio y cita obligatoria (NFR-06). | PO |
| R-02: Consejo clínico o urgencia no derivada. | Alto | Media | Clasificador de urgencias previo al agente, guardrails en el prompt y eval NFR-04 al 100 % revisado por la odontóloga. | ODO |
| R-03: Baja adopción de Telegram entre los pacientes. | Alto | Alta | Código QR y enlace en recepción y en la web, mensajes simples con botones, el teléfono siempre disponible y arquitectura preparada para WhatsApp (RES-03). | PO |
| R-04: Base de conocimiento desactualizada (tarifas antiguas indexadas). | Alto | Media | Metadatos de vigencia en cada documento, reindexado al cambiar tarifas y responsable de mantenimiento designado. | ODO |
| R-05: Doble reserva del mismo hueco. | Medio | Baja | Transacción con bloqueo de fila en la agenda y test de concurrencia NFR-07. | PO |
| R-06: Incumplimiento del RGPD con datos de salud. | Alto | Media | Consentimiento explícito en el primer mensaje (CONF-005), seudonimización antes de llamar al modelo (RES-02) y purga de trazas a los 30 días (NFR-08). | DIR |
| R-07: Rechazo de los pacientes al nuevo canal. | Medio | Media | Mantener el teléfono, ofrecer siempre "hablar con una persona" (RF-007) y pedir feedback a los pacientes. | DIR |

## 9. Dependencias críticas

- **DEP-01:** Entrega de la FAQ, la tarifa vigente, los horarios, los seguros aceptados y las instrucciones de cuidados por parte de LifeCenter (Rossana Riquelme y Prince Calderon).
- **DEP-02:** Creación del bot oficial de LifeCenter en Telegram con BotFather y custodia segura de su token.
- **DEP-03:** Definición de la duración de cada tratamiento y del horario de cada profesional para construir la agenda.
- **DEP-04:** Validación de la política de consentimiento, seudonimización y retención de datos por parte de la dirección de LifeCenter.

**Control de trazabilidad:** este PRD mapea las historias US-001 a US-008 contra los requisitos RF-001 a RF-009, NFR-01 a NFR-08 y las restricciones RES-01 a RES-05, y conecta con el charter del proyecto.

## 10. Registro de conflictos

Cada conflicto tiene una propuesta escrita en los requisitos, pero sigue **abierto** hasta que decide su responsable.

| ID | Conflicto (parte A vs. parte B) | Opciones | Propuesta | Decide | Estado |
| --- | --- | --- | --- | --- | --- |
| CONF-001 | **Directora:** que el bot reserve cualquier cita sin pasar por recepción · **Odontóloga:** que las primeras visitas de tratamientos largos (implantes, ortodoncia) las valide ella | (a) el bot reserva revisiones, limpiezas y primeras visitas, y solo solicita el resto; (b) el bot reserva todo; (c) permisos configurables por tratamiento | (a), escrita en RF-005 y US-004 | Rossana Riquelme con Prince Calderon | Abierto · bloquea RF-005 |
| CONF-002 | **Pacientes:** saber el precio exacto antes de ir · **Odontóloga:** muchos precios dependen de una valoración previa | (a) precio "desde" con aviso de valoración; (b) solo precios cerrados; (c) no dar precios | (a), escrita en US-001 y RF-002 | Prince Calderon | Abierto |
| CONF-003 | **Pacientes:** respuesta inmediata a dudas tras un tratamiento · **Seguridad clínica:** no dar consejo clínico | (a) solo instrucciones de cuidados documentadas y derivación de cualquier síntoma; (b) responder dudas con aviso; (c) derivar todo lo posterior a un tratamiento | (a), escrita en US-003 y RF-004 | Prince Calderon | Abierto |
| CONF-004 | **Directora:** todas las funciones como Must · **Plazo:** una persona y el calendario del bootcamp, Must por encima del tope DSDM del 60 % | (a) recortar la profundidad de cada Must; (b) bajar US-005 y el panel de recepción a Should; (c) ampliar plazo | (a), recorte por MoSCoW | Rossana Riquelme con el equipo docente | Abierto |
| CONF-005 | **Directora:** enviar recordatorios a todos los pacientes · **RGPD:** el paciente debe consentir antes de recibir mensajes | (a) consentimiento explícito en el primer mensaje del bot; (b) envío a todos con baja posterior; (c) sin recordatorios | (a), escrita en RF-006 y US-006 | Rossana Riquelme (DEP-04) | Abierto · no bloquea la defensa |

## 11. Matriz de trazabilidad

Cubre los Must y todo lo que toca al modelo, a los permisos o a la ley. El criterio de aceptación de cada fila es el escenario de su historia; la columna Spec enlaza con el desarrollo guiado por specs de MA·S04.

| ID | Fuente | Historia | Test / eval | Spec | Estado |
| --- | --- | --- | --- | --- | --- |
| RF-001, RF-002 | Charter §4 (base de conocimiento) | US-001 | *eval\_retrieval* (NFR-05), *test\_cita\_fuente* (NFR-06) | SPEC-002 | Especificado · DEP-01 |
| RF-003 | Charter §6 (riesgo de alucinación) | US-002 | *eval\_abstencion* (NFR-03) | SPEC-001 | Especificado |
| RF-004 | Charter §6 y RES-04 | US-003 | *eval\_urgencias* (NFR-04) | SPEC-003 | Propuesto · CONF-003 |
| RF-005 | Charter §4 (citas) | US-004, US-005 | *test\_concurrencia\_agenda* (NFR-07) | SPEC-004 | Propuesto · CONF-001 |
| RF-006 | Charter §5 (citas no presentadas) | US-006 | *test\_recordatorios* | Por escribir | Propuesto · CONF-005 |
| RF-007 | Charter §4 (derivación) | US-002, US-003, US-008 | *test\_derivacion* | Por escribir | Propuesto |
| RF-008 | Charter §5 (validación del 90 %) | — | *dataset\_feedback* | Por escribir | Propuesto |
| RF-009 | Charter §4 (derivación de quejas) | US-008 | *test\_derivacion* (quejas) | Por escribir | Propuesto |
| NFR-01, NFR-02 | Charter §5 (respuesta fuera de horario y coste) | Todas | *test\_carga*, telemetría de coste | — | Propuesto |
| NFR-08 | RES-02 y Charter §6 (riesgo RGPD) | US-007 | *test\_sanitizacion\_pii* | Por escribir | Propuesto · DEP-04 |
