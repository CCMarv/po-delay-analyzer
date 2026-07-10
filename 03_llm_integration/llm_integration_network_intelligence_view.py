import asyncio
import json
import os
import datetime
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings

# Cargar variables de entorno
load_dotenv()
model_name = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')

# ═══════════════════════════════════════════════════════════════════════════
# 📐 CLASES PYDANTIC PARA ESTRUCTURAR LA SALIDA (OUTPUT_TYPE)
# ═══════════════════════════════════════════════════════════════════════════

class AnalisisBloqueRiesgo(BaseModel):
    nivel_riesgo: str = Field(description="Debe ser exactamente uno de estos valores: 'Crítico', 'Medio' o 'Bajo'")
    entidades: List[str] = Field(description="Lista de nombres de las empresas afectadas en MAYÚSCULAS")
    
    # Exigimos la profundidad analítica que te gustaba de Qwen
    falla_raiz: str = Field(description=(
        "Análisis profundo de negocio. Debe explicar detalladamente el impacto operativo real "
        "de las métricas y conectar los números exactos extraídos del JSON (como Delay_Prom o Tasa_Reschedule). "
        "Debe incluir de forma obligatoria la cadena exacta 'Score_Riesgo_Normalizado=X.X' y desglosar "
        "cronológica o lógicamente CÓMO llegaste a esa conclusión analítica."
    ))
    
    # Exigimos acciones imperativas y detalladas
    accion: str = Field(description=(
        "Plan de intervención inmediato redactado en prosa ejecutiva de alta densidad. "
        "Debe usar verbos en un tono militar e imperativo (Se exige, Se interviene, Se condiciona) "
        "y detallar las medidas comerciales, legales o logísticas con plazos temporales estrictos (ej. 15 o 30 días)."
    ))

class ReporteEspecialista(BaseModel):
    titulo: str = Field(description="Ej: '1. PROVEEDORES', '2. TRANSPORTISTAS' o '3. CENTROS DE DISTRIBUCIÓN'")
    bloques: List[AnalisisBloqueRiesgo] = Field(description="Lista obligatoria con 3 bloques: Crítico, Medio y Bajo")

class ReporteConclusionGlobal(BaseModel):
    conclusion: str = Field(description="Párrafo consolidado de cierre directivo sobre toda la red logística")


# ═══════════════════════════════════════════════════════════════════════════
# 🤖 CONFIGURACIÓN DE AGENTES (TEMPERATURA 0.1, SIN LOOPS, MAX TOKENS 150)
# ═══════════════════════════════════════════════════════════════════════════

vendor_agent = Agent(
    name="Director de Estrategia - Vendors",
    model=model_name,
    output_type=ReporteEspecialista,
    model_settings=ModelSettings(
        max_tokens=400,  # Límite seguro y compacto
        temperature=0.1
    ),
    instructions="""
    Eres el Director de Estrategia de Operaciones en Supply Chain. Devora el JSON de proveedores y genera un informe ejecutivo ultra-conciso en la clase ReporteEspecialista.
    Métrica Excess = HORAS EXCEDIDAS en despacho vs contrato.
    
    Sé breve, usa frases cortas y directo al grano en cada campo:
    - Título: '1. PROVEEDORES'
    - Bloque Crítico: nivel_riesgo='Crítico', entidades en MAYÚSCULAS. En falla_raiz explica en una frase corta cómo sus horas de exceso estrangulan la producción (incluye obligatoriamente 'Score_Riesgo_Normalizado=X'). En accion exige reemplazo o corrección a 15 días en tono imperativo.
    - Bloque Medio: nivel_riesgo='Medio', entidades en MAYÚSCULAS. En falla_raiz detalla brevemente el impacto operativo de su Tasa_Reschedule. En accion ordena monitoreo mensual estricto.
    - Bloque Bajo: nivel_riesgo='Bajo', entidades excelentes en MAYÚSCULAS. En falla_raiz justifica su predictibilidad. En accion ordena blindaje comercial de la cuenta.
    """
)

