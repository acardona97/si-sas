# Handoff — Responsabilidades tributarias y calidad ante la DIAN

**Ruta en la app:** `/app` → Paso 5 «Capital y Régimen Tributario», bloque `#resp-block`
**Estado:** implementado y en `main` (`a78b0d0`)
**Stack:** Flask + Jinja2, JavaScript sin framework ni build, CSS con custom properties

| Capa | Archivo |
|---|---|
| Matriz normativa | [src/data/responsabilidades_tributarias.json](src/data/responsabilidades_tributarias.json) |
| Reglas | [src/processors/responsabilidades.py](src/processors/responsabilidades.py) |
| Endpoints y validación | [src/app.py](src/app.py) |
| Casillas del RUES | [src/processors/pdf_filler.py](src/processors/pdf_filler.py) |
| Interfaz | [src/static/js/app.js:630](src/static/js/app.js#L630) · [src/static/css/style.css:2688](src/static/css/style.css#L2688) |
| Contenedores | [src/templates/index.html:697](src/templates/index.html#L697) |
| Vista previa visual | [preview_resp.mjs](preview_resp.mjs) → `node preview_resp.mjs` |

---

## 1. Qué hace y por qué

La casilla 53 del RUT admite hasta 10 responsabilidades. El usuario no es
tributarista: no sabe cuáles le corresponden, y una equivocación se radica ante
la DIAN. El paso resuelve eso en tres franjas de responsabilidad decreciente:

1. **Van siempre con este régimen** — se muestran, no se tocan. Derivan del
   régimen elegido (ordinario o simple) y de la actividad.
2. **Sugeridas por la actividad que declaró** — el CIIU y el objeto social las
   hacen probables. Se destacan y van primero.
3. **Otras que puede agregar** — el resto del catálogo permitido.

Debajo, plegado, **por qué no aparecen otras**: 25 códigos con el motivo de
exclusión, para que el usuario no busque una casilla que nunca va a encontrar.

Cuando marca una responsabilidad de comercio exterior (10, 19, 21) aparece una
pregunta obligatoria: **importador / exportador / usuario aduanero**. De la
respuesta dependen las casillas 1_30, 1_31 y 1_32 del formulario RUES, que no
se pueden deducir de la responsabilidad sola.

---

## 2. Layout

El bloque vive dentro de `.form-container` (columna única, `max-width` heredado
del contenedor del cuestionario). No introduce grid propio: cada franja apila
elementos a ancho completo.

```
#resp-block                       .form-group
├── label                         "Responsabilidades tributarias"
├── p.hint                        explicación de las tres franjas
├── #resp-predeterminadas         .resp-fijas → .resp-chip (flujo en línea, envuelven)
├── #resp-adicionales             .resp-extra-titulo + .resp-opcion[] (apiladas)
├── #resp-comercio-exterior       .ce-bloque (oculto por defecto)
└── details#resp-vetadas-wrap     summary + .resp-vetada[]
```

Los tres primeros contenedores se pintan por completo desde
`cargarResponsabilidades()`; el markup no existe en la plantilla.

---

## 3. Tokens

Todos ya existen en `:root`. No se introdujo ninguno nuevo.

| Token | Valor | Uso en este bloque |
|---|---|---|
| `--gold` | `#B8920A` | Riel de las fijas, borde en hover y en marcadas |
| `--gold-light` | `#FBF6E6` | Fondo de las fijas y de la opción marcada |
| `--gold-border` | `#E8D48A` | Borde de las fichas y de las sugeridas |
| `--gold-hover` | `#9A7A08` | Número de código, notas de dependencia |
| `--navy` | `#0C1E35` | Títulos de panel, opción de calidad elegida |
| `--danger` | `#C0392B` | Riel y borde del bloque de comercio exterior, cupo lleno |
| `--border` | `#E4E0D8` | Borde de las casillas |
| `--border-light` | `#F0EDE8` | Separador entre vetadas |
| `--text` / `--text-secondary` / `--text-muted` | `#1A1612` / `#5A5550` / `#9A9490` | Título / descripción / vetadas y cupo |
| `--radius` | `6px` | Casillas y bloque de comercio exterior |
| `--font-display` | Playfair Display, serif | Solo el título del bloque de comercio exterior (`1.02rem/600`), igual que `.rues-opcion-titulo` y `.ciiu-panel-titulo` |
| `--font-body` | Inter | Todo lo demás |

Escala tipográfica usada, de mayor a menor: `1.02rem` título de panel ·
`0.875rem` título de opción · `0.83rem` motivo · `0.8rem` descripción ·
`0.78rem` ficha fija y vetada · `0.75rem` nota de dependencia · `0.68rem`
encabezado de franja · `0.62rem` distintivos.

---

## 4. Componentes

| Componente | Clase | Variantes | Notas |
|---|---|---|---|
| Ficha fija | `.resp-chip` | — | Sin checkbox: no se puede quitar. Fondo blanco sobre `.resp-fijas` |
| Encabezado de franja | `.resp-extra-titulo` | — | Versalitas, `0.08em` de tracking. Aloja `#resp-cupo` |
| Contador de cupo | `.resp-cupo` | `.lleno` | «— quedan N de M» → «— no cabe ninguna más en el anexo» en `--danger` |
| Casilla | `.resp-opcion` | `.sugerida`, `.deshabilitada`, `:has(input:checked)` | `display:flex`, checkbox alineado a la primera línea (`margin-top:.2rem`) |
| Distintivo de sugerida | `.resp-sugerida-marca` | — | «POR SU ACTIVIDAD», píldora ámbar `rgba(184,134,11,.15)` sobre `#8A6508` |
| Nota de regla | `.resp-opcion-nota` | — | «Requiere también la 18.» / «Reemplaza la 48.» |
| Vetada | `.resp-vetada` | — | Código + nombre + motivo, en una línea de `--text-muted` |
| Panel de calidad DIAN | `.ce-bloque` | — | Riel `4px` en `--danger`, fondo `rgba(192,57,43,.04)` |
| Distintivo obligatoria | `.ce-obligatoria` | — | Píldora roja al lado del título |
| Opción de calidad | `.ce-opcion` | `.elegida` | Píldora; elegida invierte a fondo `--navy`, texto blanco |

`.resp-opcion` y `.ce-opcion` son `<label>` con el `<input type="checkbox">`
adentro: toda la superficie es zona de clic sin necesidad de `for`/`id`.

---

## 5. Estados e interacciones

| Elemento | Estado | Comportamiento |
|---|---|---|
| `.resp-opcion` | hover | `border-color: var(--gold)`, transición `.15s ease` |
| `.resp-opcion` | marcada | Borde `--gold` + fondo `--gold-light` vía `:has(input:checked)` |
| `.resp-opcion` | sin cupo | `opacity:.5`, `cursor:not-allowed`, checkbox `disabled`; el hover no cambia el borde. Las ya marcadas nunca se deshabilitan |
| `.resp-opcion` | excluyente | Al marcar una, la contraria se desmarca sola y su checkbox pasa a `checked=false` (33↔50) |
| Código 53 | marcada / desmarcada | Recalcula contra el backend: reemplaza a la 48 en las fijas y libera una fila de cupo |
| `#resp-comercio-exterior` | oculto | `.hidden` mientras no haya ninguna responsabilidad con `comercio_exterior:true` marcada |
| `#resp-comercio-exterior` | visible | Se repinta en cada cambio; el motivo nombra los códigos que la dispararon |
| `#resp-comercio-exterior` | sin responder | `validateStep(5)` devuelve `false`, `alert()` y `scrollIntoView({behavior:'smooth', block:'center'})` |
| Cambio de régimen | — | Recarga la lista; suelta las marcadas que dejaron de ofrecerse o que ya no caben |
| Cambio de CIIU / objeto social | — | Recarga: cambian las sugeridas y puede cambiar el cupo |

**Copia exacta del bloqueo cliente** (`app.js:213`):

> Marcó la responsabilidad 10.
>
> Indique si la sociedad actuará como importador, exportador o usuario aduanero: de eso depende la casilla que se marca en el formulario RUES.

El servidor repite la validación en `/api/generate` con redacción equivalente:
la interfaz se puede saltar, el formulario RUES no puede salir con las tres
casillas vacías.

---

## 6. Datos

`GET /api/responsabilidades?regimen=&ciiu=&objeto_social=&marcada=` (requiere sesión)

```jsonc
{
  "predeterminadas": [{ "codigo": "05", "nombre": "…" }],
  "adicionales": [{
    "codigo": "33",
    "nombre": "Impuesto Nacional al Consumo",
    "descripcion": "Expendio de comidas y bebidas…",
    "sugerida": true,          // el CIIU o el objeto social la hacen probable
    "requiere": [],            // dependencias: se anuncian en la casilla
    "reemplaza": [],           // sustituye a otra en las fijas (53 → 48)
    "excluye": ["50"],         // la interfaz la suelta al marcar esta
    "comercio_exterior": false,// dispara la pregunta de calidad DIAN
    "fundamento": ["Estatuto Tributario, arts. 512-1 y ss."]
  }],
  "no_seleccionables": [{ "codigo": "46", "nombre": "…", "motivo": "…" }],
  "cupo_adicionales": 4,
  "maximo_anexo": 10,
  "comercio_exterior": {
    "pregunta": "…", "ayuda": "…",
    "opciones": [{ "id": "importador", "nombre": "Importador", "casilla_rues": "Casilla 1_30" }]
  }
}
```

`POST /api/generate` recibe `responsabilidades_adicionales: []` y
`perfil_comercio_exterior: []`. El backend traduce el segundo a
`casillas_comercio_exterior: { "Casilla 1_30": true, … }`, que
`pdf_filler.generar_rues()` vuelca sobre los checkboxes del formulario.

**El cupo se valida antes que la calidad ante la DIAN**: si la selección no cabe
en las diez filas, primero hay que arreglar la selección; preguntar por la
calidad de algo que se va a quitar confunde.

---

## 7. Casos límite

- **Sin adicionales disponibles** — `#resp-adicionales` muestra «No hay
  responsabilidades adicionales disponibles para este régimen.» en `.hint`.
- **Sin sugeridas** — desaparece el encabezado «Sugeridas por la actividad que
  declaró» y el segundo pasa de «Otras que puede agregar» a «Puede agregar».
- **Cupo agotado** — todas las no marcadas quedan deshabilitadas y el contador
  pasa a rojo. No se puede llegar a la pantalla de error.
- **El régimen simple reduce el cupo** — al cambiar de régimen se sueltan las
  sobrantes empezando por la última marcada.
- **Nombres largos** — las descripciones envuelven; nada se trunca. Se prefirió
  altura a truncamiento: son textos que hay que leer para decidir.
- **`excluye` ausente en la respuesta** — el renderizador tolera `requiere`,
  `reemplaza` y `excluye` indefinidos (`(r.excluye || [])`).
- **Sesión vencida** — el `fetch` falla y el bloque queda vacío. *Pendiente:* no
  hay estado de error visible (ver §9).

---

## 8. Accesibilidad

Lo que ya está:

- Cada opción es un `<label>` que envuelve su `<input>`: alcanzable con Tab,
  conmutable con Espacio, y el nombre accesible sale del contenido.
- El orden del foco sigue el orden visual: fijas (no focalizables) → sugeridas →
  otras → calidad DIAN → `<summary>` de las vetadas → campo de ingresos.
- Las vetadas van dentro de `<details>`: colapsadas no entran en el orden de
  foco, y `<summary>` es focalizable de forma nativa.
- Deshabilitar el checkbox (no solo atenuarlo con CSS) lo saca del orden de foco
  y lo anuncia como no disponible.

Lo que falta y conviene añadir:

| Elemento | Falta | Sugerencia |
|---|---|---|
| `#resp-comercio-exterior` | No se anuncia al aparecer | `role="group"` + `aria-labelledby` al `.ce-titulo`, y mover el foco a la primera opción al abrirse |
| `#resp-cupo` | El contador cambia en silencio | `aria-live="polite"` |
| Exclusión automática | Desmarcar la contraria no se anuncia | Mensaje en la región viva: «Se soltó la 33: es excluyente con la 50» |
| Distintivo «POR SU ACTIVIDAD» | Solo color y tamaño | Ya es texto, no color solo — correcto; verificar contraste `#8A6508` sobre ámbar (≈4.7:1, pasa AA en `0.62rem` bold) |
| Bloqueo de validación | `alert()` | Sustituir por mensaje en línea con `aria-describedby`, como el resto del cuestionario haga la migración |

---

## 9. Pendientes conocidos

1. **Estado de error del `fetch`** — si `/api/responsabilidades` falla, el bloque
   queda mudo. Debería mostrar un aviso con reintento.
2. **`alert()` como mecanismo de bloqueo** — heredado del resto del
   cuestionario; funciona, pero no es accesible ni se ve bien.
3. **La matriz necesita revisión de un tributarista.** Está construida sobre el
   listado oficial de la casilla 53 y el Estatuto Tributario, y cada código
   lleva su `fundamento`, pero la clasificación entre «base», «adicional» y
   «no seleccionable» es una interpretación, no una certificación.
4. **El código 46 quedó bloqueado.** Aparece en `no_seleccionables` aunque se
   había pedido como disparador de comercio exterior: la 46 es para proveedores
   **sin** domicilio en Colombia. Una S.A.S. colombiana que importe servicios va
   con la **09** (retención en la fuente en el impuesto sobre las ventas), y a
   eso remite el motivo. Si se quiere ofrecer de todos modos, hay que moverla de
   `no_seleccionables` a `adicionales` en el JSON.

---

## 10. Cobertura de pruebas

| Suite | Qué cubre |
|---|---|
| `test_responsabilidades.py` | 52 códigos clasificados, sugerencias por actividad, 53→48, dependencias 24/26→18, exclusiones, `excluye` en la respuesta, comercio exterior, bloqueo de la 46 |
| `test_paquete.py` | El anexo refleja lo marcado, se detiene si no cabe, la calidad declarada marca la casilla correcta del RUES |
| `test_cuestionario.mjs` | Franjas y dependencias en la interfaz, exclusión automática, la pregunta aparece / bloquea / se limpia |
| `test_ciiu.py`, `test_ajustes.py` | Sin cambios; se corren para verificar que nada se rompió |

```bash
python test_responsabilidades.py && python test_ciiu.py && python test_paquete.py && python test_ajustes.py && node test_cuestionario.mjs
```
