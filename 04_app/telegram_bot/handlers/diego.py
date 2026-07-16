"""Handlers de Diego — Consulta rápida de POs, alertas, timeline.

Reusa data_service.py (misma lógica que Fase 4) para cargar la data.
"""
from html import escape

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    COL_PO, COL_STAGE, COL_SEVERITY, COL_EXPLANATION, COL_ACTION,
    COL_PO_DT, COL_STA_DT, COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT,
    COL_CHECKIN_DT, COL_CHECKOUT_DT, COL_RECPT_DT,
    COL_HOT_PO_FLAG, COL_IS_SHORT_SHIP, COL_REASON_DSC, COL_LLM_COINCIDE,
    COL_LLM_CONFIANZA, COL_VENDOR_NAME, COL_CARRIER_NAME, COL_DC_NAME,
    COL_DELAY_DAYS,
    COL_LLM_HIPOTESIS, COL_LLM_HIPOTESIS_EVIDENCIA,
    COL_LLM_ACCION_INMEDIATA, COL_LLM_ACCION_CORRECTIVA, COL_LLM_ACCION_PREVENTIVA,
    COL_LLM_HIPOTESIS_ALT, COL_LLM_PASO_DISCRIMINANTE, COL_LLM_CONFIANZA_HIPOTESIS,
    STAGE_LABELS, SEVERITY_EMOJI, STAGE_EMOJI,
)
from services.data_service import load_po_output, get_po_by_number, _safe


