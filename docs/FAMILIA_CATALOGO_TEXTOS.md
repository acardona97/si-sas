# Catálogo de textos — Módulo Sociedad de Familia (S.A.S.)

Documento de análisis para incorporar la plantilla `02_Plantilla_ajustada_alternativas.docx` al motor de generación de estatutos. Fuentes usadas: `02_Plantilla_ajustada_alternativas.docx` (plantilla objetivo), `01_Plantilla_base_sin_ajustes.docx` (redacción original FAGO, referencia de texto concreto), `03_Ajustes_control_de_cambios.docx` (revisado a través de su síntesis en `Guia_y_observaciones (1).md`, en adelante "la Guía"), `Guia_de_campos_alternativas_y_ajustes.docx`, `Diccionario_placeholders.json/csv` (213 campos) y, como respaldo cuando 01 no trae una cláusula equivalente, `plantillas/estatutos_template.docx` (plantilla comercial vigente de la plataforma).

Convención de confianza: **[OK]** = texto verbatim de 01 o de la plantilla comercial, sin objeción jurídica de la Guía. **[AJUSTADO]** = texto modificado respecto del original porque la Guía señala un error, incoherencia o exigencia normativa (se cita el párrafo). **[DUDA]** = requiere decisión del usuario/abogado antes de fijarse como texto por defecto; se explica la duda en una línea y se traslada a la sección 4.

---

## 1. Mapa de estructura de la plantilla 02

Arquitectura: Acto de constitución + Estatutos (10 capítulos, artículos 1 a 67, 5 disposiciones transitorias) + tabla de capital. Fuente: `Guia_y_observaciones (1).md` §1, confirmado línea por línea en `02_Plantilla_ajustada_alternativas.docx`.

| Capítulo | Artículos | Contenido |
|---|---|---|
| Acto de constitución | — | Comparecencia (`[[REPETIR constituyentes]]`) |
| I. Nombre, forma, nacionalidad, domicilio, duración y objeto | 1–3 | Denominación, duración, objeto (con alternativa de objeto amplio) |
| II. Capital social, acciones y accionistas | 4–23 | Capital, clases (`[[REPETIR clases]]`), dividendos por escenarios (`[[REPETIR dividendos.escenarios]]`), transferencias, conversión, emisión, preferencias, gravámenes, usufructo, acuerdos de accionistas |
| III. Dirección y administración | 24 | Junta directiva (opcional), consejo de familia (opcional), definición de grupo familiar |
| IV. Asamblea general de accionistas | 25–44 | Quórum, mayorías, decisiones reservadas (`[[REPETIR decisiones_reservadas]]`), convocatoria, reformas, fusión/escisión, enajenación global |
| V. Representación legal | 45–46 | Representante legal, suplentes, facultades y límites |
| VI. Revisoría fiscal | 47–48 | Período, suplencia, funciones |
| VII. Estados financieros, reservas y utilidades | 49–55 | Reservas, dividendos, escenarios de reparto |
| VIII. Disolución y liquidación | 56–62 | Causales, liquidador |
| IX. Disposiciones varias | 63–65 | Controversias/arbitraje, protocolo de familia |
|  | 66–67 | Opción de compra (v1 = alternativa negativa) y exclusión (v1 = alternativa negativa) |
| X. Disposiciones transitorias | Art. 1º–5º transitorios | Nombramientos (`[[REPETIR nombramientos]]`), capital (`[[REPETIR suscripciones]]`), revisor fiscal inicial, registro de libros, poder para trámites, firmas (`[[REPETIR firmantes]]`) |

### 1.1 Bloques condicionales `[[SI]]` (19 módulos) — texto exacto de cada alternativa

| # | Opción (`opciones.*`) | Artículo | Alternativa A (texto exacto, se imprime si se elige) | Alternativa B / complemento |
|---|---|---|---|---|
| 1 | `objeto_amplio` | 3 | *"La sociedad podrá realizar cualquier actividad civil o comercial lícita en Colombia o en el exterior. Las actividades sujetas a autorización o régimen especial solo se desarrollarán previo cumplimiento de sus requisitos."* | No hay bloque negativo impreso; si es falso, el artículo 3 termina en el objeto principal + operaciones conexas. |
| 2 | `aportes_especie` | 4 | *"Los aportes en especie, su valoración aprobada, identificación y entrega se describen así: {{capital.aportes_especie_detalle}}. Cuando su transferencia requiera escritura pública, la constitución y la transferencia cumplirán esa formalidad y los registros correspondientes."* | Sin bloque negativo (se omite si todos los aportes son en dinero). |
| 3 | `dividendos_preferenciales_o_fijos` | 6 | *"Antes de aplicar la distribución residual, se observará el siguiente régimen especial de dividendos mínimos, preferenciales o fijos: {{dividendos.regimen_preferencial_completo}}. En este caso los porcentajes de los escenarios se aplicarán al saldo residual definido en dicho régimen, sin duplicar asignaciones."* | Sin bloque negativo (se omite si no hay dividendo preferencial). |
| 4 | `prohibicion_temporal` | 7 | *"Se prohíbe negociar las acciones de las clases {{transferencias.clases_restringidas}} durante {{transferencias.prohibicion_anios}} años, contados individualmente desde su emisión, sin exceder de diez (10) años. La prohibición constará en los títulos. Su prórroga requerirá la voluntad unánime de todos los accionistas y cada período adicional no excederá de diez (10) años."* | Sin bloque negativo (se omite el párrafo). |
| 5 | `autorizacion_transferencias` | 7 | *"La transferencia de las acciones de las clases {{transferencias.clases_autorizacion}} requerirá autorización previa de la asamblea, adoptada mediante {{mayorias.autorizacion_transferencias}} y sujeta a {{transferencias.criterios_admision}}."* | Sin bloque negativo. |
| 6 | `conversion_por_transferencia` | 8 | Bloque `[[REPETIR conversiones]]` con la regla de conversión automática por clase. | `sin_conversion_por_transferencia` (B, complemento calculado): *"La transferencia de acciones no modificará su clase por sí sola."* |
| 7 | `preferencia_suscripcion` | 18 | *"Los accionistas tendrán preferencia conforme al siguiente orden: {{preferencia_suscripcion.orden}}... Una emisión podrá colocarse sin preferencia mediante {{mayorias.exclusion_preferencia_suscripcion}}..."* | `sin_preferencia_suscripcion` (B): *"No habrá derecho estatutario de preferencia en nuevas suscripciones ni en recolocaciones, sin perjuicio de los derechos de clase y las normas imperativas."* |
| 8 | `preferencia_transferencia` | 20 | *"La transferencia voluntaria de acciones estará sujeta al siguiente orden de preferencia: {{preferencia_transferencia.orden}}..."* (procedimiento completo arts. 100-104 de la plantilla) | `sin_preferencia_transferencia` (B): *"No existirá derecho estatutario de preferencia en la transferencia, sin perjuicio de las demás restricciones expresamente pactadas."* |
| 9 | `junta_directiva` | 24 | *"Existirá junta directiva integrada por {{junta.numero_principales}} miembros principales y {{junta.regimen_suplencias}}, elegidos por {{junta.sistema_eleccion}} para períodos de {{junta.periodo}}..."* | Sin bloque negativo (se omite si no hay junta). |
| 10 | `consejo_familia` | 24 | *"Existirá un consejo de familia consultivo, integrado conforme a {{familia.integracion_consejo}}..."* | Sin bloque negativo. |
| 11 | `arbitraje` | 63 | *"Las controversias susceptibles de arbitraje... se resolverán por un tribunal de {{controversias.numero_arbitros}} árbitro(s)... administrado por {{controversias.centro_arbitraje}}, con sede en {{controversias.sede}}..."* | `sin_arbitraje` (B): *"Las controversias serán conocidas por la autoridad judicial competente, incluida la Superintendencia de Sociedades cuando tenga competencia, conforme a las reglas legales."* |
| 12 | `protocolo_familia` | 65 | *"Los accionistas podrán adoptar un protocolo de familia sobre {{familia.materias_protocolo}}. Solo tendrá la eficacia contractual, estatutaria o de acuerdo de accionistas que corresponda por su contenido y formalización..."* | Sin bloque negativo. |
| 13 | `opcion_compra` | 66 | Cláusula completa de opción de compra (arts. 207-211). **v1: no se activa** (decisión ya tomada). | `sin_opcion_compra` (B) — **texto por defecto en v1**: *"No se pacta opción estatutaria de compra por adjudicación a terceros."* |
| 14 | `exclusion` | 67 | Cláusula completa de exclusión con catálogo de causales (`[[REPETIR exclusion.causales]]`). **v1: no se activa** (decisión ya tomada). | `sin_exclusion` (B) — **texto por defecto en v1**: *"No se pactan causales estatutarias de exclusión, sin perjuicio de las medidas que autorice directamente la ley."* |
| 15 | `revisor_fiscal_inicial` | 3º transitorio | *"La sociedad designa al revisor fiscal identificado en el artículo primero transitorio, con su aceptación y acreditación de requisitos."* | `sin_revisor_fiscal_inicial` (B): *"No se designa revisor fiscal al constituirse por no configurarse obligación legal ni estatutaria. Si surge la obligación, la asamblea efectuará oportunamente la designación."* |
| 16 | `poder_tramites` | 5º transitorio | *"{{poder.poderdantes}} confiere(n) poder especial a {{poder.apoderado_nombre}}... para {{poder.facultades}}, hasta {{poder.vencimiento}}..."* | Sin bloque negativo (se omite todo el artículo 5º transitorio). |

