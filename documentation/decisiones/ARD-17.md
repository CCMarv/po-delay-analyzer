# Lenguaje visual y codificación de color de la taxonomía

* **Estatus:** 🟢 **VIGENTE** (cerrado 2026-07-14)
* **Contexto Técnico:** Fase 4 / Sistema de diseño — codificación visual de la taxonomía (etapa, severidad y confianza del LLM) compartida por las dos superficies de consumo de la app; implementación asociada al #159
* **Referencias:** Issue #162; #159 (sistema de diseño); #163 / #164 (vistas Diego / Ravi); Munzner (*What–Why–How*), Cleveland–McGill (jerarquía de canales gráficos), Okabe–Ito (*Color Universal Design*), WCAG 2.1 (§1.4.3 texto, §1.4.11 objetos no textuales); ADR-09 (personas); ADR-10 (severidad híbrida); [ADR-07](ARD-07.md) (taxonomía de Indeterminado); `04_app/config.py`, `04_app/assets/styles.css`, `04_app/components/badges.py`, `04_app/components/timeline.py`

## Contexto y Problema

La app de Fase 4 expone tres variables derivadas a dos personas de consumo (Diego y Ravi,
ADR-09): la **etapa** del retraso (Vendor / Carrier / DC / Indeterminado, taxonomía de
ADR-07), la **severidad** que emite el LLM y audita la regla de Fase 2 (ADR-10) y la
**confianza** del modelo (`llm_confianza`, escalar 0–1). Las tres se muestran repetidas en
tarjetas, tablas y gráficas; sin un lenguaje visual único, cada vista las codifica distinto
y el lector reaprende el color en cada pantalla.

La paleta previa de la app (`#2E86AB`, `#A23B72`, `#F18F01`, `#C73E1D`…) tiene dos defectos.
Primero, es arbitraria: colores elegidos por estética, sin un marco que justifique por qué
cada etapa recibe su hue. Segundo, no es segura para daltonismo (CVD): ~8 % de los hombres
tiene alguna deficiencia rojo-verde, y una codificación categórica que descansa en
distinciones de hue que colapsan bajo deuteranopía/protanopía deja de ser legible para esa
fracción de la audiencia.

El problema de fondo no es solo qué colores, sino **qué canal visual codifica cada
variable**. La etapa es nominal (categorías sin orden), la severidad es ordinal (niveles
rankeados) y la confianza es un escalar continuo que se agrupa en niveles ordinales. Cifrar
las tres con hues arbitrarios confunde los tipos de variable y hace que dos escalas de color
compitan por la atención categórica del lector. Se necesita una regla —no una preferencia—
anclada en un marco de referencia, para que la codificación sea reproducible y defendible.
El marco adoptado es Munzner (*What–Why–How*: elegir el canal por la tarea) sobre la
jerarquía de efectividad de Cleveland–McGill (posición y longitud se decodifican con menos
error que ángulo, área o color).

## Opciones Consideradas

**Paleta de etapa — Okabe–Ito (elegida).** La paleta *Color Universal Design* de Okabe–Ito
está diseñada para ser distinguible bajo los tres tipos de daltonismo y en escala de grises.
Pros: accesible por construcción, con respaldo publicado; hues estables que se reusan
idénticos en toda la app. Contras: gama fija (no se eligen los colores por gusto de marca).

**Paleta de etapa — paleta previa de la app (descartada).** Los hues actuales
(`#2E86AB`/`#A23B72`/`#F18F01`/`#C73E1D`) se descartan por no ser CVD-safe y por carecer de
marco: no hay forma de defender la elección más allá de la estética.

**Codificación de severidad — rampa de luminancia acromática + icono + texto (elegida).** La
severidad se cifra por luminancia (canal ordenado) reforzada con forma (icono) y etiqueta de
texto. Pros: la redundancia sobrevive al daltonismo y a la impresión en gris; no compite con
el hue de etapa. Contras: cede parte de la alarma "de un vistazo" que da el rojo semántico
(mitigada por el icono y el texto).

**Codificación de severidad — rojo-ámbar-verde semántico (descartada).** Es el mapeo
intuitivo de urgencia, pero falla en deuteranopía/protanopía (no distinguen rojo de verde) y,
al ser una segunda escala de hue, competiría con la codificación de etapa por el mismo canal.

**Codificación de severidad — hue único no-neutro, p. ej. azul-pizarra (descartada).** Una
rampa de un solo hue oscuro-a-claro sería ordenada y CVD-safe, pero comparte familia de hue
con Vendor (`#0072B2`) y podría leerse como relacionada a esa etapa pese al icono y el texto
redundantes. El gris acromático evita esa colisión semántica.

## Decisión

1. **Marco de selección.** Se elige el canal por la tarea (Munzner) respetando la jerarquía
   de Cleveland–McGill: posición/longitud por encima de ángulo/área. Consecuencia directa:
   quedan **prohibidos** los gráficos de pastel, dona, treemap y 3D; sin *chartjunk*;
   etiquetado directo sobre las marcas en vez de leyendas remotas; Lie Factor = 1.0 (el
   tamaño de la marca proporcional al dato).

2. **Etapa = hue categórico (Okabe–Ito), idéntico en toda la app.** El Indeterminado usa un
   gris neutro, no un color más de la escala: su semántica es "sin causa atribuible" (ausencia
   de etapa dominante, ADR-07), y un gris lo comunica sin sugerir una cuarta categoría al
   mismo nivel que las tres reales. La variante de tema oscuro ajusta la **luminancia** de
   cada hue para el fondo, sin cambiar el hue.

   | Canal | Nivel | Tema claro | Tema oscuro |
   | :--- | :--- | :--- | :--- |
   | Etapa (hue) | Vendor | `#0072B2` | `#4DA8DB` |
   | | Carrier | `#E69F00` | `#F0B840` |
   | | DC | `#009E73` | `#3FC79A` |
   | | Indeterminado (gris neutro) | `#767676` | `#9B9B9B` |
   | Severidad (ordinal + icono) | ■ HIGH | `#3D3D3D` | `#E8E8E8` |
   | | ◆ MEDIUM | `#6B6B6B` | `#A8A8A8` |
   | | ● LOW | `#A8A8A8` | `#6B6B6B` |

