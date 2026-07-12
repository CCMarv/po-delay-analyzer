from __future__ import annotations

"""
scorecard_core.py
==================
Ubicado en: /03_llm_integration/scorecard_core.py
Lee df_classified.csv desde /data/processed/ por defecto.
"""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

# ─────────────────────────────────────────────────────────────────────────
# RESOLUCIÓN DE RUTAS (RAÍZ DEL REPO)
# ─────────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent  # 03_llm_integration → repo_root
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
CSV_DEFAULT_PATH = DATA_PROCESSED / "df_classified.csv"


# ─────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE COLUMNAS
# ─────────────────────────────────────────────────────────────────────────
REQUIRED_COLUMNS = [
    "VENDOR_NAME",
    "CARRIER_PARTY_NAME",
    "DC_LOC_NAME",
    "stage_primary",
    "delay_days_calc",
    "_resched_",
    "YARD_DROP_FL",
    "excess_vendor_hrs",
    "excess_carrier_hrs",
    "excess_dc_hrs",
    "total_dc_hrs",
    "excess_yard_hrs",
]

# ─────────────────────────────────────────────────────────────────────────
# Configuración por tipo de actor
# ─────────────────────────────────────────────────────────────────────────
ACTOR_CONFIG = {
    "vendors": dict(
        entity_col="VENDOR_NAME",
        stage_label="Vendor",
        excess_col="excess_vendor_hrs",
        exclude_yard_drop=False,
        use_dwell=False,
    ),
    "carriers": dict(
        entity_col="CARRIER_PARTY_NAME",
        stage_label="Carrier",
        excess_col="excess_carrier_hrs",
        exclude_yard_drop=False,
        use_dwell=False,
    ),
    "dcs": dict(
        entity_col="DC_LOC_NAME",
        stage_label="DC",
        excess_col="excess_dc_hrs",
        exclude_yard_drop=False,
        use_dwell=True,
        dwell_col="total_dc_hrs",
        yard_excess_col="excess_yard_hrs",
    ),
}

BUSINESS_PRIOR_WEIGHTS = {
    "Delay_Prom": 0.40,
    "Excess_por_PO": 0.30,
    "Tasa_Reschedule": 0.15,
    "Tasa_Responsabilidad": 0.15,
}
MAX_WEIGHT_ADJUST = 0.30
DC_SHRINKAGE_K = 0.5


# ─────────────────────────────────────────────────────────────────────────
# Utilidades estadísticas
# ─────────────────────────────────────────────────────────────────────────
def _severity_two_layer(values: pd.Series) -> Dict[str, float]:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    vals = vals[vals >= 0]
    if len(vals) == 0:
        return {"typical": 0.0, "extreme": 0.0, "final": 0.0}
    p95 = vals.quantile(0.95)
    typical = float(vals.clip(upper=p95).mean())
    p90 = vals.quantile(0.90)
    tail = vals[vals >= p90]
    extreme = float(tail.mean()) if len(tail) else typical
    return {"typical": typical, "extreme": extreme, "final": max(typical, extreme)}


def _credibility_from_raw(group_series: Dict[str, pd.Series], fixed_k: Optional[float] = None) -> Dict:
    ns = {e: int(s.dropna().shape[0]) for e, s in group_series.items()}
    within_vars = [s.dropna().var(ddof=1) for s in group_series.values() if s.dropna().shape[0] > 1]
    var_within = float(np.mean(within_vars)) if within_vars else 0.0

    entity_means = {e: (float(s.dropna().mean()) if ns[e] > 0 else np.nan) for e, s in group_series.items()}
    valid = {e: m for e, m in entity_means.items() if not np.isnan(m)}
    
    if fixed_k is not None:
        k = fixed_k
        var_between = var_within / k if k > 0 else 1e-9
        var_between_zero = False
        if len(valid) > 1:
            raw_between = np.var(list(valid.values()), ddof=1)
        else:
            raw_between = var_between
    else:
        if len(valid) > 1:
            mean_n = float(np.mean([ns[e] for e in valid]))
            raw_between = np.var(list(valid.values()), ddof=1) - (var_within / max(mean_n, 1))
            var_between = max(raw_between, 1e-9)
            var_between_zero = raw_between <= 0
        else:
            var_between = 1e-9
            var_between_zero = True
        k = var_within / var_between if var_between > 0 else 0.0

    weights = [ns[e] for e in valid]
    grand_mean = float(np.average(list(valid.values()), weights=weights)) if valid else 0.0
    z = {e: (ns[e] / (ns[e] + k) if (ns[e] + k) > 0 else 0.0) for e in group_series}
    
    return {
        "ns": ns,
        "z": z,
        "k": float(k),
        "grand_mean": grand_mean,
        "var_within": var_within,
        "var_between": var_between,
        "var_between_zero": var_between_zero,
        "_diagnostico": f"var_between={var_between:.4f}, var_within={var_within:.4f}, k={k:.2f}"
    }


