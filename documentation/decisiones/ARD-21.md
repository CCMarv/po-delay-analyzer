# Contrato de datos tier-1/tier-2 de `po_output.csv`

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo)
* **Contexto Técnico:** Fase 3 → Fase 4 — contrato de datos del único artefacto que consume
  `04_app` (Streamlit y el bot de Telegram)
* **Referencias:** Issue #158 (tier 1 — ampliar el contrato con columnas ya computadas), Issue
  #161 (tier 2 — persistir la salida híbrida de ARD-16), PR #174 (`--action-call`); ADR-09
  (personas), ADR-10 (severidad), [ARD-16](ARD-16.md) (carril 1 — contrato híbrido de la
  llamada de acción); `04_app/config.py` (columnas canónicas), `04_app/README.md:26-37`
  (documentación exacta 33/33), `llm_integration.py` (`_ACTION_COLUMN_MAP`); artefacto paralelo
  `data/processed/agente1_raw.txt` y su generador
  `03_llm_integration/llm_integration_network_intelligence_view.py`

## Contexto y Problema

`po_output.csv` es el único input de `04_app` (ambos canales: Streamlit y el bot de
[ARD-20](ARD-20.md)) — sin él, la app no abre. Tiene 33 columnas, sin ningún contrato
registrado en `documentation/decisiones/` (`grep -rli tier documentation/decisiones/` no
encontraba resultados antes de este ARD). Dos READMEs lo documentaban de forma distinta:
`04_app/README.md:26-37` documenta las 33/33 columnas exactas, mientras
`03_llm_integration/README.md` solo documentaba 16 de 33 (quedó desactualizado, previo a
#158/#161) — sin que ningún documento de diseño declare qué son "tier 1" y "tier 2"
conceptualmente ni por qué el contrato se amplió en dos pasos.

Aparte, `data/processed/agente1_raw.txt` —el artefacto que consume la vista Network
Intelligence (persona Ravi) vía `llm_integration_network_intelligence_view.py`— es una
dependencia de datos real de Fase 3→Fase 4 que ni el SAD ni ningún ARD reconocían (el SAD
llegó a afirmar lo contrario). No es parte de `po_output.csv`, pero comparte linaje y merece
declararse en el mismo contrato para que quede completo.

## Opciones Consideradas

**Opción A — Un solo README como fuente (`04_app/README.md`, ya exacto), sin ARD.**
Pros: ya existe y es correcto hoy. Contras: `documentation/decisiones/` es donde el proyecto
registra contratos de datos con su porqué y su trazabilidad a los issues que los decidieron
(#158/#161); un README de consumo no sustituye eso, y no evita que la segunda copia
(`03_llm_integration/README.md`) se desincronice otra vez sin que nadie lo note.

**Opción B — ARD que define el contrato formalmente, con `04_app/README.md` como copia
operativa sincronizada (elegida).** El ARD fija el vocabulario (qué es tier-1, qué es tier-2,
qué distingue ambos del contrato base) y su trazabilidad a #158/#161; `04_app/README.md`
sigue siendo la tabla operativa de consumo, no se duplica su contenido aquí. Contras: sigue
existiendo una segunda copia (`03_llm_integration/README.md`) que debe corregirse para no
mantener 3 versiones del mismo contrato — corrección de esa página es trabajo de
sincronización documental de otra unidad (G8), no de este ARD.

## Decisión

Se adopta **tier-1 / tier-2** como el vocabulario oficial del contrato F3→F4, con esta
partición (33 columnas, alcance: solo POs tardíos, `delay_days_calc > 0`):

1. **Contrato base (16 columnas, sin numeración tier)** — identidad y diagnóstico del mentor
   (`PO_NBR, stage, severity, explanation, action`), timeline (`PO_DT, STA_DT, APPROVED_DT,
   TRAILER_ARRIVE_DT, CHECKIN_DT, CHECKOUT_DT, RECPT_DT`), agravantes (`HOT_PO_FLAG,
   is_short_ship`) y concordancia con la anotación humana (`REASON_DSC,
   llm_coincide_con_reason`). Preexistente a #158/#161; no se toca aquí.
2. **Tier-1 (8 columnas, #158)** — enriquecimiento con datos ya computados aguas arriba, sin
   llamada LLM adicional: `llm_confianza, VENDOR_NAME, CARRIER_PARTY_NAME, DC_LOC_NAME,
   delay_days_calc, excess_vendor_hrs, excess_carrier_hrs, excess_dc_hrs`. Da contexto de
   entidades responsables y exceso de horas por etapa a la vista individual (Diego).
3. **Tier-2 (9 columnas, #161, PR #174)** — la salida híbrida de la llamada de acción de
   [ARD-16](ARD-16.md) carril 1: `llm_razonamiento, llm_hipotesis, llm_hipotesis_evidencia,
   llm_accion_inmediata, llm_accion_correctiva, llm_accion_preventiva, llm_hipotesis_alt,
   llm_paso_discriminante, llm_confianza_hipotesis`. Requiere `--action-call` (opt-in): sin
   ese flag las 9 columnas salen vacías, no ausentes — el contrato de 33 columnas es estable
   independientemente del flag.
4. **`04_app/README.md:26-37` es la copia operativa vigente** del contrato (verificada exacta
   33/33 contra el CSV real); este ARD es su registro de diseño y trazabilidad, no una tabla
   paralela a mantener sincronizada a mano.
5. **`agente1_raw.txt` es un artefacto derivado paralelo, no parte de `po_output.csv`.**
   Mismo linaje de Fase 3, pero de otra superficie: lo produce
   `llm_integration_network_intelligence_view.py` (gobernada por [ARD-19](ARD-19.md)) a partir
   de los scorecards, no del CSV. Solo lo consume la vista Network Intelligence (persona
   Ravi). Se declara aquí para que el contrato de datos F3→F4 quede completo, aunque su
   contenido (texto narrativo por actor, no columnas tabulares) no encaje en el vocabulario
   tier-1/tier-2.

## Consecuencias

**Positivas:**
- Da una fuente citable para "qué es tier-1/tier-2", con trazabilidad a los issues que los
  decidieron — cierra la brecha que la auditoría de cierre marcó como deuda mayor (H3.12).
- Documenta explícitamente que el contrato de 33 columnas es estable con o sin
  `--action-call` (evita que alguien interprete columnas vacías como columnas faltantes).
- Reconoce formalmente la dependencia de `agente1_raw.txt`, cerrando la afirmación
  incorrecta del SAD sobre el acoplamiento de la vista Network Intelligence.

**Negativas:**
- `03_llm_integration/README.md` sigue con el contrato desactualizado (16/33 columnas); este
  ARD no lo corrige — es trabajo de sincronización documental de otra unidad, con el riesgo
  de que mientras tanto un lector consulte esa página en vez de `04_app/README.md`.
- El vocabulario tier-1/tier-2 nombra solo 17 de las 33 columnas; las 16 del contrato base
  quedan sin numeración propia, lo que puede leerse como inconsistente si alguien espera que
  todo el CSV esté "tierizado".

## Relación con otras decisiones

No supera ningún ARD previo. Formaliza el resultado de #158/#161 (ya implementados). Consume
la salida de **ADR-10** (severidad) y del carril 1 de **ARD-16** (contrato híbrido de tier-2).
Es el contrato que consume [ARD-20](ARD-20.md) (bot de Telegram) además de las dos vistas de
Streamlit de **ADR-09**. Declara la dependencia hacia [ARD-19](ARD-19.md) vía
`agente1_raw.txt`, aunque ese artefacto no forme parte de `po_output.csv`.
