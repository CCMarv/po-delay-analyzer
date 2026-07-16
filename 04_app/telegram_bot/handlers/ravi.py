"""Handlers de Ravi — KPIs globales, distribuciones, scorecards, mismatches.

Reusa data_service.py y chart_service.py para generar respuestas de texto
y/o PNG según el comando.
"""
import logging
from html import escape

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    COL_PO, COL_STAGE, COL_SEVERITY, COL_DELAY_DAYS, COL_LLM_COINCIDE,
    COL_LLM_CONFIANZA, COL_HOT_PO_FLAG,
    STAGE_LABELS, SEVERITY_EMOJI, STAGE_EMOJI,
)
from services.data_service import load_po_output, load_scorecards

logger = logging.getLogger(__name__)


# ── Helper: badge de riesgo para scorecards (solo texto) ───────────────────
_RISK_EMOJI = {"Alto": "🔴", "Medio": "🟠", "Bajo": "🟢"}


def _risk_badge(nivel: str) -> str:
    emoji = _RISK_EMOJI.get(nivel, "⚪")
    return f"{emoji} **{nivel}**" if nivel else "⚪ Sin datos"


async def cmd_kpi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /kpi — KPIs globales de la red."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    total = len(df)
    stage_counts = df[COL_STAGE].value_counts()
    severity_counts = df[COL_SEVERITY].value_counts()
    n_high = int(severity_counts.get("HIGH", 0))
    n_disagree = int((df[COL_LLM_COINCIDE] == False).sum())  # noqa: E712
    disagree_rate = n_disagree / total * 100 if total else 0.0
    top_stage = stage_counts.index[0] if not stage_counts.empty else "N/A"
    top_stage_pct = stage_counts.iloc[0] / total * 100 if total else 0.0
    top_stage_label = STAGE_LABELS.get(str(top_stage).lower(), top_stage)
    n_hot = int((df[COL_HOT_PO_FLAG] == 1).sum())

    texto = (
        "📊 **KPIs Globales — Network Intelligence**\n\n"
        f"📦 **Total POs tardíos:** {total}\n"
        f"🎯 **Etapa dominante:** {top_stage_label} ({top_stage_pct:.0f}%)\n"
        f"🚨 **Severidad alta:** {n_high} ({n_high / total * 100:.0f}%)\n"
        f"⚠️ **Tasa de desacuerdo:** {disagree_rate:.1f}%\n"
        f"🔥 **HOT POs:** {n_hot}\n\n"
        "Usa /distribucion para ver los gráficos, "
        "/scorecards para el detalle por entidad, "
        "o /mismatches para los desacuerdos."
    )

    await update.message.reply_text(texto)


async def cmd_distribucion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /distribucion — Gráficos de etapa y severidad (PNG)."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    await update.message.reply_text("🔄 Generando gráficos...")

    try:
        from services.chart_service import distribucion_etapa, distribucion_severidad

        png_etapa = distribucion_etapa(df)
        await update.message.reply_photo(
            photo=png_etapa,
            caption="📊 Distribución por Etapa",
        )

        png_sev = distribucion_severidad(df)
        await update.message.reply_photo(
            photo=png_sev,
            caption="📊 Distribución por Severidad",
        )
    except RuntimeError as e:
        logger.warning(f"No se pudo generar PNG: {e}")
        # Fallback: mostrar como texto
        stage_counts = df[COL_STAGE].value_counts()
        sev_counts = df[COL_SEVERITY].value_counts()

        texto = "📊 **Distribuciones** (fallback texto)\n\n**Por Etapa:**\n"
        for stage, count in stage_counts.items():
            emoji = STAGE_EMOJI.get(str(stage).lower(), "❓")
            texto += f"{emoji} {stage}: {count}\n"

        texto += "\n**Por Severidad:**\n"
        for sev, count in sev_counts.items():
            emoji = SEVERITY_EMOJI.get(sev, "")
            texto += f"{emoji} {sev}: {count}\n"

        await update.message.reply_text(texto)


