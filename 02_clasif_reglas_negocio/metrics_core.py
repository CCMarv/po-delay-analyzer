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
    que la anotación humana) y están disponibles como POSIBLE insumo few-shot para Fase 3.
    Estado actual: el prompt de F3 es ZERO-SHOT — todavía no consume estos ejemplos;
    cablearlos como few-shot es decisión de diseño de prompt, pendiente en Fase 3.

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


# ── Análisis del umbral de activación de Vendor (consulta mentor 06-17) ───────
# Contexto: hoy Vendor dispara con CUALQUIER STA push (APPROVED_DT > STA_DT), sin
# umbral, mientras carrier/DC exigen 8/4/6 h. El mentor señaló esa "asimetría de
# construcción" (vendor absorbe por default) y mandó darle a vendor un umbral propio,
# decidido por análisis de sensibilidad. Estas funciones PRODUCEN LA EVIDENCIA para
# elegir ese umbral; NO modifican el clasificador (eso espera a la decisión del umbral).
#
# Cómo se simula un corte sin tocar _etapa_primaria: meter un umbral de vendor es la
# MISMA operación que ya se aplica a carrier/DC — restar el umbral antes del max(0,·).
# El df clasificado ya trae el push completo en excess_vendor_hrs (umbral implícito 0) y
# los excesos de carrier/dc; aquí solo re-restamos el umbral candidato a vendor y
# re-hacemos el argmax. Fidelidad garantizada por el sanity check: el escenario 0 h debe
# reproducir EXACTO el reparto del clasificador real.

# Orden de etapas para el desempate del argmax. Réplica fiel del idxmax de
# _etapa_primaria (primera columna gana el empate) Y decisión de dominio: ante exceso de
# igual magnitud se atribuye a VENDOR, porque un push tardío es causa probable de la
# disrupción aguas abajo (propaga presión sobre carrier/DC).
_STAGE_ORDER = ["Vendor", "Carrier", "DC"]


def _gap_vendor_hrs(df: pd.DataFrame) -> pd.Series:
    """STA push en horas = max(0, −appt_lead_days*24). Es el gap_vendor CRUDO (umbral 0),
    idéntico a excess_vendor_hrs del clasificador actual. Se recomputa aquí (en vez de leer
    la columna) para que el análisis no dependa de que el df ya esté clasificado con un
    umbral concreto: el insumo es appt_lead_days, que viene del pipeline."""
    return (-df["appt_lead_days"] * 24).clip(lower=0).fillna(0)


def _simular_corte(df: pd.DataFrame, thr_vendor: float) -> pd.Series:
    """Re-clasifica stage_primary COMO SI vendor tuviera umbral `thr_vendor`, sin tocar
    el clasificador. Reusa los excesos de carrier/DC que el df ya trae (no cambian con el
    umbral de vendor) y re-resta el umbral solo a vendor. Replica la intercepción de
    Indeterminado de _etapa_primaria, ahora con el umbral de vendor incorporado:
      - 'sin_datos'           = tardío no decidible (ningún tramo medible).
      - 'sin_causa_dominante' = tardío decidible pero ningún exceso > 0 (con el umbral).
    Devuelve una Series sobre TODO el df: {Vendor,Carrier,DC,sin_datos,sin_causa_dominante}
    en los tardíos, 'On-Time' en el resto.
    """
    exc_vendor  = (_gap_vendor_hrs(df) - thr_vendor).clip(lower=0)   # ← el único cambio
    exc_carrier = df["excess_carrier_hrs"].fillna(0)
    exc_dc      = df["excess_dc_hrs"].fillna(0)

    excesos = pd.DataFrame(
        {"Vendor": exc_vendor, "Carrier": exc_carrier, "DC": exc_dc}
    )[_STAGE_ORDER]                       # orden fija el desempate hacia Vendor
    ganador = excesos.idxmax(axis=1)
    algun_exceso = excesos.max(axis=1) > 0

    es_tardio = df["delay_days_calc"] > 0
    decidible = df["_carrier_medible"] | df["_dc_medible"]

    stage = pd.Series("On-Time", index=df.index, dtype="object")
    stage = stage.mask(es_tardio & decidible & algun_exceso, ganador)
    stage = stage.mask(es_tardio & ~decidible, "sin_datos")
    stage = stage.mask(es_tardio & decidible & ~algun_exceso, "sin_causa_dominante")
    return stage


