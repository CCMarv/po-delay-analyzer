# Manejo de secretos y seguridad de API keys (multi-proveedor LLM)

* **Estatus:** 🟢 **Vigente** (cerrado 2026-07-19; abierto 2026-06-27)
* **Contexto Técnico:** Fase 3 / Integración LLM — credenciales de los proveedores de la API
* **Referencias:** Best Practices for API Key Safety (OpenAI Help Center, 7 prácticas);
  `03_llm_integration/llm_integration.py` (backends Claude/OpenAI/DeepSeek, `create_backend`);
  `.env.example`; `.gitignore`; `documentation/convenciones-issues.md` (política "nunca se
  commitea secrets")

## Contexto y Problema
El entregable invoca varios proveedores LLM (Claude, OpenAI, DeepSeek; Ollama local sin key)
y entra OpenAI como backend del CSV-entregable. Cada proveedor exige una API key, un secreto
cuya filtración expone la cuota de la cuenta a cargos y abuso. El código ya resuelve las keys
desde variables de entorno, pero faltaba una política única y documentada que fije dónde vive
cada key, cómo se nombra, quién la posee y qué hacer ante una fuga. Sin ese registro, cada
integración de proveedor nuevo arriesga reintroducir una key en código, en un argumento de
CLI versionado o en la plantilla.

## Opciones Consideradas

### Opción A: Key embebida en código o pasada por CLI
* **Pros:** No requiere configurar el entorno; arranca sin pasos previos.
* **Contras:** Vector directo de fuga: la key queda en el historial de git, en logs de shell,
  en issues o PRs. Contradice las prácticas #3 y #4 de OpenAI. Descartada.

### Opción B: Variables de entorno con `python-dotenv` y `.env` gitignored
* **Pros:** Separa el secreto del código (Twelve-Factor); nombre de variable estándar por
  proveedor, consistente en el equipo; `.env` excluido de git; plantilla `.env.example`
  versionada con placeholders vacíos. Cubre las prácticas #1–#4 y #6. Ya implementado en el
  código (`load_dotenv`, `os.environ.get`).
* **Contras:** Depende de disciplina humana (no pegar la key en un comando que se commitee);
  el `.env` vive en texto plano en la máquina de cada persona.

### Opción C: Key management service (Vault / AWS Secrets Manager / Google Secret Manager) + IP allowlisting
* **Pros:** Cifrado y control de acceso centralizado; las prácticas #5 y #7 de OpenAI. Estándar
  para despliegue en producción.
* **Contras:** Sobreingeniería para un entregable académico que corre local, sin infraestructura
  de despliegue. Fuera de alcance ahora; se registra como evolución futura.

## Decisión
Se adopta la **Opción B**. Las API keys se gestionan por variables de entorno cargadas con
`python-dotenv` desde un `.env` en la raíz, excluido de git. El nombre de cada variable es el
estándar del proveedor (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`). Cada
persona usa su propia key, no se comparten. Las keys nunca se escriben en código, en argumentos
de CLI que queden versionados, ni en issues/PRs/logs. Ante sospecha de fuga, se rota la key de
inmediato en el panel del proveedor y se avisa al equipo. La key nunca se expone en cliente; las
llamadas salen del backend local. Las prácticas #5 (key management service) y #7 (IP allowlisting)
quedan documentadas como deuda de producción, no implementadas en este alcance.

## Consecuencias
* **Positivas:** Reproducible y seguro para el alcance del entregable sin infraestructura extra;
  alineado con las 7 prácticas de OpenAI en lo aplicable; el guardarraíl en
  `.claude/instructions.md` lo hace operativo para ambos asistentes; agregar un proveedor nuevo
  sigue el mismo patrón (variable estándar + placeholder en `.env.example`).
* **Negativas:** La seguridad descansa en disciplina humana y en un `.env` en texto plano por
  máquina; no hay rotación automática ni control de acceso centralizado. Si el proyecto pasara a
  producción, habría que reabrir esta decisión hacia la Opción C (encadenar nuevo ADR).

## Nota de cierre (2026-07-19)
La auditoría de cierre detectó que `llm_integration.py` seguía implementando `--api-key`
—la Opción A que este ARD marca "Descartada"— como el ejemplo principal de su docstring y en
el orden de sus mensajes de error. Se retiró el flag de la CLI (queda solo la resolución por
`.env`), reconciliando el código con la decisión ya tomada aquí; no se reabre ninguna opción.
