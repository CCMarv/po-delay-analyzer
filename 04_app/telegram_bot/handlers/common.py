"""Handlers comunes del bot — /start, menú principal, autorización."""
from html import escape

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from services.auth import is_authorized, get_profile


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start — Muestra el menú según el perfil del usuario.

    Diego (coordinador): menú de consulta rápida de POs.
    Ravi (analista): menú con KPIs, scorecards y mismatches.
    """
    user = update.effective_user
    if not user or not is_authorized(user.id):
        await update.message.reply_text(
            "⛔ No estás autorizado para usar este bot.\n"
            "Contacta al administrador para agregar tu ID de Telegram."
        )
        return

    profile = get_profile(user.id)
    user_name = escape(user.first_name or "Usuario")

    if profile == "ravi":
        keyboard = [
            [KeyboardButton("📊 KPIs Globales")],
            [KeyboardButton("📈 Distribución (Etapa)"), KeyboardButton("📈 Distribución (Severidad)")],
            [KeyboardButton("📈 Tendencia Temporal")],
            [KeyboardButton("🏷️ Scorecards Vendors"), KeyboardButton("🏷️ Scorecards Carriers")],
            [KeyboardButton("🏷️ Scorecards DCs")],
            [KeyboardButton("⚠️ Desacuerdos AI vs Humano")],
            [KeyboardButton("🔍 Buscar PO")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Hola {user_name} 👋\n\n"
            "Soy el asistente de **Network Intelligence**.\n"
            "Puedes consultar KPIs, distribuciones, scorecards "
            "o buscar un PO específico.\n\n"
            "Selecciona una opción del menú o escribe un comando:\n"
            "• `/kpi` — KPIs globales\n"
            "• `/distribucion` — Gráficos de etapa y severidad\n"
            "• `/tendencia` — Tendencia temporal\n"
            "• `/scorecards vendors` — Scorecards de proveedores\n"
            "• `/scorecards carriers` — Scorecards de transportistas\n"
            "• `/scorecards dcs` — Scorecards de centros de distribución\n"
            "• `/mismatches` — POs con desacuerdo AI vs humano\n"
            "• `/po 12345` — Detalle de un PO específico\n"
            "• `/alertas` — Últimas alertas HIGH\n"
            "• `/hot` — POs urgentes",
            reply_markup=reply_markup,
        )
    else:
        keyboard = [
            [KeyboardButton("🔍 Buscar PO")],
            [KeyboardButton("🚨 Alertas HIGH"), KeyboardButton("🔥 HOT POs")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Hola {user_name} 👋\n\n"
            "Soy tu asistente de **Excepciones Inbound**.\n"
            "Puedes consultar el detalle de cualquier PO tardío "
            "o revisar alertas urgentes.\n\n"
            "Selecciona una opción del menú o escribe un comando:\n"
            "• `/po 12345` — Ver detalle de un PO\n"
            "• `/alertas` — Últimas alertas HIGH\n"
            "• `/hot` — POs urgentes (HOT)",
            reply_markup=reply_markup,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help — Lista de comandos disponibles."""
    user = update.effective_user
    if not user:
        return

    profile = get_profile(user.id)

    texto = (
        "🤖 **Comandos disponibles**\n\n"
    )

    if profile == "ravi":
        texto += (
            "📊 **Ravi (Analista)**\n"
            "• `/kpi` — KPIs globales\n"
            "• `/distribucion` — Gráficos etapa + severidad\n"
            "• `/tendencia` — Tendencia temporal semanal\n"
            "• `/scorecards vendors` — Scorecards de proveedores\n"
            "• `/scorecards carriers` — Scorecards de transportistas\n"
            "• `/scorecards dcs` — Scorecards de centros de distribución\n"
            "• `/mismatches` — POs con desacuerdo AI vs humano\n\n"
        )

    texto += (
        "🔍 **Diego (Coordinador)**\n"
        "• `/po 12345` — Detalle completo de un PO\n"
        "• `/timeline 12345` — Timeline del lifecycle\n"
        "• `/alertas` — Últimas 5 alertas HIGH\n"
        "• `/hot` — POs marcados como HOT\n\n"
        "🛠️ **Sistema**\n"
        "• `/start` — Menú principal\n"
        "• `/help` — Esta ayuda"
    )

    await update.message.reply_text(texto)