def distribucion_gap_vendor(df: pd.DataFrame) -> dict:
    """Distribución del gap_vendor (STA push, horas) dentro de los tardíos con push>0.

    Es el bloque que el mentor pidió EXPLÍCITO: si predominan gaps chicos, el 62.8% de
    vendor es artefacto de la regla de disparo; si son de varios días, el dato lo soporta.
    No decide nada — describe. Devuelve percentiles, el desglose por bins de la malla de
    umbrales, y la serie cruda (para el histograma del notebook). NO imprime.
    """
    es_tardio = df["delay_days_calc"] > 0
    gap = _gap_vendor_hrs(df)[es_tardio]
    push = gap[gap > 0]

    pctiles = push.describe(percentiles=[.1, .25, .5, .75, .9])
    # Conteo por banda de la malla: cuántos push caen en cada intervalo de horas.
    bins = [0, 6, 12, 18, 24, 48, 72, float("inf")]
    etiquetas = ["0-6", "6-12", "12-18", "18-24", "24-48", "48-72", "72+"]
    por_banda = pd.cut(push, bins=bins, labels=etiquetas, right=False).value_counts().sort_index()

    return {
        "n_tardios": int(es_tardio.sum()),
        "n_push_positivo": int((gap > 0).sum()),
        "percentiles_hrs": pctiles,
        "mediana_dias": float(push.median() / 24) if len(push) else float("nan"),
        "por_banda": por_banda,
        "gap_hrs": push,          # serie cruda para el histograma
    }


def sensibilidad_vendor(df: pd.DataFrame, escenarios=(0, 6, 12, 18, 24, 48, 72)) -> pd.DataFrame:
    """#sensibilidad · Reparto de stage_primary por cada umbral candidato de vendor.

    Espejo de la sensibilidad de carrier (§5.2): re-simula cada corte sin tocar el
    clasificador (ver _simular_corte) y tabula, sobre los TARDÍOS, el reparto resultante.
    El escenario 0 h es la LÍNEA BASE (= método actual sin umbral) y sirve de sanity check:
    debe reproducir el reparto real del clasificador.

    Devuelve un DataFrame indexado por umbral, una fila por escenario, con columnas:
    Vendor / Carrier / DC / sin_datos / sin_causa_dominante (conteos) + pct_vendor + n_tardios.
    NO imprime. El usuario lee esta tabla para elegir vendor_gap_hrs.
    """
    es_tardio = df["delay_days_calc"] > 0
    n_tardios = int(es_tardio.sum())
    cats = ["Vendor", "Carrier", "DC", "sin_datos", "sin_causa_dominante"]

    filas = {}
    for thr in escenarios:
        stage = _simular_corte(df, float(thr))[es_tardio]
        conteo = stage.value_counts()
        fila = {c: int(conteo.get(c, 0)) for c in cats}
        fila["pct_vendor"] = round(100 * fila["Vendor"] / n_tardios, 1) if n_tardios else float("nan")
        fila["n_tardios"] = n_tardios
        filas[thr] = fila

    out = pd.DataFrame.from_dict(filas, orient="index")[cats + ["pct_vendor", "n_tardios"]]
    out.index.name = "umbral_hrs"
    return out


def destino_migracion_vendor(df: pd.DataFrame, escenarios=(6, 12, 18, 24, 48, 72)) -> pd.DataFrame:
    """I1 · ¿A dónde van los POs que dejan de ser Vendor al subir el umbral?

    Compara cada corte contra la BASE (0 h): de los que eran Vendor en base, cuántos pasan
    a Carrier / DC / sin_causa_dominante con el umbral `thr`. Distingue REATRIBUCIÓN real
    (migran a otra etapa con exceso propio → seguramente nunca fueron vendor) de RETRASO
    DIFUSO (migran a sin_causa_dominante → push chico sin causa clara). NO imprime.
    """
    es_tardio = df["delay_days_calc"] > 0
    base = _simular_corte(df, 0.0)
    era_vendor = es_tardio & (base == "Vendor")

    destinos = ["Carrier", "DC", "sin_causa_dominante", "sin_datos"]
    filas = {}
    for thr in escenarios:
        stage = _simular_corte(df, float(thr))
        migran = era_vendor & (stage != "Vendor")
        conteo = stage[migran].value_counts()
        fila = {d: int(conteo.get(d, 0)) for d in destinos}
        fila["total_migran"] = int(migran.sum())
        fila["siguen_vendor"] = int((era_vendor & (stage == "Vendor")).sum())
        filas[thr] = fila

    out = pd.DataFrame.from_dict(filas, orient="index")[["total_migran", "siguen_vendor"] + destinos]
    out.index.name = "umbral_hrs"
    return out


