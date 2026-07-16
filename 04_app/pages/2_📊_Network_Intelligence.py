"""Network Intelligence — Vista de Ravi (Supply-Chain Analyst).
Reporte agregado de la población de POs tardíos con distribución por etapa,
severidad, y tasa de desacuerdo AI vs humano.
Ticket #103: Panel de métricas agregadas
"""
from pathlib import Path
import re
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
# 🔧 PARSER FLEXIBLE - Maneja múltiples secciones y niveles de riesgo
# ═══════════════════════════════════════════════════════════════════════════

def parse_informe_completo(ruta_txt: Path):
    """Parser que maneja la estructura completa con múltiples actores y niveles de riesgo"""
    if not ruta_txt.exists():
        return [], ""
    
    texto = ruta_txt.read_text(encoding="utf-8")
    
    # Extraer conclusión si existe
    conclusion = ""
    conclusion_match = re.search(r"(?i)\*\*Conclusión:\*\*\s*\n*(.+?)(?=\Z)", texto, re.DOTALL)
    if conclusion_match:
        conclusion = clean_md(conclusion_match.group(1).strip())
    
    # Dividir por secciones principales (### **1., ### **2., ### **3.)
    # Usamos un patrón más flexible que capture números con o sin paréntesis
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
        
        # Extraer TODOS los bloques de riesgo (Alto, Medio, Bajo, etc.)
        # Patrón que captura desde "Zona de Riesgo" hasta la siguiente "Zona de Riesgo" o el final
        patron_bloques = r"\*\*Zona de Riesgo\s+(\w+)[^*]*\*\*\s*\n\*Entidad o Entidades?:\s*([^*\n]+)\*?\s*\n\*Análisis:\s*(.+?)(?=\n\*\*Acción:\*\*|\Z)"
        
        # Buscar todos los bloques de riesgo en esta sección
        bloques_encontrados = re.findall(patron_bloques, sec_text, re.DOTALL)
        
        # Si no encuentra con el patrón anterior, intentar con uno más simple
        if not bloques_encontrados:
            patron_simple = r"\*\*Zona de Riesgo\s+(\w+)[^*]*\*\*\s*\n\*Entidad o Entidades?:\s*([^\n]+)\s*\n\*Análisis:\s*([^\n]+?)(?=\n\*\*Acción:|\Z)"
            bloques_encontrados = re.findall(patron_simple, sec_text, re.DOTALL)
        
        subsecciones = []
        
        for nivel_riesgo, entidades_raw, analisis_raw in bloques_encontrados:
            # Limpiar entidades
            entidades_raw_clean = entidades_raw.replace("*", "").strip()
            # Dividir por comas y " y "
            entidades = []
            for e in entidades_raw_clean.replace(" y ", ",").split(","):
                e_clean = e.strip()
                if e_clean:
                    entidades.append(e_clean)
            
            # Extraer la acción específica para este bloque de riesgo
            # Buscamos la acción que viene después de este análisis
            # Creamos un patrón que busca desde este análisis hasta la siguiente zona de riesgo
            patron_accion = rf"\*Análisis:\s*{re.escape(analisis_raw)}.*?\*\*Acción:\*\*\s*(.+?)(?=\n\*\*Zona de Riesgo|\n\n###|\Z)"
            accion_match = re.search(patron_accion, sec_text, re.DOTALL)
            
            if not accion_match:
                # Intentar con patrón más simple
                patron_accion_simple = r"\*\*Acción:\*\*\s*(.+?)(?=\n\*\*Zona de Riesgo|\n\n###|\Z)"
                accion_match = re.search(patron_accion_simple, sec_text, re.DOTALL)
            
            accion = clean_md(accion_match.group(1).strip()) if accion_match else "No se especificó acción"
            
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
            
            # Extraer métricas del análisis
            metricas = extraer_metricas(analisis_raw)
            
            subsecciones.append({
                "entidades": entidades,
                "metricas": metricas,
                "accion": accion,
                "zona": zona,
                "score": score,
                "nivel_riesgo": nivel_display,
                "analisis": clean_md(analisis_raw)
            })
        
        if subsecciones:
            secciones.append({
                "icono": icono,
                "titulo": titulo,
                "subsecciones": subsecciones,
            })
    
    # Ordenar las secciones por número (1, 2, 3)
    secciones.sort(key=lambda x: int(re.search(r"(\d+)", x["titulo"]).group(1)) if re.search(r"(\d+)", x["titulo"]) else 0)
    
    return secciones, conclusion