async def cmd_po(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /po <nbr> — Detalle completo de un PO.

    Args:
        context.args[0]: Número de PO (ej: /po 12345)
    """
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/po 12345`\nEjemplo: `/po 1001`"
        )
        return

    try:
        po_nbr = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            f"❌ Número de PO inválido: {escape(context.args[0])}. "
            "Debe ser un número entero."
        )
        return

    try:
        df = load_po_output()
        po = get_po_by_number(df, po_nbr)
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró `po_output.csv`. "
            "Ejecuta el pipeline de Fase 3 primero."
        )
        return
    except ValueError as e:
        await update.message.reply_text(f"❌ {escape(str(e))}")
        return

    # ── Extraer campos ─────────────────────────────────────────────────────
    stage = str(po.get(COL_STAGE, "indeterminado")).lower()
    severity = str(po.get(COL_SEVERITY, "")).upper()
    hot_po = po.get(COL_HOT_PO_FLAG, 0)
    short_ship = po.get(COL_IS_SHORT_SHIP, False)
    delay = po.get(COL_DELAY_DAYS)
    coincide = po.get(COL_LLM_COINCIDE)
    confianza = po.get(COL_LLM_CONFIANZA)

    stage_label = STAGE_LABELS.get(stage, stage.title())
    stage_emoji = STAGE_EMOJI.get(stage, "❓")
    sev_emoji = SEVERITY_EMOJI.get(severity, "")
    vendor = _safe(po.get(COL_VENDOR_NAME))
    carrier = _safe(po.get(COL_CARRIER_NAME))
    dc = _safe(po.get(COL_DC_NAME))
    reason = _safe(po.get(COL_REASON_DSC))
    delay_str = f"{delay:.1f} d" if pd.notna(delay) else "N/A"

    # ── Badge de coincidencia ──────────────────────────────────────────────
    if pd.notna(coincide):
        if coincide:
            badge_ai = "✅ Coincide con humano"
        else:
            badge_ai = "⚠️ No coincide con humano"
    else:
        badge_ai = "⏳ Sin análisis LLM"

    # ── Encabezado ─────────────────────────────────────────────────────────
    header = f"🔍 **PO #{po_nbr}**\n"
    if hot_po:
        header += "🔥 **HOT PO** — Prioridad máxima\n"
    header += "\n"

    # ── Métricas principales ───────────────────────────────────────────────
    metrics = (
        f"🏷️ **Etapa:** {stage_emoji} {stage_label}\n"
        f"{sev_emoji} **Severidad:** {severity if severity else 'Sin análisis'}\n"
        f"⏱️ **Retraso:** {delay_str}\n"
        f"🏭 **Vendor:** {vendor}\n"
        f"🚛 **Carrier:** {carrier}\n"
        f"🏬 **DC:** {dc}\n"
    )

    if pd.notna(confianza):
        metrics += f"🎯 **Confianza LLM:** {confianza:.0%}\n"

    metrics += f"\n📋 **Validación:** {badge_ai}\n"
    metrics += f"📝 **Razón humana:** {reason}\n"

    if short_ship:
        metrics += "📦 **Short Shipment** — Envío incompleto ⚠️\n"

    # ── Explicación / acción ──────────────────────────────────────────────
    explanation = _safe(po.get(COL_EXPLANATION))
    action = _safe(po.get(COL_ACTION))
    accion_inmediata = _safe(po.get(COL_LLM_ACCION_INMEDIATA))

    cuerpo = header + metrics

    # Acción inmediata (prioritaria)
    accion_principal = accion_inmediata if accion_inmediata != "N/A" else action
    if accion_principal != "N/A":
        cuerpo += f"\n**🚀 Qué hacer:** {accion_principal}\n"

    if explanation != "N/A":
        cuerpo += f"\n**📖 Causa raíz:** {explanation}\n"

    # ── Diagnóstico diferencial (tier 2) si existe ─────────────────────────
    hipotesis = po.get(COL_LLM_HIPOTESIS)
    if pd.notna(hipotesis) and str(hipotesis).strip():
        conf_hip = po.get(COL_LLM_CONFIANZA_HIPOTESIS)
        conf_str = f" (confianza: {conf_hip:.0%})" if pd.notna(conf_hip) else ""
        cuerpo += (
            f"\n**🔬 Hipótesis:** {_safe(hipotesis)}{conf_str}\n"
            f"📎 **Evidencia:** {_safe(po.get(COL_LLM_HIPOTESIS_EVIDENCIA))}\n"
        )

        hip_alt = po.get(COL_LLM_HIPOTESIS_ALT)
        if pd.notna(hip_alt) and str(hip_alt).strip():
            cuerpo += (
                f"🔄 **Alternativa:** {_safe(hip_alt)}\n"
                f"🔑 **Paso discriminante:** {_safe(po.get(COL_LLM_PASO_DISCRIMINANTE))}\n"
            )

        acc_correctiva = _safe(po.get(COL_LLM_ACCION_CORRECTIVA))
        acc_preventiva = _safe(po.get(COL_LLM_ACCION_PREVENTIVA))
        if acc_correctiva != "N/A":
            cuerpo += f"🛠️ **Correctiva:** {acc_correctiva}\n"
        if acc_preventiva != "N/A":
            cuerpo += f"🔒 **Preventiva:** {acc_preventiva}\n"

    # Enviar (dividir si excede límite de Telegram ~4000 chars)
    max_len = 4000
    if len(cuerpo) > max_len:
        partes = [cuerpo[i:i+max_len] for i in range(0, len(cuerpo), max_len)]
        for parte in partes:
            await update.message.reply_text(parte)
    else:
        await update.message.reply_text(cuerpo)


async def cmd_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /timeline <nbr> — Timeline del lifecycle de un PO."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/timeline 12345`"
        )
        return

    try:
        po_nbr = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ Número inválido: {escape(context.args[0])}")
        return

    try:
        df = load_po_output()
        po = get_po_by_number(df, po_nbr)
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"❌ {escape(str(e))}")
        return

    stage = str(po.get(COL_STAGE, "indeterminado")).lower()
    stage_emoji = STAGE_EMOJI.get(stage, "❓")

    timeline_events = [
        ("📝 PO Creada", COL_PO_DT),
        ("📦 STA (prometida)", COL_STA_DT),
        ("✅ Cita Aprobada", COL_APPROVED_DT),
        ("🚛 Tráiler Llega", COL_TRAILER_ARRIVE_DT),
        ("📥 Check-in", COL_CHECKIN_DT),
        ("📤 Check-out", COL_CHECKOUT_DT),
        ("📦 Recepción", COL_RECPT_DT),
    ]

    lines = [f"📅 **Timeline — PO #{po_nbr}**\n"]
    for label, col in timeline_events:
        ts = po.get(col)
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if pd.notna(ts) else "⏳ Sin registro"
        lines.append(f"▸ {label}: `{ts_str}`")

    # Indicar etapa responsable
    stage_label = STAGE_LABELS.get(stage, stage.title())
    lines.append(f"\n🎯 Etapa responsable: {stage_emoji} **{stage_label}**")

    await update.message.reply_text("\n".join(lines))


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /alertas — Últimos 5 POs con severidad HIGH."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    alerts = df[df[COL_SEVERITY] == "HIGH"].head(5)

    if alerts.empty:
        await update.message.reply_text("✅ No hay POs con severidad HIGH.")
        return

    lines = ["🚨 **Últimas alertas HIGH**\n"]
    for _, po in alerts.iterrows():
        po_nbr = int(po[COL_PO])
        stage = str(po.get(COL_STAGE, "indeterminado")).lower()
        stage_label = STAGE_LABELS.get(stage, stage.title())
        delay = po.get(COL_DELAY_DAYS)
        delay_str = f"{delay:.1f} d" if pd.notna(delay) else "?"
        hot = "🔥 " if po.get(COL_HOT_PO_FLAG, 0) else ""
        lines.append(f"{hot}PO #{po_nbr} — {stage_label} — {delay_str}")

    await update.message.reply_text("\n".join(lines))


async def cmd_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /hot — POs marcados como HOT (HOT_PO_FLAG=1)."""
    try:
        df = load_po_output()
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ No se encontró po_output.csv. Ejecuta Fase 3 primero."
        )
        return

    hot_pos = df[df[COL_HOT_PO_FLAG] == 1].head(10)

    if hot_pos.empty:
        await update.message.reply_text("✅ No hay POs marcados como HOT.")
        return

    lines = ["🔥 **HOT POs — Prioridad máxima**\n"]
    for _, po in hot_pos.iterrows():
        po_nbr = int(po[COL_PO])
        severity = str(po.get(COL_SEVERITY, ""))
        delay = po.get(COL_DELAY_DAYS)
        delay_str = f"{delay:.1f} d" if pd.notna(delay) else "?"
        sev_emoji = SEVERITY_EMOJI.get(severity, "")
        lines.append(f"PO #{po_nbr} {sev_emoji} — {delay_str}")

    await update.message.reply_text("\n".join(lines))