Bloques `[[REPETIR]]` (colecciones, no campos únicos): `constituyentes`, `clases`, `dividendos.escenarios` (anidado con `escenario.asignaciones`), `conversiones`, `decisiones_reservadas`, `exclusion.causales`, `nombramientos`, `suscripciones` (con instrucción editorial de duplicar solo la fila de la tabla + el detalle individual, conservando encabezado/totales una vez — Guía §2), `firmantes`.

---

## 2. Campos de texto jurídico (banco de textos principal/subsidiario)

213 campos totales en el diccionario. De ellos, en este análisis se clasifican **103 como campos de texto jurídico** (requieren redacción controlada, no captura libre del usuario final — Guía §2 "no conviene permitir texto libre del usuario final en ellos"), **23 como interruptores de módulo** (`opciones.*`, booleanos, ya cubiertos en la sección 1) y **87 como datos simples** (sección 3).

Se agrupan por artículo/cláusula porque casi todos comparten una sola frase-plantilla en 02 (columna "contexto" del diccionario). Fuente por defecto: 01 (redacción FAGO) cuando trae el concepto; si no, la plantilla comercial `estatutos_template.docx`; ajustada donde la Guía lo exige.

### Capítulo I — Objeto

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `sociedad.objeto_principal` | 3 | **Fijo por decisión del usuario**: objeto de "precautelación del patrimonio familiar" (texto exacto en sección 5 de este documento). | No aplica (objeto fijo para este módulo). | 01, art. 3 | [OK] — decisión ya tomada |
| `sociedad.operaciones_conexas` | 3 | *"todas las operaciones, de cualquier naturaleza que ellas fueren, relacionadas con el objeto mencionado, así como cualquier actividad similar, conexa o complementaria o que permita facilitar o desarrollar el comercio o la industria de la sociedad, entre ellas, adquirir bienes muebles e inmuebles necesarios para sus actividades primordiales y enajenar unos y otros, construir edificios e instalaciones que requiera para el cumplimiento del objeto, tomar o dar dinero en préstamo a interés, gravar en cualquier forma sus bienes muebles e inmuebles..., obtener derechos de propiedad sobre marcas, patentes y privilegios..., promover y formar empresas de la misma índole..., celebrar contratos de sociedad o de asociación..., ejercer la representación o agencia..., y en general hacer en su propio nombre o por cuenta de terceros... toda clase de operaciones..."* (texto completo en 01 línea 10 / plantilla comercial línea 13, idéntico en ambas) | — | 01 art. 3 / plantilla comercial (verbatim, idénticas) | [OK] |

