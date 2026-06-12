# ═══════════════════════════════════════════════════════════════════════
# BLOQUE DE UMBRALES 
# ═══════════════════════════════════════════════════════════════════════

# ── Umbrales operativos  ───────────────────────────────
YARD_THR            = 4.0    # hrs  ─ flag_yard_congestion
DOCK_THR            = 6.0    # hrs  ─ flag_dock_backlog
CARRIER_THR         = 4.0    # hrs  ─ flag_carrier_miss (referencia pipeline)
CARRIER_LAG_STRONG  = 6.0    # hrs  ─ discriminador EDA Fase 1 para auto-class
LEAD_THR            = 3.0    # days ─ flag_short_lead_time
FILL_RATE_THR       = 0.90   # %    ─ _short_ship

# ── Severity Score — factores y pesos ────────────────────────────────────
SEV_MAX_SCORE    = 100

SEV_DELAY_PER_DAY   = 10   # pts/día  ─ hasta 4 días → 40 pts máx
SEV_MAX_DELAY_DAYS  = 4    # cap de días computables
SEV_HOT_PO          = 30   # HOT_PO_FLAG == 1
SEV_CO_FAULT        = 20   # co-responsabilidad ('+' en stage_class)
SEV_SHORT_SHIP      = 15   # _short_ship == True
SEV_CARRIER_LAG     = 15   # carrier_lag_hrs > CARRIER_LAG_STRONG
SEV_YARD            = 10   # flag_yard_congestion == True

# Score máximo teórico: 40+30+20+15+15+10 = 130 → clipado a 100

# ── Bandas de clasificación ───────────────────────────────────────────────
SEV_BANDS = {
    'Low'     : (1,  25),
    'Medium'  : (26, 50),
    'High'    : (51, 75),
    'Critical': (76, 100),
}

# ── Funciones de severity ─────────────────────────────────────────────────
def compute_severity_score(row: pd.Series) -> int:
    """Calcula el Severity Score (0–100). Retorna 0 para POs On-Time."""
    if row.get('IS_LATE') != 'Y':
        return 0

    score = 0
    delay = min(float(row.get('delay_days_calc', 0) or 0), SEV_MAX_DELAY_DAYS)
    score += int(delay) * SEV_DELAY_PER_DAY

    if int(row.get('HOT_PO_FLAG', 0) or 0) == 1:
        score += SEV_HOT_PO

    if '+' in str(row.get('stage_class', '')):
        score += SEV_CO_FAULT

    if bool(row.get('_short_ship', False)):
        score += SEV_SHORT_SHIP

    if float(row.get('carrier_lag_hrs', 0) or 0) > CARRIER_LAG_STRONG:
        score += SEV_CARRIER_LAG

    if bool(row.get('flag_yard_congestion', False)):
        score += SEV_YARD

    return min(score, SEV_MAX_SCORE)


def severity_band(score: int) -> str:
    """Convierte puntaje en banda Low / Medium / High / Critical."""
    if score == 0:
        return 'On-Time'
    for band, (lo, hi) in SEV_BANDS.items():
        if lo <= score <= hi:
            return band
    return 'Critical'


print("✅ Umbrales y funciones Severity definidos.")
print(f"   CARRIER_LAG_STRONG={CARRIER_LAG_STRONG}h | YARD_THR={YARD_THR}h | DOCK_THR={DOCK_THR}h")
print(f"   FILL_RATE_THR={FILL_RATE_THR} | LEAD_THR={LEAD_THR}d")
print(f"   Score máx real: {SEV_MAX_SCORE} pts")
