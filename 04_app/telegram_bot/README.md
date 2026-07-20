# Bot de Telegram — Fase 4 (cómo correr)

> Por ahora **solo en español**; la versión en inglés se añade al cierre del desarrollo.

Segundo front-end de la Fase 4 ([ADR-20](../../documentation/decisiones/ARD-20.md)):
comandos fijos por persona sobre el mismo contrato F3→F4 que consume Streamlit
(`04_app/README.md`), sin razonamiento libre ni llamada a LLM en tiempo de consulta. No
reemplaza esa app: es el mismo contrato, otro canal.

## 1. Prerrequisitos

El bot lee los mismos artefactos que la app de Streamlit — no los recomputa:

- `data/processed/po_output.csv` (todos los comandos)
- `data/processed/scorecards/reporte_{vendors,carriers,dcs}.json` (`/scorecards`)

Si faltan, generarlos primero con los pasos §1–2 de `04_app/README.md`.

## 2. Instalar dependencias

```bash
pip install -r requirements.txt                      # dependencias base del repo
pip install -r 04_app/telegram_bot/requirements-bot.txt   # extra: python-telegram-bot, plotly, kaleido
```

`kaleido>=1.0` (el que instala este `requirements-bot.txt`) no usa el navegador del
sistema: trae su propio Chrome vía `choreographer` y necesita descargarlo una vez:

```bash
choreo_get_chrome
```

Sin este paso, cualquier comando que genere gráfico (`/distribucion`, `/mismatches_chart`)
falla con `BrowserFailedError`. Los comandos de solo texto no lo necesitan.

## 3. Variables de entorno (`.env`, raíz del repo)

| Variable | Requerida | Para qué |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Sí | Token del bot, de @BotFather. Sin él el bot no arranca. |
| `TELEGRAM_USER_WHITELIST` | Fail-closed | IDs de Telegram autorizados, separados por coma. Vacía = nadie autorizado, salvo `DEMO_MODE`. |
| `DEMO_MODE` | No | `true` bypassea la whitelist por completo — solo para demo/presentación, nunca producción ([ARD-20](../../documentation/decisiones/ARD-20.md)). |
| `TELEGRAM_RAVI_USER_IDS` | No | IDs con perfil "Ravi" (analista). El resto cae en perfil "Diego". Vacía = todos Diego. |
| `TELEGRAM_BOT_USERNAME` | No | Solo para el botón "Consultar por Telegram" de la landing de Streamlit; no la usa el bot. |

Plantilla completa en `.env.example`. Para obtener un ID de Telegram: escribir `/start` a
`@userinfobot`.

## 4. Arrancar

```bash
python 04_app/telegram_bot/bot.py
```

El bot usa **long polling** (`app.run_polling`), no webhook: no requiere URL pública ni
túnel (ngrok o similar). Basta con que el proceso quede corriendo — `Ctrl+C` para
detenerlo. Cada usuario autorizado interactúa directo con el bot ya vinculado al token del
`.env`.

## 5. Comandos disponibles

- **Diego** (coordinador de excepciones): `/po`, `/timeline`, `/alertas`, `/hot`
- **Ravi** (analista): `/kpi`, `/distribucion`, `/tendencia`, `/scorecards`, `/mismatches`,
  `/mismatches_chart`
- **Comunes**: `/start`, `/help`

## Referencias

- Decisión de diseño: [ARD-20](../../documentation/decisiones/ARD-20.md)
- Contrato de datos: `04_app/README.md` §1
- Autenticación: `services/auth.py` (fail-closed + bypass de `DEMO_MODE`)