### Capítulo II — Capital, clases y dividendos

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `mayorias.creacion_conversion_clases` | 5 | *"el voto favorable de accionistas que representen al menos el setenta por ciento (70 %) de los votos que confieren las acciones suscritas, sin perjuicio de las aprobaciones de clase que correspondan cuando la creación, emisión o conversión afecte derechos adquiridos"* | *"...el voto favorable de accionistas que representen la mitad más una de los votos que confieren las acciones suscritas..."* (umbral más bajo, si el diseño familiar prioriza agilidad sobre protección) | 01 art. 5 (`articulo_5.parametro_1/2`, sin cifra fija) + plantilla comercial (70 %) | [AJUSTADO] — Guía §4 exige que cada `mayorias.*` incluya umbral + operador + denominador explícitos, no solo "70 %" |
| `clase.regimen_voto_especial` | 6.a | *"No existen asuntos sometidos a reglas especiales de voto ni eventos de adquisición o recuperación del voto distintos de los generales de estos estatutos."* (opción por defecto = sin reglas especiales) | Texto a definir si la clase tiene voto múltiple con reglas de recuperación (p. ej. "el voto múltiple se suspende si el titular dejare de ejercer funciones directivas"). | Nuevo (02 no trae texto por defecto) | [DUDA] — depende del diseño de control que elija la familia (ver Guía §3 "un número alto de votos no es automáticamente ilegal") |
| `clase.derechos_economicos_adicionales` | 6.b | *"Esta clase no tiene derechos económicos adicionales a los previstos en el régimen de dividendos por escenarios de este artículo."* | Texto si se pacta dividendo preferencial/fijo (remite a `dividendos.regimen_preferencial_completo`). | Nuevo | [DUDA] |
| `clase.derechos_liquidacion` | 6.c | *"Su derecho sobre el remanente será proporcional al capital nominal pagado de sus acciones, sin preferencia adicional sobre otras clases."* | *"Esta clase tendrá preferencia sobre el remanente hasta la restitución del capital pagado, antes de cualquier reparto a otras clases."* | Nuevo, formulado a partir de la regla general del art. 62 de 02 | [AJUSTADO] — evita el vacío que la Guía señala en §5 (faltaba escenario A+C / regla para remanentes) |
| `clase.requisitos_titularidad` | 6.d | *"No se exigen requisitos especiales de titularidad distintos de los generales para ser accionista."* | *"Solo podrán ser titulares de esta clase las personas naturales que integren el grupo familiar según la definición de {{familia.definicion_grupo}}."* | Nuevo | [DUDA] — condicionar la titularidad por parentesco es una elección válida pero debe coordinarse con la sucesión y no vaciar derechos de terceros (Guía §4, transferencias y gobierno) |
| `clase.derechos_especiales` / `clase.aprobacion_modificacion_derechos` | 6.e | *"Esta clase no tiene derechos particulares adicionales."* / *"además de las aprobaciones generales aplicables, se requerirá el voto favorable de la totalidad de los titulares de la clase afectada"* | Texto a definir si hay veto u otros derechos particulares. | Nuevo | [DUDA] |
| `dividendos.regimen` | 6 (cierre) | *"Reparto por escenarios de concurrencia de clases, conforme a la matriz explícita de este artículo, sin fórmula genérica de reparto"* | *"Reparto proporcional simple al capital nominal pagado, sin distinción de escenarios"* (solo viable si hay una única clase con acciones en circulación) | Guía §4 "Dividendos por escenarios" (matriz explícita exigida cuando hay ≥2 clases) | [OK] — sigue la corrección de la Guía §5 (faltaba el escenario A+C en el original) |
| `dividendos.regimen_preferencial_completo` | 6 alt. A | *(solo si se activa el módulo)* debe definir: base o monto, tasa, prioridad, acumulación o no, tratamiento de insuficiencia de utilidades, participación residual y derechos de voto excepcionales, conforme al listado exigido en la Guía §4. No hay texto por defecto en 01 (no existía esta figura en el original). | — | Guía §4 "Si se activan dividendos fijos o preferenciales..." | [DUDA] — módulo nuevo, exige diseño ad hoc; bloquear si el régimen queda incompleto |
| `dividendos.regla_redondeo` | 6 / 53 | *"El residuo de redondeo se asignará a la clase o accionista con mayor participación en el escenario respectivo, dejando constancia expresa en el acta, sin perder ninguna suma del monto total distribuido."* | *"El residuo se distribuirá proporcionalmente entre todos los beneficiarios del escenario, en la unidad monetaria mínima."* | Nuevo, a partir de la exigencia de la Guía §4 ("redondear con asignación documentada de residuos, sin perder dinero del reparto") | [AJUSTADO] |