carrier_agent = Agent(
    name="Director de Estrategia - Carriers",
    model=model_name,
    output_type=ReporteEspecialista,
    model_settings=ModelSettings(
        max_tokens=400,
        temperature=0.1
    ),
    instructions="""
    Eres el Director de Estrategia de Operaciones en Supply Chain. Evalúa la red de transporte con el JSON recibido. Estructura en la clase ReporteEspecialista.
    Métrica Excess = HORAS EXCEDIDAS en ruta o tránsito.
    Regla de Score: 100 es pésimo rendimiento (peligro), 0 es excelencia.
    
    Sé ultra-sintético y ejecutivo en tus descripciones:
    - Título: '2. TRANSPORTISTAS'
    - Bloque Crítico: nivel_riesgo='Crítico', entidades en MAYÚSCULAS. En falla_raiz explica brevemente cómo sus demoras y exceso de horas fracturan la entrega al cliente (incluye obligatoriamente 'Score_Riesgo_Normalizado=X'). En accion detalla la presión comercial a 30 días.
    - Bloque Medio: nivel_riesgo='Medio', entidades en MAYÚSCULAS. En falla_raiz describe problemas de control de flota por su Tasa_Reschedule. En accion impón auditorías obligatorias a sus bitácoras.
    - Bloque Bajo: nivel_riesgo='Bajo', entidades excelentes en MAYÚSCULAS. En falla_raiz resalta su cumplimiento. En accion ordena transferencia táctica de carga a 90 días.
    """
)

dc_agent = Agent(
    name="Director de Estrategia - Centros de Distribución",
    model=model_name,
    output_type=ReporteEspecialista,
    model_settings=ModelSettings(
        max_tokens=400,
        temperature=0.1
    ),
    instructions="""
    Eres el Director de Estrategia de Operaciones en Supply Chain. Analiza el JSON de infraestructura física de los almacenes (DCs). Estructura en la clase ReporteEspecialista.
    Métrica Excess = HORAS EXCEDIDAS operativas en andenes de carga vs contrato.
    Regla de Score: 100 es colapso operativo, 0 es flujo óptimo.
    
    Redacta de forma directa, concisa y sin rodeos teóricos:
    - Título: '3. CENTROS DE DISTRIBUCIÓN'
    - Bloque Crítico: nivel_riesgo='Crítico', entidades en MAYÚSCULAS. En falla_raiz explica en una línea el cuello de botella en andenes conectando Delay_Prom con Excess_por_PO (incluye obligatoriamente 'Score_Riesgo_Normalizado=X'). En accion ordena auditoría física inmediata a 15 días.
    - Bloque Medio: nivel_riesgo='Medio', entidades en MAYÚSCULAS. En falla_raiz vincula la Tasa_Reschedule con problemas en armado de pedidos. En accion exige doble control de picking.
    - Bloque Bajo: nivel_riesgo='Bajo', entidades excelentes en MAYÚSCULAS. En falla_raiz resalta la velocidad de desalojo de andenes. En accion ordena clonar mejores prácticas.
    """
)

master_analyst_agent = Agent(
    name="Analista Maestro - Consolidador",
    model=model_name,
    model_settings=ModelSettings(
        temperature=0.1,
        max_tokens=600
    ),
    output_type=ReporteConclusionGlobal,
    instructions="""
    Recibe los reportes previos de la red de suministro y redacta un único párrafo de conclusión estratégica agregada. 
    Estructura la salida en la clase ReporteConclusionGlobal.
    """
)


# ═══════════════════════════════════════════════════════════════════════════
# 🛠️ TRADUCTOR DE OBJETOS PYDANTIC AL FORMATO TEXTO DE TU PARSER
# ═══════════════════════════════════════════════════════════════════════════

def construir_segmento_texto(reporte: ReporteEspecialista) -> str:
    """Transforma el objeto Pydantic validado al formato exacto de texto que lee tu Streamlit."""
    texto_bloque = f"### **{reporte.titulo}**\n\n"
    
    for b in reporte.bloques:
        lista_empresas = ", ".join(b.entidades)
        # Ajustamos el string para que tu frontend detecte "Crítico", "Medio" o "Bajo" sin problemas
        texto_bloque += f"**Zona de Riesgo {b.nivel_riesgo}**\n"
        texto_bloque += f"*Entidad o Entidades: {lista_empresas}*\n"
        texto_bloque += f"*Falla Raíz: {b.falla_raiz}*\n"
        texto_bloque += f"**Acción:** {b.accion}\n\n"
    
    return texto_bloque


