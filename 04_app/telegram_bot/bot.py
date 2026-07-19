#!/usr/bin/env python3
"""Punto de entrada del bot de Telegram — PO Delay Root Cause Analyzer."""
import logging
import sys
from pathlib import Path
from functools import wraps

_BOT_DIR = Path(__file__).resolve().parent
if str(_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(_BOT_DIR))

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_WHITELIST
from services.auth import is_authorized, get_profile, get_profile_name
from handlers.common import start, help_command
from handlers.diego import cmd_po, cmd_timeline, cmd_alertas, cmd_hot
from handlers.ravi import (
    cmd_kpi,
    cmd_distribucion,
    cmd_tendencia,
    cmd_scorecards,
    cmd_mismatches,
    cmd_mismatches_chart,
)

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Decorator de autorización ───────────────────────────────────────────────
def require_auth(func):
    """Decorator que bloquea handlers si el usuario no está autorizado."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        logger.info(f"auth: user_id={user.id}, authorized={is_authorized(user.id)}")
        if not is_authorized(user.id):
            await update.message.reply_text(
                "No estás autorizado para usar este bot.\n"
                "Contacta al administrador para agregar tu ID de Telegram."
            )
            return
        return await func(update, context)
    return wrapper


# ── Decorador de perfil ────────────────────────────────────────────────────
def require_profile(profile: str):
    """Decorator que bloquea handlers si el usuario no tiene el perfil indicado.

    Args:
        profile: 'ravi' o 'diego'
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if not user:
                return
            user_profile = get_profile_name(user.id)
            if user_profile != profile:
                logger.info(
                    f"perfil: user_id={user.id}, perfil={user_profile}, "
                    f"requerido={profile} — acceso denegado"
                )
                await update.message.reply_text(
                    f"❌ Este comando solo está disponible para "
                    f"**{profile.title()}**.\n"
                    f"Tu perfil actual es {user_profile.title()}."
                )
                return
            return await func(update, context)
        return wrapper
    return decorator


# ── Aplicar decorators a todos los handlers ──────────────────────────────────
cmd_po        = require_auth(cmd_po)
cmd_timeline  = require_auth(cmd_timeline)
cmd_alertas   = require_auth(cmd_alertas)
cmd_hot       = require_auth(cmd_hot)
cmd_kpi       = require_auth(require_profile("ravi")(cmd_kpi))
cmd_distribucion   = require_auth(require_profile("ravi")(cmd_distribucion))
cmd_tendencia      = require_auth(require_profile("ravi")(cmd_tendencia))
cmd_scorecards     = require_auth(require_profile("ravi")(cmd_scorecards))
cmd_mismatches     = require_auth(require_profile("ravi")(cmd_mismatches))
cmd_mismatches_chart = require_auth(require_profile("ravi")(cmd_mismatches_chart))
help_command  = require_auth(help_command)
# start ya tiene su propia verificación en common.py


# ── Message handler: texto libre ────────────────────────────────────────────
_MENU_MAP = {
    "🔍 buscar po": None,
    "🚨 alertas high": cmd_alertas,
    "🔥 hot pos": cmd_hot,
    "📊 kpis globales": cmd_kpi,
    "📈 distribución (etapa)": cmd_distribucion,
    "📈 distribución (severidad)": cmd_distribucion,
    "📈 tendencia temporal": cmd_tendencia,
    "🏷️ scorecards vendors": cmd_scorecards,
    "🏷️ scorecards carriers": cmd_scorecards,
    "🏷️ scorecards dcs": cmd_scorecards,
    "⚠️ desacuerdos ai vs humano": cmd_mismatches,
}


@require_auth
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto (no comandos)."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()

    if text.isdigit():
        context.args = [text]
        await cmd_po(update, context)
        return

    for key, handler in _MENU_MAP.items():
        if text == key.lower():
            if handler:
                # Verificar perfil antes de ejecutar handlers de Ravi
                if key in ("📊 kpis globales", "📈 distribución (etapa)",
                            "📈 distribución (severidad)", "📈 tendencia temporal",
                            "🏷️ scorecards vendors", "🏷️ scorecards carriers",
                            "🏷️ scorecards dcs", "⚠️ desacuerdos ai vs humano"):
                    user_profile = get_profile_name(update.effective_user.id)
                    if user_profile != "ravi":
                        await update.message.reply_text(
                            f"❌ Esta opción solo está disponible para "
                            f"**Ravi** (Analista).\n"
                            f"Tu perfil actual es {user_profile.title()}.\n\n"
                            "Usa /start para ver el menú de Diego."
                        )
                        return
                if "scorecards" in key:
                    actor = key.split()[-1]
                    context.args = [actor]
                await handler(update, context)
            else:
                await update.message.reply_text(
                    "Buscar PO\n\n"
                    "Escribe el número de PO que quieres consultar.\n"
                    "Ejemplo: 1001\n\n"
                    "O usa /po 1001 directamente.",
                )
            return

    await update.message.reply_text(
        "No entendí ese mensaje.\n\n"
        "Usa /start para ver el menú o /help para la lista de comandos."
    )


# ── Error handler ──────────────────────────────────────────────────────────
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Excepción no capturada:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Ocurrió un error interno. El equipo ha sido notificado."
        )


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN no está definido.\n"
            "Agrega la variable en el archivo .env en la raíz del repo:\n"
            "TELEGRAM_BOT_TOKEN=tu_token_aqui"
        )
        sys.exit(1)

    if not TELEGRAM_USER_WHITELIST:
        logger.warning(
            "TELEGRAM_USER_WHITELIST está vacía: el bot arrancará pero "
            "rechazará todos los comandos (fail-closed). Define la variable "
            "en .env con los IDs de Telegram autorizados para habilitar acceso."
        )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Diego
    app.add_handler(CommandHandler("po", cmd_po))
    app.add_handler(CommandHandler("timeline", cmd_timeline))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("hot", cmd_hot))

    # Ravi
    app.add_handler(CommandHandler("kpi", cmd_kpi))
    app.add_handler(CommandHandler("distribucion", cmd_distribucion))
    app.add_handler(CommandHandler("tendencia", cmd_tendencia))
    app.add_handler(CommandHandler("scorecards", cmd_scorecards))
    app.add_handler(CommandHandler("mismatches", cmd_mismatches))
    app.add_handler(CommandHandler("mismatches_chart", cmd_mismatches_chart))

    # Comunes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Texto libre
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)

    logger.info("Bot iniciado. Presiona Ctrl+C para detener.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()