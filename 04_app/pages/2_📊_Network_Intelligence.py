"""Network Intelligence — Vista de Ravi (Supply-Chain Analyst).
Reporte agregado de la población de POs tardíos con distribución por etapa,
severidad, y tasa de desacuerdo AI vs humano.
Ticket #103: Panel de métricas agregadas
"""
from pathlib import Path
import re
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from config import COLORS, COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE
from services.data_service import load_po_output
from components.navbar import render_navbar

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navbar superior ─────────────────────────────────────────────────────────
render_navbar(active_page="ravi")

# ─ Cargar CSS personalizado ────────────────────────────────────────────────
css_file = Path(__file__).parent.parent / "assets" / "styles.css"
if css_file.exists():
    with open(css_file, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── CSS compacto para esta vista ───────────────────────────────────────────
st.markdown("""
<style>
    /* KPIs más compactos */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }

    /* Tarjetas del plan ejecutivo */
    .exec-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
        height: 100%;
        transition: transform 0.2s;
    }
    .exec-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .exec-card .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .badge-red    { background: #fed7d7; color: #c53030; }
    .badge-yellow { background: #feebc8; color: #c05621; }
    .badge-green  { background: #c6f6d5; color: #276749; }
    .exec-card .name { font-size: 1.05rem; font-weight: 700; color: #1a202c; margin: 0 0 0.3rem 0; }
    .exec-card .score { font-size: 0.75rem; color: #a0aec0; margin: 0 0 0.5rem 0; }
    .exec-card .metrics {
        margin: 0.5rem 0;
        padding: 0.5rem 0.6rem;
        background: #f7fafc;
        border-radius: 6px;
        font-size: 0.78rem;
    }
    .exec-card .metrics ul {
        margin: 0;
        padding-left: 1.2rem;
    }
    .exec-card .metrics li {
        margin: 0.2rem 0;
        color: #4a5568;
        line-height: 1.4;
    }
    .exec-card .action {
        margin-top: 0.6rem;
        padding-top: 0.6rem;
        border-top: 1px dashed #e2e8f0;
        font-size: 0.8rem;
        color: #2d3748;
        line-height: 1.5;
    }
    .exec-card .action b { color: #3182ce; }

    /* Cards de validación compactas */
    .val-card { padding: 0.8rem 1rem !important; }
    .val-card h4 { font-size: 0.85rem !important; }
    .val-card p.big { font-size: 1.5rem !important; }
    .val-card p.small { font-size: 0.75rem !important; }

    /* Headers de sección más compactos */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #2d3748;
        margin: 0.5rem 0 0.6rem 0;
        border-left: 4px solid #4299e1;
        padding-left: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════════════
# 🔧 PARSER ULTRA-ROBUSTO INTEGRADO 
# ═══════════════════════════════════════════════════════════════════════════

def parse_informe_completo(ruta_txt: Path):
    """Parser unificado que maneja múltiples actores y niveles de riesgo sin usar conclusiones."""
    if not ruta_txt.exists():
        return []
    
    texto = ruta_txt.read_text(encoding="utf-8")
    
    # Dividir por secciones principales (### **1., ### **2., ### **3.)
    secciones_raw = re.split(r"(?=###\s+\*\*\d+\.)", texto)
    secciones = []
    
    # Mapeo de íconos por tipo de entidad
    iconos_map = {
        "VENDORS": "🏭",
        "PROVEEDORES": "🏭", 
        "TRANSPORTISTAS": "🚛",
        "CARRIERS": "🚛",
        "CENTROS DE DISTRIBUCIÓN": "🏢",
        "DCs": "🏢",
        "DISTRIBUTION CENTERS": "🏢"
    }
    
    for sec_text in secciones_raw:
        sec_text = sec_text.strip()
        if not sec_text or not sec_text.startswith("###"):
            continue
        
        # Extraer título de la sección
        primera_linea = sec_text.split("\n")[0]
        titulo_match = re.search(r"###\s+\*\*(\d+\.\s+[A-ZÁÉÍÓÚÑ\s\(\)]+)\*\*", primera_linea)
        titulo = titulo_match.group(1).strip() if titulo_match else "Operaciones"
        
        # Determinar el tipo de actor para el ícono
        icono = "📌"
        titulo_upper = titulo.upper()
        for key, icon in iconos_map.items():
            if key in titulo_upper:
                icono = icon
                break
        
        # 🔥 REGEX MAESTRA CORREGIDA: 
        # Captura Análisis y Acción al mismo tiempo, soportando el formato real (**Análisis:** y **Acción:**)
        # Modifica ligeramente el patrón unificado de tu función para capturar el texto limpio:
        patron_bloques_unificado = r"\*\*Zona de Riesgo\s+(\w+)\*\*\s*\n\*?Entidad o Entidades?:\s*([^\n\*]+)\*?\s*\n(?:\*\*|\*)Análisis(?:\*\*|\*)?:?[\s\*]*\n*(.+?)\n(?:\*\*|\*)Acción(?:\*\*|\*)?:?[\s\*]*(.+?)(?=\n\*\*Zona de Riesgo|\n\n###|\Z)"
        
        bloques_encontrados = re.findall(patron_bloques_unificado, sec_text, re.DOTALL)
        subsecciones = []
        
        for nivel_riesgo, entidades_raw, analisis_raw, accion_raw in bloques_encontrados:
            # Limpiar entidades (quitando asteriscos de los extremos)
            entidades_raw_clean = entidades_raw.replace("*", "").strip()
            
            # Dividir por comas y " y "
            entidades = []
            for e in entidades_raw_clean.replace(" y ", ",").split(","):
                e_clean = e.strip()
                if e_clean:
                    entidades.append(e_clean)
            
            # Determinar zona y score basado en el nivel de riesgo
            nivel_lower = nivel_riesgo.lower()
            if nivel_lower in ["alto", "crítico", "critico", "high"]:
                zona = "roja"
                score = 100.0
                nivel_display = "Alto"
            elif nivel_lower in ["medio", "moderado", "medium"]:
                zona = "media"
                score = 50.0
                nivel_display = "Medio"
            else:  # bajo, low, etc.
                zona = "verde"
                score = 0.0
                nivel_display = "Bajo"
            
            subsecciones.append({
                "entidades": entidades,
                "zona": zona,
                "score": score,
                "nivel_riesgo": nivel_display,
                "analisis": clean_analysis_md(analisis_raw),
                "accion": clean_analysis_md(accion_raw)  # Mantiene las viñetas en la acción también
            })
        
        if subsecciones:
            secciones.append({
                "icono": icono,
                "titulo": titulo,
                "subsecciones": subsecciones,
            })
    
    # Ordenar las secciones por número (1, 2, 3)
    secciones.sort(key=lambda x: int(re.search(r"(\d+)", x["titulo"]).group(1)) if re.search(r"(\d+)", x["titulo"]) else 0)
    
    return secciones


# ═══════════════════════════════════════════════════════════════════════════
# 🧼 FUNCIONES DE LIMPIEZA AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

def clean_analysis_md(texto: str) -> str:
    """Limpia el markdown conservando saltos de línea estructurados para listas en HTML"""
    texto = texto.strip()
    
    # 🧼 Quita dobles asteriscos residuales que puedan quedar al inicio del bloque
    texto = re.sub(r"^[\s\*]+-\s*", "- ", texto)
    
    # 🚨 SOLUCIÓN: Si el texto de la acción empieza con un bullet '-', 
    # le metemos un salto de línea HTML al inicio para obligarlo a bajar de renglón
    if texto.startswith("-"):
        texto = "<br>" + texto
        
    # Convierte todos los saltos de línea intermedios en etiquetas HTML <br>
    texto = texto.replace("\n", "<br>")
    
    return texto



def clean_md(texto: str) -> str:
    """Limpia markdown básico colapsando a una sola línea (para fallback)"""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# ═══════════════════════════════════════════════════════════════════════════
# 🎨 RENDERIZADO DE TARJETAS MEJORADO
# ══════════════════════════════════════════════════════════════════════════

def render_badge(zona: str) -> str:
    """Renderiza una badge según la zona de riesgo"""
    mapa = {
        "roja":  ("badge-red",    "🔴 Alto Riesgo"),
        "media": ("badge-yellow", "🟡 Riesgo Medio"),
        "verde": ("badge-green",  "🟢 Bajo Riesgo"),
    }
    clase, texto = mapa.get(zona, ("badge-yellow", "🟡 Riesgo Medio"))
    return f'<span class="badge {clase}">{texto}</span>'



def render_exec_card_v3(subsec: dict) -> str:
    """Renderiza una tarjeta ejecutiva que abarca el 100% del ancho de página"""
    entidades = subsec["entidades"]
    zona = subsec["zona"]
    score = subsec.get("score", 0)
    accion = subsec.get("accion", "")
    analisis = subsec.get("analisis", "")
    
    # Color de borde izquierdo basado en la zona
    borde_color = "#fed7d7" if zona == "roja" else "#feebc8" if zona == "media" else "#c6f6d5"
    
    # Crear cabecera con empresas
    if len(entidades) == 1:
        nombre_principal = entidades[0]
        icono_alerta = "🚨 " if zona == "roja" else ""
        empresas_html = f'<div class="name" style="margin-top:0.4rem; font-size:1.3rem; font-weight:800; color:#1a202c;">{icono_alerta}{nombre_principal}</div>'
    else:
        badges_empresas = "".join(
            f'<span style="display:inline-block; background:#edf2f7; color:#2d3748; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:700; margin:4px 6px 4px 0;">{emp}</span>' 
            for emp in entidades
        )
        empresas_html = f'<div style="margin: 0.6rem 0; line-height: 1.6;">{badges_empresas}</div>'
    
    # Score
    score_html = f'<p class="score" style="margin:0 0 0.6rem 0; font-size:0.85rem; color:#718096;">Score de Riesgo: <b style="color:#2d3748;">{score:.1f}</b></p>'
    
   
    # Análisis completo (sin truncar a 180 caracteres)
    analisis_html = ""
    if analisis:
        analisis_html = f'<div style="font-size:0.88rem; color:#2d3748; margin:0.6rem 0; padding:0.6rem 1rem; background:#f7fafc; border-radius:6px; border-left:3px solid #cbd5e0;">📋 <b>Análisis:</b> {analisis}</div>'
    
    # Acción
    accion_html = ""
    if accion and accion != "No se especificó acción":
        accion_html = f'<div class="action" style="margin-top:0.8rem; padding-top:0.8rem; border-top:1px dashed #e2e8f0; font-size:0.9rem;">🎯 <b>Acción recomendada:</b> {accion}</div>'


    return f"""
    <div class="exec-card" style="width: 100%; background:#ffffff; border-radius:12px; padding:1.25rem; margin-bottom: 1.2rem; border-left: 6px solid {borde_color}; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        {render_badge(zona)}
        {empresas_html}
        {score_html}
        {analisis_html}
        {accion_html}
    </div>
    """



# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1> Network Intelligence</h1>
        <p style="color: #718096; font-size: 1rem;">
    </div>
    """,
    unsafe_allow_html=True,
)



# ═══════════════════════════════════════════════════════════════════════════
# 📊 PANEL ASIMÉTRICO: BARRA DE KPIS (IZQ) & GRÁFICOS APILADOS (DER)
# ═══════════════════════════════════════════════════════════════════════════
# 🎨 COLORES PROFESIONALES COMPARTIDOS
PROFESSIONAL_COLORS = {
    # Etapas
    "Vendor": "#1e3a8a", "Carrier": "#3b82f6", "DC": "#0d9488", "Indeterminado": "#94a3b8",
    # Severidades (Mapeo automático para minúsculas/mayúsculas si tu DF varía)
    "HIGH": "#1e3a8a", "MEDIUM": "#3b82f6", "LOW": "#94a3b8",
    "high": "#1e3a8a", "medium": "#3b82f6", "low": "#94a3b8"
}

st.markdown("#### Patrones sistémicos en POs tardíos")

# 📐 CREAMOS LAS COLUMNAS PRINCIPALES: Peso 1 para KPIs (angosto) y 3 para Gráficos (ancho)
col_barra_kpis, col_panel_graficos = st.columns([1, 3])


# ── COLUMNA IZQUIERDA (SÚPER ANGOSTA): TARJETICAS KPI VERTICALES ──────────
with col_barra_kpis:
    # Espaciador sutil para alinearlo visualmente con el título de los gráficos
    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
    
    # Tarjeta 1
    st.metric(label="Total POs Tardíos", value=f"{247}")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
    
    # Tarjeta 2
    st.metric(label="Severidad Alta", value="81 (32.8%)")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
    
    # Tarjeta 3
    st.metric(label="Tasa de Acuerdo AI", value="87.4%")


# ── COLUMNA DERECHA (ANCHA): GRÁFICOS UNO ENCIMA DEL OTRO ──────────────────
with col_panel_graficos:
    
    # GRÁFICO 1: DISTRIBUCIÓN POR ETAPA
    st.markdown('<div style="text-align: center;"><p style="font-size: 1.05rem; font-weight: 700; color: #2d3748; margin-bottom: 0.3rem; display: inline-block;"> Distribución por Etapa</p></div>', unsafe_allow_html=True)
    
    stage_counts = df[COL_STAGE].value_counts().reset_index()
    stage_counts.columns = ['stage', 'count']
    total_stages = stage_counts['count'].sum()
    stage_counts['percentage'] = (stage_counts['count'] / total_stages * 100).round(1)
    stage_counts['dummy'] = 'Etapas'

    fig_stage = px.bar(
        stage_counts, x='count', y='dummy', color='stage', orientation='h',
        color_discrete_map=PROFESSIONAL_COLORS, custom_data=['percentage'], text='count'
    )
    fig_stage.update_traces(
        texttemplate="<b>%{x}</b> (%{customdata}%)", textposition="inside",
        insidetextanchor="middle", textfont=dict(size=12, color="white"), width=0.4,
        hovertemplate="<b>%{scale_name}</b><br>Cantidad: %{x}<br>Porcentaje: %{customdata}%<extra></extra>"
    )
    fig_stage.update_layout(
        height=125, margin=dict(l=20, r=0, t=5, b=0), # Añadimos margen izquierdo para despegar de los KPIs
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
        barmode='stack', showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-1.9, xanchor="center", x=0.5,
            title=None, font=dict(size=12)
        )
    )
    st.plotly_chart(fig_stage, use_container_width=True)
    
    # Espaciador vertical elegante entre ambos gráficos
    st.markdown("<div style='margin-bottom: 3.5rem;'></div>", unsafe_allow_html=True)

    # GRÁFICO 2: DISTRIBUCIÓN POR SEVERIDAD
    st.markdown('<div style="text-align: center;"><p style="font-size: 1.05rem; font-weight: 700; color: #2d3748; margin-bottom: 0.3rem; display: inline-block;"> Distribución por Severidad</p></div>', unsafe_allow_html=True)

    severity_counts_df = df['severity'].value_counts().reset_index()
    severity_counts_df.columns = ['severity', 'count']
    total_severities = severity_counts_df['count'].sum()
    severity_counts_df['percentage'] = (severity_counts_df['count'] / total_severities * 100).round(1)
    severity_counts_df['dummy'] = 'Severidad'

    fig_severity = px.bar(
        severity_counts_df, x='count', y='dummy', color='severity', orientation='h',
        color_discrete_map=PROFESSIONAL_COLORS, custom_data=['percentage'], text='count'
    )
    fig_severity.update_traces(
        texttemplate="<b>%{x}</b> (%{customdata}%)", textposition="inside",
        insidetextanchor="middle", textfont=dict(size=12, color="white"), width=0.4,
        hovertemplate="<b>%{scale_name}</b><br>Cantidad: %{x}<br>Porcentaje: %{customdata}%<extra></extra>"
    )
    fig_severity.update_layout(
        height=125, margin=dict(l=20, r=0, t=5, b=0),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
        barmode='stack', showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-1.9, xanchor="center", x=0.5,
            title=None, font=dict(size=12)
        )
    )
    st.plotly_chart(fig_severity, use_container_width=True)

