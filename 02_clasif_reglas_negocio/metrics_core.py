# ── Métricas de validación del clasificador (Fase 2) ─────────────────────────
# Funciones PURAS: reciben el DataFrame ya clasificado (salida de classify_po_stages)
# y devuelven números / tablas. NO imprimen y NO mutan la entrada — el notebook (o el
# doc) las llama y presenta. Cubren los dos chequeos de validación de la fase:
#   #46 Stage Classification accuracy — stage_primary (exceso sobre umbral) contra el
#       "gap dominante" del lifecycle (duración bruta del tramo más largo).
#   #47 Reason Code agreement + mismatches — stage_primary contra reason_group_manual
#       (la anotación humana REASON_DSC), y los casos donde los timestamps la contradicen.
import pandas as pd


# Etapas "decidibles": las tres a las que se puede atribuir un retraso con evidencia.
# Indeterminado y On-Time quedan fuera de los denominadores de validación a propósito
# (no son un acierto ni un fallo: son "no hay evidencia para juzgar").
_STAGES = ("Vendor", "Carrier", "DC")

_HRS = 3600.0  # segundos → horas


def _hrs(df: pd.DataFrame, a: str, b: str) -> pd.Series:
    """Horas de a→b (b − a) como Series float. NaN si falta cualquiera de los dos."""
    return (df[b] - df[a]).dt.total_seconds() / _HRS


# ── #46 · Gap dominante + Stage accuracy ─────────────────────────────────────
def gap_dominante(df: pd.DataFrame) -> pd.Series:
    """Etapa del tramo de MAYOR DURACIÓN BRUTA del lifecycle, por PO.

    Métrica INDEPENDIENTE de stage_primary, a propósito: stage_primary mide EXCESO
    sobre el umbral del mentor; el gap dominante mide DURACIÓN cruda. Compararlas (en
    stage_accuracy) valida que la atribución por exceso no se aleja de dónde físicamente
    se fue el tiempo — sin forzar que coincidan (son ejes distintos).

    Secuencia ATRIBUIBLE (decidida con el mentor: "segmentar para que los tiempos muertos
    no entren al cálculo"), validada contra el dataset:
        STA → APPROVED → TRAILER_ARRIVE → CHECKIN → CHECKOUT
    Se EXCLUYE el lead time PO→STA (mediana 192 h: es tiempo de compra normal, no un
    retraso) y todo lo posterior a CHECKOUT (TRAILER_DEPART ocurre DESPUÉS de RECPT en
    el 99.8% de los POs → post-recepción, fuera del ciclo).

    Mapeo tramo→etapa:
        STA→APPROVED            = Vendor   (STA push: la cita se aprobó tarde)
        APPROVED→TRAILER_ARRIVE = Carrier  (tránsito)
        TRAILER_ARRIVE→CHECKIN  = DC (yard) ┐ se consolidan en DC (el responsable es el
        CHECKIN→CHECKOUT        = DC (dock) ┘ mismo: operaciones del CD)

    Máscaras field-level: un tramo no medible (timestamp nulo / inversión temporal) no
    compite. Carrier necesita TRAILER_ARRIVE (_carrier_medible); DC además que la
    secuencia no esté invertida (_dc_medible); Vendor (STA→APPROVED) no necesita tráiler.

    Devuelve una Series con {'Vendor','Carrier','DC'} o NA cuando ningún tramo es medible.
    """
    vendor  = _hrs(df, "STA_DT", "APPROVED_DT").clip(lower=0)
    carrier = _hrs(df, "APPROVED_DT", "TRAILER_ARRIVE_DT").clip(lower=0)
    yard    = _hrs(df, "TRAILER_ARRIVE_DT", "CHECKIN_DT").clip(lower=0)
    dock    = _hrs(df, "CHECKIN_DT", "CHECKOUT_DT").clip(lower=0)

    # Aplicar máscaras: un tramo no medible no debe ganar el argmax → se vuelve NaN.
    carrier = carrier.where(df["_carrier_medible"])
    yard    = yard.where(df["_dc_medible"])
    dock    = dock.where(df["_dc_medible"])

    cand = pd.DataFrame({
        "Vendor":  vendor,
        "Carrier": carrier,
        # DC = el mayor de yard/dock (ambos del mismo responsable); si los dos NaN → NaN.
        "DC":      pd.concat([yard, dock], axis=1).max(axis=1),
    })

    dom = cand.idxmax(axis=1)
    # idxmax sobre una fila toda-NaN devuelve NaN: marcar explícito el "no medible".
    return dom.where(cand.max(axis=1).notna())


