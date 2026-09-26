# SÍ tiene su impulso

SÍ S.A.S. es una sola firma: las tres eses repiten exactamente el mismo contorno; la A y la Í tienen la misma altura nominal y peso. El barco a la izquierda vincula la marca con Quarta. La Í convierte una letra en símbolo, siguiendo el principio de Anuwa: una intervención memorable dentro de una palabra sobria. Su remate sube hacia la derecha y conserva el acento agudo.

## Construcción

Todos los caracteres son contornos dibujados a mano, no texto convertido en tiempo de ejecución. La referencia de proporciones es una grotesca negrita compatible con DIN/Barlow; no se reproduce una fuente comercial.

- Retícula nominal: altura de mayúsculas 91 unidades; línea superior y=40 y base y=131. Asta principal de la Í: 18 unidades. La S sobresale 2 unidades arriba y abajo para compensar sus curvas.
- La S mide 65 unidades. Sus aperturas y terminales oblicuos preservan el reconocimiento en pequeño. La A tiene contraforma triangular y barra a y=94–110; puntos cuadrados de 17 unidades, alineados a la base.
- Í: asta vertical hasta y=105; dos curvas Bézier enlazan la base con un remate ascendente. El extremo exterior llega a x=53 respecto del asta, con corte diagonal de 45°. No hay letra cursiva importada.
- Acento: paralelogramo de 20 unidades de alto, entre y=8 y y=28. Separación de 12 unidades respecto del asta; desplazamiento a la derecha que sigue la dirección del gesto.
- Posiciones de letras: S=172, Í=250, S=325, punto=400, A=428, punto=517, S=546, punto=621. El espacio S–Í es 13 unidades; la separación entre el remate de la Í y la siguiente S es 22. No separar ni cambiar el tamaño de S.A.S.
- Barco: alto 91 unidades, ancho aproximado 149; base común con las letras. Hay unas 15 unidades entre su punta derecha y la primera S. Se aproxima ópticamente a la relación compacta de Quarta, sin invadir el contorno de la S.
- El archivo completo usa `viewBox="0 0 646 141"`, con aproximadamente 8 unidades de margen exterior. Reservar adicionalmente una zona libre equivalente a un asta (18 unidades) alrededor de la marca. No deformar el SVG.
- Símbolo: barco + Í, `231 × 141`, composición compacta horizontal. Para un avatar cuadrado, centrarlo sin estirarlo y respetar el área libre. Favicon: Í sola con tilde y cola, sin el barco para no saturar 16 px.

## Procedencia del barco

Se leyó completo `src/static/img/logo_quarta.svg`. Los contornos se copiaron literalmente de `clip_2` y `clip_3`:

```svg
<!-- Ala -->
<path d="M63.195 488.601 202.098 342.543H63.195V249.658H455.656L63.195 645.185Z"/>
<!-- Casco -->
<path d="M63.324 248.821H457.985L712.641 476.817Z"/>
```

La matriz original `matrix(1,0,0,-1,0,880)` invierte el eje vertical del PDF. En la nueva firma se compone como `translate(8 40) scale(.22958 -.22958) translate(-63.195 -645.185)`: escala uniforme, inversión y traslado, sin alterar vértices ni ángulos.

El SVG original no define degradados SVG para el barco: contiene dos PNG incrustados recortados por esas siluetas. Se decodificaron para comprobar el color: el ala incluye muestras RGB(0,68,131) y (0,26,54); el casco incluye RGB(0,93,184), (13,66,150) y (0,68,114). La entrega interpreta esos colores con ala navy #004571 y un único degradado vectorial del casco #0060B8 → #1B3F95, conforme al encargo. **La geometría es exacta; el color es una reconstrucción vectorial, no una reproducción píxel a píxel de los PNG.** No se modificó ni se copió el PDF externo al repositorio.

## Color y tamaños

| Uso | Archivo / tono |
| --- | --- |
| Fondo blanco o claro | `si-logo-full.svg` / `claro`: letras navy, barco azul |
| Fondo navy o negro | `si-logo-full-white.svg` / `oscuro`: todo blanco |
| Una tinta | `si-logo-mono.svg` / `mono`: `currentColor` |
| Perfil o aplicación | `si-mark.svg`; macro `variante='mark'` en los tres tonos |
| Pestaña del navegador | `si-favicon.svg`; navy en tema claro, blanco en tema oscuro |

La paleta de familia sigue siendo #3641E4, #004571, #E3E3EF y #82389A. Los dos últimos tonos y el azul primario no se añaden a la firma. Sin sombras, brillos ni otros degradados nuevos.

Mínimo recomendado del logotipo: 20 px de alto del SVG; uso habitual 24–32 px. A 16 px utilizar el favicon. El tablero conserva muestras completas a 16 px como prueba de estrés. En impresión a una tinta, elegir negro o navy sobre blanco, o blanco sobre negro. `currentColor` hereda del documento cuando el SVG está inline; una imagen `<img>` no hereda el color de su padre.

## Integración y movimiento

`{% from '_marca.html' import si_logo %}` permite llamar `si_logo(variante='full', tono='claro', clase='')`. La macro inserta paths y asigna identificadores consecutivos al degradado para admitir varias marcas en una página. `tono='mono'` hereda color; `oscuro` usa blanco. Cada SVG tiene nombre accesible y no captura el foco.

La tilde se asienta al cargar y al pasar el puntero: 240 ms, ease-out, desplazamiento vertical de 5 unidades CSS (4 en hover) y opacidad. La forma final está presente sin JavaScript. `prefers-reduced-motion: reduce` elimina las dos animaciones.

La sección delimitada al final de `style.css` contiene todos los estilos de marca. `marca-si.css` replica esa sección para landing y autenticación: cargar el CSS global del cuestionario allí modificaría componentes ajenos al encargo. Mantener ambas secciones sincronizadas. Anuwa permanece en sus ubicaciones existentes.

Abrir `src/static/img/si/preview.html` directamente: no necesita Flask, Jinja, fuentes remotas ni servidor. Presenta todos los archivos y las variantes de la macro sobre blanco, navy y negro, en 16, 24, 32, 64, 128 y 400 px. Las combinaciones blanco/blanco y navy/navy se incluyen para inspección, no están autorizadas como aplicación final. Las muestras grandes tienen desplazamiento horizontal para mantener la escala real.

## Límites de la revisión

El tablero verifica la marca y su convivencia con Anuwa. No sustituye una revisión de todas las páginas Flask con datos reales. No se han cambiado backend, eventos, atributos funcionales ni JavaScript. Las reglas de navegación y distribución generales existentes quedan fuera del alcance de este cambio.

Validación realizada: SVG parseables como XML, revisión visual del tablero mediante Chrome headless, `git diff --check`, comparación de todos los atributos funcionales y bloques de scripts de las cuatro páginas contra HEAD, y `node test_cuestionario.mjs`: **«Cuestionario verificado.»**. La junction de `node_modules` no exponía `jsdom` en esta sesión: se instaló una copia aislada en `output/marca/deps` y se resolvió mediante `NODE_OPTIONS=--import=./output/marca/dependencias.mjs`, sin modificar la prueba ni escribir en el destino externo de la junction. No se pudo ejecutar Python/Jinja en este entorno; queda pendiente la revisión de las páginas servidas por Flask.