### Capítulo II — Transferencias, conversión, gravámenes, emisión, preferencias

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `transferencias.clases_restringidas`, `transferencias.clases_autorizacion`, `transferencias.criterios_admision`, `mayorias.autorizacion_transferencias` | 7 | Restricción temporal: contada **desde la emisión** (no desde el registro), máximo 10 años, prórroga por unanimidad y máximo 10 años adicionales — texto ya fijado en 02. `criterios_admision` por defecto: *"que el adquirente acredite su pertenencia al grupo familiar según {{familia.definicion_grupo}} o, en su defecto, la aprobación de la asamblea"*. `mayorias.autorizacion_transferencias`: *"el voto favorable de accionistas que representen al menos el setenta por ciento (70 %) de los votos que confieren las acciones suscritas"* | `criterios_admision` alternativo: *"sin criterios adicionales distintos de la autorización de la asamblea"* | 02 art. 7 (regla del plazo, ya corregida) + Guía §5 Art. 7 ("el artículo 13 de la Ley 1258 cuenta la restricción... se corrige el inicio desde... la emisión", fuente 1) | [AJUSTADO] para el plazo (sigue la ley); [DUDA] para `criterios_admision` (no hay texto de origen) |
| `conversion.clase_origen`, `titulares_habilitados`, `evento`, `clase_destino`, `relacion_canje`, `momento_efectos`, `excepciones` | 8 | Reconstrucción del mecanismo "intuito personae" de 01 (arts. 7-8): la clase de fundador se mantiene solo en cabeza del titular original; ante transferencia voluntaria, forzosa o transmisión por causa de muerte, las acciones **se convierten automáticamente** a la clase ordinaria, en relación de canje 1:1 (mismo valor nominal), desde el momento en que se perfecciona la transferencia o la adjudicación a herederos. Excepciones sugeridas: *"la mera constitución de un gravamen o embargo no dispara la conversión"*. | *"Sin conversión automática: las acciones conservan su clase pese al cambio de titular"* (equivale a activar `opciones.sin_conversion_por_transferencia`). | 01 arts. 7-8 (texto original, con corrección) | [AJUSTADO] — Guía §5 Art. 8: *"un embargo no es por sí solo transferencia. Se elimina como disparador automático..."*; y Guía §4: *"relación de canje compatible con igual valor nominal y conservación de capital... La muerte de un fundador no transmite automáticamente a otro su voto privilegiado."* |
| `mayorias.gravamenes` | 14 | *"el voto favorable de accionistas que representen, al menos, la mitad más una de los votos que confieren las acciones suscritas"* | *"...al menos el setenta por ciento (70 %)..."* (umbral reforzado) | Plantilla comercial, cláusula de gravámenes (verbatim) | [AJUSTADO] — Guía §5: *"Artículos 14, 15 y 65: había autorizaciones por mitad más uno y por más del 70 %... Se centralizaron las mayorías"* |
| `mayorias.usufructo` | 15 | *"el voto favorable de accionistas que representen, al menos, la mitad más una de los votos que confieren las acciones suscritas"* | *"...al menos el setenta por ciento (70 %)..."* | Plantilla comercial (verbatim) | [AJUSTADO] — misma referencia que gravámenes |
| `mayorias.emision`, `emision.plazo_oferta_texto` | 16-17 | Mayoría: *"la mitad más una de los votos que confieren las acciones suscritas"*. Plazo de oferta: *"no menor de quince (15) días hábiles ni superior a tres (3) meses calendario"* (límites legales de 01 art. 16 literal d). | Mayoría alterna 70 %. | 01 art. 16 (plazo verbatim) / comercial (mayoría) | [OK] plazo (cumple mínimos legales); [AJUSTADO] mayoría (formato completo) |
| `preferencia_suscripcion.orden`, `.procedimiento`, `.negociabilidad`, `mayorias.exclusion_preferencia_suscripcion` | 18-19 | Orden por defecto: *"un único turno, proporcional entre todos los accionistas según su participación en el capital suscrito"* (más simple que el escalonado A/B/C de 01, que era un diseño de control, no una exigencia legal). Procedimiento: turno único, remanente ofrecido nuevamente a quienes aceptaron. Negociabilidad: *"el derecho será negociable únicamente entre accionistas, a prorrata de su participación"* (01 art. 19, verbatim). Mayoría de exclusión de preferencia: 70 % (01/comercial). | Orden alterno: *"escalonado — primero clase {{...}}, luego clase {{...}}"* (reproduce el diseño de 01, válido pero es elección de control, no default recomendado). | 01 arts. 18-19 (orden escalonado original) + Guía §5 "Artículo 18: preferencia escalonada A/B/C es una elección de control. Se parametriza..." | [DUDA] para el orden (elección de diseño familiar); [OK] para negociabilidad (verbatim, sin objeción legal) |
| `preferencia_transferencia.orden`, `.eventos`, `.excepciones`, `.equivalencia_actos_no_dinerarios`, `mayorias.dispensa_preferencia_transferencia` | 20 | Orden por defecto: *"1) la sociedad; 2) los demás accionistas, a prorrata de su participación"* (esquema simple de la plantilla comercial, sin escalonar por clases). Eventos incluidos: *"venta, permuta, donación, aporte en especie a sociedades, constitución de usufructo"* (01 parágrafo 2º, verbatim). Excepciones sugeridas: *"escisión o fusión con unidad de beneficiario real; transferencia a matriz/filial/subsidiaria con unidad de beneficiario real; adjudicación por liquidación de un accionista persona jurídica a sus propios socios; sociedad con accionista único"* (01 parágrafo 3º, verbatim). Equivalencia actos no dinerarios: *"se tomará el valor comercial o catastral más reciente del bien o derecho ofrecido en pago, o el que determine un perito si las partes no lo acuerdan"*. Dispensa: 70 % (01/comercial). | Orden alterno escalonado por clases (reproduce 01 arts. 20 lits. B-I). | 01 art. 20 y parágrafos 1º-3º (verbatim en eventos/excepciones) | [OK] eventos/excepciones (verbatim, sin objeción); [AJUSTADO] consecuencia de incumplimiento — ver nota abajo; [DUDA] excepciones por reorganización (Guía §5: *"pueden permitir ingreso indirecto de personas no deseadas... deben armonizarse con la definición de grupo familiar"*) |
| — | 20 (consecuencia) | La consecuencia por incumplir el procedimiento de preferencia es **ineficacia de pleno derecho** (art. 15 Ley 1258/2008), no "inoponibilidad" como decía 01. | — | Guía §5: *"el original calificaba la contravención como 'inoponible'... el artículo 15 de la Ley 1258 contempla ineficacia de pleno derecho... Fuente 1"* | [AJUSTADO] |
| `mayorias.readquisicion` | 21 | *"la mitad más una de los votos que confieren las acciones suscritas"* | *"...al menos el setenta por ciento (70 %)..."* | 01 art. 20-21 / comercial (verbatim "mitad más una") | [OK] |

### Capítulo III — Junta directiva, consejo de familia, grupo familiar

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `junta.regimen_suplencias` | 24 | **Fijo por decisión del usuario**: *"suplencias personales para cada miembro principal"* | — | Decisión del proyecto | [OK] |
| `junta.sistema_eleccion` | 24 | *"cociente electoral, permitiendo el voto acumulativo o por planchas conforme lo decida la asamblea en cada elección"* | *"mayoría simple de la asamblea, sin sistema de cociente"* | Ley 1258 art. 23 (remite al mecanismo legal de fraccionamiento para cuerpos colegiados) | [DUDA] — elección de diseño, no hay texto de 01 (01 no preveía junta directiva) |
| `junta.periodo` | 24 | *"un (1) año, con posibilidad de reelección indefinida"* | *"dos (2) años"* | Analogía con período del representante legal en 01/comercial (1 año) | [DUDA] |
| `junta.funciones` | 24 | *"las que le asigne la asamblea al momento de su creación, sin asumir las funciones indelegables de la asamblea"* | Lista específica de funciones delegadas (asesoría estratégica, supervisión del representante legal, etc.) | Nuevo (01 no tenía junta) | [DUDA] |
| `junta.convocante`, `junta.medio_convocatoria`, `junta.dias_convocatoria` (número) | 24 | Convocante: *"el representante legal o cualquiera de sus miembros"*. Medio: *"comunicación escrita física o electrónica a los datos registrados"*. Días: 5 hábiles (mínimo legal análogo al de la asamblea, art. 34). | — | Analogía con art. 34 de 02 | [AJUSTADO] (se homologa al mínimo de 5 días hábiles que exige la Guía §4) |
| `junta.quorum`, `junta.mayoria` | 24 | Quorum: *"la mayoría de sus miembros"*. Mayoría: *"la mayoría de los miembros presentes"*. | Quorum/mayoría calificados (p. ej. unanimidad para ciertos temas). | Estándar societario genérico | [DUDA] |
| `junta.reglas_funcionamiento` | 24 | *"se reunirá de manera ordinaria al menos una vez al año y extraordinariamente cuando sea convocada; las actas se llevarán en libro registrado; en caso de empate decidirá el voto del presidente de la junta"* | — | Nuevo | [DUDA] |
| `familia.integracion_consejo`, `.periodo_consejo`, `.funcionamiento_consejo`, `.funciones_consejo` | 24 | Consultivo, sin funciones de administración (para no exigirle el régimen de responsabilidad de administradores). Integración: *"los accionistas mayores de edad del grupo familiar definido, o sus representantes"*. Funciones: *"recomendar sobre política de dividendos, ingreso de nuevas generaciones y protocolo de familia, sin sustituir las decisiones de la asamblea ni conferir representación legal"*. | Consejo de familia con funciones de administración real (requiere entonces diseñar competencias y responsabilidades como órgano administrador). | Guía §3: *"El consejo de familia se propone consultivo; si se le atribuye administración real hay que diseñar sus competencias y responsabilidades como órgano administrador."* | [AJUSTADO] (naturaleza consultiva, siguiendo la Guía) |
| `familia.definicion_grupo` | 24 (cierre) | *"los accionistas fundadores, sus cónyuges o compañeros permanentes, y los descendientes y ascendientes en primer grado de consanguinidad de los fundadores"* (definición contractual, no sustituye la ley) | Definición más amplia (incluye colaterales) o más restringida (solo descendencia directa). | Nuevo — la plantilla exige explícitamente: *"Esa definición no altera el parentesco legal, la vocación hereditaria ni los derechos de cónyuges, compañeros permanentes, acreedores u otros terceros"* (02 art. 24 cierre, verbatim) | [DUDA] — decisión de diseño central de todo el módulo familiar |
| `familia.materias_protocolo` | 65 | *"gobierno corporativo familiar, ingreso y salida de familiares como accionistas o empleados, política de dividendos y educación patrimonial de las siguientes generaciones"* | — | Nuevo | [DUDA] |

