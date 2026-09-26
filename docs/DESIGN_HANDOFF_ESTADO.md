# Design & Engineering Handoff — Sí S.A.S. / Anuwa

Fecha: 26-sep-2026. Rama: `claude/awesome-turing-lkk35m`. Handoff operativo anterior:
`docs/HANDOFF_v3.md`. Plan y decisiones: `docs/PLAN_MEJORAS.md`. Catálogo jurídico del
módulo familia: `docs/FAMILIA_CATALOGO_TEXTOS.md`.

## 0. Última sesión: rediseño tipográfico del wordmark "SÍ S.A.S."

El cliente pidió corregir la tilde descuadrada de la Í y cambiar el estilo de letra a "una
especie de cursiva" en tipografía "antigua griega o romana", más diferencial de marca.

**Causa raíz de la tilde descuadrada:** el logo anterior (commit `2b4c2f5`) dibujaba la Í
como dos trazos geométricos independientes (asta + tilde) hechos a mano; la tilde no estaba
anclada al glifo real, por eso quedaba desalineada.

**Solución aplicada:** se reemplazó el wordmark completo por contornos vectoriales reales
extraídos de la fuente **Playfair Display Black Italic** (SIL OFL, Google Fonts) — se probaron
tres direcciones (Playfair Display Italic, Cormorant Italic, Cinzel con inclinación forzada) y
el cliente eligió Playfair Display por ser itálica genuina (no una inclinación simulada) y
sostenerse mejor en tamaños chicos. Al usar el glifo `Í` real de la fuente, la tilde queda
perfectamente anclada al asta sin ningún ajuste manual. El contorno de la tilde se separó en
un `<path class="si-acento">` propio (igual que antes) para conservar la animación de
"asentado" en `marca-si.css`.

Proceso técnico: se descargó el `.woff2` de Google Fonts, se extrajeron los contornos de los
glifos `S`, `Iacute`, `period`, `A` con `fontTools` (Python), se reescalaron para que la
altura de mayúscula coincida con la altura del barquito de Quarta (que no cambió), y se
compusieron en un único `<path>` por color (más el `<path class="si-acento">` de la tilde).

Archivos actualizados: `src/static/img/si/si-logo-full.svg`, `si-logo-full-white.svg`,
`si-logo-mono.svg`, `si-mark.svg` y la macro `src/templates/_marca.html` (que es lo que
realmente pintan `landing.html`, `auth.html`, `index.html` y `admin.html`).

**Favicon (`si-favicon.svg`) — cambio de criterio, no solo de fuente:** el favicon anterior
era solo la "Í" (sin la S). Se probó primero extraer igual la Í de Playfair Display, pero a
16-32px el asta se volvía casi invisible (los serifs finos de una itálica de texto no
sobreviven a esos tamaños, a diferencia del trazo geométrico grueso hecho a mano que había
antes). Se decidió usar el **barquito solo** (sin letra) como favicon: es la pieza más
geométrica y de trazo grueso de la identidad, se probó a 16/24/32/48/64px y se lee con
claridad en todos. El wordmark completo con letras sigue siendo Playfair Display en todos los
demás usos (header, sidebar, footer, auth).

Verificado en navegador real (Chromium headless) renderizando las plantillas Jinja reales
(`_marca.html` importado igual que en `landing.html`/`auth.html`/`index.html`) con
`style.css`/`marca-si.css` reales, en claro, oscuro, junto al logo de Anuwa y a distintos
tamaños. No se tocó ningún otro archivo del proyecto.

**Pendiente de esta sesión:** ninguno — cambio autocontenido en los 6 archivos de marca. El
resto de fases pendientes (§4 más abajo) sigue igual.

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
| 6b | **Identidad "SÍ S.A.S."**: barquito de Quarta junto a la S, "SÍ S.A.S." como unidad homogénea, Í con tilde y asta diagonal (sin cola, por ajuste final del cliente) | `static/img/si/*.svg`, `_marca.html` | 4 plantillas | ✅ completo (commit `2b4c2f5`) |
| 5b | **Cuestionario del módulo familia** (frontend): ruta `/app/familia`, clases 1-3, matriz de escenarios validada, parentesco obligatorio, opciones/elecciones del módulo, CIIU y objeto fijos | — | `familia.html`/`familia.js` | ✅ completo (commit `62b9b4f`) |
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