st.markdown("---")



# 📈 LOGÍSTICA DE MÉTRICAS EN MEMORIA (No genera elementos visuales) ───
total_pos = len(df)
severity_counts = df[COL_SEVERITY].value_counts()

coincide_col = COL_LLM_COINCIDE
if coincide_col in df.columns:
    coincide_values = df[coincide_col].dropna()
    total_with_validation = len(coincide_values)
    disagreements = (coincide_values == False).sum() # 👈 RESCATADO: Cuenta los desacuerdos
    agreement_rate = ((coincide_values == True).sum() / total_with_validation * 100) if total_with_validation > 0 else 0
else:
    total_with_validation = 0
    disagreements = 0
    agreement_rate = 0
    


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 SECCIÓN DINÁMICA: DIAGNÓSTICO ESTRATÉGICO CON DESGLOSE COMPLETO POR ACTOR
# ═══════════════════════════════════════════════════════════════════════════

# 1. Definición de rutas base hacia los archivos correspondientes
ruta_base_03 = Path(__file__).resolve().parent.parent.parent / "03_llm_integration"
ruta_informe = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "agente1_raw.txt"

# 🛠️ MAPEO MAESTRO: Sincroniza cada sección del reporte con su JSON y clave correspondiente
CONFIG_ACTORES_COMPLETO = {
    "1. VENDORS": {
        "archivo_json": "reporte_vendors.json",
        "clave_json": "vendors",
        "emoji_tabla": "Tabla de Métricas Consolidadas: VENDORS"
    },
    "2. CARRIERS": {
        "archivo_json": "reporte_carriers.json",
        "clave_json": "carriers",
        "emoji_tabla": "Tabla de Métricas Consolidadas: CARRIERS"
    },
    "3. DISTRIBUTION CENTERS": {
        "archivo_json": "reporte_dcs.json",
        "clave_json": "dcs",
        "emoji_tabla": "Tabla de Métricas Consolidadas: DISTRIBUTION CENTERS"
    }
}

