# Plan de mejoras — Sí S.A.S. / Anuwa

Rama: `feature/cedulas-disposiciones-modelo-propio`. Todo es aditivo: el flujo
actual (sociedad comercial) sin las opciones nuevas genera exactamente lo mismo.

Orden aprobado: 1 → 1b → 2 → 3 → 6 → 5 → 4 → 7.

## 1. Soportes en el ZIP — HECHO (9e453e3)
Cédulas, certificados de existencia (accionista PJ) y tarjetas profesionales
(revisor/contador) van a `Soportes/`. Falta → PDF "PENDIENTE DE CARGAR ...".
Misma persona con varios roles → un solo soporte. Arrastrar y soltar en toda
zona de carga.

## 1b. Número de órganos reflejado en estatutos (todo usuario)
Número de miembros de junta (principales/suplentes), representantes legales
principales/suplentes y revisor principal/suplente se escriben en los
artículos respectivos. Suplentes siempre opcionales. Junta: "con sus
respectivos suplentes personales" si hay igual número; si hay menos, el
número exacto; si no hay, sin suplentes. Nuevo bloque opcional de revisor
fiscal suplente.

## 2. Llave: tarjeta profesional de abogado
Se carga en cada constitución. Validación automática con IA (visión): TP de
abogado del Consejo Superior de la Judicatura. Habilita fases 3 y 4. Se
verifica en servidor, no solo en la UI. No aparece en el paquete.

## 3. Disposiciones especiales con Sonnet (requiere TP)
Textos para junta (si hay junta), revisoría (si hay revisor) y adicionales
ilimitadas. Sonnet elige artículo destino, redacta como parágrafo o inciso,
valida contra estatutos y ley (Ley 1258, C.Co.), y si un párrafo base choca
lo ajusta/reemplaza/elimina. Preview estilo control de cambios antes de
generar. Inserción clonando el párrafo ancla: interlineado, sangría,
espaciado y estructura intactos. ZIP: estatutos limpios + copia con control
de cambios nativo de Word + informe.

## 6. Marca Anuwa
Logo: "Anuwa" con la A-vela (propuesta ajustada, slide 31 del deck
ANUWA X 301). "SÍ S.A.S." en la misma familia tipográfica. Paleta
#3641E4 / #004571 / #E3E3EF / #82389A. Tipografía de marca DIN Pro
(Medium destacados, Regular corrido); en web, Barlow mientras no haya
licencia webfont de DIN Pro. Landing, login, app y admin.

## 5. Módulo sociedad de familia
Clon del flujo comercial (que pasa a llamarse "sociedad comercial"). Plantilla
02_Plantilla_ajustada_alternativas.docx y diccionario de placeholders.
Formulario de empresa familiar siempre en "sí". CIIU principal fijo 7010;
secundario opcional. Objeto social siempre el de precautelación del
patrimonio familiar de la plantilla. Campos jurídicos extensos desde textos
de la plantilla (principal/subsidiario); dudas se definen con el usuario.
Primera versión: núcleo + módulos simples; opción de compra y exclusión en su
alternativa negativa hasta revisión jurídica.

Decisiones (25-sep-2026), catálogo en docs/FAMILIA_CATALOGO_TEXTOS.md:
- Grupo familiar: opción del cuestionario; por defecto fundadores + cónyuge o
  compañero permanente + descendientes y ascendientes en primer grado.
  Alternativas: fundadores y descendencia; hasta segundo grado; personalizada.
- Mayoría para transferencias, gravámenes y usufructo: 70 % de los votos.
- Excepciones al derecho de preferencia: se mantienen solo si el beneficiario
  final sigue perteneciendo al grupo familiar.
- Preferencia en suscripción y transferencia: por defecto sociedad y luego
  accionistas a prorrata; variante escalonada por clase a elección.
- Junta, consejo de familia, dividendos preferenciales, causales adicionales
  de disolución, límites del RL, préstamos/garantías y titularidad por clase:
  opciones del cuestionario con la alternativa recomendada por defecto.

## 4. Modelo propio de estatutos (requiere TP)
Solo .docx. Sonnet ubica dónde van los datos, inserta placeholders del
diccionario y el código los reemplaza sin tocar formato. Inserta
nombramientos junta/revisor, tabla de accionistas, firmas, limitaciones del
RL y disposiciones especiales. Preview + informe de lo no ubicado.

## 7. Envío del paquete para asistencia en radicación
Botón "Enviar a Quarta para asistencia": el ZIP va por correo a
acardona@quarta.co mediante webhook de Make o n8n (datos del usuario,
sociedad y el ZIP o enlace de descarga si excede el límite de adjuntos).