### 4.1 Identidad visual "SÍ S.A.S." — ✅ CERRADO (commit `2b4c2f5`)
Implementado por Codex (`gpt-6-astra`) y ajustado a mano tras revisión visual del cliente.
Queda así, no pendiente:
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
5. **El logo lo diseñó Codex** (`gpt-6-astra`), por pedido explícito del cliente. Ajuste
   final (quitar la cola de la base de la Í, dejarla con asta diagonal/cursiva en vez de
   la curva) lo hizo Claude directamente sobre el SVG, con aprobación previa del cliente
   sobre el resto del sistema.
Resultado final en `src/static/img/si/` (wordmark completo, versión blanca, monocromo,
marca/favicon) + macro Jinja `src/templates/_marca.html`, ya integrado en las 4 plantillas.
Un primer intento (agente Sonnet, antes del feedback definitivo del cliente) quedó como
referencia histórica descartada en la rama `wip/identidad-si-sas` (commit `a56c3d2`) — no
se usó.

### 4.2 Cuestionario del módulo familia (frontend) — ✅ CERRADO (commit `62b9b4f`)
Implementado por Codex (`gpt-6-astra`). Ruta `/app/familia`, plantilla y script propios
(`familia.html`/`familia.js`), reutilizando el contrato de soportes y extracción del
cuestionario comercial. Cubre clases 1-3, matriz de escenarios validada al 100 %,
parentesco obligatorio por accionista persona natural, opciones y elecciones del módulo,
CIIU 7010 y objeto social fijos de solo lectura. El cuestionario comercial solo ganó un
enlace de cambio de módulo en la cabecera; su comportamiento no cambió (test_cuestionario.mjs
y test_paquete.py siguen en verde).

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

1. **Frontend del modelo propio** (fase 4) — único frontend que falta; contrato de backend
   ya fijo y probado (`processors/modelo_propio.py`, `test_modelo_propio.py`).
2. **Prueba real end-to-end con Sonnet** en producción (una constitución completa con
   disposiciones especiales, revisando el Word que sale), ahora que Railway tiene la clave
   de API real.
3. **Pulido de marca**: revisar el logo de SÍ S.A.S. en landing/auth/admin con datos reales
   (no solo el tablero `preview.html`), y corregir el color de la A de Anuwa en el logo claro.
4. **Deuda técnica de Railway** (Volume, Postgres) cuando el volumen de uso lo justifique.

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

## 7. Cierre de sesión: ambas tareas de Codex terminadas, revisadas e integradas

Las dos tareas delegadas a Codex (`gpt-6-astra`) terminaron (ambas agotaron su cuota de
Codex justo al final, con el trabajo ya escrito en disco) y quedaron **revisadas,
probadas, commiteadas, mergeadas a `main` y desplegadas**:

1. **Logo de SÍ S.A.S. + barquito** — rama `logo-si-codex` (commit `2b4c2f5`). Se revisó
   visualmente en navegador real (los gradientes del barquito no se veían bien con el
   rasterizador usado para una primera inspección; en Chromium se confirmó correcto). El
   cliente pidió un ajuste: quitar la cola curva de la base de la Í y dejarla con un asta
   diagonal/cursiva — cambio hecho a mano directamente sobre los 5 SVG y la macro Jinja
   (reemplazo del path del asta, sin tocar el resto del sistema).
2. **Cuestionario frontend del módulo familia** — rama `fase5-familia-frontend` (commit
   `62b9b4f`). Se limpiaron scripts de construcción que Codex dejó sueltos en la raíz
   (`crear_familia.cjs`, `familia_extra.js`, `.npm-cache/`) antes de commitear: su
   contenido ya estaba incorporado en `familia.js`/`familia.html`.

Ambas ramas se mergearon a `main` sin conflictos relevantes (`index.html` tuvo auto-merge
limpio). Se corrió la suite completa sobre `main` ya fusionado — todos los `test_*.py` y
ambos `test_*.mjs` en verde — y se hizo push a GitHub, disparando el deploy en Railway.

**Incidente detectado y corregido durante la integración:** uno de los agentes de Codex
ejecutó `npm install` dentro de su worktree, y como `node_modules` de los worktrees es una
junction al `node_modules` real del repo, el install sobrescribió/vació el `node_modules`
compartido (quedó con 0 paquetes, rompiendo `node test_cuestionario.mjs` en todos los
worktrees, incluido el checkout principal). Se corrigió con `npm install` +
`npm install jsdom --no-save` en el repo principal. **Recomendación:** si se vuelve a
delegar trabajo de frontend a un agente en un worktree con `node_modules` en junction,
pedirle explícitamente que NO ejecute `npm install`/`npm ci` ahí, o darle un `node_modules`
real (copiado, no enlazado) para su worktree.

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