def _rate_efron_morris(df: pd.DataFrame, entity_col: str, flag_col: str) -> Tuple[Dict, float]:
    g = df.groupby(entity_col)[flag_col].agg(["sum", "count"])
    p_bar = float(g["sum"].sum() / g["count"].sum()) if g["count"].sum() > 0 else 0.0

    raw_rates = (g["sum"] / g["count"]).replace([np.inf, -np.inf], np.nan).dropna()
    if len(raw_rates) > 1:
        sampling_var_mean = float(np.mean(raw_rates * (1 - raw_rates) / g.loc[raw_rates.index, "count"]))
        var_between = max(float(np.var(raw_rates, ddof=1)) - sampling_var_mean, 1e-6)
    else:
        var_between = 1e-6

    out = {}
    for e, row in g.iterrows():
        n, x = int(row["count"]), int(row["sum"])
        p = x / n if n > 0 else p_bar
        var_sampling = p * (1 - p) / n if n > 0 else var_between
        b = var_sampling / (var_sampling + var_between) if (var_sampling + var_between) > 0 else 0.0
        shrunk = b * p_bar + (1 - b) * p
        out[e] = {"n": n, "raw_rate": float(p), "shrunk_rate": float(shrunk), "b_shrink": float(b)}
    return out, p_bar


def _percentile_rank_0_100(values: Dict[str, float]) -> Dict[str, float]:
    s = pd.Series(values)
    ranked = s.rank(pct=True) * 100
    return ranked.to_dict()


def _po_level_risk_cuts(df: pd.DataFrame, delay_col: str) -> Tuple[float, float, Dict]:
    vals = df[delay_col].fillna(0).clip(lower=0).values.reshape(-1, 1)
    try:
        gmm = GaussianMixture(n_components=3, random_state=42, n_init=5)
        labels = gmm.fit_predict(vals)
        order = np.argsort(gmm.means_.flatten())
        rank_of_label = {lab: rank for rank, lab in enumerate(order)}
        ranks = np.array([rank_of_label[l] for l in labels])
        pct = pd.Series(vals.flatten()).rank(pct=True).values * 100
        cut_low = float(pct[ranks == 0].max()) if (ranks == 0).any() else 33.3
        cut_high = float(pct[ranks <= 1].max()) if (ranks <= 1).any() else 66.7
        po_percentiles = {idx: float(pct[i]) for i, idx in enumerate(df.index)}
    except Exception:
        cut_low, cut_high = 33.3, 66.7
        po_percentiles = {idx: float(pd.Series(vals.flatten()).rank(pct=True).values[i]) 
                         for i, idx in enumerate(df.index)}
    cut_low = float(np.clip(cut_low, 5, 90))
    cut_high = float(np.clip(cut_high, cut_low + 1, 95))
    return cut_low, cut_high, po_percentiles


def _classify_risk(score: float, cut_low: float, cut_high: float) -> str:
    if pd.isna(score):
        return "Sin datos"
    if score <= cut_low:
        return "Bajo"
    if score <= cut_high:
        return "Medio"
    return "Alto"


def _ridge_weight_adjustment(df: pd.DataFrame, excess_col: str, stage_label: str, delay_col: str) -> Dict[str, float]:
    sub_priors = {k: v for k, v in BUSINESS_PRIOR_WEIGHTS.items() if k != "Delay_Prom"}
    band = sum(sub_priors.values())

    X = pd.DataFrame({
        "Excess_por_PO": df[excess_col].fillna(0.0),
        "Tasa_Reschedule": df["_resched_"].fillna(0).astype(float),
        "Tasa_Responsabilidad": (df["stage_primary"] == stage_label).astype(float),
    })
    y = df[delay_col].fillna(0.0).clip(lower=0)

    try:
        Xs = StandardScaler().fit_transform(X.values)
        ridge = Ridge(alpha=1.0, random_state=42)
        ridge.fit(Xs, y.values)
        abs_coef = np.abs(ridge.coef_)
        if abs_coef.sum() == 0:
            data_weights = np.array(list(sub_priors.values()))
        else:
            data_weights = abs_coef / abs_coef.sum() * band
    except Exception:
        data_weights = np.array(list(sub_priors.values()))

    keys = list(sub_priors.keys())
    adjusted = {}
    for i, k in enumerate(keys):
        lo, hi = sub_priors[k] * (1 - MAX_WEIGHT_ADJUST), sub_priors[k] * (1 + MAX_WEIGHT_ADJUST)
        adjusted[k] = float(np.clip(data_weights[i], lo, hi))
    total_adj = sum(adjusted.values())
    adjusted = {k: v / total_adj * band for k, v in adjusted.items()}
    adjusted["Delay_Prom"] = BUSINESS_PRIOR_WEIGHTS["Delay_Prom"]
    return adjusted


