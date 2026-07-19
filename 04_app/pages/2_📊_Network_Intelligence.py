"""Network Intelligence — Vista de Ravi (Supply-Chain Analyst).
Reporte agregado de la población de POs tardíos con distribución por etapa,
severidad, y tasa de desacuerdo AI vs humano.
Panel de métricas agregadas
"""
from pathlib import Path
import re
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from config import (
    SCORECARDS_DIR, COL_PO, COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE,
    stage_colors, severity_colors, plot_theme, current_theme
)
from services.data_service import load_po_output
from components.navbar import render_navbar

# ─────────────────────────────────────────────────────────────────────────
# RESOLUCIÓN DE RUTAS (RAÍZ DEL REPO) - CORREGIDO
# ─────────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # 02_streamlit_app → repo_root
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Intelligence",
    page_icon="📊",
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

# ── CSS compacto para esta vista ────────────────────────────────────────
st.markdown("""
<style>
    /* KPIs más compactos */
    [data-testid="stMetric"] {
        background-color: var(--surface-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }

    /* Tarjetas del plan ejecutivo */
    .exec-card {
        background: var(--surface-elevated);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        border-left: 6px solid var(--border-subtle);
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .exec-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }
    .exec-card .name {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0.3rem 0 0.3rem 0;
    }
    .exec-card .score {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin: 0 0 0.6rem 0;
    }
    .exec-card .action {
        margin-top: 0.8rem;
        padding-top: 0.8rem;
        border-top: 1px dashed var(--border-subtle);
        font-size: 0.85rem;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    .exec-card .action b { color: var(--accent); }

    /* Badges de riesgo - SEMÁFOROS CON COLORES */
    .badge-risk {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-risk--alto {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }
    .badge-risk--medio {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-risk--bajo {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .badge-risk--sin-datos {
        background-color: #f3f4f6;
        color: #6b7280;
        border: 1px solid #e5e7eb;
    }

    /* Badge de riesgo con círculo de color - SEMÁFORO */
    .risk-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 14px 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .risk-indicator .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }
    .risk-indicator--alto {
        background-color: #fee2e2;
        color: #991b1b;
    }
    .risk-indicator--alto .dot { background-color: #dc2626; }
    
    .risk-indicator--medio {
        background-color: #fef3c7;
        color: #92400e;
    }
    .risk-indicator--medio .dot { background-color: #f59e0b; }
    
    .risk-indicator--bajo {
        background-color: #d1fae5;
        color: #065f46;
    }
    .risk-indicator--bajo .dot { background-color: #10b981; }
    
    .risk-indicator--sin-datos {
        background-color: #f3f4f6;
        color: #6b7280;
    }
    .risk-indicator--sin-datos .dot { background-color: #9ca3af; }

    /* Headers de sección más compactos */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-secondary);
        margin: 0.5rem 0 0.6rem 0;
        border-left: 4px solid var(--accent);
        padding-left: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 🔧 PARSER ULTRA-ROBUSTO INTEGRADO
# ═══════════════════════════════════════════════════════════════════════════

def parse_informe_completo(ruta_txt: Path):
    """Parser unificado que maneja múltiples actores y niveles de riesgo."""
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

        # Regex para capturar bloques de riesgo
        patron_bloques = r"\*\*Zona de Riesgo\s+(\w+)\*\*\s*\n\*?Entidad o Entidades?:\s*([^\n\*]+)\*?\s*\n(?:\*\*|\*)Análisis(?:\*\*|\*)?:?[\s\*]*\n*(.+?)\n(?:\*\*|\*)Acción(?:\*\*|\*)?:?[\s\*]*(.+?)(?=\n\*\*Zona de Riesgo|\n\n###|\Z)"

        bloques_encontrados = re.findall(patron_bloques, sec_text, re.DOTALL)
        subsecciones = []

        for nivel_riesgo, entidades_raw, analisis_raw, accion_raw in bloques_encontrados:
            # Limpiar entidades
            entidades_raw_clean = entidades_raw.replace("*", "").strip()
            entidades = [e.strip() for e in entidades_raw_clean.replace(" y ", ",").split(",") if e.strip()]

            # Determinar zona y score
            nivel_lower = nivel_riesgo.lower()
            if nivel_lower in ["alto", "crítico", "critico", "high"]:
                zona = "alto"
                score = 100.0
                nivel_display = "Alto"
            elif nivel_lower in ["medio", "moderado", "medium"]:
                zona = "medio"
                score = 50.0
                nivel_display = "Medio"
            else:
                zona = "bajo"
                score = 0.0
                nivel_display = "Bajo"

            subsecciones.append({
                "entidades": entidades,
                "zona": zona,
                "score": score,
                "nivel_riesgo": nivel_display,
                "analisis": clean_analysis_md(analisis_raw),
                "accion": clean_analysis_md(accion_raw)
            })

        if subsecciones:
            secciones.append({
                "icono": icono,
                "titulo": titulo,
                "subsecciones": subsecciones,
            })

    # Ordenar las secciones por número
    secciones.sort(key=lambda x: int(re.search(r"(\d+)", x["titulo"]).group(1)) if re.search(r"(\d+)", x["titulo"]) else 0)

    return secciones


# ═══════════════════════════════════════════════════════════════════════════
# 🧼 FUNCIONES DE LIMPIEZA AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

def clean_analysis_md(texto: str) -> str:
    """Limpia el markdown conservando saltos de línea estructurados."""
    texto = texto.strip()
    texto = re.sub(r"^[\s\*]+-\s*", "- ", texto)
    if texto.startswith("-"):
        texto = "<br>" + texto
    texto = texto.replace("\n", "<br>")
    return texto


def clean_md(texto: str) -> str:
    """Limpia markdown básico colapsando a una sola línea (fallback)."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# ═══════════════════════════════════════════════════════════════════════════
# 🎨 RENDERIZADO DE TARJETAS CON SEMÁFOROS
# ═══════════════════════════════════════════════════════════════════════════

def render_risk_badge(zona: str) -> str:
    """Renderiza un badge de riesgo con círculo de color (semáforo)."""
    zona_lower = zona.lower()
    
    if zona_lower == "alto":
        return f'<span class="risk-indicator risk-indicator--alto"><span class="dot"></span>Alto Riesgo</span>'
    elif zona_lower == "medio":
        return f'<span class="risk-indicator risk-indicator--medio"><span class="dot"></span>Riesgo Medio</span>'
    elif zona_lower == "bajo":
        return f'<span class="risk-indicator risk-indicator--bajo"><span class="dot"></span>Bajo Riesgo</span>'
    else:
        return f'<span class="risk-indicator risk-indicator--sin-datos"><span class="dot"></span>Sin datos</span>'


def render_exec_card(subsec: dict, stage_hue: str) -> str:
    """Tarjeta ejecutiva con semáforos de colores."""
    entidades = subsec["entidades"]
    zona = subsec["zona"]
    score = subsec.get("score", 0)
    accion = subsec.get("accion", "")
    analisis = subsec.get("analisis", "")

    # Cabecera con empresas
    if len(entidades) == 1:
        empresas_html = f'<div class="name">{entidades[0]}</div>'
    else:
        badges_empresas = "".join(
            f'<span style="display:inline-block; background:var(--surface-elevated); color:var(--text-secondary); padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:700; margin:4px 6px 4px 0;">{emp}</span>'
            for emp in entidades
        )
        empresas_html = f'<div style="margin: 0.6rem 0; line-height: 1.6;">{badges_empresas}</div>'

    # Score
    score_html = f'<p class="score">Score de Riesgo: <b style="color:var(--text-secondary);">{score:.1f}</b></p>'

    # Análisis
    analisis_html = ""
    if analisis:
        analisis_html = f'<div style="font-size:0.88rem; color:var(--text-secondary); margin:0.6rem 0; padding:0.6rem 1rem; background:var(--surface-elevated); border-radius:6px; border-left:3px solid var(--border-subtle);"><b>Análisis:</b> {analisis}</div>'

    # Acción
    accion_html = ""
    if accion and accion != "No se especificó acción":
        accion_html = f'<div class="action"><b>Acción recomendada:</b> {accion}</div>'

    return f"""
    <div class="exec-card" style="border-left-color: {stage_hue};">
        {render_risk_badge(zona)}
        {empresas_html}
        {score_html}
        {analisis_html}
        {accion_html}
    </div>
    """


# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# Paleta y tokens de Plotly
_STAGE_COLORS = stage_colors()
_SEVERITY = severity_colors()
_PLOT_THEME = plot_theme()

STAGE_COLOR_MAP = {
    s: _STAGE_COLORS.get(str(s).lower(), _STAGE_COLORS["indeterminado"])
    for s in df[COL_STAGE].dropna().unique()
}
SEV_COLOR_MAP = {k: v["color"] for k, v in _SEVERITY.items()}


# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Colores con soporte para tema oscuro ──────────────────────────────────
def get_colors():
    """Retorna colores según el tema activo (light/dark)"""
    theme = current_theme()
    if theme == "dark":
        return {
            "STAGE": {
                "Vendor": "#4DA8DB",
                "Carrier": "#F0B840",
                "DC": "#3FC79A",
                "Indeterminado": "#9B9B9B"
            },
            "SEV": {
                "HIGH": "#E8E8E8",
                "MEDIUM": "#A8A8A8",
                "LOW": "#6B6B6B"
            }
        }
    else:
        return {
            "STAGE": {
                "Vendor": "#ef4444",    # Rojo
                "Carrier": "#f59e0b",   # Ámbar
                "DC": "#3b82f6",        # Azul
                "Indeterminado": "#9ca3af"  # Gris
            },
            "SEV": {
                "HIGH": "#dc2626",      # Rojo
                "MEDIUM": "#f59e0b",    # Ámbar
                "LOW": "#10b981"        # Verde
            }
        }

colors = get_colors()
STAGE_COLOR_MAP = colors["STAGE"]
SEV_COLOR_MAP = colors["SEV"]

# Asegurar que todos los valores tengan color (por si hay valores inesperados)
for stage in df[COL_STAGE].dropna().unique():
    if stage not in STAGE_COLOR_MAP:
        STAGE_COLOR_MAP[stage] = "#6b7280"  # Gris por defecto

for sev in df[COL_SEVERITY].dropna().unique():
    if sev not in SEV_COLOR_MAP:
        SEV_COLOR_MAP[sev] = "#6b7280"      # Gris por defecto

# Tema para Plotly (fuente y grid)
_PLOT_THEME = plot_theme()




# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>📊 Network Intelligence</h1>
        <p>Reporte agregado — Patrones sistémicos en la población de POs tardíos (Vista de Ravi)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════
# 📈 MÉTRICAS EN MEMORIA
# ═══════════════════════════════════════════════════════════════════════════
total_pos = len(df)
severity_counts = df[COL_SEVERITY].value_counts()
n_high = int(severity_counts.get("HIGH", 0))
high_pct = (n_high / total_pos * 100) if total_pos else 0.0

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

# ═══════════════════════════════════════════════════════════════════════════
# 📊 PANEL ASIMÉTRICO: BARRA DE KPIS (IZQ) & GRÁFICOS APILADOS (DER)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("#### Patrones sistémicos en POs tardíos")

col_barra_kpis, col_panel_graficos = st.columns([1, 3])

# ── COLUMNA IZQUIERDA: KPIS ──────────────────────────────────────────────
with col_barra_kpis:
    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
    st.metric(label="Total POs Tardíos", value=f"{total_pos}")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
    st.metric(label="Severidad Alta", value=f"{n_high} ({high_pct:.1f}%)")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
    st.metric(label="Tasa de Acuerdo AI", value=f"{agreement_rate:.1f}%")

# ── COLUMNA DERECHA: GRÁFICOS ─────────────────────────────────────────────
with col_panel_graficos:
    # GRÁFICO 1: DISTRIBUCIÓN POR ETAPA
    st.markdown('<div style="text-align: center;"><p style="font-size: 1.05rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.3rem; display: inline-block;">Distribución por Etapa</p></div>', unsafe_allow_html=True)

    stage_counts = df[COL_STAGE].value_counts().reset_index()
    stage_counts.columns = ['stage', 'count']
    total_stages = stage_counts['count'].sum()
    stage_counts['percentage'] = (stage_counts['count'] / total_stages * 100).round(1)
    stage_counts['dummy'] = 'Etapas'
    
    stage_legend = {
        row['stage']: f"{row['stage']} — {int(row['count'])} ({row['percentage']}%)"
        for _, row in stage_counts.iterrows()
    }

    fig_stage = px.bar(
        stage_counts, x='count', y='dummy', color='stage', orientation='h',
        color_discrete_map=STAGE_COLOR_MAP,
    )
    fig_stage.for_each_trace(lambda t: t.update(name=stage_legend.get(t.name, t.name)))
    fig_stage.update_traces(width=0.4, hovertemplate="<b>%{fullData.name}</b><extra></extra>")
    fig_stage.update_layout(
        height=125, margin={"l": 20, "r": 0, "t": 5, "b": 0},
        xaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "title": ""},
        yaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "title": ""},
        barmode='stack', showlegend=True,
        legend={
            "orientation": "h", "yanchor": "bottom", "y": -1.9, "xanchor": "center", "x": 0.5,
            "title": None, "font": {"size": 12, "color": _PLOT_THEME["font_color"]},
        },
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=_PLOT_THEME["font_color"],
    )
    st.plotly_chart(fig_stage, width="stretch")

    st.markdown("<div style='margin-bottom: 3.5rem;'></div>", unsafe_allow_html=True)

    # GRÁFICO 2: DISTRIBUCIÓN POR SEVERIDAD
    st.markdown('<div style="text-align: center;"><p style="font-size: 1.05rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.3rem; display: inline-block;">Distribución por Severidad</p></div>', unsafe_allow_html=True)

    severity_counts_df = df[COL_SEVERITY].value_counts().reset_index()
    severity_counts_df.columns = ['severity', 'count']
    total_severities = severity_counts_df['count'].sum()
    severity_counts_df['percentage'] = (severity_counts_df['count'] / total_severities * 100).round(1)
    severity_counts_df['dummy'] = 'Severidad'
    
    severity_legend = {
        row['severity']: f"{_SEVERITY.get(row['severity'], {}).get('icon', '')} {row['severity']} — {int(row['count'])} ({row['percentage']}%)"
        for _, row in severity_counts_df.iterrows()
    }

    fig_severity = px.bar(
        severity_counts_df, x='count', y='dummy', color='severity', orientation='h',
        color_discrete_map=SEV_COLOR_MAP,
        category_orders={'severity': ['LOW', 'MEDIUM', 'HIGH']},
    )
    fig_severity.for_each_trace(lambda t: t.update(name=severity_legend.get(t.name, t.name)))
    fig_severity.update_traces(width=0.4, hovertemplate="<b>%{fullData.name}</b><extra></extra>")
    fig_severity.update_layout(
        height=125, margin={"l": 20, "r": 0, "t": 5, "b": 0},
        xaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "title": ""},
        yaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "title": ""},
        barmode='stack', showlegend=True,
        legend={
            "orientation": "h", "yanchor": "bottom", "y": -1.9, "xanchor": "center", "x": 0.5,
            "title": None, "font": {"size": 12, "color": _PLOT_THEME["font_color"]},
        },
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=_PLOT_THEME["font_color"],
    )
    st.plotly_chart(fig_severity, width="stretch")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# 🔥 SECCIÓN DINÁMICA: DIAGNÓSTICO ESTRATÉGICO