### Capítulo IV — Asamblea (mayorías y decisiones reservadas)

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `asamblea.operador_mayoria` | 30 | *"superen el"* (para mayoría de más del 50 %) | *"representen al menos el"* (si se pacta un umbral superior, p. ej. 60 % o 70 %) | Guía §4: *"el valor de 'asamblea.operador_mayoria' será, por ejemplo, 'superen el' para más del 50 %, o 'representen al menos el' para un umbral superior admisible. No representar mayoría simple como 'al menos 50 %'."* | [OK] — sigue literalmente la instrucción de la Guía |
| `asamblea.regla_fraccionamiento` | 32 | *"para los demás asuntos no se permite el fraccionamiento del voto, salvo lo dispuesto por norma imperativa"* | *"se permite el fraccionamiento en cualquier votación, en los mismos términos que para juntas directivas"* | Guía §5: *"se elimina la prohibición absoluta de fraccionar votos; el artículo 23 [Ley 1258] contempla fraccionamiento para elegir juntas u otros cuerpos colegiados. Fuente 1"* | [AJUSTADO] |
| `decision.aprobacion`, `decision.regla_sin_clase` (por cada fila de `decisiones_reservadas`) | 31 | Aprobación adicional tipo: *"el voto favorable de la totalidad de los titulares de la clase protegida"*. Regla si no hay acciones en circulación de esa clase: *"la decisión se adopta con la mayoría general aplicable, sin aprobación adicional"* | Aprobación de clase por mayoría simple de la clase (menos protector). | Nuevo, siguiendo Guía §4: *"listar materia, clase protegida, umbral y solución si la clase deja de existir"* | [DUDA] — depende de qué decisiones se listen (típicamente: reformas que afecten la clase, fusión/escisión, emisión que diluya) |

### Capítulos V-VIII — Representación legal, revisoría, reservas, dividendos, disolución

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `representacion.denominacion_cargo` | 45 | *"un representante legal"* | *"un representante legal principal y uno o más suplentes personales"* | 01/comercial (representante legal único, con suplentes opcionales) | [OK] |
| `representacion.organo_designacion`, `.periodo` | 45 | Designación: *"la asamblea general de accionistas"*. Período: *"un (1) año, reelegible indefinidamente y removible en cualquier tiempo"* (verbatim 01/comercial). | Período de 2 años. | 01 art. 45 / comercial (verbatim) | [OK] |
| `representacion.regimen_suplencias`, `.facultades_suplentes` | 45 | **Fijo por decisión del usuario**: suplencias personales, opcionales; *"el suplente asumirá las mismas funciones y facultades del principal, en sus faltas absolutas, temporales o accidentales"* | — | Decisión del proyecto + 01 art. 45 | [OK] |
| `representacion.organo_autorizacion`, `.operaciones_reservadas`, `.limite_cuantia` | 46 | Órgano: *"la asamblea general de accionistas"*. Operaciones reservadas por defecto: *"adquirir, enajenar o gravar activos por un valor superior al {{limite}} % del patrimonio líquido de la sociedad en un mismo año, y otorgar garantías a favor de terceros"*. Límite de cuantía: *"operaciones relacionadas dentro de un mismo ejercicio se acumulan para efectos del límite"*. | Sin límite de cuantía (solo operaciones enumeradas taxativamente). | Nuevo — reemplaza la cláusula abierta de 01/comercial ("bajo las siguientes condiciones", sin contenido) | [AJUSTADO] — Guía §5: *"Artículo 46: había facultades con frases abiertas sin condiciones... Se convirtieron en facultades generales y límites configurables."* |
| `representacion.politica_prestamos_garantias` | 46/65 | *"se prohíbe a la sociedad otorgar préstamos a accionistas o administradores, así como avalar, afianzar o garantizar sus obligaciones personales"* (regla más protectora del patrimonio familiar) | *"se permite previa autorización de la asamblea con el voto favorable de la mitad más una de las acciones suscritas"* | 01 art. 46 párrafo prohibiciones (base) + Guía §5: *"prohibir préstamos y garantías para familiares es una elección de protección patrimonial, no un requisito universal. Se convierte en política definida"* | [AJUSTADO] |
| `revisoria.periodo`, `.suplencia` | 47 | Período: *"un (1) año, pudiendo ser reelegido"* (verbatim 01/comercial). Suplencia: *"el suplente reemplazará al principal en sus faltas absolutas, temporales o accidentales"* (verbatim). | — | 01 art. 47 / comercial (verbatim) | [OK] |
| `reservas.regimen`, `.parametros` | 51 | *"no será obligatoria la apropiación de una reserva legal estatutaria, sin perjuicio de las reservas de normas especiales aplicables"* (verbatim 01/comercial, "no será obligatorio... apropiar reserva legal alguna") | *"se pactará una reserva estatutaria del {{parámetro}} % de las utilidades líquidas de cada ejercicio, hasta alcanzar el {{límite}} % del capital suscrito"* | 01 art. 51 / comercial (verbatim, opción "no reserva") | [OK] — Guía §5: *"la ausencia de reserva legal obligatoria puede formar parte del régimen de S.A.S.; se permite seleccionar una reserva estatutaria o no pactarla"* |
| `mayorias.reservas` | 52 | *"la mitad más una (1) de las acciones representadas en la reunión"* | 70 % de las acciones representadas | 01/comercial art. 52 (verbatim) | [OK] |
| `mayorias.dividendos`, `dividendos.forma_plazo_pago` | 53 | Mayoría: se remite a la mayoría ordinaria general del art. 30 (`asamblea.operador_mayoria` + `asamblea.mayoria_porcentaje`), no un porcentaje fijo distinto. Forma y plazo de pago: *"en dinero efectivo, en la proporción pagada de cada acción, dentro del plazo que fije la asamblea al decretarlos"* (01 art. 53, verbatim). | Mayoría reforzada específica para dividendos (p. ej. 70 %). | 01 art. 53 (forma/plazo verbatim) + Guía §5: *"el 70 % del original no se deja como regla universal suficiente"* | [AJUSTADO] mayoría; [OK] forma/plazo |
| `dividendos.destino_renuncias` | 54 | *"las sumas renunciadas incrementarán la utilidad distribuible entre los demás accionistas de la misma clase, a prorrata de su participación, en el mismo ejercicio"* | *"las sumas renunciadas se llevarán a una reserva ocasional"* | Nuevo (01 no regulaba la renuncia individual a dividendos) | [DUDA] |
| `dividendos.no_reclamados` | 55 | *"quedarán en la caja social, en depósito disponible a la orden de sus titulares, sin generar intereses"* (verbatim 01/comercial) | — | 01 art. 55 / comercial (verbatim) | [OK] |
| `mayorias.disolucion` | 56 | *"por lo menos la mitad más una de las acciones suscritas"* (verbatim 01/comercial) | 70 % | 01 art. 56 / comercial (verbatim) | [OK] |
| `liquidacion.causales_adicionales` | 56 | *"no se pactan causales estatutarias adicionales a las legales"* (opción por defecto, más simple) | Causal adicional específica (p. ej. "pérdida de la calidad de S.A.S. familiar por salida de todos los fundadores") | Nuevo | [DUDA] — opcional, sin default sugerido por la Guía |