# ─────────────────────────────────────────────────────────────────────────
# Construcción del scorecard por tipo de actor
# ─────────────────────────────────────────────────────────────────────────
def _build_actor_scorecard(df: pd.DataFrame, actor_key: str, 
                          po_delay_percentiles: Dict,
                          cut_low_global: float,
                          cut_high_global: float,
                          delay_col: str) -> Dict[str, Dict]:
    cfg = ACTOR_CONFIG[actor_key]
    entity_col, stage_label, excess_col = cfg["entity_col"], cfg["stage_label"], cfg["excess_col"]
    use_dwell = cfg.get("use_dwell", False)

    entities = sorted(df[entity_col].dropna().unique())
    root_cause_mask = df["stage_primary"] == stage_label

    # ── Delay_Prom ──
    delay_groups = {e: g[delay_col] for e, g in df[root_cause_mask].groupby(entity_col)}
    for e in entities:
        delay_groups.setdefault(e, pd.Series(dtype=float))
    delay_cred = _credibility_from_raw(delay_groups)
    delay_layers = {e: _severity_two_layer(s) for e, s in delay_groups.items()}
    delay_finals = {e: delay_layers[e]["final"] for e in entities}
    n_rc = delay_cred["ns"]
    valid_e = [e for e in entities if n_rc.get(e, 0) > 0]
    delay_grand_mean = (
        float(np.average([delay_finals[e] for e in valid_e], weights=[n_rc[e] for e in valid_e]))
        if valid_e else 0.0
    )
    delay_shrunk = {
        e: delay_cred["z"].get(e, 0.0) * delay_finals[e] + (1 - delay_cred["z"].get(e, 0.0)) * delay_grand_mean
        for e in entities
    }

    # ── Excess_por_PO ──
    excess_finals = {e: 0.0 for e in entities}
    excess_cred_info = None
    temp_excess_col = excess_col

    if use_dwell:
        # DCs: calcular Dwell_Time_Net
        if "total_dc_hrs" not in df.columns:
            df["_dwell_net"] = df["excess_yard_hrs"].fillna(0) + df["excess_dock_hrs"].fillna(0)
        else:
            df["_dwell_net"] = df["total_dc_hrs"] - df["excess_yard_hrs"].fillna(0)
        
        df["_dwell_net"] = df["_dwell_net"].clip(lower=0)
        
        dwell_groups = {e: g["_dwell_net"] for e, g in df.groupby(entity_col)}
        for e in entities:
            dwell_groups.setdefault(e, pd.Series(dtype=float))
        
        dwell_cred = _credibility_from_raw(dwell_groups, fixed_k=DC_SHRINKAGE_K)
        dwell_layers = {e: _severity_two_layer(s) for e, s in dwell_groups.items()}
        excess_finals = {e: dwell_layers[e]["final"] for e in entities}
        
        n_dw = dwell_cred["ns"]
        valid_dw = [e for e in entities if n_dw.get(e, 0) > 0]
        dwell_grand_mean = (
            float(np.average([excess_finals[e] for e in valid_dw], weights=[n_dw[e] for e in valid_dw]))
            if valid_dw else 0.0
        )
        excess_shrunk = {
            e: dwell_cred["z"].get(e, 0.0) * excess_finals[e] + (1 - dwell_cred["z"].get(e, 0.0)) * dwell_grand_mean
            for e in entities
        }
        excess_cred_info = dwell_cred
        temp_excess_col = "_dwell_net"
    else:
        # Vendors y Carriers: usar excess_*_hrs
        if cfg.get("exclude_yard_drop", False):
            excess_mask = df["YARD_DROP_FL"] != 1
        else:
            excess_mask = pd.Series(True, index=df.index)
        excess_groups = {e: g[excess_col] for e, g in df[excess_mask].groupby(entity_col)}
        for e in entities:
            excess_groups.setdefault(e, pd.Series(dtype=float))
        excess_cred = _credibility_from_raw(excess_groups)
        excess_layers = {e: _severity_two_layer(s) for e, s in excess_groups.items()}
        excess_finals = {e: excess_layers[e]["final"] for e in entities}
        
        n_ex = excess_cred["ns"]
        valid_ex = [e for e in entities if n_ex.get(e, 0) > 0]
        excess_grand_mean = (
            float(np.average([excess_finals[e] for e in valid_ex], weights=[n_ex[e] for e in valid_ex]))
            if valid_ex else 0.0
        )
        excess_shrunk = {
            e: excess_cred["z"].get(e, 0.0) * excess_finals[e] + (1 - excess_cred["z"].get(e, 0.0)) * excess_grand_mean
            for e in entities
        }
        excess_cred_info = excess_cred

    # ── Tasa_Reschedule ──
    resched_info, resched_pool_rate = _rate_efron_morris(df, entity_col, "_resched_")

    # ── Tasa_Responsabilidad ──
    resp_info, resp_pool_rate = _rate_efron_morris(
        df.assign(_es_causa_raiz=root_cause_mask.astype(int)), entity_col, "_es_causa_raiz"
    )

    # ── Pesos ──
    weights = _ridge_weight_adjustment(df, temp_excess_col, stage_label, delay_col)

    # ── Normalización relativa (dentro del grupo) ──
    delay_pct = _percentile_rank_0_100(delay_shrunk)
    excess_pct = _percentile_rank_0_100(excess_shrunk)
    resched_pct = _percentile_rank_0_100({e: resched_info[e]["shrunk_rate"] for e in entities})
    resp_pct = _percentile_rank_0_100({e: resp_info[e]["shrunk_rate"] for e in entities})

    composite = {
        e: (
            weights["Delay_Prom"] * delay_pct[e]
            + weights["Excess_por_PO"] * excess_pct[e]
            + weights["Tasa_Reschedule"] * resched_pct[e]
            + weights["Tasa_Responsabilidad"] * resp_pct[e]
        )
        for e in entities
    }
    score_normalizado = _percentile_rank_0_100(composite)

    # ── Cortes para riesgo relativo (dentro del grupo) ──
    scores_list = list(score_normalizado.values())
    cut_low_group = np.percentile(scores_list, 33.3) if scores_list else 33.3
    cut_high_group = np.percentile(scores_list, 66.7) if scores_list else 66.7

    total_n = df[entity_col].value_counts().to_dict()

    # ── Percentil de delay vs red (riesgo absoluto) ──
    entity_delay_percentiles = {}
    for e in entities:
        po_indices = df[df[entity_col] == e].index
        pcts = [po_delay_percentiles.get(idx, 50.0) for idx in po_indices]
        entity_delay_percentiles[e] = float(np.mean(pcts)) if pcts else 50.0

    result = {}
    for e in entities:
        riesgo_absoluto = _classify_risk(entity_delay_percentiles[e], cut_low_global, cut_high_global)
        riesgo_relativo = _classify_risk(score_normalizado[e], cut_low_group, cut_high_group)
        
        rec = {
            "Delay_Prom": round(delay_shrunk[e], 2),
            "Tasa_Reschedule": round(resched_info[e]["shrunk_rate"] * 100, 1),
            "Excess_por_PO": round(excess_shrunk[e], 2),
            "Score_Riesgo_Normalizado": round(score_normalizado[e], 1),
            "Nivel_Riesgo_Absoluto": riesgo_absoluto,
            "Nivel_Riesgo_Relativo": riesgo_relativo,
            "Percentil_Delay_vs_Red": round(entity_delay_percentiles[e], 1),
            "Nivel_Riesgo": riesgo_relativo,
            "n_POs_total": int(total_n.get(e, 0)),
            "n_POs_causa_raiz": int(n_rc.get(e, 0)),
            "Credibilidad_Z_Delay": round(delay_cred["z"].get(e, 0.0), 3),
            "Credibilidad_Z_Excess": round(excess_cred_info["z"].get(e, 0.0), 3) if excess_cred_info else 0.0,
            "Delay_Prom_sin_shrink": round(delay_finals[e], 2),
            "Excess_por_PO_sin_shrink": round(excess_finals[e], 2),
            "Tasa_Responsabilidad": round(resp_info[e]["shrunk_rate"] * 100, 1),
            "Pesos_Compuesto": {k: round(v, 3) for k, v in weights.items()},
        }
        
        if excess_cred_info:
            rec["_diagnostico_excess"] = excess_cred_info["_diagnostico"]
        
        if use_dwell:
            rec["_metrica_excess"] = "Dwell_Time_Net (excess_yard_hrs + excess_dock_hrs)"
            rec["_shrinkage_tipo"] = f"suave (k={DC_SHRINKAGE_K})"
        
        result[e] = rec

    return result


