# Handoff v3 — Sí S.A.S. / Anuwa (25-sep-2026)

Rama de trabajo: `feature/cedulas-disposiciones-modelo-propio`, integrada en `main`.
Plan y decisiones: `docs/PLAN_MEJORAS.md`. Catálogo de textos de familia:
`docs/FAMILIA_CATALOGO_TEXTOS.md`.

## Hecho (con pruebas)

| # | Qué | Dónde | Prueba |
|---|---|---|---|
| 1 | Soportes en el ZIP (`Soportes/`): cédulas, certificados, tarjetas; PDF "PENDIENTE…" si faltan; sin duplicar personas con varios roles; arrastrar y soltar | `processors/soportes.py`, `app.js` | `test_soportes.py`, `test_paquete.py`, `test_cuestionario.mjs` |
| 1b | Número de órganos en el articulado: capítulo de junta (principales y suplentes personales), suplentes del RL, revisor suplente; coherencia con junta (voto fraccionado art. 23 Ley 1258, "si se llegare a crear") | `processors/estatutos.py` | `test_organos.py` |
| 2 | Tarjeta profesional de abogado (IA) como llave de funciones avanzadas; vale para una constitución | `app.py` `/api/extract/tp-abogado` | `test_tp_abogado.py` |
| 3 | Disposiciones especiales con Claude Sonnet: vista previa tipo control de cambios, integración como parágrafo o inciso, validación final; ZIP con estatutos limpios + control de cambios nativo de Word + informe | `processors/disposiciones.py`, `/api/disposiciones/preview` | `test_disposiciones.py` |
| 4 | Modelo propio de estatutos (.docx): Sonnet ubica datos y anclas; tokenización sin tocar formato (solo backend) | `processors/modelo_propio.py`, `/api/modelo-propio/preview` | `test_modelo_propio.py` |
| 5 | Módulo familia (backend): motor de plantilla `[[SI]]`/`[[REPETIR]]`, contexto con textos aprobados, CIIU 7010 fijo, empresa familiar siempre; `modulo: "familia"` en `/api/generate` | `processors/plantilla_familia.py`, `processors/familia.py` | `test_plantilla_familia.py`, `test_familia.py`, `test_generar_familia.py` |
| 6 | Marca Anuwa: logo vectorial, paleta, tipografía Barlow (DIN Pro cuando haya licencia webfont) | `static/img/logo_anuwa*.svg`, `style.css`, plantillas | visual |
| 7 | Envío del paquete a Quarta por Make (adjunto o enlace si es grande) | `/api/enviar-asistencia` | `test_asistencia.py` |
| — | Casilla "Condición sociedad BIC" del RUES cuando la razón social contiene BIC (antes o después de S.A.S.) | `app.py`, `pdf_filler.py` | `test_bic.py` |

Correr todo: `python test_<x>.py` para cada archivo `test_*.py` y `node test_cuestionario.mjs`.

## Make

Escenario "Integration Webhooks" (id 6406292, cuenta nueva, org 9104504), activo:
Webhook personalizado → Gmail "Send an email" a acardona@quarta.co (asunto con la
razón social, cuerpo con usuario, teléfono, fecha y mensaje, adjunto `zip`). Probado
de extremo a extremo (ejecución exitosa). Pendiente cosmético: renombrarlo a
"Anuwa - Envío a Quarta asistencia radicación SAS" (el cambio de nombre no persistió).
Si el ZIP supera `MAKE_MAX_ADJUNTO_BYTES`, el correo lleva el enlace de descarga; en
ese caso el adjunto va vacío y Gmail podría fallar: agregar un router o filtro
(`zip` existe) si se vuelve frecuente.

## Variables de entorno (local `.env` y Railway)

```
MAKE_WEBHOOK_URL=https://hook.us2.make.com/qfou7i8zd8n4svhoxwb28ilc0noc9g3p
MAKE_MAX_ADJUNTO_BYTES=5242880        # opcional, por defecto 5 MB
ANTHROPIC_API_KEY=sk-ant-...          # válida; la del .env local es un placeholder
```

## Falta

1. **Identidad SÍ S.A.S.**: el agente de marca se cortó por límite de sesión. Su avance
   (WIP, antes del feedback) está en la rama `worktree-agent-a4efc8d26be8d9142`
   (basada en el `main` antiguo; no mezclar tal cual). Retomar con el feedback: "SÍ S.A.S."
   como un todo homogéneo (misma escala y peso), la Í con tilde y cola cursiva en la base
   (como la i manuscrita escolar), la S puede llevar la marca, mismos colores y negrilla
   de Anuwa. Luego refactor del frontend alrededor de la marca (skills: ui-ux-pro-max,
   ui-refactor, web-design-guidelines, frontend-design, taste-skill, redesign-skill).
2. **Cuestionario del módulo familia** (frontend): selector sociedad comercial / de
   familia; clases (1–3), matriz de escenarios editable que sume 100 %, parentesco por
   accionista, opciones (junta, consejo, protocolo, arbitraje, preferencia simple o
   escalonada, grupo familiar con definición personalizada), CIIU 7010 fijo +
   secundario. Enviar `modulo: "familia"`.
3. **Modelo propio (frontend)**: carga del .docx en el bloque de abogado, vista previa de
   reemplazos y "no ubicados", aprobación y envío de `modelo_propio`.
4. **Prueba real con Sonnet**: con `ANTHROPIC_API_KEY` válida, correr la simulación de
   disposiciones (junta, revisor, restricción de 15 años, quórum libre) y revisar el Word.
   En local hay inspección SSL: usar `truststore` (`pip install truststore`).
5. Logo Anuwa claro: la "A" debería ir en azul #3641E4 (hoy toda navy).
6. Hallazgos del texto base comercial (solo reportados, no corregidos): paréntesis sin
   cerrar en el art. 26 ("(cuando haya lugar a ello;") y el art. 52; "los acuerdo
   consten" en el art. 23; segunda convocatoria "incluyendo las mayorías especiales"
   (art. 36) frente a las unanimidades legales.
7. Vercel: no hay configuración ni CLI; la app es Flask y hoy despliega en Railway.