### Capítulo IX — Controversias, protocolo, opción de compra (v1 negativa), exclusión (v1 negativa), poder

| Campo(s) | Artículo | Texto principal | Texto subsidiario | Fuente | Confianza |
|---|---|---|---|---|---|
| `opcion_compra.*` (13 campos: `clases`, `terceros_comprendidos`, `eventos`, `beneficiarios_orden`, `prorrata`, `fecha_limite_eventos`, `plazo_ejercicio`, `inicio_computo`, `fecha_valoracion`, `metodo_valoracion`, `entidad_designadora`, `requisitos_perito`, `objeciones`, `costos`, `pago_garantias_cierre`) | 66 | **Diferido a versión 2.** Para v1 se usa la alternativa B fija: *"No se pacta opción estatutaria de compra por adjudicación a terceros."* Estos 13 campos no se piden en el cuestionario de v1. | — | Decisión del proyecto (v1 = alternativa negativa) + Guía §5: *"la compra a herederos o adjudicatarios no es una confiscación... no se conserva automáticamente una opción de cien años con tres años para ejercer... su alcance debe revisarse según el evento y los terceros afectados. Fuente 4"* | [DUDA] (bloqueado para revisión legal, no se activa en v1) |
| `exclusion.clases`, `exclusion.metodo_reembolso`, `mayorias.exclusion`, `causal.codigo`, `causal.descripcion`, `causal.acreditacion` | 67 | **Diferido a versión 2.** Para v1 se usa la alternativa B fija: *"No se pactan causales estatutarias de exclusión, sin perjuicio de las medidas que autorice directamente la ley."* Si en v2 se activa, catálogo sugerido de causales objetivas (Guía §3): *"disposición contraria a restricciones estatutarias; incumplimiento grave y probado de obligaciones societarias; apropiación o daño doloso acreditado al patrimonio social; divulgación ilícita grave de información reservada"*, cada una con reembolso conforme arts. 14-16 Ley 222/1995 y, si reduce capital, art. 145 C. Co. (sin descuento sancionatorio automático del 20 %, a diferencia del original). | — | Decisión del proyecto (v1 negativa) + Guía §5 (catálogo de causales admisibles y eliminación del descuento del 20 % y del indicio por inasistencia) | [DUDA] (bloqueado en v1); catálogo sugerido [AJUSTADO] para cuando se active |
| `controversias.dias_arreglo`, `.numero_arbitros`, `.centro_arbitraje`, `.sede`, `.dias_designacion` | 63 | Arreglo directo: 30 días calendario (01/comercial, verbatim). Árbitros: número impar, p. ej. 1 o 3 (Guía §4: "número impar de árbitros"). Centro: Centro de Conciliación y Arbitraje de la Cámara de Comercio del domicilio social (01/comercial, verbatim, adaptado al domicilio real). Sede: la misma ciudad del domicilio social. Designación: 5 días calendario (01, verbatim). | Sin arbitraje (activa `opciones.sin_arbitraje`, texto ya fijado: remisión a jueces y a la Superintendencia de Sociedades). | 01/comercial art. 63 (verbatim, adaptado al domicilio de cada sociedad) | [OK] |
| `familia.materias_protocolo` | 65 | Ver tabla de Capítulo III. | | | |
| `poder.poderdantes`, `.sustitucion`, `.vencimiento`, `.facultades` | 5º transitorio | Poderdantes: *"todos los constituyentes"*. Vencimiento: *"doce (12) meses contados desde la fecha de este documento"* (mismo plazo de 01, pero variable, no fijo). Sustitución: *"el apoderado podrá sustituir y reasumir el poder"* (verbatim 01). Facultades: lista taxativa de trámites de constitución, RUT, cámara de comercio, DIAN, inscripción de libros y situación de control — **sin** facultad para modificar aportes, derechos accionarios o decisiones sustanciales (así quedó acotado en 02, a diferencia de 01 que daba poderes "amplios y suficientes"). | — | 01 art. 5º transitorio (base) + 02 art. cierre ("Este mandato no autoriza a modificar aportes, derechos accionarios o decisiones sustanciales...") | [AJUSTADO] — Guía §5: *"Poder transitorio y firmas: había facultades muy amplias de modificación y aceptación de cargos... Se delimitó el mandato... El plazo de doce meses se volvió variable."* |

**Recuento de la sección 2:** 103 campos de texto jurídico cubiertos → 34 marcados **[OK]** (verbatim o siguiendo instrucción literal de la Guía), 24 **[AJUSTADO]** (modificados por exigencia normativa o de coherencia), 45 **[DUDA]** (de los cuales 28 corresponden a los módulos íntegros de opción de compra y exclusión, diferidos a v2 por decisión ya tomada; los 17 restantes son decisiones de diseño familiar genuinas: junta directiva, consejo de familia, definición de grupo, órdenes de preferencia, decisiones reservadas, límites de representación, causales de disolución adicionales y destino de renuncias a dividendos).

---