# ─────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────
def load_po_data(csv_path: str | Path = None) -> pd.DataFrame:
    """Carga df_classified.csv desde data/processed/ por defecto."""
    
    if csv_path is None:
        csv_path = CSV_DEFAULT_PATH
    else:
        csv_path = Path(csv_path)
        if not csv_path.is_absolute():
            csv_path = REPO_ROOT / csv_path
    
    # Verificar que el archivo existe
    if not csv_path.exists():
        raise FileNotFoundError(
            f"❌ Archivo no encontrado: {csv_path}\n"
            f"Asegúrate de que df_classified.csv esté en {DATA_PROCESSED}"
        )
    
    df = pd.read_csv(csv_path, low_memory=False)

    
    # ── 1. _is_late_: calcular de delay_days_calc != 0 ──
    # SOLO los que son EXACTAMENTE 0 están a tiempo
    df["_is_late_"] = (df["delay_days_calc"] > 0).astype(int)
    
    # ── 2. _resched_: usar _rescheduled ──
    # Si la columna existe, mapea los valores válidos a 1; todo lo demás (incluido si no existe) es 0
    df["_resched_"] = np.where(df["_rescheduled"].astype(str).str.lower().isin(["true", "1"]), 1, 0) if "_rescheduled" in df.columns else 0

    
    # ── 3. total_dc_hrs: calcular si no existe ──
    if "total_dc_hrs" not in df.columns:
        if "excess_yard_hrs" in df.columns and "excess_dock_hrs" in df.columns:
            df["total_dc_hrs"] = df["excess_yard_hrs"].fillna(0) + df["excess_dock_hrs"].fillna(0)
        else:
            df["total_dc_hrs"] = df["excess_dc_hrs"].fillna(0)
    
    # ── 4. Verificar columnas requeridas ──
    # Rellenar en silencio enmascararía datos ausentes (ceros que se propagan a
    # las métricas del scorecard). Si falta alguna columna requerida, fallar
    # nombrándolas para que el problema sea visible y trazable a la fuente.
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "df_classified.csv no contiene columnas requeridas por el scorecard: "
            f"{missing}. Revisa el pipeline de Fase 2 que genera este archivo."
        )

    return df


