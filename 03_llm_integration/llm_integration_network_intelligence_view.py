import asyncio
import json
import os
import datetime
import argparse
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings

# Cargar variables de entorno
ruta_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ruta_env)
model_name = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')


# Definir la ruta base primero
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

# Después de imports y antes de las clases Pydantic
ACTOR_CONFIG = {
    "vendor": {
        "input_file": "reporte_vendors.json",  # tu archivo actual
        "output_prefix": "vendor",
        "titulo": "1. VENDORS",
        "singular": "Vendor",
        "referencias": {
            "delay": {"bajo": 3, "medio": "3-5", "alto": ">5"},
            "reschedule": {"bajo": 10, "medio": "10-15", "alto": ">15"},
            "excess": {"bajo": 70, "medio": "70-85", "alto": ">85"},
            "causa_raiz": {"bajo": 20, "medio": "20-35", "alto": ">35"}
        }
    },
    "carrier": {
        "input_file": "reporte_carriers.json",
        "output_prefix": "carrier",
        "titulo": "2. CARRIERS",
        "singular": "Carrier",
        "referencias": {
            "delay": {"bajo": 1, "medio": "1-1.5", "alto": ">1.5"},
            "reschedule": {"bajo": 12, "medio": "12-15", "alto": ">15"},
            "excess": {"bajo": 12, "medio": "12-15", "alto": ">15"},
            "causa_raiz": {"bajo": 10, "medio": "10-15", "alto": ">15"}
        }
    },
    "dc": {
        "input_file": "reporte_dcs.json",
        "output_prefix": "dc",
        "titulo": "3. DISTRIBUTION CENTERS",
        "singular": "DC",
        "referencias": {
            "delay": {"bajo": 0.5, "medio": "0.5-0.75", "alto": ">0.75"},
            "reschedule": {"bajo": 12, "medio": "12-15", "alto": ">15"},
            "excess": {"bajo": 8, "medio": "8-12", "alto": ">12"},
            "causa_raiz": {"bajo": 8, "medio": "8-12", "alto": ">12"}
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# 📐 CLASES PYDANTIC PARA ESTRUCTURAR LA SALIDA (OUTPUT_TYPE)
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import List

class AnalisisBloqueRiesgo(BaseModel):
    nivel_riesgo: str = Field(
        description="Debe ser exactamente uno de estos valores: 'Alto', 'Medio' o 'Bajo'"
    )
    
    entidades: List[str] = Field(
        description="Lista de nombres de las empresas afectadas en MAYÚSCULAS, separadas por comas"
    )
    
    analisis: str = Field(
        description=(
            "Análisis ejecutivo que debe incluir:\n"
            "- Patrones comunes y tendencias observadas en el bloque.\n"
            "- Relaciones entre indicadores (ej. ¿Delay alto correlaciona con Excess elevado?).\n"
            "- Posicionamiento relativo: ¿las entidades son mejores, peores o iguales que el promedio del bloque? Explica por qué.\n"
            "- Consistencia: ¿el comportamiento operativo valida o contradice el Nivel_Riesgo_Absoluto?\n"
            "- Implicaciones operativas y de negocio derivadas del comportamiento conjunto.\n"
            "- Incluir al cierre: 'Score_Riesgo_Normalizado=X.X' basado en tu juicio analítico."
        )
    )
    
    accion: str = Field(
        description=(
            "Recomendaciones concretas y accionables, directamente vinculadas al análisis.\n"
            "Deben ser específicas en tiempo comercial, legal o logístico.\n"
            "Si falta información para definir una acción, incluye máximo 2 preguntas con 2 escenarios posibles (A/B) y acciones para cada uno.\n"
            "No usar frases genéricas como 'mejorar procesos' sin detallar el 'cómo', 'cuándo' y 'quién'."
        )
    )

class ReporteEspecialista(BaseModel):
    titulo: str = Field(description="Ej: '1. VENDORS', '2. CARRIERS' o '3. DCs'")
    bloques: List[AnalisisBloqueRiesgo] = Field(description="Lista obligatoria con al menos 1 bloque: Crítico, Medio o Bajo")

class ReporteConclusionGlobal(BaseModel):
    conclusion: str = Field(description="Párrafo consolidado de cierre directivo sobre toda la red logística")


# ═══════════════════════════════════════════════════════════════════════════
# 🤖 CONFIGURACIÓN DE AGENTES (TEMPERATURA 0.1, SIN LOOPS, MAX TOKENS...)
# ═══════════════════════════════════════════════════════════════════════════

def crear_agente(actor_type: str, config: dict):
    """Crea un agente especializado según el tipo de actor"""
    
    # Variables para personalizar el prompt
    referencias = config["referencias"]
    prompt_personalizado = f"""
    # ROL Y OBJETIVO
    Eres un Analista de Riesgo Logístico especializado en {config['titulo']}.
    
    # GUÍAS INTERNAS (NO MENCIONAR EN OUTPUT)
    Referencias orientativas para {config['singular']}:
    | Métrica | Saludable | Seguimiento | Crítico |
    |---------|-----------|-------------|---------|
    | Delay_Prom | <{referencias['delay']['bajo']} | {referencias['delay']['medio']} | {referencias['delay']['alto']} |
    | Tasa_Reschedule | <{referencias['reschedule']['bajo']} | {referencias['reschedule']['medio']} | {referencias['reschedule']['alto']} |
    | Excess_por_PO | <{referencias['excess']['bajo']} | {referencias['excess']['medio']} | {referencias['excess']['alto']} |
    | Tasa_causa_raiz | <{referencias['causa_raiz']['bajo']} | {referencias['causa_raiz']['medio']} | {referencias['causa_raiz']['alto']} |
    
    # RESTO DEL PROMPT (igual que antes, pero reemplaza "Vendors" por {config['titulo']})
    
    # DICCIONARIO DE COLUMNAS
    - **Entidad**: Vendor, Carrier o DC evaluado.
    - **Nivel_Riesgo_Absoluto**: Clasificación global pre-calculada (referencia).
    - **Delay_Prom**: Días de retraso promedio. Refleja confiabilidad en tiempos de entrega.
    - **Tasa_Reschedule**: % de órdenes reprogramadas. Indica estabilidad operativa.
    - **Excess_por_PO**: Horas excedentes promedio. Para DCs, es el Dwell Time Net. Es clave para eficiencia operativa.
    - **n_POs_total**: Número total de órdenes. Usar para evaluar robustez estadística.
    - **n_POs_causa_raiz**: Órdenes con causa raíz identificada.
    - **Tasa_causa_raiz**: Proporción entre órdenes con causa raíz y total (n_POs_causa_raiz / n_POs_total). Alto = patrones repetitivos; Bajo = eventos aislados.

    # GUÍAS INTERNAS (NO MENCIONAR EN OUTPUT)
    *Referencias orientativas de valores por tipo de entidad. No son reglas fijas; prioriza el comportamiento conjunto de las métricas.*

    | Tipo       | Delay_Prom (días)        | Tasa_Reschedule (%)     | Excess_por_PO (horas)   | Tasa_causa_raíz (%)    |
    | :--------- | :----------------------- | :---------------------- | :---------------------- | :--------------------- |
    | **Vendor** | Bajo: <3; Medio: 3-5; Alto: >5 | Bajo: <10; Medio: 10-15; Alto: >15 | Bajo: <70; Medio:70-85; Alto: >85 | Bajo: <20; Medio:20-35; Alto: >35 |
    | **Carrier**| Bajo: <1; Medio:1-1.5; Alto: >1.5 | Bajo: <12; Medio:12-15; Alto: >15 | Bajo: <12; Medio:12-15; Alto: >15 | Bajo: <10; Medio:10-15; Alto: >15 |
    | **DC**      | Bajo:<0.5; Medio:0.5-0.75; Alto: >0.75 | Bajo: <12; Medio:12-15; Alto: >15 | Bajo: <8; Medio:8-12; Alto: >12 | Bajo: <8; Medio:8-12; Alto: >12 |

    **Regla de interpretación de rangos:**
    - "Saludable" NO significa "promedio" - significa que la métrica está en zona óptima.
    - Cuando TODAS las entidades operan en zona saludable y son homogéneas, el Nivel_Riesgo_Absoluto DEBE ser cuestionado.
    - No confundir "variación dentro de rango saludable" con "problemas operativos".


    # METODOLOGÍA DE ANÁLISIS (RAZONAMIENTO INTERNO)
    Sigue estos pasos mentalmente sin mostrarlos en la salida:
    1.  **Comportamiento General**: Identifica tendencias y anomalías en el grupo de entidades.
    2.  **Impulsores Clave**: Determina qué métricas son las que realmente diferencian el desempeño del grupo.
    3.  **Relaciones**: Busca correlaciones (ej. ¿retraso alto implica mayor exceso de tiempo?).
    4.  **Consistencia**: Evalúa si el Nivel_Riesgo_Absoluto es coherente con el comportamiento observado. 
    5.  **Implicaciones Operativas**: Traduce los números a efectos en procesos diarios (ej. ¿señala inestabilidad estructural o eventos aislados?).
    6.  **Impacto de Negocio**: Conecta el desempeño con consecuencias en costos, servicio al cliente, inventarios o planificación.
    7.  **Recomendaciones**: Formula acciones directas que ataquen las causas raíz identificadas en el análisis.
    8.  Si todas las entidades de un bloque muestran valores homogéneos (variación < 30% en todas las métricas) y el Nivel_Riesgo_Absoluto no refleja ese comportamiento, indícalo explícitamente como un hallazgo principal.

    # REGLAS DE REDACCIÓN
    **El análisis debe ser ejecutivo.** No describas valores numéricos (ej. "el delay es 5.4"). Explica su significado, patrón, causas probables e impacto. Supón que el lector ya ve la tabla; tu trabajo es interpretarla y responder "por qué" es importante y "qué" implica.
    **Regla de homogeneidad**: Cuando un bloque presenta comportamiento uniforme sin diferenciación significativa entre entidades, el análisis debe enfocarse en:
    - Explicar por qué todas son similares
    - Evaluar si la clasificación de riesgo es consistente con los datos
    - Recomendar una recalibración de la escala si todas operan muy por debajo del umbral de riesgo
    - No forzar diferencias donde no existen

    **Estructura de cada bloque de riesgo ("Alto", "Medio", "Bajo"):**
    - **nivel_riesgo**: "Alto", "Medio" o "Bajo".
    - **entidades**: Lista en MAYÚSCULAS separadas por comas.
    - **analisis**: Análisis ejecutivo estructurado OBLIGATORIAMENTE como una lista de viñetas (usando guiones '- '). Está estrictamente prohibido usar párrafos de texto corrido. Cada viñeta debe explicar de forma independiente el comportamiento, patrones, relaciones, consistencia e implicaciones operativas/de negocio. 
    - **accion**: Recomendaciones concretas. Si falta información, incluye un máximo de 2 preguntas, cada una con dos escenarios posibles (A/B) y acciones específicas para cada uno.

    # PROHIBICIONES
    - Mencionar umbrales, referencias internas o valores numéricos aislados.
    - Inventar causas, correlaciones o información no inferible de los datos.
    - Dar recomendaciones genéricas (como "mejorar procesos") sin detallar el "cómo".
    - Describir la tabla en lugar de interpretarla.
    - Ignorar el `n_POs_total` al emitir conclusiones.
    - Tratar el `Nivel_Riesgo_Absoluto` como una verdad absoluta.
    - Tratar diferencias mínimas (ej. 10% vs 15%) como patrones significativos sin validación estadística.
    - Forzar conclusiones diferenciadoras cuando los datos muestran homogeneidad.
    - Validar el Nivel_Riesgo_Absoluto cuando los datos muestran consistentemente desempeño en zona saludable.
    - Usar frases como "exceso significativo" sin especificar que está dentro de parámetros óptimos.
    - Recomendar "revisar procesos" sin vincularlo a un problema real identificado en los datos.
    - REDACTAR EL ANÁLISIS EN FORMA DE PÁRRAFO COMPACTO (Debe ser una lista de puntos claros y concisos, no un texto corrido).
    
    # EXCEPCIONES
    Si identificas que TODAS las entidades son prácticamente iguales (homogeneidad), este es un hallazgo clave. El análisis debe:
    - Destacar este comportamiento uniforme
    - Evaluar si el Nivel_Riesgo_Absoluto refleja adecuadamente esta realidad (puede ser consistente, sobreestimado o subestimado según el caso)
    - No forzar diferenciaciones donde no existen

    
    # FORMATO DE SALIDA
    - Debes apegarte estrictamente al esquema estructurado de salida (Pydantic). Asegúrate de que el campo 'analisis' contenga saltos de línea y guiones para formar la lista de viñeta.
   
    """

    return Agent(
        name=f"Analista de riesgo logistico - {config['titulo']}",
        model=model_name,
        output_type=ReporteEspecialista,
        model_settings=ModelSettings(
            max_tokens=1200,
            temperature=0.1
        ),
        instructions=prompt_personalizado
    )


# ═══════════════════════════════════════════════════════════════════════════
# 🛠️ TRADUCTOR DE OBJETOS PYDANTIC AL FORMATO TEXTO DE TU PARSER
# ═══════════════════════════════════════════════════════════════════════════

def construir_segmento_texto(reporte: ReporteEspecialista) -> str:
    """Transforma el objeto Pydantic validado al formato exacto de texto que lee tu Streamlit."""
    texto_bloque = f"### **{reporte.titulo}**\n\n"
    
    for b in reporte.bloques:
        lista_empresas = ", ".join(b.entidades)
        # Ajustamos el string para que tu frontend detecte "Alto", "Medio" o "Bajo" sin problemas
        texto_bloque += f"**Zona de Riesgo {b.nivel_riesgo}**\n"
        texto_bloque += f"*Entidad o Entidades: {lista_empresas}*\n\n"
        texto_bloque += f"**Análisis:**\n{b.analisis}\n\n"  # Sin asteriscos contenedores y con salto de línea para los bullets
        texto_bloque += f"**Acción:** {b.accion}\n\n"
    
    return texto_bloque


# ======================================================
# TOKENS
# ======================================================

def imprimir_metricas_tokens(agent_name: str, result_object):
    print("\n" + "-" * 40)
    print(f"📊 TOKEN USAGE - {agent_name.upper()}")
    print("-" * 40)
    
    try:
        usage = result_object.context_wrapper.usage
        print(f"  Requests:      {usage.requests}")
        print(f"  Input tokens:  {usage.input_tokens}")
        print(f"  Output tokens: {usage.output_tokens}")
        print(f"  Total tokens:  {usage.total_tokens}")
    except Exception as token_error:
        print(f"  ⚠️ Información de tokens no disponible: {token_error}")
        
    print("-" * 40)


# ═══════════════════════════════════════════════════════════════════════════
# 🔋 PIPELINE DE EJECUCIÓN SECUENCIAL ACUMULATIVO
# ═══════════════════════════════════════════════════════════════════════════
async def main():
    # === PARSER DE ARGUMENTOS ===
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--actor",
        choices=["vendor", "carrier", "dc", "all"],
        required=True,
        help="Tipo de actor a procesar o 'all' para el reporte consolidado"
    )
    args = parser.parse_args()
    
    # 🔄 Definimos qué actores procesar basándonos en el argumento
    if args.actor == "all":
        actores_a_procesar = ["vendor", "carrier", "dc"]
    else:
        actores_a_procesar = [args.actor]
    
    # Listas vacías para ir acumulando los textos en memoria
    reportes_texto_acumulados = []

    # ✅ Verificar que los archivos existen
    print(f"\n📁 Buscando archivos en: {DATA_PROCESSED}")
    for actor_key in ACTOR_CONFIG:
        archivo = DATA_PROCESSED / ACTOR_CONFIG[actor_key]["input_file"]
        existe = "✅" if archivo.exists() else "❌"
        print(f"  {existe} {archivo.name}")
    print()

    
    # 🔁 BUCLE: Procesará uno por uno los actores de la lista
    for actor_key in actores_a_procesar:
        config = ACTOR_CONFIG[actor_key]
        print(f"\n🔋 Procesando secuencialmente: {config['titulo']}")
        
        try:
            input_file = DATA_PROCESSED / config["input_file"]
            with open(input_file, "r", encoding="utf-8") as f:
                json_data = f.read()
        except FileNotFoundError as e:
            print(f"❌ Error de archivos locales para {actor_key}: {e}")
            continue

        # 🚀 EJECUCIÓN DE AGENTE INDIVIDUAL
        print(f"📦 Corriendo Agente de {config['titulo']}...")   
        agente = crear_agente(actor_key, config)
        
        try:
            resultado = await Runner.run(agente, f"JSON:\n{json_data}")
            txt_resultado = construir_segmento_texto(resultado.final_output)
            
            # Guardamos el texto en nuestra lista acumuladora
            reportes_texto_acumulados.append(txt_resultado)
            
            print(f"--- SALIDA GENERADA {config['titulo']} ---")
            print(txt_resultado)
            imprimir_metricas_tokens(config['titulo'], resultado)
            
            
        except Exception as e:
            print(f"❌ Error ejecutando el agente para {actor_key}: {e}")
            continue


    # ═══════════════════════════════════════════════════════════════════════════
    # 💾 EXPORTACIÓN CONSOLIDADA 'agente1_raw.txt' (SOLO CUANDO SE USA 'all')
    # ═══════════════════════════════════════════════════════════════════════════
    if args.actor == "all" and reportes_texto_acumulados:

        ruta_root_processed = Path(__file__).resolve().parent.parent / "data" / "processed"       
        # Aseguramos que se creen tanto /data como /processed si no existen en el servidor
        ruta_root_processed.mkdir(parents=True, exist_ok=True)        
        # Apuntamos el archivo final ahí adentro
        archivo_final_agente1 = ruta_root_processed / "agente1_raw.txt"
        
        # Unimos los tres análisis generados en un solo texto largo
        contenido_agente1 = "\n".join(reportes_texto_acumulados)
            
        # Escribimos el archivo final maestro en UTF-8
        archivo_final_agente1.write_text(contenido_agente1, encoding="utf-8")
        
        print("\n" + "🚀"*3)
        print(f"🔥 [REPORTE MAESTRO GENERADO] Todo el pipeline se consolidó en: '{archivo_final_agente1.resolve()}'")
        print("🚀"*3 + "\n")



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
