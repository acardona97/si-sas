# Design & Engineering Handoff — Sí S.A.S. / Anuwa

Fecha: 25-sep-2026. Rama: `feature/cedulas-disposiciones-modelo-propio` (integrada en `main`,
`main` en GitHub = `6975729`). Handoff operativo anterior: `docs/HANDOFF_v3.md`. Plan y
decisiones: `docs/PLAN_MEJORAS.md`. Catálogo jurídico del módulo familia: `docs/FAMILIA_CATALOGO_TEXTOS.md`.

---

## 1. Qué es esto, en una frase

App Flask que genera el paquete completo de constitución de una S.A.S. colombiana
(estatutos + formularios RUES/DIAN/Cámara) a partir de un cuestionario web, con asistencia
de Claude para objeto social, extracción de documentos de identidad, redacción de
disposiciones especiales y ubicación de campos en modelos propios de estatutos.

---

## 2. Desarrollado de forma principal (con pruebas automatizadas)

| # | Funcionalidad | Backend | Frontend | Estado |
|---|---|---|---|---|
| 1 | **Soportes en el ZIP**: cédulas, certificados, tarjetas profesionales van a `Soportes/`; si falta alguno sale un PDF "PENDIENTE DE CARGAR…"; una persona con varios roles no se duplica; arrastrar y soltar en toda zona de carga | `processors/soportes.py` | `app.js` | ✅ completo |
| 1b | **Número de órganos reflejado en el articulado**: capítulo de junta directiva con el número real de principales y suplentes personales; artículo del RL dice cuántos suplentes tiene; revisor fiscal suplente opcional; coherencia interna corregida (voto fraccionable art. 23 Ley 1258, "si se llegare a crear" eliminado cuando ya hay junta) | `processors/estatutos.py` | `index.html`/`app.js` | ✅ completo |
| 2 | **Tarjeta profesional de abogado** como llave de funciones avanzadas: se valida con Claude Vision, vale para una sola constitución, se exige server-side | `app.py` `/api/extract/tp-abogado` | bloque en paso 6 | ✅ completo |
| 3 | **Disposiciones especiales redactadas con Claude Sonnet**: el abogado escribe reglas de junta/revisoría/adicionales; Sonnet propone inserciones (parágrafo/inciso) y ajustes de párrafos en conflicto; segunda pasada de validación jurídica sobre el documento íntegro; preview como control de cambios (aceptar/editar cada operación); el ZIP final trae estatutos limpios + copia con control de cambios **nativo de Word** + informe PDF | `processors/disposiciones.py`, `/api/disposiciones/preview` | bloque `#avanzado-block`, `.cambio-card` | ✅ completo, probado con simulación end-to-end (ver §6) |
| 4 | **Modelo propio de estatutos** (.docx del abogado): si trae los tokens `{{...}}` de la plantilla se usan directo; si no, Sonnet ubica en cada párrafo el fragmento correspondiente a cada dato y las anclas estructurales (nombramientos, firmas, tabla, limitaciones); tokenización sin alterar formato de párrafo/run | `processors/modelo_propio.py`, `/api/modelo-propio/preview` | **falta el frontend** (ver §4) | ⚠️ solo backend |
| 5 | **Módulo "sociedad de familia"**: plantilla jurídica distinta (`02_Plantilla_ajustada_alternativas`), motor propio de `[[SI]]`/`[[REPETIR]]`, textos jurídicos aprobados (no redactados por el usuario salvo la definición personalizada de grupo familiar), CIIU 7010 fijo + secundario opcional, objeto de precautelación patrimonial fijo, formato de empresa familiar siempre generado (exige parentesco por accionista PN), opción de compra y exclusión diferidas (alternativa negativa) | `processors/plantilla_familia.py`, `processors/familia.py`, `modulo:"familia"` en `/api/generate` | **en curso** (Codex, ver §7) | ⚠️ backend listo, frontend en curso |
| 6 | **Rebranding a Anuwa**: paleta (#3641E4/#004571/#E3E3EF/#82389A), tipografía Barlow (sustituto de DIN Pro, que es de pago), logo Anuwa vectorial (trazado con potracer desde el arte original) | `static/img/logo_anuwa*.svg`, `style.css`, todas las plantillas | — | ✅ completo, **pendiente ajuste**: la A del logo claro debería ir en azul #3641E4, hoy toda navy |
| 6b | **Identidad "SÍ S.A.S."**: en curso, ver §7 | — | — | 🔴 en curso, dirección definida por el cliente pero no implementada aún |
| 7 | **Envío del paquete a Quarta** para asistencia en radicación, vía webhook de Make (adjunto si es ≤5 MB, si no enlace de descarga con token no adivinable) | `/api/enviar-asistencia`, `/descargas/asistencia/<token>` | bloque tras generar | ✅ completo, **probado de extremo a extremo** (correo recibido, confirmado por el usuario) |
| — | **Casilla "Condición sociedad BIC"** en la hoja 1 del RUES, activada cuando la razón social contiene "BIC" (antes o después del indicativo societario) | `app.py`, `processors/pdf_filler.py` | ninguno (se detecta del campo existente) | ✅ completo |

**Cómo verificar todo:** cada `test_*.py` se corre con `python test_<nombre>.py`; el cuestionario
con `node test_cuestionario.mjs`. Todos pasan sobre `main` en este momento.

---

## 3. Infraestructura y despliegue

- **Repositorio:** `https://github.com/acardona97/si-sas`, rama `main` desplegada.
- **Hosting:** Railway (autodeploy desde `main`, `Procfile` + `runtime.txt`). El usuario
  confirmó que ya actualizó `ANTHROPIC_API_KEY` (la real, la del entorno de Railway) y
  `MAKE_WEBHOOK_URL` en las variables de Railway.
- **Automatización de correo:** Make.com, escenario "Integration Webhooks" (id `6406292`,
  cuenta nueva `us2.make.com`, org `9104504`). Webhook personalizado → Gmail "Send an email"
  a `acardona@quarta.co`. Activo y probado (ejecución exitosa registrada en el historial).
  Pendiente cosmético: el intento de renombrarlo a "Anuwa - Envío a Quarta asistencia
  radicación SAS" no persistió (Make revirtió el nombre); no afecta el funcionamiento.
- **Variables de entorno necesarias** (local `.env` y Railway):
  ```
  ANTHROPIC_API_KEY=sk-ant-...       # ya actualizada por el usuario en Railway
  MAKE_WEBHOOK_URL=https://hook.us2.make.com/qfou7i8zd8n4svhoxwb28ilc0noc9g3p
  MAKE_MAX_ADJUNTO_BYTES=5242880     # opcional, default 5 MB
  ```
- **No hay CLI de Vercel/Railway/gh instalado** en esta máquina; el deploy se dispara
  únicamente por push a `main` en GitHub. Ya se hizo push; verificar en el panel de Railway
  que el build más reciente corresponda a `6975729` o posterior.

---

## 4. Pendiente — por orden de prioridad

### 4.1 Identidad visual "SÍ S.A.S." (🔴 bloqueante para la percepción de marca)
Dirección final del cliente (después de dos iteraciones de feedback):
1. "SÍ S.A.S." es **un todo indivisible**: misma escala y mismo peso (negrilla) para ambas
   partes. Nada de wordmark grande + descriptor pequeño.
2. La **Í** lleva su tilde y además una **cola cursiva en la base** (el asta baja y remata
   en una curva suave hacia la derecha, como la i cursiva escolar) — controlada, como path
   geométrico, no como fuente script.
3. El **barquito de Quarta** (símbolo azul que en el logo de Quarta va junto a la "q") se
   coloca a la izquierda de la S de SÍ, con "el azul de la foto" (los azules exactos del
   barquito: ala navy #004571, casco con degradado azul). Fuente vectorial de referencia:
   `C:\Users\User\Downloads\Logo Quarta2Curvas.pdf` y los `clipPath` `clip_2`/`clip_3` de
   `src/static/img/logo_quarta.svg`.
4. Se mantienen los colores y la negrilla de la marca actual (Anuwa).
5. **El usuario pidió explícitamente que el logo lo diseñe Codex**, no un agente Sonnet.
   Esto está delegado y en curso — ver §7 para el estado exacto y cómo retomarlo si la
   sesión se corta.
Un primer intento (agente Sonnet, antes del feedback definitivo) quedó como referencia
histórica en la rama `wip/identidad-si-sas` (commit `a56c3d2`) — **no usar tal cual**, no
incorpora el barquito ni la dirección de "todo indivisible".

### 4.2 Cuestionario del módulo familia (frontend)
El backend (`processors/familia.py`, `processors/plantilla_familia.py`) está completo y
probado; falta la pantalla. Está delegado a Codex en curso (§7). Debe cubrir: selector de
módulo (comercial ↔ familia), clases de 1 a 3, matriz de escenarios de dividendos editable
que valide 100 % por escenario, parentesco obligatorio por accionista persona natural,
opciones (junta, consejo de familia, protocolo, arbitraje, preferencia simple/escalonada,
definición de grupo familiar con opción personalizada revisada por el abogado), CIIU 7010
fijo + secundario opcional, envío de `modulo: "familia"` en el payload.

### 4.3 Frontend del modelo propio de estatutos
Falta el bloque de carga del `.docx`, la vista previa de los reemplazos propuestos por
Sonnet y de los datos "no ubicados", la aprobación/edición por el abogado, y el envío de
`modelo_propio` en el payload de `/api/generate`. Contrato exacto en
`processors/modelo_propio.py` y `test_modelo_propio.py`.

### 4.4 Prueba real de Sonnet en producción
Toda la validación de disposiciones especiales se probó con **respuestas simuladas** del
modelo (mismo esquema JSON, criterio jurídico verificado a mano) porque la clave de API
local era un placeholder. Ahora que Railway tiene la clave real, correr al menos un caso
real de constitución con disposiciones (junta + revisor + una restricción que la Ley limite,
p. ej. pedir 15 años de restricción de transferencia para verificar que Sonnet la ajusta a
los 10 años que permite la Ley 1258) y revisar el Word resultante.
Nota técnica: en el entorno local hay inspección SSL corporativa que rompe las llamadas a
Anthropic; se resuelve con `pip install truststore` y `truststore.inject_into_ssl()` antes
de crear el cliente — no debería afectar a Railway, pero si se prueba en local, tenerlo en
cuenta.

### 4.5 Ajustes menores identificados y no corregidos (opcional)
Hallazgos en la plantilla comercial base, reportados por la revisión de Sonnet durante la
simulación de disposiciones especiales, no corregidos por no estar en el alcance pedido:
- Art. 26: paréntesis sin cerrar ("…con sus notas y el dictamen del revisor fiscal (cuando
  haya lugar a ello;").
- Art. 52: paréntesis de cierre sin apertura ("…cuando la sociedad cuente con revisoría
  fiscal)").
- Art. 23: "siempre que los acuerdo consten por escrito" (concordancia).
- Art. 36 (segunda convocatoria): permite decidir "incluyendo las mayorías especiales" con
  cualquier número de acciones, lo que puede desconocer las unanimidades legales de los
  arts. 31 y 41 de la Ley 1258 de 2008.

### 4.6 Deuda técnica / operativa
- Persistencia de `users.db` en Railway: agregar un Volume (viene arrastrado del handoff
  anterior, no es de esta sesión pero sigue pendiente).
- Migrar SQLite → PostgreSQL si el volumen de usuarios crece (idem).
- El escenario de Make no tiene manejo de error explícito si Gmail falla (p.ej. cuota
  excedida): hoy Make reintenta según su política por defecto; considerar una notificación
  de fallo si se vuelve crítico.

---

## 5. Fases que siguen (orden recomendado)

1. **Cerrar identidad "SÍ S.A.S."** (Codex, en curso) — es lo más visible para el usuario
   final y bloquea cualquier captura de pantalla de marketing.
2. **Cerrar cuestionario del módulo familia** (Codex, en curso) — completa la fase 5 que
   lleva más tiempo de trabajo jurídico invertido (catálogo de 213 campos).
3. **Frontend del modelo propio** (fase 4) — menor volumen de trabajo, ya con contrato de
   backend fijo y probado.
4. **Prueba real end-to-end con Sonnet** en producción (una constitución completa con
   disposiciones especiales, revisando el Word que sale).
5. **Pulido de marca**: aplicar el logo definitivo de SÍ en landing/auth/admin (no solo en
   el cuestionario), y corregir el color de la A de Anuwa en el logo claro.
6. **Deuda técnica de Railway** (Volume, Postgres) cuando el volumen de uso lo justifique.

---

## 6. Cómo se verificó lo que dice "completo"

- **Suite automatizada**: `test_soportes.py`, `test_organos.py`, `test_tp_abogado.py`,
  `test_disposiciones.py`, `test_modelo_propio.py`, `test_plantilla_familia.py`,
  `test_familia.py`, `test_generar_familia.py`, `test_bic.py`, `test_asistencia.py`,
  `test_paquete.py`, `node test_cuestionario.mjs` — todos verdes sobre `main`.
- **Simulación real de disposiciones especiales**: se generó un paquete completo (escenario
  con junta directiva, revisor fiscal PJ, controlante, empresa familiar) con 4 disposiciones
  pedidas (2 de ellas conscientemente inválidas: restricción de transferencia a 15 años y
  quórum libre en primera convocatoria), usando el pipeline real de inserción/control de
  cambios pero con respuestas de Sonnet escritas a mano con el mismo esquema JSON (por la
  clave de API local placeholder). Se verificó visualmente en Word: el control de cambios
  nativo mostró exactamente lo insertado/reemplazado, palabra por palabra, sin tocar
  formato ajeno; los ajustes por Ley (10 años en vez de 15) quedaron en el informe.
- **Correo de Quarta**: prueba de extremo a extremo con un ZIP de prueba real vía el
  webhook de Make; el usuario confirmó la recepción del correo.

---

## 7. Estado de los agentes en curso al cierre de esta sesión

Dos tareas de Codex (`gpt-6-astra`) seguían corriendo en background al momento de escribir
este handoff y **no se pudieron confirmar terminadas** antes del cierre de la sesión:

1. **Logo de SÍ S.A.S. + barquito** — worktree `.claude/worktrees/logo`, rama `logo-si-codex`
   (creada desde `main` limpio). Prompt completo en el historial de esta sesión; instrucción
   clave: extraer la geometría exacta del barquito de Quarta (PDF vectorial +
   `logo_quarta.svg`), construir los caracteres como paths SVG (no depender de webfont en
   el SVG), entregar el sistema completo en `src/static/img/si/` + macro Jinja
   `_marca.html` + `docs/MARCA_SI.md`.
2. **Cuestionario frontend del módulo familia** — worktree `.claude/worktrees/fase5c`, rama
   `fase5-familia-frontend` (creada desde `main` limpio, con `_test_cuestionario` copiado y
   junction a `node_modules`). Debe generar `src/templates/familia.html` +
   `src/static/js/familia.js` + ruta `/app/familia`, sin tocar los archivos de la sociedad
   comercial salvo un enlace de cambio de módulo.

**Si esta sesión se cierra antes de que terminen:** revisar el estado de esos dos
worktrees (`git -C .claude/worktrees/logo log` y `git -C .claude/worktrees/fase5c log`,
y `git status` en cada uno). Si Codex dejó cambios sin commitear (ha pasado antes: su
sandbox a veces no puede ejecutar `git commit` ni Python), commitear manualmente el
contenido válido después de correr las pruebas correspondientes
(`node test_cuestionario.mjs`, y si aplica `test_familia_frontend.mjs`), y luego
`git merge --no-ff` esa rama sobre `main` (o sobre la rama de trabajo si sigue abierta).
Los prompts completos que se les dio quedan en los archivos de scratch de la sesión
(`codex_logo.md`, `codex_fase5c.md`) por si hay que relanzar la tarea con instrucciones
idénticas.

---

## 8. Qué mejorar (recomendaciones, no bloqueantes)

- **Automatizar la corrida de tests** en un flujo de CI (GitHub Actions) para que cada push
  a `main` corra `test_*.py` y `test_cuestionario.mjs` antes de que Railway despliegue.
- **Mover el escenario de Make a la cuenta/organización principal** si la cuenta nueva usada
  en esta sesión (org `9104504`) era solo temporal para pruebas; si es la definitiva, no se
  requiere ninguna acción.
- **Revisar el límite de generaciones por usuario** (`check_puede_generar`) frente al nuevo
  costo de las llamadas a Sonnet en disposiciones especiales y modelo propio — esas rutas no
  descuentan generación por sí mismas hoy (solo el `/api/generate` final la descuenta), lo
  cual es correcto pero vale la pena confirmarlo con el modelo de negocio.
- **Considerar cachear el listado CIIU y el diccionario de placeholders de familia en
  memoria de proceso** (ya se cargan desde JSON en cada request en algunos puntos); no es
  crítico al volumen actual pero es una mejora barata de latencia.
