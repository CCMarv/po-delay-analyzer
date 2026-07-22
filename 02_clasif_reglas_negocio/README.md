# Fase 2 — Clasificación por etapa (reglas de negocio)

> Documento de metodología (#50). Por ahora **solo en español**; la versión en inglés se
> añade al cierre del desarrollo. Las cifras son sobre el dataset real (400 POs, 247 tardíos).

Esta fase asigna a cada PO tardío la **etapa responsable** del retraso (Vendor / Carrier /
DC / Indeterminado), una **subclase de DC** (Yard / Dock) y una **severidad** determinística,
y valida esas asignaciones contra dos referencias independientes. Toda la lógica vive en
funciones reusables de `classifier_core.py` y `metrics_core.py`; el notebook solo presenta.

## 1. Flujo

```
CSV crudo
  └─ clean_po_data()          [pipeline_core.py, Fase 1]  → deltas *_calc + flags de calidad
       └─ classify_po_stages() [classifier_core.py]        → stage_primary, severity, dc_substage, …
            ├─ save_classified_output()                    → data/processed/df_classified.csv (#49)
            └─ metrics_core.py                              → validación (#46, #47)
```

`classify_po_stages` orquesta cuatro pasos: `_flags_por_umbral` (#44) → `_etapa_primaria`
(#45) → `_capa_complementaria` (flags de contexto) → `_severidad` (#48).

## 2. Taxonomía y decisiones del mentor

La taxonomía y los umbrales se cerraron con el mentor (2026-06-16) y se afinaron tras una
consulta de atribución (2026-06-17). Cada decisión con su porqué:

| # | Decisión | Por qué |
|---|----------|---------|
| #39 | **Cuatro etapas**: Vendor / Carrier / DC / Indeterminado. | "Indeterminado" es una categoría válida y auditable: forzar una atribución sin evidencia sería inventar causalidad. |
| #40 | **Vendor por STA push** (`APPROVED_DT > STA_DT`), NO por residual. | El residual (delay − carrier − DC) asume que los tramos son aditivos y mutuamente excluyentes; en la práctica hay solapamientos. La señal directa es más sólida y **funciona en los 27 POs sin hora de tráiler** (no necesita carrier/DC para medirse). |
| #41 | **Umbral carrier = 8h** (no 4h), con tabla de sensibilidad. | La mediana de `gap_carrier` es ≈3h y el p75 ≈4.4h; 8h produce una proporción de carrier consistente con un dataset de trayectos cortos. Lo que vale es la **trazabilidad** (sección 5). |
| #42 | **Rescheduled y short-ship = contexto / agravante**, no etapa. | Una reprogramación describe un *evento*, no una causa raíz; el clasificador responde *quién* causó el retraso, no *qué* ocurrió. Como flag de contexto aporta más al LLM (Fase 3). |
| #40b | **DC = Yard + Dock consolidado**, con subclase `dc_substage`. | El responsable final es el mismo (operaciones del CD); el detalle Yard/Dock se conserva como subclasificación informativa. |
| 06-17 (b) | Los **14 tardíos sin ninguna señal** → Indeterminado. | Datos completos pero ningún umbral superado (retrasos chicos, mediana 3.2h): no hay a quién atribuir con evidencia. Honra "no inventar causalidad" aunque amplíe la definición de Indeterminado. |

### Cómo se decide `stage_primary` (`_etapa_primaria`, #45)

1. **Exceso por tramo medible** = `max(0, observado − umbral del mentor)`, en horas
   (carrier 8h, yard 4h, dock 6h). Un tramo no medible (máscara field-level en False) aporta
   0 al argmax, pero la máscara registra el "no se pudo medir".
2. **Vendor por STA push sobre umbral** = `max(0, −appt_lead_days × 24 − 24h)`, donde
   `appt_lead_days = STA − APPROVED` (días); es negativo cuando `APPROVED > STA`, así que el
   push en horas es positivo. El push solo cuenta como exceso **por encima de `vendor_gap_hrs`
   = 24h**, igual que carrier/DC tienen su umbral (consulta del mentor 06-17; ver §3 y §5.3).
3. **Etapa primaria** = argmax de `{Vendor, Carrier, DC}`.
4. **Indeterminado** (con subclase `indeterminado_substage`, espejo de `dc_substage`): (a)
   **`sin_datos`** = el PO es tardío pero no medible (sin `TRAILER_ARRIVE_DT`); (b)
   **`sin_causa_dominante`** = es medible pero ningún tramo supera su umbral (incluido el de
   vendor). La etiqueta superior es `Indeterminado`; la razón específica vive en la subclase.

### Reparto resultante (247 tardíos)

| Etapa | % | n |
|-------|---|---|
| Vendor | 56.3% | 139 |
| Carrier | 16.2% | 40 |
| DC | 15.0% | 37 |
| Indeterminado | 12.6% | 31 |

Los 31 Indeterminados se desglosan en **7 `sin_datos`** (sin hora de tráiler) + **24
`sin_causa_dominante`** (medibles pero sin ningún exceso sobre umbral). *(Nota de cierre
ARD-03b, 2026-07-22: el gate `decidible` excluía a vendor sin condición propia — 8 POs sin
tráiler pero con exceso de vendor medible (22.6-92.5h) quedaban en `sin_datos` por descarte;
ver [ADR-03b](../documentation/decisiones/ARD-03b.md).)*

Vendor domina (56%) por encima del ~20% del kickoff. Tras la consulta del mentor (06-17),
vendor lleva **umbral propio (24h)** para corregir la *asimetría de construcción*: antes
disparaba con cualquier push positivo mientras carrier/DC exigían 8/4/6h, así que absorbía por
default. El 53% **lo soporta el dato, no la regla de disparo**: la distribución del push es
**bimodal** — 12 POs con push casi-cero (≤6h) y 141 con push de días (mediana 3.1 días), con un
**hueco vacío entre 6h y 18h** (ningún PO). Las órdenes tardías lo son casi siempre porque la
cita se aprobó tarde. *(La correlación push↔retraso total es alta por construcción —un retraso
temprano se propaga— y NO es evidencia de causalidad; lo relevante es el exceso por tramo.)*

## 3. Umbrales (`rules_config.json`)

Los umbrales se leen por nombre desde el JSON (nunca hardcodeados); recalibrar es editar el
JSON, no el código.

| Clave | Valor | Uso |
|-------|-------|-----|
| `vendor_gap_hrs` | 24.0 h | Exceso de vendor (STA push) sobre este umbral. 24h = grano natural del dato (STA a nivel día). |
| `carrier_lag_hrs` | 8.0 h | Exceso de carrier sobre este umbral (confirmado por el mentor). |
| `yard_wait_hrs` | 4.0 h | Exceso de yard. |
| `dock_hrs` | 6.0 h | Exceso de dock. |
| `short_ship_fill_rate` | 0.9 | Por debajo → short-ship (flag de contexto). |
| `severity_delay_days` | 3.0 d | Gate HIGH de severidad. |
| `severity_low_days` | 1.0 d | Corte LOW (borderline) de severidad. |

> Se eliminó el bloque `expected_leg_times` (presupuestos semilla 3/1.5/2.5 h): nunca se
> validaron y el método ahora mide exceso sobre los umbrales del mentor, no sobre presupuestos.

## 4. Severidad (`_severidad`, #48)

Severidad **determinística** (no la decide el LLM; esa es una capa narrativa aparte en Fase 3).
La rúbrica pide un ranking auditable, y el cómputo desde columnas confiables es defendible.

- **HIGH** = `flag_hot_late` (HOT_PO_FLAG=1 e IS_LATE) **y** `delay_days_calc > 3.0`.
- **LOW** = `delay_days_calc < 1.0` (borderline, casi a tiempo, <~24 h).
- **MEDIUM** = el resto de los tardíos.
- **(vacío)** = no tardío (no entra al ranking).

**Agravantes** (decisión #40/#42): `is_short_lead` o `is_short_ship` suben **un nivel**
(LOW→MEDIUM, MEDIUM→HIGH); HIGH se mantiene (tope). Una orden borderline con lead corto deja
de ser borderline. No acumulan más allá de HIGH: el gate HIGH "real" sigue siendo HOT + retraso fuerte.

Reparto (247 tardíos): MEDIUM 131 · LOW 82 · HIGH 34.

## 5. Validación (`metrics_core.py`)

| Métrica | Resultado | Umbral | Estado |
|---------|-----------|--------|--------|
| **Stage accuracy** (#46) | 100% (216/216 evaluables) | > 80% | ✅ |
| **Reason agreement** (#47) | 88.7% (180/203 clasificables) | — (referencia) | hallazgo |
| **Severity ranking** (#48) | determinístico, auditable | > 95% | ✅ |

### 5.1 Stage accuracy (#46): gap dominante vs `stage_primary`

`stage_primary` mide **exceso sobre umbral**; el **gap dominante** mide **duración bruta** del
tramo más largo. Son métricas **distintas a propósito** — compararlas valida que la atribución
por exceso no se aleja de dónde físicamente se fue el tiempo, sin forzar que coincidan.

El gap dominante se mide sobre la **secuencia atribuible**, segmentada para que los tiempos
muertos no entren al cálculo (instrucción del mentor):

```
STA → APPROVED → TRAILER_ARRIVE → CHECKIN → CHECKOUT
```

Se **excluye** el lead time `PO→STA` (mediana 192 h: tiempo de compra normal, no retraso) y
todo lo posterior a CHECKOUT: `TRAILER_DEPART` ocurre **después** de `RECPT` en el **99.8%**
de los POs (verificado), o sea fuera del ciclo de recepción.

Denominador = **evaluables** (216): tardíos con stage decidible y gap medible. Los
Indeterminados quedan fuera (el gap dominante no puede juzgar un PO sin tráiler). Con el umbral
de vendor (24h) el acuerdo es **total (216/216)**: al exigir un push de al menos un día, los
casos antes multicausales (push pequeño + tramo interno) ya no se clasifican Vendor, así que la
atribución por exceso coincide con el tramo de mayor duración bruta en todos los evaluables.

### 5.2 Sensibilidad del umbral carrier (4 / 6 / 8 / 12 h)

Reparto = Vendor / Carrier / DC / Indeterminado (% de tardíos, con `vendor_gap_hrs`=24 activo).

| Umbral | `flag_carrier_calc` | Reparto `stage_primary` |
|--------|---------------------|--------------------------|
| 4 h | 25.8% (103) | 56.3 / 17.4 / 15.0 / 11.3 |
| 6 h | 12.8% (51) | 56.3 / 16.2 / 15.0 / 12.6 |
| **8 h** | **12.8% (51)** | **56.3 / 16.2 / 15.0 / 12.6** |
| 12 h | 11.2% (45) | 56.3 / 14.6 / 15.0 / 14.2 |

**Lectura:** el umbral carrier mueve mucho la *flag bruta* `flag_carrier_calc` (de 25.8% a
~12% al pasar de 4h a 8h, justo lo que predijo el mentor) pero apenas mueve `stage_primary`,
porque la señal de vendor domina el argmax y el umbral carrier solo reordena los pocos casos
donde carrier compite de cerca. 8h es el valor confirmado.

### 5.3 Sensibilidad del umbral vendor (6 / 12 / 18 / 24 / 48 / 72 h)

Decidir `vendor_gap_hrs` con el mismo análisis que carrier (instrucción del mentor 06-17).
Reparto = Vendor / Carrier / DC / sin_datos / sin_causa_dominante (conteos sobre 247 tardíos).

| Umbral | Vendor | %Vendor | Reparto |
|--------|--------|---------|---------|
| 0 (sin umbral) | 151 | 61.1 | 151 / 40 / 37 / 5 / 14 |
| 6 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| 12 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| 18 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| **24 h** | **139** | **56.3** | **139 / 40 / 37 / 7 / 24** |
| 48 h | 121 | 49.0 | 121 / 40 / 37 / 8 / 41 |
| 72 h | 81 | 32.8 | 81 / 40 / 37 / 10 / 79 |

**Lectura:** 6/12/18h son equivalentes (la distribución del push tiene un hueco vacío entre 6h
y 18h). **24h** es el valor elegido por tres razones: (1) es el **grano natural del dato** —
`STA_DT` está a nivel día (sin resolución sub-día), así que medir el push contra un día completo
es la unidad en que el problema está expresado; (2) cae en la **zona vacía** de la distribución
→ robusto a perturbaciones; (3) no fuerza el reparto hacia el ~20% del kickoff (que el mentor
desaconsejó). Los POs que dejan de ser Vendor al subir el umbral migran a `sin_causa_dominante`
(la mayoría) o a `sin_datos` (los sin tráiler cuyo push cae bajo el nuevo umbral) — **ninguno a
Carrier/DC** → el umbral no reatribuye, solo separa los push difusos. Detalle del análisis:
[`documentation/decisiones/ARD-06b.md`](../documentation/decisiones/ARD-06b.md).

*(Nota de cierre ARD-03b, 2026-07-22: antes de este fix, `sin_datos` aparecía constante en
15 para los 7 escenarios de esta tabla — una señal, en retrospectiva, de que el umbral de
vendor nunca alcanzaba a esos POs por el gate `decidible` roto. Ahora varía correctamente
con el umbral: 5/7/7/7/7/8/10.)*

### 5.4 Reason agreement (#47): la tesis del proyecto

Agreement = 88.7% sobre 203 clasificables (`stage_primary` vs `reason_group_manual`, el mapeo
de la anotación humana `REASON_DSC`; los nulos entre tardíos → "Unknown", fuera del denominador).

El agreement < 100% es **esperado y deseado**: la anotación humana es ~20% incorrecta (dato del
kickoff). Los **23 mismatches** son la evidencia de que el cómputo temporal supera a la
anotación humana — disponibles como posible insumo few-shot para Fase 3 (ver el estado en §6).

## 6. Mismatches seleccionados (#47) — evidencia temporal

Ocho casos donde los timestamps contradicen el reason code humano y el cómputo es defendible.
Cubren los tres tipos de discrepancia. ("STA push" = push crudo `APPROVED − STA` en horas, la
evidencia del fenómeno; el argmax usa el exceso sobre el umbral de 24h, que es 24h menor pero no
altera la atribución: todos superan el día con holgura.)

| PO | Cómputo | Humano (REASON_DSC) | Evidencia temporal |
|----|---------|---------------------|--------------------|
| 100280 | Vendor | Carrier ("Missed appointment window") | STA push 124.6 h; exceso carrier/DC = 0 |
| 100382 | Vendor | DC ("Yard congestion") | STA push 111.0 h; exceso yard/dock = 0 |
| 100236 | Vendor | Carrier ("Equipment/trailer issue") | STA push 118.5 h; exceso carrier = 0 |
| 100262 | Vendor | DC ("Dock processing backlog") | STA push 81.0 h; exceso dock = 0 |
| 100073 | Vendor | Carrier ("Weather/road conditions") | STA push 93.5 h; exceso carrier = 0 |
| 100024 | Carrier | DC ("Dock processing backlog") | exceso carrier 25.7 h; exceso dock = 0 |
| 100058 | DC (Yard) | Carrier ("Equipment/trailer issue") | exceso yard 19.3 h; exceso carrier = 0 |
| 100204 | DC (Dock) | Vendor ("Vendor delayed shipment") | exceso dock 9.0 h; STA push = 0 |

Patrón estrella (los 5 primeros): el humano culpó al eslabón visible (carrier/yard) mientras la
cita se había aprobado días tarde y ese tramo no tenía exceso alguno. Patrón interno (3
últimos): el cómputo detecta un exceso de tramo que la anotación humana confundió.

`metrics_core.select_mismatches(df, n)` devuelve este ranking por fuerza de señal. Con
`stratify=True` reparte `n` entre las etapas presentes (Vendor/Carrier/DC) y toma el más
fuerte de cada una, en vez de los `n` más fuertes en bruto: como el universo de mismatches
está dominado por Vendor, el ranking plano tiende a ser casi todo Vendor, y la selección
estratificada asegura que el few-shot (#99) y la narración de mismatches (#95) cubran las
tres etapas. El default (`stratify=False`) conserva el ranking plano histórico.

> **Estado del few-shot (al cierre de Fase 2).** Estos mismatches están **disponibles** como
> posible few-shot, pero **el prompt de Fase 3 es hoy zero-shot**: todavía NO los consume. El
> cableado (inyectar estos ejemplos en el prompt) es una decisión de diseño de prompt, pendiente
> en Fase 3. Aquí solo se produce y se justifica el insumo; usarlo o no lo decide F3.

## 7. Cómo correr

```bash
# Desde la raíz del repo, con el CSV en data/raw/ (o PO_CSV_PATH apuntándolo):
PYTHONPATH=01_data_pipeline_and_eda PO_CSV_PATH=data/raw/po_root_cause_synthetic.csv \
  python 02_clasif_reglas_negocio/classifier_core.py
# → imprime el reparto y escribe data/processed/df_classified.csv (gitignored).

# Tests:
python -m pytest -q
```

El output (`data/processed/df_classified.csv`) **no se versiona**; se regenera ejecutando el módulo.