def robustez_vendor(df: pd.DataFrame, escenarios=(0, 6, 12, 18, 24, 48, 72)) -> pd.DataFrame:
    """I2 · De los que SIGUEN siendo Vendor en cada corte, ¿cuántos son multicausales?

    Multicausal = el PO tiene, ADEMÁS del push de vendor, exceso en carrier o DC. El mentor
    notó "solo 2 multicausales" con el método actual (0 h); esto verifica si esa cifra
    aguanta al subir el umbral (al endurecer vendor, los que sobreviven deberían ser los de
    push grande, no necesariamente más multicausales). NO imprime.
    """
    es_tardio = df["delay_days_calc"] > 0
    otro_exceso = (df["excess_carrier_hrs"].fillna(0) > 0) | (df["excess_dc_hrs"].fillna(0) > 0)

    filas = {}
    for thr in escenarios:
        stage = _simular_corte(df, float(thr))
        es_vendor = es_tardio & (stage == "Vendor")
        n_v = int(es_vendor.sum())
        n_multi = int((es_vendor & otro_exceso).sum())
        filas[thr] = {
            "n_vendor": n_v,
            "n_multicausal": n_multi,
            "pct_multicausal": round(100 * n_multi / n_v, 1) if n_v else float("nan"),
        }
    out = pd.DataFrame.from_dict(filas, orient="index")[["n_vendor", "n_multicausal", "pct_multicausal"]]
    out.index.name = "umbral_hrs"
    return out


def agreement_por_umbral(df: pd.DataFrame, escenarios=(0, 6, 12, 18, 24, 48, 72)) -> pd.DataFrame:
    """I3 · Agreement con la anotación humana (REASON_DSC) por cada umbral de vendor.

    Re-simula el corte y recalcula el agreement contra reason_group_manual (mismo criterio
    que reason_agreement: población clasificable = tardíos con stage decidible y reason en
    {Vendor,Carrier,DC}). Si meter umbral SUBE el agreement, es señal de que corrige
    sobreatribución de vendor (acerca el cómputo a lo que el humano anotó); si lo BAJA,
    cuidado. Cross-check barato y defendible ante el mentor. NO imprime.

    Nota: el agreement < 100% es esperado (la anotación humana es ~20% incorrecta); aquí
    interesa la DIRECCIÓN del cambio entre umbrales, no el valor absoluto.
    """
    es_tardio = df["delay_days_calc"] > 0
    tiene_reason = "reason_group_manual" in df.columns
    filas = {}
    for thr in escenarios:
        stage = _simular_corte(df, float(thr))
        if not tiene_reason:
            filas[thr] = {"n_clasificable": 0, "n_coincidencias": 0, "agreement": float("nan")}
            continue
        clasificable = (
            es_tardio
            & stage.isin(_STAGES)
            & df["reason_group_manual"].isin(_STAGES)
        )
        n = int(clasificable.sum())
        coin = int((stage[clasificable] == df.loc[clasificable, "reason_group_manual"]).sum())
        filas[thr] = {
            "n_clasificable": n,
            "n_coincidencias": coin,
            "agreement": round(100 * coin / n, 1) if n else float("nan"),
        }
    out = pd.DataFrame.from_dict(filas, orient="index")[["n_clasificable", "n_coincidencias", "agreement"]]
    out.index.name = "umbral_hrs"
    return out


def umbral_vs_mismo_dia(df: pd.DataFrame, umbral_hrs: float = 24.0) -> dict:
    """I-extra · Valida la teoría del usuario: ¿"gap > umbral_hrs" captura los mismos POs
    que "APPROVED cae en distinto día calendario que STA"?

    Dos lecturas de "tolerable si llega el mismo día":
      (A) umbral en horas       → gap_vendor > umbral_hrs   (lo comparable con carrier)
      (B) mismo día calendario  → APPROVED_DT.date() != STA_DT.date()
    Si (A) y (B) capturan casi los mismos POs, la teoría queda validada y se elige la más
    explicable. Reporta la matriz de solapamiento sobre los tardíos con push>0. NO imprime.
    """
    es_tardio = df["delay_days_calc"] > 0
    gap = _gap_vendor_hrs(df)
    universo = es_tardio & (gap > 0)

    por_horas = gap > umbral_hrs
    # Distinto día calendario entre APPROVED y STA (solo donde ambos existen).
    distinto_dia = df["APPROVED_DT"].dt.normalize() != df["STA_DT"].dt.normalize()

    a = por_horas[universo]
    b = distinto_dia[universo].fillna(False)
    matriz = pd.crosstab(a.rename(f"gap>{umbral_hrs:g}h"), b.rename("distinto_dia"))
    coincide = int((a == b).sum())
    n = int(universo.sum())
    return {
        "umbral_hrs": umbral_hrs,
        "n_universo": n,
        "n_coinciden": coincide,
        "pct_coinciden": round(100 * coincide / n, 1) if n else float("nan"),
        "n_solo_horas": int((a & ~b).sum()),
        "n_solo_dia": int((~a & b).sum()),
        "matriz": matriz,
    }