# ═══════════════════════════════════════════════════════════════════════════

# ✅ RUTA CORREGIDA: usa DATA_PROCESSED
ruta_informe = DATA_PROCESSED / "agente1_raw.txt"

# 🛠️ MAPEO MAESTRO
CONFIG_ACTORES_COMPLETO = {
    "1. VENDORS": {
        "archivo_json": "reporte_vendors.json",
        "clave_json": "vendors",
        "stage_key": "vendor",
        "tabla_titulo": "Tabla de Métricas Consolidadas: VENDORS",
        "color": "#ef4444",  # Rojo para Vendors
    },
    "2. CARRIERS": {
        "archivo_json": "reporte_carriers.json",
        "clave_json": "carriers",
        "stage_key": "carrier",
        "tabla_titulo": "Tabla de Métricas Consolidadas: CARRIERS",
        "color": "#f59e0b",  # Ámbar para Carriers
    },
    "3. DISTRIBUTION CENTERS": {
        "archivo_json": "reporte_dcs.json",
        "clave_json": "dcs",
        "stage_key": "dc",
        "tabla_titulo": "Tabla de Métricas Consolidadas: DISTRIBUTION CENTERS",
        "color": "#3b82f6",  # Azul para DCs
    },
}

# Título de la sección
st.markdown(
    """
    <div style="text-align:center; margin: 1.5rem 0 1rem 0;">
        <h2 style="margin:0; font-size:2.00rem; color:var(--text-secondary);">Diagnóstico Estratégico</h2>
        <p style="color:var(--text-muted); margin:0.2rem 0 0 0; font-size:1.25rem;">
            Análisis de Riesgo y Recomendaciones de Mejora
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Procesar el archivo del agente de IA
if not ruta_informe.exists():
    st.warning(f"No se encontró el archivo `agente1_raw.txt`. Buscado en: {ruta_informe.resolve()}")
else:
    secciones = parse_informe_completo(ruta_informe)

    if not secciones:
        st.info("El archivo de diagnóstico no contiene secciones de riesgo válidas.")
    else:
        # Recorremos cada actor principal
        for sec in secciones:
            titulo_seccion = sec["titulo"].upper()

            # Config del actor
            config_tabla = None
            for clave_config, valor_config in CONFIG_ACTORES_COMPLETO.items():
                if clave_config in titulo_seccion:
                    config_tabla = valor_config
                    break
            
            # Color para el borde izquierdo de las tarjetas
            stage_hue = config_tabla["color"] if config_tabla else "var(--stage-indeterminado)"

            # Encabezado del Actor
            st.markdown(
                f'<p class="section-title"> {sec["titulo"]}</p>',
                unsafe_allow_html=True,
            )

            # Renderizar todas las tarjetas de este actor
            for subsec in sec["subsecciones"]:
                card_html = render_exec_card(subsec, stage_hue)
                st.markdown(card_html, unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

            # Mostrar la tabla de métricas
            if config_tabla:
                # ✅ RUTA CORREGIDA: usa DATA_PROCESSED
                ruta_json_actor = DATA_PROCESSED / config_tabla["archivo_json"]

                if ruta_json_actor.exists():
                    try:
                        with open(ruta_json_actor, "r", encoding="utf-8") as f:
                            datos_json = json.load(f)

                        diccionario_entidades = datos_json.get(config_tabla["clave_json"], {})

                        if diccionario_entidades:
                            filas_tabla = []
                            for nombre_entidad, metricas in diccionario_entidades.items():
                                filas_tabla.append({
                                    "Entidad": nombre_entidad,
                                    "Riesgo": metricas.get("nivel_riesgo_absoluto") or metricas.get("nivel_riesgo"),
                                    "Delay Prom.": metricas.get("delay_promedio") or metricas.get("delay_prom"),
                                    "Excess / PO": metricas.get("excess_por_po") or metricas.get("excess_time"),
                                    "Reschedule %": metricas.get("tasa_reschedule") or metricas.get("reschedule_rate") or 0,
                                    "Causa Raíz %": metricas.get("tasa_causa_raiz") or metricas.get("causa_raiz_rate") or 0,
                                })

                            df_actor_completo = pd.DataFrame(filas_tabla)

                            st.markdown(f'<p style="font-size:0.92rem; font-weight:600; color:var(--text-secondary); margin: 1rem 0 0.5rem 0.2rem;">{config_tabla["tabla_titulo"]}</p>', unsafe_allow_html=True)
                            st.dataframe(
                                df_actor_completo,
                                width="stretch",
                                hide_index=True,
                                column_config={
                                    "Entidad": st.column_config.TextColumn("Entidad"),
                                    "Riesgo": st.column_config.TextColumn("Riesgo"),
                                    "Delay Prom.": st.column_config.NumberColumn("Delay", format="%.2f d"),
                                    "Excess / PO": st.column_config.NumberColumn("Excess", format="%.1f hrs"),
                                    "Reschedule %": st.column_config.NumberColumn("Resched", format="%.1f%%"),
                                    "Causa Raíz %": st.column_config.NumberColumn("Causa Raíz", format="%.1f%%"),
                                }
                            )
                    except Exception as e:
                        st.caption(f"No se pudieron cargar las métricas en tabla: {e}")
                else:
                    st.caption(f"Archivo de métricas '{config_tabla['archivo_json']}' no localizado en {DATA_PROCESSED}.")

            # Línea divisoria
            st.markdown("<hr style='border-top: 2px solid var(--border-subtle); margin: 2.5rem 0;'>", unsafe_allow_html=True)

st.markdown("---")

# ── Tabla de POs con Desacuerdo ──────────────────────────────────────────
if disagreements > 0:
    st.markdown("### POs con Desacuerdo AI vs Humano")
    df_disagreement = df[df[COL_LLM_COINCIDE] == False].copy()
    st.dataframe(
        df_disagreement[[COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE]],
        width="stretch"
    )

# ── Drill-down Ravi → Diego ──────────────────────────────────────────────
st.markdown("---")
st.markdown("### Ver detalle de un PO (Exception Workbench)")

only_disagree = st.checkbox("Solo POs con desacuerdo AI vs humano", value=False)
pool = df[df[COL_LLM_COINCIDE] == False] if only_disagree else df
po_options = sorted(pool[COL_PO].unique().tolist())

if not po_options:
    st.info("No hay POs que cumplan el filtro seleccionado.")
else:
    col_dd1, col_dd2 = st.columns([3, 1])
    with col_dd1:
        dd_po = st.selectbox(
            "PO_NBR", options=po_options,
            format_func=lambda x: f"PO #{x}", key="ravi_drill_select",
        )
    with col_dd2:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Ver en Exception Workbench →", width="stretch"):
            st.session_state["drilldown_po"] = dd_po
            st.switch_page("pages/1_🔍_Exception_Workbench.py")

# ─ Footer ──────────────────────────────────────────────────────────────────
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