3. **Severidad = ordinal, no compite por hue.** Se cifra con una rampa de luminancia
   acromática (gris-carbón) reforzada con forma (■ HIGH / ◆ MEDIUM / ● LOW) y etiqueta de
   texto, **confinada a contextos de severidad**. En tema claro, más oscuro = más urgente
   (HIGH `#3D3D3D`). En tema oscuro la rampa se **invierte en luminancia** (HIGH `#E8E8E8`)
   para conservar el mismo principio perceptual: el extremo HIGH es siempre el de mayor
   contraste contra el fondo. La triple redundancia (luminancia + forma + texto) hace la
   codificación robusta al daltonismo y a la impresión en gris.

4. **Confianza (`llm_confianza`, 0–1) = mismo mecanismo ordinal, sin icono.** Reusa la rampa
   de luminancia de severidad, agrupada en tres buckets: **Alta** 0.80–1.00 (evidencia
   suficiente), **Media** 0.50–0.79 (requiere verificación humana), **Baja** < 0.50 (datos
   insuficientes). Se muestra como badge de bucket, no como número crudo ni medidor.

5. **Contraste WCAG.** El texto va siempre en el foreground neutro (`--text-primary`: oscuro
   en tema claro, claro en tema oscuro); **nunca** se colorea el texto con el hue de
   etapa/severidad. El color vive solo en *swatches*, iconos y marcas de gráfica, que como
   objetos no textuales requieren 3:1 (WCAG §1.4.11) y no el 4.5:1 del texto (§1.4.3). Las
   combinaciones fondo/marca de ambos temas se verificaron por cálculo de luminancia relativa;
   los valores exactos viven en `styles.css`.

6. **Selección de gráfica por tarea** (la heredan las vistas de #163 / #164): reparto por
   etapa → **barra horizontal** (reemplaza el `px.pie` previo); severidad → **barra ordenada**
   HIGH > MEDIUM > LOW; desacuerdo LLM ↔ regla → **KPI + barra por etapa**; tendencia sobre
   `PO_DT` → **línea con etiquetado directo**; recorrido de una PO → **`px.timeline` estático**
   que resalta el tramo de mayor `excess_*_hrs`; confianza → **badge de bucket** (no dotplot,
   no gauge).

## Consecuencias

**Positivas:** toda la app —las dos vistas de Diego (#163) y Ravi (#164)— hereda una sola
codificación, definida una vez en `config.py`/`styles.css`, sin ningún hex suelto fuera de
esas fuentes. La codificación es accesible por construcción (daltonismo, contraste WCAG y
lectura en escala de grises) y defendible: cada elección se remite a un marco publicado, no a
la estética. La separación de canales (hue = etapa nominal; luminancia + forma = severidad
ordinal) evita que dos escalas compitan por la atención del lector.

**Negativas:** la rampa acromática de severidad cede parte de la alarma inmediata que da el
rojo semántico aprendido (se mitiga con icono + etiqueta). **Límite conocido:** el *chrome*
nativo de Streamlit (sidebar, algunos widgets) no respeta `prefers-color-scheme`; solo los
componentes personalizados (navbar, badges, tarjetas, timeline) responden al tema del sistema.
Ese *chrome* queda fuera del alcance de `config.py`/`styles.css`/`components/` (#159).

## Relación con otras decisiones

Sirve a las dos superficies de consumo que motiva **ADR-09** (personas Diego / Ravi). Preserva
**ADR-10**: la severidad oficial la emite el LLM y la audita la regla de Fase 2; este ARD solo
fija su **codificación visual**, no cambia su fuente ni la supersede. Toma de **[ADR-07](ARD-07.md)**
la taxonomía de Indeterminado, que justifica el tratamiento en gris neutro (ausencia de causa
atribuible, no una categoría par de las otras tres). No supera ni encadena ningún ARD previo:
es una capa nueva de codificación visual sobre decisiones vigentes.

## Nota de cierre (2026-07-22)

La auditoría ADR↔repo detectó que el punto 5 (contraste WCAG) afirmaba una verificación por
luminancia relativa que, recalculada contra los tres fondos reales de `styles.css`, no se
sostenía para dos swatches: Carrier (`#E69F00`, 2.05-2.25:1) y severidad/confianza Baja
(`#A8A8A8`, 2.16-2.38:1), ambos por debajo del 3:1 exigido. Se corrigieron a **`#B88000`**
(Carrier) y **`#8A8A8A`** (Baja) — mismo hue/saturación, solo se redujo el brillo — verificados
en ≈3.1:1 contra `--surface-elevated` (el fondo más exigente de los 3). Adicionalmente, se
detectó que la pill de texto del timeline (punto 6, vista Diego) solo se asignaba al primer
segmento resaltado de un PO: cuando Carrier abarca 2 columnas de segmento, el segundo
comunicaba su etapa solo por hue, sin la redundancia de texto que el resto de la app sí
respeta. Se corrigió para que todos los segmentos resaltados lleven su pill. El marco de
selección (Munzner/Cleveland-McGill/Okabe-Ito), la tabla de hues de etapa y el resto de la
codificación no se reabren — solo estos dos valores hex y la asignación de la pill.
