# 03 — Integración con LLM

Genera explicaciones de causa raíz para Purchase Orders (POs) retrasados, usando un LLM para analizar las métricas calculadas en las fases anteriores y producir un diagnóstico estructurado.

## Qué hace

Toma el DataFrame ya limpio y clasificado (fases 1 y 2), filtra los POs con retraso (`delay_days_calc > 0`), y para cada uno construye un prompt con el contexto completo (fechas, métricas de yard/dock, clasificación automática, reason code del DC) que envía a un LLM. La respuesta se parsea a JSON y se agregan estas columnas al DataFrame:

| Columna | Descripción |
|---|---|
| `llm_causa_raiz` | Explicación de 1-2 líneas generada por el modelo |
| `llm_accion_recomendada` | Acción concreta sugerida, con responsable |
| `llm_severidad` | `HIGH`, `MEDIUM` o `LOW` |
| `llm_coincide_con_reason` | `True`/`False` si la causa coincide con el reason code del DC |
| `llm_confianza` | Score de 0.0 a 1.0 |

## Backends soportados

| Backend | Motor | Requiere API key | Costo |
|---|---|---|---|
| `local` | Qwen 2.5:7B vía Ollama | No | Gratis (corre en tu máquina) |
| `claude` | Claude (Anthropic API) | Sí | De pago |
| `deepseek` | DeepSeek API | Sí | De pago |

## Requisitos previos

- Python 3.10+ con el `venv` del repo activado
- Dependencias instaladas: `pip install -r ../requirements.txt`
- Si usas `--backend local`: [Ollama](https://ollama.com) corriendo localmente con el modelo descargado:
  ```bash
  ollama pull qwen2.5:7b
  ```
- Si usas `--backend claude` o `--backend deepseek`: una API key válida del proveedor correspondiente

## Configuración de API keys

Las keys **nunca** se escriben en el código ni se pasan como argumento en producción. Se guardan en un archivo `.env` en la raíz del repo (mismo nivel que `pyproject.toml`), que está excluido de git vía `.gitignore`.

1. Copia la plantilla:
   ```bash
   cd "/home/icastro/Documents/LIACD/2026 V/Blend/team-repo/po-delay-analyzer"
   cp .env.example .env
   ```
2. Edita `.env` con tus keys reales:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DEEPSEEK_API_KEY=sk-...
   OLLAMA_URL=http://localhost:11434/api/generate
   ```
3. Confirma que `.env` está en `.gitignore`:
   ```bash
   grep "^\.env$" .gitignore
   ```

El script carga estas variables automáticamente con `load_dotenv()`, así que no necesitas pasar `--api-key` en la terminal una vez configurado el `.env`.

## Uso

Activa el entorno virtual antes de correr cualquier comando:

```bash
cd "/home/icastro/Documents/LIACD/2026 V/Blend/team-repo/po-delay-analyzer"
source venv/bin/activate
cd 03_llm_integration
```

### Modo test (10 POs, para validar que todo funciona)

```bash
# Local (Qwen/Ollama)
python llm_integration.py --mode test --backend local

# Claude
python llm_integration.py --mode test --backend claude

# DeepSeek
python llm_integration.py --mode test --backend deepseek
```

### Modo custom (N POs específicos)

```bash
python llm_integration.py --mode custom --limit 50 --backend deepseek
```

### Modo producción (todos los POs retrasados)

```bash
python llm_integration.py --mode full --backend claude
```

### Parámetros adicionales

| Flag | Default | Descripción |
|---|---|---|
| `--mode` | `test` | `test` (10 POs), `full` (todos), `custom` (usa `--limit`) |
| `--limit` | `50` | Cantidad de POs en modo `custom` |
| `--backend` | `local` | `local`, `claude` o `deepseek` |
| `--api-key` | `None` | Override manual de la key (no recomendado; usa `.env`) |
| `--claude-model` | `claude-3-sonnet-20241022` | Modelo de Claude a usar |
| `--deepseek-model` | `deepseek-chat` | Modelo de DeepSeek (`deepseek-chat` o `deepseek-reasoner`) |
| `--ollama-model` | `qwen2.5:7b` | Modelo local en Ollama |
| `--ollama-url` | `http://localhost:11434/api/generate` | URL de la API de Ollama |

## Salida

Los resultados se guardan como CSV en `../data/processed/`, con nombre según el modo y backend usados:

- `df_with_llm_test_{backend}.csv`
- `df_with_llm_full_{backend}.csv`
- `df_with_llm_{limit}_{backend}.csv`

También se generan guardados parciales cada 50 POs (configurable vía `DEFAULT_SAVE_EVERY` en el código) para no perder progreso si el proceso se interrumpe en corridas largas.

## Manejo de errores

- **401/403 (API key inválida o sin permisos):** el script falla de inmediato sin reintentar y muestra un mensaje claro indicando qué variable de entorno revisar.
- **Otros errores HTTP (429, 500, etc.):** se reintenta hasta 3 veces con una pausa de 2 segundos entre intentos.
- **Errores de red (timeout, conexión):** mismo comportamiento de reintento.
- Si un PO falla tras los reintentos, se marca como `FALLÓ` en la barra de progreso y continúa con el siguiente (no detiene el batch completo).

## Troubleshooting

**`ModuleNotFoundError: No module named 'dotenv'`**
El venv no está activado. Corre `source venv/bin/activate` desde la raíz del repo antes de ejecutar el script.

**`Error HTTP 401: ... api key ... is invalid`**
La key en `.env` no es válida o tiene espacios/caracteres extra al copiarla. Verifícala directamente con un `curl` de prueba al endpoint del proveedor, o regenera la key desde su dashboard.

**`CSV no encontrado en ...`**
El script espera el CSV crudo en `../data/raw/po_root_cause_synthetic.csv` relativo a la raíz del repo. Verifica que el archivo exista en esa ruta exacta.

## Notas de diseño

- **Fuente del prompt (T6).** El prompt que se envía al modelo lo arma `build_prompt()` en `llm_integration.py`: es el prompt **operativo**, el que realmente corre, e interpola los datos de cada PO. El archivo `prompt_template.txt` es un **borrador de system prompt** más elaborado (rol, contexto de negocio, criterios de calidad) que **hoy no se carga desde el código** — queda como insumo para el diseño del prompt de Fase 3 (decidir si adoptarlo como system prompt, añadir few-shot, etc.). Mientras F3 no lo cablee, la fuente única en uso es `build_prompt()`; el `.txt` no es código muerto sino material de diseño pendiente.
- El parseo de la respuesta JSON del LLM está centralizado en `_parse_llm_json()` para evitar duplicar lógica entre backends.
- El backend `local` (Qwen) tiene fallback a texto libre si el modelo no devuelve JSON válido; los backends cloud (`claude`, `deepseek`) no, porque se espera que sigan instrucciones de formato de forma más confiable.
- Los tres backends comparten la misma interfaz (`call(prompt, max_retries)`), por lo que agregar un nuevo proveedor solo requiere implementar una clase nueva y registrarla en `create_backend()`.