## 3. Campos de datos simples (especificación del cuestionario)

87 campos. Se agrupan por bloque de cuestionario. Todos se capturan directamente del usuario (texto libre corto, número, fecha o selección de una lista cerrada) y no requieren banco de cláusulas.

| Bloque | Campos | Tipo |
|---|---|---|
| **Sociedad** | `sociedad.nombre_completo`, `sociedad.municipio`, `sociedad.departamento`, `sociedad.duracion_texto` (menú: indefinida / plazo fijo), `sociedad.organo_sucursales` (menú: asamblea / representante legal) | texto, texto, texto, selección, selección |
| **Constitución** | `constitucion.lugar`, `constitucion.fecha`, `constitucion.instrumento` (documento privado / escritura pública) | texto, fecha, selección |
| **Constituyentes** (colección `constituyentes`) | `constituyente.nombre`, `.tipo_persona`, `.nacionalidad`, `.tipo_documento`, `.numero_documento`, `.domicilio`, `.calidad_actuacion`, `.representacion_soporte` | texto/selección |
| **Capital** | `capital.autorizado`, `.autorizado_letras`, `.acciones_autorizadas`, `.valor_nominal`, `.suscrito`, `.acciones_suscritas`, `.pagado`, `.saldo`, `.clases_iniciales`, `.aportes_especie_detalle` (si aplica el módulo) | dinero/número/texto |
| **Clases** (colección `clases`) | `clase.codigo`, `.denominacion`, `.naturaleza`, `.votos_por_accion` | texto/número |
| **Escenarios de dividendos** (colecciones anidadas) | `escenario.codigo`, `.clases_concurrentes`, `asignacion.clase`, `.porcentaje` | texto/número |
| **Conversión** (si aplica el módulo) | *(todos los campos de `conversion.*` se trasladaron a la sección 2 por ser de contenido jurídico; no hay campos simples adicionales)* | — |
| **Decisiones reservadas** (colección) | `decision.materia`, `.clases` | texto |
| **Causales de exclusión** (colección, diferido v2) | `causal.codigo` (trasladado a sección 2 junto con `.descripcion`/`.acreditacion`) | — |
| **Emisión** | `emision.dias_comunicacion` | número |
| **Asamblea** | `asamblea.quorum_porcentaje`, `.mayoria_porcentaje`, `.dias_convocatoria`, `.dias_inspeccion`, `.porcentaje_solicitud_convocatoria`, `.medios_convocatoria` (menú), `.medios_inspeccion_adicionales` (menú), `.plazo_reunion_ordinaria` (menú) | número/selección |
| **Preferencia de suscripción** | *(campos jurídicos, sección 2)* | — |
| **Preferencia de transferencia** | `preferencia_transferencia.dias_aceptacion`, `.dias_acrecimiento`, `.dias_traslado`, `.dias_venta_tercero` | número |
| **Junta / consejo de familia** | `junta.numero_principales` | número |
| **Nombramientos** (colección `nombramientos`) | `nombramiento.cargo`, `.nombre`, `.tipo_documento`, `.numero_documento`, `.domicilio`, `.tarjeta_profesional`, `.aceptacion_soporte`, y `nombramientos_situacion_inicial` (texto corto, p. ej. "sin suplentes") | texto |
| **Suscripción / capital transitorio** (colección `suscripciones`) | `suscripcion.accionista_nombre`, `.accionista_documento`, `.clase`, `.numero_acciones`, `.capital_suscrito`, `.capital_pagado`, `.saldo`, `.porcentaje_capital` (calculado), `.aporte_detalle`, `.prima_detalle`, `.calendario_pago` | texto/número/dinero |
| **Revisoría** | *(campos jurídicos, sección 2, salvo la selección de si hay o no revisor — booleano en sección 1)* | — |
| **Controversias** | *(mayoritariamente jurídicos; ver sección 2)* | — |
| **Poder** | `poder.apoderado_nombre`, `.apoderado_documento` | texto |
| **Firmantes** (colección `firmantes`) | `firmante.nombre`, `.tipo_documento`, `.numero_documento`, `.calidad`, `.representado` | texto |

**Nota sobre CIIU:** el diccionario de 213 campos **no incluye** ningún campo `ciiu.*`. Dado que la decisión del proyecto fija el CIIU principal en 7010 (actividades de administración empresarial, según src/data/listado_ciiu.json) con un secundario opcional, es necesario **agregar** dos campos nuevos al diccionario para el módulo de familia: `sociedad.ciiu_principal` (fijo = "7010", no editable) y `sociedad.ciiu_secundario` (texto/selección, opcional). Esto es un hallazgo de este análisis, no un campo preexistente.

---

## 4. Preguntas para el usuario (elementos [DUDA])

Máximo 15, ordenadas por importancia. Formato de opción múltiple, con la recomendada en primer lugar.

1. **Definición de "grupo familiar" (`familia.definicion_grupo`)**, que condiciona clases, titularidad y protocolo:
   a) *(recomendada)* Fundadores + cónyuge o compañero permanente + descendientes y ascendientes en primer grado de los fundadores.
   b) Solo fundadores y su descendencia directa (sin cónyuges ni ascendientes).
   c) Fundadores y todos sus parientes hasta el segundo grado de consanguinidad o afinidad.
   d) Definición personalizada (el usuario la redacta y el abogado la revisa).

2. **¿La sociedad tendrá junta directiva (`opciones.junta_directiva`)?**
   a) *(recomendada)* No, solo asamblea y representante legal (estructura simple, art. 24 base).
   b) Sí, con 3 miembros principales y suplentes personales.
   c) Sí, con 3 miembros principales sin suplentes.
   d) Sí, con otro número de miembros (especificar).

3. **¿Habrá consejo de familia consultivo (`opciones.consejo_familia`)?**
   a) *(recomendada)* No en esta primera versión (se puede incorporar luego mediante protocolo de familia).
   b) Sí, consultivo, integrado por los accionistas mayores de edad del grupo familiar.
   c) Sí, con funciones de administración real (requiere diseño adicional de responsabilidades, Guía §3).

4. **Orden de preferencia en la suscripción de nuevas acciones (`preferencia_suscripcion.orden`)**:
   a) *(recomendada)* Turno único, proporcional entre todos los accionistas.
   b) Escalonado por clase (primero fundadores, luego las demás clases), como en la plantilla original.

5. **Orden de preferencia en la transferencia de acciones (`preferencia_transferencia.orden`)**:
   a) *(recomendada)* 1) la sociedad; 2) los demás accionistas a prorrata.
   b) Escalonado por clase (primero fundadores, luego las demás clases).