# Título de la sección
st.markdown(
    """
    <div style="text-align:center; margin: 1.5rem 0 1rem 0;">
        <h2 style="margin:0; font-size:2.00rem; color:#2d3748;">Diagnóstico Estratégico </h2>
        <p style="color:#718096; margin:0.2rem 0 0 0; font-size:1.25rem;">
            Análisis de Riesgo y Recomendaciones de Mejora
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Procesar el archivo del agente de IA
if not ruta_informe.exists():
    st.warning(f"⚠️ No se encontró el archivo `agente1_raw.txt`. Buscado en: {ruta_informe.resolve()}")
else:
    secciones = parse_informe_completo(ruta_informe)
    
    if not secciones:
        st.info("📋 El archivo de diagnóstico no contiene secciones de riesgo válidas.")
    else:
        # 🔄 1. RECORREMOS CADA ACTOR PRINCIPAL (VENDORS -> CARRIERS -> DCs)
        for sec in secciones:
            titulo_seccion = sec["titulo"].upper()
            
            # Encabezado del Actor (Abarca el 100% del ancho)
            st.markdown(
                f'<p class="section-title" style="font-size:1.2rem; font-weight:700; color:#2d3748; margin:2.5rem 0 1rem 0; border-left:4px solid #4299e1; padding-left:0.8rem;">{sec["icono"]} {sec["titulo"]}</p>',
                unsafe_allow_html=True,
            )
            
            # 🔄 2. APILAMOS TODAS LAS CARDS QUE SVALGAN PARA ESTE ACTOR (Alto, Medio, Bajo...)
            for subsec in sec["subsecciones"]:
                card_html = render_exec_card_v3(subsec)
                st.markdown(card_html, unsafe_allow_html=True)
                # Separación sutil entre tarjetas del mismo actor
                st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)
            
            # Espacio intermedio antes de pintar la tabla
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
            
            # 📂 3. PROCESAMOS Y RENDERIZAMOS LA TABLA COMPLETA DE ESTE ACTOR ABAJO
            config_tabla = None
            for clave_config, valor_config in CONFIG_ACTORES_COMPLETO.items():
                if clave_config in titulo_seccion:
                    config_tabla = valor_config
                    break
            
            if config_tabla:
                ruta_json_actor = ruta_base_03 / config_tabla["archivo_json"]
                
                if ruta_json_actor.exists():
                    try:
                        import json
                        with open(ruta_json_actor, "r", encoding="utf-8") as f:
                            datos_json = json.load(f)
                        
                        diccionario_entidades = datos_json.get(config_tabla["clave_json"], {})
                        
                        if diccionario_entidades:
                            filas_tabla = []
                            for nombre_entidad, metricas in diccionario_entidades.items():
                                
                                # Extraemos las tasas directo del JSON sin dividir entre 100
                                tasa_resched_raw = metricas.get("tasa_reschedule") or metricas.get("reschedule_rate") or 0
                                tasa_causa_raw = metricas.get("tasa_causa_raiz") or metricas.get("causa_raiz_rate") or 0
                                
                                filas_tabla.append({
                                    "Entidad": nombre_entidad,
                                    "Riesgo": metricas.get("nivel_riesgo_absoluto") or metricas.get("nivel_riesgo"),
                                    "Delay Prom.": metricas.get("delay_promedio") or metricas.get("delay_prom"),
                                    "Excess / PO": metricas.get("excess_por_po") or metricas.get("excess_time"),
                                    "Reschedule %": tasa_resched_raw,  
                                    "Causa Raíz %": tasa_causa_raw     
                                    
                                    })
                            
                            df_actor_completo = pd.DataFrame(filas_tabla)
                            
                            # Renderizado de la tabla completa abajo de sus cards
                            st.markdown(f'<p style="font-size:0.92rem; font-weight:600; color:#4a5568; margin: 1rem 0 0.5rem 0.2rem;"> {config_tabla["emoji_tabla"]}</p>', unsafe_allow_html=True)
                            st.dataframe(
                                df_actor_completo,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Entidad": st.column_config.TextColumn("Entidad"),
                                    "Riesgo": st.column_config.TextColumn("Riesgo"),
                                    "Delay Prom.": st.column_config.NumberColumn("Delay", format="%.2f d"),
                                    "Excess / PO": st.column_config.NumberColumn("Excess", format="%.1f hrs"),
                                    "Reschedule %": st.column_config.NumberColumn("Resched", format="%.1f%%"),
                                    "Causa Raíz %": st.column_config.NumberColumn("Causa Raíz", format="%.1f%%")
                                }
                            )
                    except Exception as e:
                        st.caption(f"ℹ️ No se pudieron cargar las métricas en tabla: {e}")
                else:
                    st.caption(f"ℹ️ Archivo de métricas '{config_tabla['archivo_json']}' no localizado.")
            
            # Línea divisoria gruesa para cerrar el bloque completo del actor antes de pasar al siguiente
            st.markdown("<hr style='border-top: 2px solid #e2e8f0; margin: 2.5rem 0;'>", unsafe_allow_html=True)

st.markdown("---")


# ── Tabla de POs con Desacuerdo (SE MANTIENE AL FINAL) ─────────────────────
if disagreements > 0:
    st.markdown("### ⚠️ POs con Desacuerdo AI vs Humano")
    df_disagreement = df[df[COL_LLM_COINCIDE] == False].copy()
    st.dataframe(
        df_disagreement[[COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE]],
        use_container_width=True
    )


# ─ Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="simple-footer">
        <p>Network Intelligence · Vista de Ravi (Supply-Chain Analyst)</p>
        <p>Reporte agregado de patrones sistémicos en la red de POs tardíos</p>
    </div>
    """,
    unsafe_allow_html=True,
)