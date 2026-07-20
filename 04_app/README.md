# Fase 4 — Demo + evaluación final (app)

> Documento de la fase. Por ahora **solo en español**; la versión en inglés se añade al
> cierre del desarrollo.

La Fase 4 presenta los resultados del análisis a dos perfiles de usuario. No produce
análisis nuevo: **lee** el artefacto de la Fase 3 y lo muestra. La app es Streamlit; toda
la lógica de limpieza (F1), clasificación (F2) y explicación (F3) ya ocurrió aguas arriba.

## 1. Entrada: el contrato F3→F4 (#100)

El input primario de la app es el contrato F3→F4:

```
data/processed/po_output.csv
```

Lo genera la Fase 3 (`03_llm_integration/llm_integration.py`, `export_deliverable_csv`).
La app **no recomputa** Fase 1/2 ni vuelve a llamar al LLM: solo lee artefactos ya
producidos aguas arriba. El contrato del CSV está blindado por `tests/test_handoff_f3.py`.

La vista agregada (§2) consume además scorecards por entidad y la síntesis ejecutiva de red
(`agente1_raw.txt`): indicadores y narrativa derivados que se generan offline/vía LLM (§3), no
forman parte del contrato del mentor, son regenerables y quedan fuera del control de
versiones. `agente1_raw.txt` es una dependencia real de Fase 3→Fase 4, no un artefacto
aislado ([ARD-21](../documentation/decisiones/ARD-21.md)).

Estructura del CSV (las cinco del mentor primero, en orden; luego soporte para la app):

| Bloque | Columnas | Para qué |
|---|---|---|
| Contrato del mentor | `PO_NBR, stage, severity, explanation, action` | Identidad + diagnóstico (`severity`, `explanation`, `action` los emite el LLM — ver ADR-10) |
| Timeline | `PO_DT, STA_DT, APPROVED_DT, TRAILER_ARRIVE_DT, CHECKIN_DT, CHECKOUT_DT, RECPT_DT` | Dibujar el recorrido del PO |
| Agravantes | `HOT_PO_FLAG, is_short_ship` | Marcar urgencia / envío incompleto |
| Concordancia | `REASON_DSC, llm_coincide_con_reason` | Mostrar si el diagnóstico coincide con la anotación humana |
| Enriquecimiento tier 1 | `llm_confianza, VENDOR_NAME, CARRIER_PARTY_NAME, DC_LOC_NAME, delay_days_calc, excess_vendor_hrs, excess_carrier_hrs, excess_dc_hrs` | Confianza del diagnóstico, entidades responsables y exceso de horas por etapa (contexto de la vista individual) |
| Diagnóstico diferencial tier 2 | `llm_razonamiento, llm_hipotesis, llm_hipotesis_evidencia, llm_accion_inmediata, llm_accion_correctiva, llm_accion_preventiva, llm_hipotesis_alt, llm_paso_discriminante, llm_confianza_hipotesis` | Salida híbrida de ARD-16: hipótesis principal/alternativa, evidencia, paso discriminante, plan escalonado y 2ª confianza |

Alcance de filas: solo POs tardíos (`delay_days_calc > 0`).

Si una vista necesita un dato que el CSV no trae, se amplía el contrato (#100) en la Fase 3,
**no** se recomputa en la app.

## 2. Salida: dos vistas, dos personas (ADR-09)

El diseño se organiza por **modo de consumo**, no por entidad de la cadena:

- **Vista individual — persona Diego (#102).** Consulta de un PO: timeline, etapa
  responsable, explicación y acción del LLM, severidad y concordancia con el REASON_DSC.
  Consume la prosa del LLM.
- **Vista agregada — persona Ravi (#103).** Reporte por lote: métricas, reparto por etapa,
  drill-down. Consume agregados, no prosa.

Detalle de las personas en `../documentation/user_personas.md`.

Streamlit no es el único canal: `telegram_bot/` ([ADR-20](../documentation/decisiones/ARD-20.md))
expone un segundo front-end con comandos fijos por persona (`/po`, `/timeline`, `/alertas`,
`/hot` para Diego; `/kpi`, `/scorecards`, `/distribucion`, `/mismatches` para Ravi) sobre el
mismo contrato F3→F4 — sin razonamiento libre ni llamada a LLM en tiempo de consulta, distinto
del chatbot conversacional diferido (#160). Cómo correr el bot: `telegram_bot/README.md`.

## 3. Cómo correr

```bash
# 1. Generar el artefacto de entrada (Fase 3), si no existe:
#    produce data/processed/po_output.csv
#    --action-call (opt-in) puebla las columnas del diagnóstico diferencial tier 2
#    (#161/#174); sin ese flag esas columnas salen vacías.
python 03_llm_integration/llm_integration.py --backend openai --action-call   # u otro backend

# 2. Generar los scorecards por entidad (offline, sin API):
#    produce data/processed/scorecards/reporte_{vendors,carriers,dcs}.json
python 03_llm_integration/scorecard_core.py \
    data/processed/df_classified.csv data/processed/scorecards
#    En Windows, si la consola falla con emojis, anteponer PYTHONUTF8=1

# 3. Generar la síntesis ejecutiva de red (GASTA API, ADR-19), input de Network
#    Intelligence: produce data/processed/agente1_raw.txt. Debe correr después del
#    paso 2 (lee esos scorecards). Requiere --actor all para consolidar el reporte.
python 03_llm_integration/llm_integration_network_intelligence_view.py --actor all

# 4. Lanzar la app:
streamlit run 04_app/app.py
```

## 4. Estado

La app lee tres artefactos, todos regenerables y fuera del control de versiones:

- `data/processed/po_output.csv` — contrato base + tier-1/tier-2 (§1, ARD-21), input
  primario de ambas vistas.
- `data/processed/scorecards/reporte_{vendors,carriers,dcs}.json` — indicadores por
  entidad que alimentan la vista agregada. Los produce offline
  `03_llm_integration/scorecard_core.py` sobre `df_classified.csv`; la app los lee, no
  recomputa la capa estadística ni llama a ninguna API.
- `data/processed/agente1_raw.txt` — síntesis ejecutiva de red por actor. La produce
  `03_llm_integration/llm_integration_network_intelligence_view.py --actor all` (ADR-19,
  gasta API) a partir de los scorecards; la consume Network Intelligence, no la app en
  general.

Las dos vistas, individual (#163) y agregada (#164), están reconstruidas sobre el sistema
de diseño de la fase. Incorporado en el lote de elevación a calidad de deployment:

- Panel de diagnóstico diferencial tier 2 en la vista individual (#175/#176): hipótesis
  principal/alternativa, paso discriminante y plan escalonado.
- Tema claro/oscuro adaptado a las gráficas Plotly (#186, ARD-17).
- Corrección de la navegación del landing hacia las vistas (#187).

## Referencias

- Contrato de handoff: issue #100 · `../tests/test_handoff_f3.py`
- Decisiones: `../documentation/decisiones/ARD-09.md` (personas) · `ARD-10.md` (severidad)
- Personas: `../documentation/user_personas.md`