# ─────────────────────────────────────────────────────────────────────────
# ─── FUNCIÓN AUXILIAR 
def _simplificar_scorecard(scorecard_completo: dict) -> dict:
    """Filtra el diccionario eliminando métricas estadísticas secundarias."""
    return {
        entidad: {
            "nivel_riesgo": metricas.get("Nivel_Riesgo"),
            "score_riesgo": metricas.get("Score_Riesgo_Normalizado"),
            "delay_promedio": metricas.get("Delay_Prom"),
            "excess_por_po": metricas.get("Excess_por_PO"),
            "tasa_reschedule": metricas.get("Tasa_Reschedule"),
            "tasa_responsabilidad": metricas.get("Tasa_Responsabilidad"),
            "pos_totales": metricas.get("n_POs_total"),
            "pos_causa_raiz": metricas.get("n_POs_causa_raiz")
        }
        for entidad, metricas in scorecard_completo.items()
    }


def build_all_scorecards(
    csv_path: str | Path = None,
    output_dir: str | Path = ".",
) -> Dict[str, Dict]:
    """Construye los 3 scorecards y escribe los JSON en output_dir."""
    
    df = load_po_data(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    delay_col = "delay_days_calc"
    
    cut_low_global, cut_high_global, po_delay_percentiles = _po_level_risk_cuts(df, delay_col)

    report_date = date.today().isoformat()
    all_reports = {}
    
    for actor_key in ACTOR_CONFIG:
        scorecard = _build_actor_scorecard(df, actor_key, po_delay_percentiles,
                                          cut_low_global, cut_high_global,
                                          delay_col)
        # scorecard simplificado para JSON final
        scorecard_limpio = _simplificar_scorecard(scorecard)
        payload = {"report_date": report_date, actor_key: scorecard_limpio}

        all_reports[actor_key] = payload
        out_path = out_dir / f"reporte_{actor_key}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return all_reports


if __name__ == "__main__":
    # Ejecución como script: usa CSV default o argumento
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "."
    
    try:
        reports = build_all_scorecards(csv_arg, out_arg)
        for key, payload in reports.items():
            n_ent = len(payload[key])
            print(f"[OK] reporte_{key}.json escrito con {n_ent} entidades.")
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)