6. **Excepciones al derecho de preferencia en transferencia (`preferencia_transferencia.excepciones`)** — riesgo de ingreso indirecto de terceros ajenos a la familia (Guía §5):
   a) *(recomendada)* Mantener las 4 excepciones legales estándar (escisión/fusión con mismo beneficiario real; matriz-filial-subsidiaria con mismo beneficiario real; adjudicación en liquidación de un accionista persona jurídica a sus propios socios; sociedad con accionista único).
   b) Eliminar todas las excepciones (toda transferencia, sin importar la vía, pasa por el derecho de preferencia).
   c) Mantenerlas pero condicionarlas a que el beneficiario final siga perteneciendo al grupo familiar definido.

7. **Umbral de mayoría para autorizar transferencias, gravámenes y usufructo (`mayorias.autorizacion_transferencias`, `mayorias.gravamenes`, `mayorias.usufructo`)**:
   a) *(recomendada)* Mitad más una de los votos (régimen general).
   b) Setenta por ciento (70 %) de los votos (mayoría calificada, como en el original y la plantilla comercial).
   c) Cien por ciento (100 %) — unanimidad.

8. **¿Se pacta un régimen de dividendos preferenciales o fijos para alguna clase (`opciones.dividendos_preferenciales_o_fijos`)?**
   a) *(recomendada)* No; reparto exclusivamente por el régimen de escenarios del artículo 6.
   b) Sí (requiere definir base/monto, prioridad, acumulación y tratamiento de insuficiencia de utilidades — módulo adicional).

9. **Destino de las sumas de dividendos renunciados individualmente (`dividendos.destino_renuncias`)**:
   a) *(recomendada)* Se reparten entre los demás accionistas de la misma clase, a prorrata.
   b) Se llevan a una reserva ocasional de la sociedad.

10. **¿Se pactan causales estatutarias adicionales de disolución (`liquidacion.causales_adicionales`)?**
    a) *(recomendada)* No, solo las causales legales.
    b) Sí — especificar (p. ej., "salida de todos los fundadores del grupo accionario").

11. **Límite de cuantía y operaciones que requieren autorización previa de la asamblea para el representante legal (`representacion.operaciones_reservadas`, `.limite_cuantia`)**:
    a) *(recomendada)* Adquirir, enajenar o gravar activos por más del 20 % del patrimonio líquido en un mismo ejercicio, y otorgar garantías a favor de terceros; las operaciones relacionadas se acumulan para el límite.
    b) Sin límite de cuantía; solo requieren autorización las operaciones taxativamente enumeradas (fusión, enajenación global, endeudamiento por encima de determinado monto).
    c) Otro porcentaje (especificar).

12. **Política de préstamos y garantías a favor de accionistas o administradores (`representacion.politica_prestamos_garantias`)**:
    a) *(recomendada)* Prohibición total (protección reforzada del patrimonio familiar).
    b) Permitidos previa autorización de la asamblea con mitad más una de los votos.

13. **Sistema de elección y período de la junta directiva, si se activa (`junta.sistema_eleccion`, `.periodo`)** — solo aplica si la pregunta 2 fue afirmativa:
    a) *(recomendada)* Mayoría simple de la asamblea, período de 1 año reelegible.
    b) Cociente electoral (permite representación de minorías), período de 2 años.

14. **Requisitos especiales de titularidad por clase (`clase.requisitos_titularidad`)** — p. ej., ¿alguna clase solo puede pertenecer a integrantes del grupo familiar?:
    a) *(recomendada)* No se exigen requisitos especiales de titularidad.
    b) Sí, cierta(s) clase(s) solo pueden ser tituladas por integrantes del grupo familiar definido (requiere coordinación con conversión y sucesión).

15. **Confirmación de que Opción de compra (art. 66) y Exclusión (art. 67) quedan en su alternativa negativa para esta versión** (ya decidido, se confirma para dejar constancia formal):
    a) *(recomendada)* Confirmar: ambas cláusulas quedan en "no se pacta" hasta revisión legal específica.
    b) Revisar ahora la posibilidad de activar alguna de las dos (implica trabajo adicional de redacción y validación jurídica antes de habilitarlas en producción).

---

## 5. Objeto social — "precautelación del patrimonio familiar" (texto exacto)

Texto localizado en `01_Plantilla_base_sin_ajustes.docx`, artículo 3 (única fuente que trae el objeto desarrollado; la plantilla 02 lo reemplazó por el placeholder `{{sociedad.objeto_principal}}` y la plantilla comercial no contiene este objeto específico). El párrafo del documento fuente presenta una duplicación evidente de la frase inicial (defecto de edición del documento original, no del análisis); se transcribe primero tal como aparece literalmente y luego la versión depurada que se propone usar como texto principal.

**Tal como aparece en 01 (con la duplicación del documento original):**

> "La sociedad tendrá como objeto social principal La sociedad tendrá como objeto social principal la tenencia, precautelación e inversión de activos como bienes muebles e inmuebles, acciones, bonos y cualquier otro título representativo de derechos; en mercados públicos o privados nacionales o internacionales."

**Texto principal propuesto para `sociedad.objeto_principal` (depurando la duplicación, sin alterar el contenido sustantivo):**

> "La sociedad tendrá como objeto social principal la tenencia, precautelación e inversión de activos como bienes muebles e inmuebles, acciones, bonos y cualquier otro título representativo de derechos; en mercados públicos o privados nacionales o internacionales."

Confianza: **[AJUSTADO]** solo en el aspecto tipográfico (se retira la frase duplicada); el contenido sustantivo es verbatim de 01 y no está señalado por la Guía como objetable. Debe combinarse con `sociedad.operaciones_conexas` (sección 2, [OK]) y, si el usuario activa `opciones.objeto_amplio`, con el párrafo adicional ya fijado en 02 art. 3 alt. A.

---

## Resumen de conteos

| Categoría | Cantidad |
|---|---|
| Campos totales en el diccionario | 213 |
| Interruptores de módulo (`opciones.*`, booleanos) | 23 |
| Campos de texto jurídico (banco principal/subsidiario) | 103 |
| — de los cuales [OK] | 34 |
| — de los cuales [AJUSTADO] | 24 |
| — de los cuales [DUDA] | 45 (28 corresponden a opción de compra/exclusión, diferidas a v2) |
| Campos de datos simples (cuestionario) | 87 |
| Bloques `[[SI]]` mapeados con texto exacto A/B | 16 (19 contando los tres calculados como complemento puro) |
| Colecciones `[[REPETIR]]` mapeadas | 9 |
| Preguntas para el usuario (sección 4) | 15 |
| Campos nuevos identificados como faltantes (CIIU) | 2 (`sociedad.ciiu_principal`, `sociedad.ciiu_secundario`) |