def extraer_metricas(analisis: str) -> list:
    """Extrae métricas relevantes del texto de análisis"""
    metricas = []
    
    # Buscar métricas numéricas
    patrones = [
        (r"retraso\s*(?:promedio)?\s*(?:de)?\s*([\d.]+)\s*(?:días|dias)", "Retraso promedio"),
        (r"tasa\s*(?:de)?\s*(?:reprogramación|reprogramacion)\s*(?:de)?\s*([\d.]+)%", "Tasa de reprogramación"),
        (r"tasa\s*(?:de)?\s*(?:causa|raíz)\s*(?:de)?\s*([\d.]+)%", "Tasa de causa raíz"),
        (r"exceso\s*(?:de)?\s*(?:tiempo|por orden)\s*(?:de)?\s*([\d.]+)", "Exceso de tiempo"),
        (r"incumplimiento\s*(?:de)?\s*([\d.]+)%", "Incumplimiento"),
        (r"desviación\s*(?:de)?\s*([\d.]+)\s*(?:días|dias)", "Desviación"),
        (r"puntualidad\s*(?:de)?\s*([\d.]+)%", "Puntualidad"),
    ]
    
    for patron, nombre in patrones:
        matches = re.findall(patron, analisis, re.IGNORECASE)
        for match in matches:
            metricas.append(f"📊 {nombre}: {match}")
    
    # Si no encontramos métricas numéricas, extraemos frases clave
    if not metricas:
        frases_clave = [
            "desempeño significativamente inferior",
            "nivel de riesgo alto",
            "retraso promedio",
            "tasa de reprogramación",
            "umbrales críticos",
            "inestabilidad operativa",
            "problemas recurrentes",
            "factores externos",
            "comportamiento homogéneo",
            "tasas de reprogramación consistentemente altas"
        ]
        
        for frase in frases_clave:
            if frase.lower() in analisis.lower():
                metricas.append(f"⚠️ {frase.capitalize()}")
    
    return metricas[:3]  # Limitamos a 3 métricas