# ═══════════════════════════════════════════════════════════════════════════
# 🔋 PIPELINE DE EJECUCIÓN SECUENCIAL ACUMULATIVO
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    print("🔋 Iniciando Pipeline estructurado (Secuencial, Acumulativo, Temp 0.1, Max Tokens...)...")

    base_path = Path(__file__).parent
    data_folder = base_path / "data"
    data_folder.mkdir(parents=True, exist_ok=True)

    try:
        with open("reporte_vendors.json", "r", encoding="utf-8") as f: json_vendors = f.read()
        with open("reporte_carriers.json", "r", encoding="utf-8") as f: json_carriers = f.read()
        with open("reporte_dcs.json", "r", encoding="utf-8") as f: json_dcs = f.read()
    except FileNotFoundError as e:
        print(f"❌ Error de archivos locales: {e}")
        return

    # 🚀 EJECUCIÓN DE AGENTES + IMPRESIÓN DE SALIDAS EN PANTALLA + TOKENS
    
    # --- AGENTE 1: PROVEEDORES ---
    print("\n📦 Corriendo Agente de Proveedores...")
    r_vendors = await Runner.run(vendor_agent, f"JSON:\n{json_vendors}")
    txt_vendors = construir_segmento_texto(r_vendors.final_output)
    print("--- SALIDA GENERADA VENDORS ---")
    print(txt_vendors)
    imprimir_metricas_tokens("Vendors", r_vendors)

    # --- AGENTE 2: TRANSPORTISTAS ---
    print("\n🚛 Corriendo Agente de Transportistas...")
    r_carriers = await Runner.run(carrier_agent, f"JSON:\n{json_carriers}")
    txt_carriers = construir_segmento_texto(r_carriers.final_output)
    print("--- SALIDA GENERADA CARRIERS ---")
    print(txt_carriers)
    imprimir_metricas_tokens("Carriers", r_carriers)

    # --- AGENTE 3: ALMACENES ---
    print("\n🏢 Corriendo Agente de Almacenes...")
    r_dcs = await Runner.run(dc_agent, f"JSON:\n{json_dcs}")
    txt_dcs = construir_segmento_texto(r_dcs.final_output)
    print("--- SALIDA GENERADA DCs ---")
    print(txt_dcs)
    imprimir_metricas_tokens("Centros de Distribución", r_dcs)

    # --- AGENTE 4: CONSOLIDADOR DE CONCLUSIÓN ---
    print("\n💡 Corriendo Agente Consolidador...")
    paquete_contexto = f"{txt_vendors}\n{txt_carriers}\n{txt_dcs}"
    r_master = await Runner.run(master_analyst_agent, f"Genera la conclusión basándote en esto:\n{paquete_contexto}")
    txt_conclusion = f"**Conclusión:**\n{r_master.final_output.conclusion}"
    print("--- SALIDA GENERADA CONCLUSIÓN ---")
    print(txt_conclusion)
    imprimir_metricas_tokens("Consolidador", r_master)

    # ═══════════════════════════════════════════════════════════════════════════
    # 💾 GUARDADO ACUMULATIVO EN DRIVE/LOCAL CON TIMESTAMPS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Generamos el timestamp exacto para el nombre del archivo
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo_maestro = f"agente1_raw_{timestamp}.txt"
    ruta_salida_streamlit = data_folder / nombre_archivo_maestro

    # Ensamblaje final de los bloques estructurados
    informe_maestro_completo = f"{txt_vendors}{txt_carriers}{txt_dcs}{txt_conclusion}"

    with open(ruta_salida_streamlit, "w", encoding="utf-8") as f:
        f.write(informe_maestro_completo)

    print("\n" + "="*60)
    print(f"🎯 [ÉXITO] Archivo maestro acumulado guardado en: '{ruta_salida_streamlit}'")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