async def cmd_tendencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /tendencia — Tendencia temporal semanal (PNG)."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    await update.message.reply_text("🔄 Generando tendencia...")

    try:
        from services.chart_service import tendencia_temporal

        png = tendencia_temporal(df)
        await update.message.reply_photo(
            photo=png,
            caption="📈 Tendencia Semanal — POs Tardíos",
        )
    except RuntimeError as e:
        logger.warning(f"No se pudo generar PNG: {e}")
        await update.message.reply_text(
            "❌ No se pudo generar el gráfico. "
            "Asegúrate de tener instalado kaleido: `pip install kaleido`"
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {escape(str(e))}")


async def cmd_scorecards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /scorecards [vendors|carriers|dcs] — Scorecards por entidad.

    Si no se especifica tipo, muestra los vendors por defecto.
    """
    scorecards = load_scorecards()
    if scorecards is None:
        await update.message.reply_text(
            "❌ Scorecards no encontrados. Genéralos con:\n"
            "`python 03_llm_integration/scorecard_core.py "
            "data/processed/df_classified.csv data/processed/scorecards`"
        )
        return

    # Determinar qué actores mostrar
    actor_arg = context.args[0].lower() if context.args else "vendors"

    actor_map = {
        "vendors": ("vendors", "🏭 **Scorecards — Proveedores**", "vendor"),
        "carriers": ("carriers", "🚛 **Scorecards — Transportistas**", "carrier"),
        "dcs": ("dcs", "🏬 **Scorecards — Centros de Distribución**", "dc"),
    }

    if actor_arg not in actor_map:
        await update.message.reply_text(
            "❌ Tipo inválido. Usa: `/scorecards vendors`, "
            "`/scorecards carriers` o `/scorecards dcs`"
        )
        return

    actor_key, title, stage_key = actor_map[actor_arg]
    entities = scorecards.get(actor_key, {})

    if not entities:
        await update.message.reply_text(f"Sin entidades en {title}.")
        return

    # Ordenar por score de riesgo descendente
    ordered = sorted(
        entities.items(),
        key=lambda kv: kv[1].get("Score_Riesgo_Normalizado", 0),
        reverse=True,
    )

    lines = [f"{title}\n"]
    for name, rec in ordered[:10]:  # Top 10
        nivel = rec.get("Nivel_Riesgo", "Sin datos")
        badge = _risk_badge(nivel)
        delay = rec.get("Delay_Prom_sin_shrink", 0.0)
        excess = rec.get("Excess_por_PO_sin_shrink", 0.0)
        score = rec.get("Score_Riesgo_Normalizado", 0)
        n_pos = rec.get("n_POs_total", 0)
        n_root = rec.get("n_POs_causa_raiz", 0)

        lines.append(
            f"▸ **{name}** {badge}\n"
            f"  📊 Score: {score:.0f}/100 | Retraso: {delay:.1f} d\n"
            f"  ⏱ Exceso: {excess:.1f} h | POs: {n_pos} (causa raíz: {n_root})\n"
        )

    lines.append("\n_Indicadores con shrinkage empírico-Bayes. Score = ranking relativo dentro del grupo._")

    await update.message.reply_text("\n".join(lines))


async def cmd_mismatches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /mismatches — POs donde AI ≠ humano.

    Muestra los POs donde llm_coincide_con_reason es False, agrupados por etapa.
    """
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    mismatches = df[df[COL_LLM_COINCIDE] == False]  # noqa: E712

    if mismatches.empty:
        await update.message.reply_text(
            "✅ Todos los diagnósticos AI coinciden con el reason code humano."
        )
        return

    total = len(mismatches)
    by_stage = mismatches[COL_STAGE].value_counts()

    lines = [f"⚠️ **Desacuerdos AI vs Humano** ({total} POs)\n"]

    for stage, count in by_stage.items():
        emoji = STAGE_EMOJI.get(str(stage).lower(), "❓")
        pct = count / total * 100
        lines.append(f"{emoji} {stage}: {count} ({pct:.0f}%)")

    lines.append("\n**Últimos 10:**\n")
    for _, po in mismatches.head(10).iterrows():
        po_nbr = int(po[COL_PO])
        stage = str(po.get(COL_STAGE, ""))
        stage_label = STAGE_LABELS.get(stage.lower(), stage)
        delay = po.get(COL_DELAY_DAYS)
        delay_str = f"{delay:.1f} d" if pd.notna(delay) else "?"
        lines.append(f"▸ PO #{po_nbr} — {stage_label} — {delay_str}")

    lines.append("\n_Usa /po <nbr> para ver el detalle de cada uno._")

    await update.message.reply_text("\n".join(lines))


async def cmd_mismatches_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /mismatches_chart — Gráfico de desacuerdo por etapa (PNG)."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    await update.message.reply_text("🔄 Generando gráfico de desacuerdos...")

    try:
        from services.chart_service import desacuerdo_por_etapa

        png = desacuerdo_por_etapa(df)
        await update.message.reply_photo(
            photo=png,
            caption="⚠️ % de Desacuerdo AI vs Humano por Etapa",
        )
    except RuntimeError as e:
        logger.warning(f"No se pudo generar PNG: {e}")
        await update.message.reply_text(
            "❌ No se pudo generar el gráfico. "
            "Usa `/mismatches` para ver la lista."
        )
