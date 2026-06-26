"""Cálculo de métricas y KPIs para cada dashboard."""
import pandas as pd

from config import (
    COL_CARRIER, COL_DC, COL_DELAY_DAYS, COL_EXCESS_CARRIER,
    COL_EXCESS_DC, COL_EXCESS_DOCK, COL_EXCESS_VENDOR, COL_EXCESS_YARD,
    COL_IS_RESCHEDULED, COL_IS_SHORT_SHIP, COL_SEVERITY, COL_STAGE_PRIMARY,
    COL_VENDOR,
)


# ── Métricas globales ───────────────────────────────────────────────────────
def total_pos(df: pd.DataFrame) -> int:
    return len(df)


def total_tardios(df: pd.DataFrame) -> int:
    return int((df[COL_DELAY_DAYS] > 0).sum())


def pct_tardios(df: pd.DataFrame) -> float:
    total = len(df)
    if total == 0:
        return 0.0
    return total_tardios(df) / total * 100


def distribucion_etapas(df: pd.DataFrame) -> pd.Series:
    """Reparto de stage_primary sobre tardíos."""
    tardios = df[df[COL_DELAY_DAYS] > 0]
    return tardios[COL_STAGE_PRIMARY].value_counts()


# ── Vendor ──────────────────────────────────────────────────────────────────
def vendor_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    """Scorecard de vendors sobre POs tardíos con culpa Vendor."""
    tardios = df[df[COL_DELAY_DAYS] > 0]
    vendor_culpa = tardios[tardios[COL_STAGE_PRIMARY] == "Vendor"]

    agg = (
        vendor_culpa
        .groupby(COL_VENDOR)
        .agg(
            POs=(COL_DELAY_DAYS, "count"),
            excess_sum_hrs=(COL_EXCESS_VENDOR, "sum"),
            rescheduled=(COL_IS_RESCHEDULED, "sum"),
            short_ship=(COL_IS_SHORT_SHIP, "sum"),
            high_severity=(COL_SEVERITY, lambda x: (x == "HIGH").sum()),
        )
        .reset_index()
        .sort_values("excess_sum_hrs", ascending=False)
    )

    # % tardíos = POs vendor / total POs de ese vendor
    total_por_vendor = df.groupby(COL_VENDOR).size().reset_index(name="total")
    agg = agg.merge(total_por_vendor, on=COL_VENDOR, how="left")
    agg["pct_tardios"] = (agg["POs"] / agg["total"] * 100).round(1)

    return agg

def culpas_injustas_vendor(df: pd.DataFrame) -> pd.DataFrame:
    """POs donde el reason humano dice Vendor pero el cómputo dice Carrier/DC."""
    tardios = df[df["delay_days_calc"] > 0]
    # reason_group_manual == "Vendor" pero stage_primary != "Vendor"
    return tardios[
        (tardios["reason_group_manual"] == "Vendor")
        & (tardios["stage_primary"] != "Vendor")
    ].copy()


# ── Carrier ─────────────────────────────────────────────────────────────────
def carrier_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    """Scorecard de carriers sobre POs tardíos con culpa Carrier."""
    tardios = df[df[COL_DELAY_DAYS] > 0]
    carrier_culpa = tardios[tardios[COL_STAGE_PRIMARY] == "Carrier"]

    agg = (
        carrier_culpa
        .groupby(COL_CARRIER)
        .agg(
            POs=(COL_DELAY_DAYS, "count"),
            excess_sum_hrs=(COL_EXCESS_CARRIER, "sum"),
            rescheduled=(COL_IS_RESCHEDULED, "sum"),
        )
        .reset_index()
        .sort_values("excess_sum_hrs", ascending=False)
    )

    total_por_carrier = df.groupby(COL_CARRIER).size().reset_index(name="total")
    agg = agg.merge(total_por_carrier, on=COL_CARRIER, how="left")
    agg["pct_tardios"] = (agg["POs"] / agg["total"] * 100).round(1)
    agg["pct_miss"] = agg["pct_tardios"]  # alias para el mockup

    return agg


def carrier_miss_por_dc(df: pd.DataFrame) -> pd.DataFrame:
    """Heatmap: % carrier miss por carrier × DC."""
    tardios = df[df[COL_DELAY_DAYS] > 0]
    carrier_culpa = tardios[tardios[COL_STAGE_PRIMARY] == "Carrier"]

    pivot = (
        carrier_culpa
        .groupby([COL_CARRIER, COL_DC])
        .size()
        .unstack(fill_value=0)
    )

    # Convertir a % sobre total de carrier
    totals = pivot.sum(axis=1)
    pct = pivot.div(totals, axis=0) * 100
    return pct.round(1)

def culpas_injustas_carrier(df: pd.DataFrame) -> pd.DataFrame:
    """POs donde el reason humano dice Carrier pero el cómputo dice Vendor/DC."""
    tardios = df[df["delay_days_calc"] > 0]
    # reason_group_manual == "Carrier" pero stage_primary != "Carrier"
    return tardios[
        (tardios["reason_group_manual"] == "Carrier")
        & (tardios["stage_primary"] != "Carrier")
    ].copy()


# ── DC Ops ──────────────────────────────────────────────────────────────────
def dc_substage_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Stats de Yard vs Dock sobre POs con stage_primary == DC."""
    dc_pos = df[df[COL_STAGE_PRIMARY] == "DC"]
    return (
        dc_pos
        .groupby("dc_substage")
        .agg(
            POs=(COL_DELAY_DAYS, "count"),
            avg_yard_hrs=("excess_yard_hrs", "mean"),
            avg_dock_hrs=("excess_dock_hrs", "mean"),
            avg_excess_hrs=("excess_dc_hrs", "mean"),
        )
        .reset_index()
    )


def culpas_injustas(df: pd.DataFrame) -> pd.DataFrame:
    """POs donde el reason humano dice DC pero el cómputo dice Vendor/Carrier."""
    tardios = df[df[COL_DELAY_DAYS] > 0]
    # reason_group_manual == "DC" pero stage_primary != "DC"
    return tardios[
        (tardios["reason_group_manual"] == "DC")
        & (tardios[COL_STAGE_PRIMARY] != "DC")
    ].copy()