def stage_accuracy(df: pd.DataFrame) -> dict:
    """#46 · Coincidencia entre stage_primary (exceso) y gap_dominante (duración bruta).

    Denominador = EVALUABLES: tardíos (delay_days_calc>0) cuyo stage_primary es decidible
    (Vendor/Carrier/DC, no Indeterminado) y cuyo gap dominante es medible. Los
    Indeterminados quedan fuera: el gap dominante no puede juzgar un PO sin tráiler, así
    que contarlos como "fallo" mezclaría "no medible" con "erró".

    Devuelve un dict con el número, el umbral del mentor (>80%), los tres tamaños de
    población (tardíos / confiables / evaluables) y la matriz de contingencia. NO imprime.

    El accuracy alto NO es circular: ambas métricas convergen porque cuando hay STA push
    el tramo STA→APPROVED es de días (domina la duración) y a la vez es la señal de
    exceso de vendor. Los DESACUERDOS son multicausalidad (un PO con push grande Y un
    tramo interno largo) — un hallazgo a documentar, no un error.
    """
    es_tardio = df["delay_days_calc"] > 0
    dom = gap_dominante(df)

    confiable = es_tardio & df["_data_reliable"]
    evaluable = (
        es_tardio
        & dom.notna()
        & df["stage_primary"].isin(_STAGES)
    )

    sub_primary = df.loc[evaluable, "stage_primary"]
    sub_dom = dom[evaluable]
    coincidencias = int((sub_primary == sub_dom).sum())
    n_eval = int(evaluable.sum())
    accuracy = coincidencias / n_eval if n_eval else float("nan")

    matriz = pd.crosstab(sub_primary, sub_dom, dropna=False)

    return {
        "accuracy": accuracy,
        "threshold": 0.80,
        "passes": accuracy > 0.80 if n_eval else False,
        "n_tardios": int(es_tardio.sum()),
        "n_confiables": int(confiable.sum()),
        "n_evaluables": n_eval,
        "n_coincidencias": coincidencias,
        "matriz": matriz,
    }


# ── #47 · Reason Code agreement + mismatches ─────────────────────────────────
def reason_agreement(df: pd.DataFrame) -> dict:
    """#47 · Coincidencia entre stage_primary (cómputo) y reason_group_manual (humano).

    Población CLASIFICABLE: tardíos cuyo stage_primary es decidible (Vendor/Carrier/DC) y
    cuyo reason_group_manual también cae en una de esas tres etapas. Quedan fuera los
    REASON_DSC nulos (2.2% → 'Unknown'), los 'On-Time' y los 'Unknown': no hay etapa
    humana contra la cual comparar. Se reporta el conteo de cada exclusión para transparencia.

    Devuelve dict con el número, los tamaños de población, el desglose de reason_group y
    la matriz de contingencia. NO imprime. (El agreement < 100% es ESPERADO y deseado: la
    anotación humana es ~20% incorrecta; los mismatches son el insumo de Fase 3.)
    """
    es_tardio = df["delay_days_calc"] > 0
    clasificable = (
        es_tardio
        & df["stage_primary"].isin(_STAGES)
        & df["reason_group_manual"].isin(_STAGES)
    )

    sub_primary = df.loc[clasificable, "stage_primary"]
    sub_reason = df.loc[clasificable, "reason_group_manual"]
    coincidencias = int((sub_primary == sub_reason).sum())
    n_clasif = int(clasificable.sum())
    agreement = coincidencias / n_clasif if n_clasif else float("nan")

    return {
        "agreement": agreement,
        "n_tardios": int(es_tardio.sum()),
        "n_clasificable": n_clasif,
        "n_coincidencias": coincidencias,
        "n_mismatches": n_clasif - coincidencias,
        "n_reason_null": int(df.loc[es_tardio, "REASON_DSC"].isna().sum())
        if "REASON_DSC" in df.columns else None,
        "reason_group_breakdown": df.loc[es_tardio, "reason_group_manual"].value_counts(),
        "matriz": pd.crosstab(sub_primary, sub_reason, dropna=False),
    }


def select_mismatches(df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """#47 · Los `n` mismatches más fuertes donde el cómputo discrepa del reason humano.

    Un mismatch es un PO clasificable cuyo stage_primary ≠ reason_group_manual: los
    timestamps (cómputo) atribuyen el retraso a una etapa distinta de la que anotó el
    staff. Son la EVIDENCIA de la tesis del proyecto (el cómputo temporal es más preciso
    que la anotación humana) y el insumo few-shot de Fase 3.

    "Fuerza de señal" = la magnitud del exceso de la etapa que el cómputo eligió
    (excess_*_hrs de stage_primary). Ordenar por ella pone arriba los casos más
    contundentes (p.ej. STA push de 5 días que el humano atribuyó a "yard congestion").

    Devuelve un DataFrame con PO_NBR, ambas etiquetas, REASON_DSC, los excess_*_hrs y la
    fuerza de señal — listo para presentar/exportar. NO imprime.
    """
    es_tardio = df["delay_days_calc"] > 0
    clasificable = (
        es_tardio
        & df["stage_primary"].isin(_STAGES)
        & df["reason_group_manual"].isin(_STAGES)
    )
    mis = clasificable & (df["stage_primary"] != df["reason_group_manual"])

    cols = [
        "PO_NBR", "stage_primary", "dc_substage", "reason_group_manual", "REASON_DSC",
        "excess_vendor_hrs", "excess_carrier_hrs", "excess_yard_hrs",
        "excess_dock_hrs", "excess_dc_hrs", "delay_days_calc",
    ]
    cols = [c for c in cols if c in df.columns]
    out = df.loc[mis, cols].copy()

    # Fuerza de señal = exceso de la etapa que el cómputo eligió.
    exc_de_etapa = {
        "Vendor": "excess_vendor_hrs",
        "Carrier": "excess_carrier_hrs",
        "DC": "excess_dc_hrs",
    }
    out["senal_computo_hrs"] = [
        row[exc_de_etapa[row["stage_primary"]]] for _, row in out.iterrows()
    ]

    out = out.sort_values("senal_computo_hrs", ascending=False)
    return out.head(n).reset_index(drop=True)