def clean_md(texto: str) -> str:
    """Limpia markdown básico."""
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
    metricas = subsec.get("metricas", [])
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
    
    # Métricas
    metricas_html = ""
    if metricas:
        items = "".join(f'<li style="font-size:0.85rem; margin:0.25rem 0; color:#4a5568;">{m}</li>' for m in metricas)
        metricas_html = f'<div class="metrics" style="margin:0.6rem 0; padding:0.6rem 1rem; background:#f7fafc; border-radius:6px;"><ul style="margin:0; padding-left:1.2rem;">{items}</ul></div>'
    
    # Análisis completo (sin truncar a 180 caracteres)
    analisis_html = ""
    if analisis:
        analisis_html = f'<div style="font-size:0.88rem; color:#2d3748; margin:0.6rem 0; padding:0.6rem 1rem; background:#f7fafc; border-radius:6px; border-left:3px solid #cbd5e0;">📋 <b>Análisis:</b> {analisis}</div>'
    
    # Acción
    accion_html = ""
    if accion and accion != "No se especificó acción":
        accion_html = f'<div class="action" style="margin-top:0.8rem; padding-top:0.8rem; border-top:1px dashed #e2e8f0; font-size:0.9rem; line-height:1.5;"><span style="font-weight:700; color:#3182ce;">🎯 Acción recomendada:</span> {accion}</div>'
    
    return f"""
    <div class="exec-card" style="width: 100%; background:#ffffff; border-radius:12px; padding:1.25rem; margin-bottom: 1.2rem; border-left: 6px solid {borde_color}; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        {render_badge(zona)}
        {empresas_html}
        {score_html}
        {metricas_html}
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
            Inteligencia agregada de red — Patrones sistémicos en POs tardíos
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs globales (SIN "Etapa #1") ────────────────────────────────────────
st.markdown("### 📈 Resumen de la Red")
total_pos = len(df)
severity_counts = df[COL_SEVERITY].value_counts()

coincide_col = COL_LLM_COINCIDE
if coincide_col in df.columns:
    coincide_values = df[coincide_col].dropna()
    total_with_validation = len(coincide_values)
    disagreements = (coincide_values == False).sum()
    agreement_rate = ((coincide_values == True).sum() / total_with_validation * 100) if total_with_validation > 0 else 0
else:
    total_with_validation = 0
    disagreements = 0
    agreement_rate = 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total POs Tardíos", value=total_pos)
with col2:
    high_count = severity_counts.get('HIGH', 0)
    st.metric(label="Severidad Alta", value=f"{high_count} ({high_count/total_pos*100:.1f}%)")
with col3:
    st.metric(label="Tasa de Acuerdo AI", value=f"{agreement_rate:.1f}%")

st.markdown("---")

# ── Gráfico 1: Distribución por Etapa (COMPACTO) ──────────────────────────
st.markdown("### 📦 Distribución por Etapa")
col_chart1, col_chart2 = st.columns(2)

stage_counts = df[COL_STAGE].value_counts().reset_index()
stage_counts.columns = ['stage', 'count']

with col_chart1:
    fig_pie = px.pie(
        stage_counts, names='stage', values='count',
        title="Reparto de Etapas",
        color='stage', color_discrete_map=COLORS
    )
    fig_pie.update_layout(
        height=280, margin=dict(l=10, r=10, t=35, b=10),
        title=dict(font=dict(size=13)),
        legend=dict(font=dict(size=10), itemsizing='constant')
    )
    fig_pie.update_traces(textfont=dict(size=11))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    fig_bar = px.bar(
        stage_counts, x='stage', y='count',
        title="Conteo por Etapa",
        color='stage', color_discrete_map=COLORS
    )
    fig_bar.update_layout(
        height=280, margin=dict(l=10, r=10, t=35, b=10),
        title=dict(font=dict(size=13)),
        xaxis=dict(tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11))
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ── Gráfico 2: Distribución por Severidad (COMPACTO) ──────────────────────
st.markdown("### 🚨 Distribución por Severidad")
col_sev1, col_sev2 = st.columns(2)

severity_counts_df = df['severity'].value_counts().reset_index()
severity_counts_df.columns = ['severity', 'count']

with col_sev1:
    fig_sev_pie = px.pie(
        severity_counts_df, names='severity', values='count',
        title="Distribución de Severidad",
        color='severity',
        color_discrete_map={
            'HIGH': COLORS['high'], 'MEDIUM': COLORS['medium'], 'LOW': COLORS['low']
        }
    )
    fig_sev_pie.update_layout(
        height=280, margin=dict(l=10, r=10, t=35, b=10),
        title=dict(font=dict(size=13)),
        legend=dict(font=dict(size=10), itemsizing='constant')
    )
    fig_sev_pie.update_traces(textfont=dict(size=11))
    st.plotly_chart(fig_sev_pie, use_container_width=True)

with col_sev2:
    st.markdown("#### Detalle de Severidad")
    sev_df = severity_counts_df.copy()
    sev_df.columns = ['Severidad', 'Cantidad']
    sev_df['Porcentaje'] = (sev_df['Cantidad'] / total_pos * 100).round(1)
    st.dataframe(sev_df, use_container_width=True, height=200)

st.markdown("---")

# ── Métricas de Validación (COMPACTAS) ────────────────────────────────────
st.markdown("### ✅ Métricas de Validación")
col_val1, col_val2, col_val3 = st.columns(3)

with col_val1:
    st.markdown(
        f"""
        <div class="custom-card val-card" style="border-left: 4px solid #48bb78;">
            <h4 style="margin: 0 0 0.3rem 0; color: #718096;">Tasa de Acuerdo</h4>
            <p class="big" style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #48bb78;">
                {agreement_rate:.1f}%
            </p>
            <p class="small" style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #718096;">
                AI vs Reason Humano
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_val2:
    st.markdown(
        f"""
        <div class="custom-card val-card" style="border-left: 4px solid #4299e1;">
            <h4 style="margin: 0 0 0.3rem 0; color: #718096;">POs con Validación</h4>
            <p class="big" style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #4299e1;">
                {total_with_validation}
            </p>
            <p class="small" style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #718096;">
                de {total_pos} totales
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_val3:
    st.markdown(
        f"""
        <div class="custom-card val-card" style="border-left: 4px solid #f56565;">
            <h4 style="margin: 0 0 0.3rem 0; color: #718096;">Desacuerdos</h4>
            <p class="big" style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #f56565;">
                {disagreements}
            </p>
            <p class="small" style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #718096;">
                Casos para revisar
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 SECCIÓN DINÁMICA: DIAGNÓSTICO ESTRATÉGICO (desde agente1_raw.txt)
# ═══════════════════════════════════════════════════════════════════════════

# Definir la ruta del archivo
ruta_informe = Path(__file__).parent.parent.parent / "data" / "agente1_raw.txt"

# Título de la sección
st.markdown(
    """
    <div style="text-align:center; margin: 1.5rem 0 1rem 0;">
        <h2 style="margin:0; font-size:1.5rem; color:#2d3748;">🔍 Diagnóstico Estratégico Maestro</h2>
        <p style="color:#718096; margin:0.2rem 0 0 0; font-size:0.95rem;">
            Análisis de Riesgo y Plan de Acciones por Entidad
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Procesar el archivo
if not ruta_informe.exists():
    st.warning("⚠️ No se encontró el archivo `agente1_raw.txt` en la carpeta data/. El agente LLM aún no ha generado el reporte de diagnóstico.")
else:
    # Parsear el informe
    secciones, conclusion = parse_informe_completo(ruta_informe)
    
    if not secciones:
        st.info("📋 El archivo de diagnóstico no contiene secciones de riesgo. Verifica el formato del archivo.")
        # Mostrar el contenido del archivo para debugging
        with st.expander("🔍 Ver contenido del archivo para depuración"):
            st.code(ruta_informe.read_text(encoding="utf-8")[:1000])
    else:
        # Renderizar cada sección
        for sec in secciones:
            # Título de la sección
            st.markdown(
                f'<p class="section-title" style="font-size:1.2rem; font-weight:700; color:#2d3748; margin:1.5rem 0 0.8rem 0; border-left:4px solid #4299e1; padding-left:0.8rem;">{sec["icono"]} {sec["titulo"]}</p>',
                unsafe_allow_html=True,
            )
            
            # 🔥 CAMBIO AQUÍ: Se eliminan las columnas. Cada bloque va directo, uno abajo del otro.
            for subsec in sec["subsecciones"]:
                card_html = render_exec_card_v3(subsec)
                st.markdown(card_html, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)



        # Mostrar conclusión si existe
        if conclusion:
            st.markdown("---")
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #ebf8ff 0%, #bee3f8 100%); 
                            border-left: 4px solid #3182ce; 
                            padding: 1.2rem 1.5rem; 
                            border-radius: 8px; 
                            margin-top: 1rem;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #2c5282;">💡 Conclusión Estratégica</h4>
                    <p style="margin: 0; color: #2d3748; line-height: 1.7; font-size: 0.95rem;">{conclusion}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

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