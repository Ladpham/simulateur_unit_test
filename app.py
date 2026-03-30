import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Waribei – Unit Economics", layout="wide")
DUREE_PERIODE_LIQUIDITE_JOURS = 10

# --------------------------------------------------
# PRESETS HISTORIQUES (source : MEMORY.md + dashboard réel)
#
# revenu_pct  = MRR / volume décaissé × 100
# cycles/mois = volume décaissé / avg loan book
# loan_book_k = moyenne (book opening + book closing) / 2
#
# Jan 2026 : MRR 17 530€, disbursed 408k€, avg book 229k€ → revenu=4.30%, cycles=1.78
# Fév 2026 : MRR 16 203€, disbursed 355k€, avg book 220k€ → revenu=4.57%, cycles=1.61
# --------------------------------------------------
PRESETS_BY_DATE = {
    date(2025, 6, 1): {
        "name": "Réel — Jun 2025",
        "revenu_pct": 3.73,
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.21,
        "defaut_30j_pct": 1.43,
        "loan_book_k": 80.0,
        "cycles_per_month": 2.0,
    },
    date(2025, 12, 1): {
        "name": "Réel — Dec 2025",
        "revenu_pct": 3.76,
        "cout_paiement_pct": 1.80,
        "cout_liquidite_10j_pct": 0.36,
        "defaut_30j_pct": 1.00,
        "loan_book_k": 156.5,   # net loan portfolio Dec 2025 = 156 452€
        "cycles_per_month": 2.82,  # 440 578€ décaissés / 156 452€ net book
    },
    date(2026, 1, 1): {
        "name": "Réel — Jan 2026",
        "revenu_pct": 4.30,    # 17 530€ MRR / 407 904€ décaissés (exact)
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,  # PAR30 ~1.5% (base transactions au 30/03)
        "loan_book_k": 148.6,   # net loan portfolio Jan 2026 = 148 648€
        "cycles_per_month": 2.74,  # 407 904€ / 148 648€ net book
    },
    date(2026, 2, 1): {
        "name": "Réel — Fév 2026",
        "revenu_pct": 4.58,    # 16 203€ MRR / 354 367€ décaissés (exact)
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,
        "loan_book_k": 135.0,   # net loan portfolio Fév 2026 = 135 005€
        "cycles_per_month": 2.63,  # 354 367€ / 135 005€ net book
    },
    date(2026, 6, 1): {
        "name": "Projection — Jun 2026",
        "revenu_pct": 3.80,
        "cout_paiement_pct": 1.20,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 1.00,
        "loan_book_k": 400.0,
        "cycles_per_month": 2.0,
    },
}

DEFAULT_DATE = date(2026, 2, 1)  # dernière donnée réelle disponible
HISTORY_DATES = [
    date(2025, 6, 1),
    date(2025, 12, 1),
    date(2026, 1, 1),
    date(2026, 2, 1),
]

# --------------------------------------------------
# SCÉNARIOS RAPIDES — alignés sur la narrative investisseur
#
# 1. Réalité Fév 2026    → état actuel, EBITDA ~-11k€
# 2. Break-even OB       → 340k loan book + Open Banking → EBITDA ~0€
# 3. Post-Seed 12 mois   → 600k loan book, OB partiel → EBITDA légèrement positif
# 4. Series A target     → 1.5M loan book, full OB, score mature → EBITDA +18k€
# 5. Scénario Seed deck  → chiffres du pitch deck original (conservé pour cohérence)
# --------------------------------------------------
SCENARIOS_PRESETS = {
    "Custom": None,
    "Réalité — Fév 2026": {
        # Source : tableau financier — données réelles exactes
        # Volume décaissé : 354 367€ | Net book : 135 005€ | MRR : 16 203€
        # EBITDA attendu : ~-10.8k€ (réel : -10 623€ ✓)
        "revenu_pct": 4.58,           # 16 203€ / 354 367€ (exact)
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,       # PAR30 ~1.5% au 30/03
        "loan_book_k": 135.0,         # net loan portfolio Fév 2026 = 135 005€
        "cycles_per_month": 2.63,     # 354 367€ / 135 005€
        "avg_loan_value_eur": 338.0,  # 354 367€ / 1 050 prêts = 337.5€
        "tx_per_client_per_month": 2.6,  # 1 050 prêts / ~400 retailers
        "opex_current_k": 12.0,       # burn réel Jan-Fév 2026
        "scenario_name_autofill": "Réalité — Fév 2026",
    },
    "Break-even — Open Banking": {
        # Open Banking : frais paiement 1.75% → 0.50% (Visa/MC éliminés)
        # Scoring WariBrain : PAR30 1.50% → 0.80%
        # Net book 250k × 2.6 cycles → volume ~650k
        # CM% = 4.40 - 0.50 - 0.35 - 0.80 = 2.75% → EBITDA ~+2k€ à opex 12k€
        "revenu_pct": 4.40,
        "cout_paiement_pct": 0.50,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.80,
        "loan_book_k": 250.0,         # net book cible pour break-even
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 12.0,       # même équipe, pas de nouvelles embauches
        "scenario_name_autofill": "Break-even — Open Banking",
    },
    "Post-Seed — 12 mois": {
        # 12 mois après clôture Seed (1M€)
        # Net book via facility dette MFI, OB déployé partiellement
        # Net book 460k × 2.6 → volume ~1.2M
        # CM% = 4.40 - 0.80 - 0.35 - 0.90 = 2.35% → EBITDA ~+10k€ à opex 18k€
        "revenu_pct": 4.40,
        "cout_paiement_pct": 0.80,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.90,
        "loan_book_k": 460.0,         # net book cible 12 mois post-Seed
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 18.0,       # 1-2 embauches post-Seed
        "scenario_name_autofill": "Post-Seed — 12 mois",
    },
    "Series A target": {
        # Cible levée Series A : net book ~1.15M, full OB, score mature
        # Net book 1 150k × 2.6 → volume ~3M
        # CM% = 4.00 - 0.50 - 0.35 - 0.60 = 2.55% → EBITDA +18k€ à opex 35k€ ✓
        "revenu_pct": 4.00,
        "cout_paiement_pct": 0.50,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.60,
        "loan_book_k": 1150.0,        # net book Series A
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 35.0,       # équipe scale (tech, ops, growth)
        "scenario_name_autofill": "Series A target",
    },
    "Scénario Seed (deck)": {
        # Chiffres du pitch deck Seed — conservés pour cohérence narrative
        "revenu_pct": 3.77,
        "cout_paiement_pct": 1.38,
        "cout_liquidite_10j_pct": 0.34,
        "defaut_30j_pct": 1.26,
        "loan_book_k": 294.0,
        "cycles_per_month": 3.3,
        "avg_loan_value_eur": 300.0,
        "tx_per_client_per_month": 2.9,
        "opex_current_k": 12.0,
        "scenario_name_autofill": "Scénario Seed (deck)",
    },
}

def apply_scenario_preset(name: str):
    preset = SCENARIOS_PRESETS.get(name)
    if not preset:
        return
    allowed = {
        "revenu_pct", "cout_paiement_pct", "cout_liquidite_10j_pct", "defaut_30j_pct",
        "loan_book_k", "cycles_per_month", "avg_loan_value_eur", "tx_per_client_per_month",
        "opex_current_k", "scenario_name_autofill",
    }
    for k, v in preset.items():
        if k not in allowed:
            continue
        st.session_state[k] = v

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []
if "baseline" not in st.session_state:
    st.session_state.baseline = None
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = DEFAULT_DATE
if "last_loaded_date" not in st.session_state:
    st.session_state.last_loaded_date = None

for k, default_val in [
    ("revenu_pct", 4.40),              # take-rate réel Q1 2026
    ("cout_paiement_pct", 1.75),
    ("cout_liquidite_10j_pct", 0.30),
    ("defaut_30j_pct", 1.50),          # PAR30 réel
    ("cycles_per_month", 2.63),        # cycles réels Fév 2026 (354 367€ / 135 005€)
    ("loan_book_k", 135.0),            # net loan portfolio réel Fév 2026 = 135 005€
    ("avg_loan_value_eur", 338.0),     # 354 367€ / 1 050 prêts = 337.5€
    ("tx_per_client_per_month", 2.6),  # 1 050 prêts / ~400 retailers
    # P&L extra inputs
    ("cogs_per_client_eur", 5.0),
    ("cac_per_new_client_eur", 30.0),
    ("growth_months", 12),
    ("opex_current_k", 12.0),          # burn réel Jan-Fév 2026 ≈ 12-15k€/mois
]:
    if k not in st.session_state:
        st.session_state[k] = default_val

def apply_preset_for_date(d: date, force: bool = False):
    if d not in PRESETS_BY_DATE:
        return
    if (not force) and (st.session_state.last_loaded_date == d):
        return
    p = PRESETS_BY_DATE[d]
    st.session_state["revenu_pct"] = float(p["revenu_pct"])
    st.session_state["cout_paiement_pct"] = float(p["cout_paiement_pct"])
    st.session_state["cout_liquidite_10j_pct"] = float(p["cout_liquidite_10j_pct"])
    st.session_state["defaut_30j_pct"] = float(p["defaut_30j_pct"])
    if "loan_book_k" in p:
        st.session_state["loan_book_k"] = float(p["loan_book_k"])
    if "cycles_per_month" in p:
        st.session_state["cycles_per_month"] = float(p["cycles_per_month"])
    st.session_state["scenario_name_autofill"] = p.get("name", f"Preset – {d.isoformat()}")
    st.session_state.last_loaded_date = d

if "seeded_history" not in st.session_state:
    st.session_state.seeded_history = False
if not st.session_state.seeded_history:
    for d in HISTORY_DATES:
        p = PRESETS_BY_DATE[d]
        cm = p["revenu_pct"] - (p["cout_paiement_pct"] + p["cout_liquidite_10j_pct"] + p["defaut_30j_pct"])
        st.session_state.scenarios.append({"date": d, "name": p["name"], "contribution_margin_pct": cm})
    st.session_state.seeded_history = True

apply_preset_for_date(st.session_state.scenario_date, force=False)

# --------------------------------------------------
# GLOBAL CSS
# --------------------------------------------------
st.markdown(
    """
<style>
div.block-container { padding-top: 1.2rem; font-size: 12px; }
h1 { font-size: 1.4rem !important; letter-spacing: -0.02em; }
h2, h3 { font-size: 1.0rem !important; letter-spacing: -0.02em; }
p, li, .stMarkdown p { font-size: 12px !important; }
.stMetric label { font-size: 11px !important; }
.stMetric [data-testid="stMetricValue"] { font-size: 15px !important; }
.wb-card {
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  background: rgba(255,255,255,0.70);
}
.vbar-wrap { display:flex; align-items:center; gap:12px; }
.vbar {
  height: 168px;
  width: 16px;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.18);
  background: rgba(0,0,0,0.06);
  position: relative;
  overflow: hidden;
}
.vbar-fill {
  position:absolute;
  bottom:0;
  left:0;
  width:100%;
  border-radius: 14px;
}
.vbar-metric { display:flex; flex-direction:column; gap:2px; }
.vbar-metric .big { font-size: 22px; font-weight: 800; line-height: 1; }
.vbar-metric .sub { font-size: 12px; opacity: 0.7; }
.knob-wrap { display:flex; align-items:center; gap:12px; }
.knob-shell { width: 110px; height: 110px; position: relative; }
.knob-ring {
  width: 90px; height: 90px;
  border-radius: 50%;
  border: 3px solid rgba(0,0,0,0.55);
  position:absolute; left:10px; top:10px;
  background: rgba(255,255,255,0.15);
}
.knob-ticks {
  position:absolute; inset:0;
  border-radius: 50%;
  border: 6px dotted rgba(0,0,0,0.25);
  clip-path: inset(0 0 0 0 round 50%);
  opacity: 0.9;
}
.knob-needle {
  position:absolute;
  width: 6px; height: 44px;
  background: rgba(6,76,114,0.95);
  left: 52px; top: 14px;
  transform-origin: 50% 85%;
  border-radius: 4px;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
}
.small-label { font-size: 12px; opacity: 0.7; margin-top: 4px; }
/* P&L Table */
.pnl-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 8px;
}
.pnl-table td {
  padding: 4px 10px;
  border-bottom: 1px solid rgba(0,0,0,0.07);
}
.pnl-table td:last-child { text-align: right; font-weight: 600; }
.pnl-table td:first-child { color: #333; }
.pnl-row-sub td { opacity: 0.72; font-size: 11px; }
.pnl-row-sub td:first-child { padding-left: 22px; }
.pnl-row-margin td {
  font-weight: 800;
  font-size: 12px;
  background: rgba(6,76,114,0.07);
  border-top: 2px solid rgba(6,76,114,0.25) !important;
  border-bottom: 2px solid rgba(6,76,114,0.25) !important;
  color: #064C72;
}
.pnl-row-ebitda td {
  font-weight: 900;
  font-size: 13px;
  background: rgba(27,90,67,0.10);
  border-top: 2px solid #1B5A43 !important;
  color: #1B5A43;
}
.pnl-row-neg td:last-child { color: #C0392B; }
.pnl-row-pos td:last-child { color: #1B5A43; }
/* Cost comparison cards */
.cost-card-row { display: flex; gap: 16px; margin-bottom: 8px; }
.cost-card {
  flex: 1;
  border: 1.5px solid rgba(0,0,0,0.12);
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.8);
}
.cost-card .cc-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.6; margin-bottom: 4px; }
.cost-card .cc-value { font-size: 22px; font-weight: 900; color: #064C72; }
.cost-card .cc-sub { font-size: 11px; opacity: 0.55; margin-top: 2px; }
.cost-card.improved { border-color: #1B5A43; background: rgba(27,90,67,0.05); }
.cost-card.improved .cc-value { color: #1B5A43; }
/* Narrative boxes */
.narrative-box {
  border-left: 3px solid #064C72;
  padding: 8px 14px;
  background: rgba(6,76,114,0.04);
  border-radius: 0 8px 8px 0;
  margin: 8px 0;
  font-size: 12px;
}
.narrative-box.green { border-left-color: #1B5A43; background: rgba(27,90,67,0.04); }
.narrative-box.orange { border-left-color: #E67E22; background: rgba(230,126,34,0.04); }
</style>
""",
    unsafe_allow_html=True,
)

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def vbar_widget(label, key, vmin, vmax, step, help_txt, color_mode):
    if key not in st.session_state:
        st.session_state[key] = (vmin + vmax) / 2
    val = float(st.session_state[key])
    pct = 0 if vmax == vmin else (val - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)
    if color_mode == "rev":
        grad = "linear-gradient(180deg, rgba(34,197,94,0.95), rgba(239,68,68,0.95))"
    else:
        grad = "linear-gradient(180deg, rgba(239,68,68,0.95), rgba(34,197,94,0.95))"
    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div class="vbar-wrap">
          <div class="vbar">
            <div class="vbar-fill" style="height:{pct*100:.1f}%; background:{grad};"></div>
          </div>
          <div class="vbar-metric">
            <div class="big">{val:.2f}%</div>
            <div class="sub">min {vmin:g}% • max {vmax:g}%</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.slider("", min_value=float(vmin), max_value=float(vmax), value=float(val),
              step=float(step), key=key, help=help_txt, label_visibility="collapsed")

def knob_simple_visual(label, value, vmin, vmax, value_fmt="{:,.0f}"):
    pct = 0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)
    deg = -135 + pct * 270
    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div class="knob-wrap">
          <div class="knob-shell">
            <div class="knob-ticks"></div>
            <div class="knob-ring"></div>
            <div class="knob-needle" style="transform: rotate({deg:.1f}deg);"></div>
          </div>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="font-size:22px; font-weight:800; line-height:1;">{value_fmt.format(value)}</div>
            <div style="font-size:12px; opacity:0.7;">min {vmin:g} • max {vmax:g}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def fmt_k(val_k):
    return f"{val_k:+,.1f} k€" if val_k != 0 else "0 k€"

def pnl_row(label, value_k, row_class="", indent=False):
    sign_class = "pnl-row-pos" if value_k >= 0 else "pnl-row-neg"
    if row_class:
        sign_class = ""
    val_str = f"{value_k:,.1f} k€"
    return f'<tr class="{row_class} {sign_class}"><td>{label}</td><td>{val_str}</td></tr>'

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
page = st.sidebar.radio("Navigation", ["Simulateur", "Comment ça marche — le modèle Waribei"])

# ==================================================
# PAGE 2 — EXPLICATION DU MODÈLE WARIBEI
# ==================================================
if page == "Comment ça marche — le modèle Waribei":
    st.title("Le modèle économique de Waribei")
    st.caption("Comprendre les unit economics pour les expliquer à n'importe quel investisseur.")

    st.markdown("---")

    # ---- QUI EST WARIBEI
    st.subheader("🏗️ Qui est Waribei ?")
    st.markdown(
        """
        <div class="narrative-box">
        Waribei est l'<strong>OS du crédit marchand court terme</strong> en Afrique francophone.
        On connecte les <strong>détaillants informels</strong> aux <strong>microfinances (MFIs)</strong>
        via notre stack propriétaire : WariStock (commandes), WariBrain (scoring), WariPortal (MFI dashboard).
        <br><br>
        <strong>On n'est pas un prêteur.</strong> Le capital vient des MFIs. On est l'infrastructure.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    # ---- COMMENT ON GAGNE DE L'ARGENT
    st.subheader("💰 Comment on gagne de l'argent ?")
    col_a, col_b = st.columns([0.55, 0.45])
    with col_a:
        st.markdown(
            """
            **Notre revenu = un pourcentage de chaque prêt décaissé.**

            Quand une MFI partenaire déploie du crédit via Waribei :
            - Le prêt moyen ≈ **350€**, durée **10 jours**
            - On facture **~4.4% du montant décaissé** en frais de service
            - Le détaillant rembourse la MFI ; Waribei touche sa commission

            Avec ~2.6 cycles/mois sur le net loan portfolio
            (3 cycles théoriques sur 10j, 2.6 réels net of provisions),
            un net book de **135k€** génère **~354k€ de volume mensuel**
            et **~16k€ de MRR**.
            """
        )
    with col_b:
        st.markdown(
            """
            <div class="narrative-box green">
            <strong>Chiffres réels Q1 2026</strong><br><br>
            Jan 2026 : 407 904€ disbursed, 1 134 prêts, 449 retailers → MRR 17 530€<br>
            Fév 2026 : 354 367€ disbursed, 1 050 prêts, 400 retailers → MRR 16 203€<br><br>
            Net loan portfolio : 135k€ | PAR30 &lt; 1.5%<br>
            <strong>EBITDA ~ -10k€/mois | Burn ~ 12k€/mois</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ---- LES 3 COÛTS
    st.subheader("⚠️ Les 3 coûts qui érodent la marge")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div class="narrative-box orange">
            <strong>1. Coût paiement (~1.75%)</strong><br>
            Frais des rails de paiement (Visa, Mastercard, mobile money) sur chaque transaction.<br><br>
            🚀 <strong>Open Banking réduit ce coût à ~0.50%</strong> — gain de +1.25% de CM par transaction.
            C'est le levier numéro 1.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="narrative-box">
            <strong>2. Coût liquidité (~0.30%)</strong><br>
            Coût du capital sur 10 jours = taux d'intérêt de la dette de financement en transit.<br><br>
            Reflète le coût de la facility dette des MFIs. Diminue avec la maturité des partenariats.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="narrative-box">
            <strong>3. Défaut 30j (~1.50%)</strong><br>
            Perte nette attendue sur le portefeuille à 30 jours (PAR30).<br><br>
            🧠 <strong>WariBrain améliore le scoring</strong> → cible &lt;0.80% avec maturité. Gain de +0.70% de CM.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ---- WATERFALL EXPLIQUÉ
    st.subheader("📊 La décomposition par transaction")

    wf_col, txt_col = st.columns([0.5, 0.5])
    with txt_col:
        st.markdown(
            """
            **Réalité Fév 2026 (données exactes) :**

            | Ligne | % du volume |
            |---|---|
            | Revenu (take-rate) | +4.58% |
            | — Coût paiement | -1.75% |
            | — Coût liquidité | -0.30% |
            | — Défaut 30j | -1.50% |
            | **= CM / transaction** | **+1.03%** |

            Sur 354k€ de volume → **~3.6k€ de CM brute/mois**.
            Net book : 135k€ | Cycles : 2.63/mois.
            Il faut **~2× le net book actuel + Open Banking**
            pour atteindre l'équilibre opérationnel.
            """
        )
        st.markdown(
            """
            <div class="narrative-box green">
            <strong>Avec Open Banking (−1.25%) + scoring (−0.70%)</strong><br>
            CM passe de 0.85% → <strong>2.80%</strong><br>
            Break-even atteint à ~340k€ loan book (vs 220k€ aujourd'hui)
            </div>
            """,
            unsafe_allow_html=True,
        )

    with wf_col:
        wf_data = pd.DataFrame({
            "Étape": ["Revenu", "Coût paiement", "Coût liquidité", "Défaut 30j", "CM nette"],
            "value": [4.40, -1.75, -0.30, -1.50, 0.85],
            "start": [0.0, 4.40, 2.65, 2.35, 0.0],
            "end": [4.40, 2.65, 2.35, 0.85, 0.85],
            "type": ["positive", "negative", "negative", "negative", "total"],
        })
        color_scale = alt.Scale(domain=["positive", "negative", "total"], range=["#1B5A43", "#F83131", "#064C72"])
        wf_chart = (
            alt.Chart(wf_data)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                      cornerRadiusBottomLeft=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Étape:N", sort=list(wf_data["Étape"]), title=None),
                y=alt.Y("start:Q", axis=alt.Axis(title="%")),
                y2="end:Q",
                color=alt.Color("type:N", scale=color_scale, legend=None),
                tooltip=[alt.Tooltip("Étape:N"), alt.Tooltip("value:Q", format=".2f", title="%")],
            )
        )
        wf_labels = (
            alt.Chart(wf_data).mark_text(dy=-8, fontSize=11, color="#333")
            .encode(
                x=alt.X("Étape:N", sort=list(wf_data["Étape"])),
                y="end:Q",
                text=alt.Text("value:Q", format="+.2f"),
            )
        )
        st.altair_chart((wf_chart + wf_labels).properties(height=260), use_container_width=True)

    st.markdown("---")

    # ---- LES 3 LEVIERS
    st.subheader("🚀 Les 3 leviers d'amélioration")
    st.markdown(
        """
        | Levier | Impact sur CM | Timeline | Statut |
        |---|---|---|---|
        | **Open Banking** | Paiement 1.75% → 0.50% → **+1.25% CM** | 6-12 mois | En cours (FMCI/BCEAO) |
        | **Scoring WariBrain** | Défaut 1.50% → 0.80% → **+0.70% CM** | 12-18 mois | En développement |
        | **Scale loan book** | Revenu × 3-7× sur même opex fixe | Post-Seed | Priorité #1 |

        **L'opex est majoritairement fixe.** Passer de 220k€ à 1.5M€ de loan book ne triple pas l'équipe.
        C'est là qu'est le levier d'échelle.
        """
    )

    st.markdown("---")

    # ---- SCÉNARIOS EXPLIQUÉS
    st.subheader("🎯 Lecture des scénarios")

    s1, s2 = st.columns(2)
    with s1:
        st.markdown(
            """
            **Réalité — Fév 2026**
            État actuel. Net book 135k€, cycles 2.63/mois, volume 354k€.
            EBITDA ~-10.8k€/mois (réel : -10 623€ ✓). Il faut scale.

            ---

            **Break-even — Open Banking**
            Avec OB déployé : coût paiement 1.75% → 0.50%.
            Scoring amélioré : défaut 1.50% → 0.80%.
            Net book 250k€ × 2.6 cycles → volume 650k → break-even (opex 12k€).
            """
        )
    with s2:
        st.markdown(
            """
            **Post-Seed — 12 mois**
            12 mois après clôture Seed (1M€). Net book 460k€ via facility MFI.
            OB partiellement déployé. Volume ~1.2M€/mois. EBITDA +10k€.

            ---

            **Series A target**
            Net book 1.15M€, full Open Banking, score mature.
            Volume ~3M€/mois, MRR ~120k€, EBITDA +18k€ à opex 35k€.
            C'est le story pour le Series A.
            """
        )

    st.markdown("---")
    st.markdown(
        """
        <div class="narrative-box">
        <strong>Rappel méthodologique</strong><br>
        <em>revenu_pct</em> = MRR / volume décaissé mensuel × 100<br>
        <em>cycles/mois</em> = volume décaissé / avg loan book closing<br>
        <em>volume mensuel</em> = loan book × cycles<br>
        <em>contribution value (k€)</em> = volume × CM%<br><br>
        Les données historiques Jun 2025 et Dec 2025 utilisent les presets du board.
        Les données Jan-Fév 2026 sont calculées depuis les exports CSV réels (MEMORY.md).
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==================================================
# PAGE 1 — SIMULATEUR
# ==================================================
else:
    top = st.columns([0.7, 0.3])
    with top[0]:
        st.title("Unit Economics – Waribei")
    with top[1]:
        try:
            st.image("logo_waribei_icon@2x.png", width=100)
        except Exception:
            st.write("Logo Waribei (ajoute `logo_waribei_icon@2x.png`)")
    st.markdown("---")

    # Apply pending scenario
    if "pending_scenario" in st.session_state and st.session_state.pending_scenario:
        apply_scenario_preset(st.session_state.pending_scenario)
        st.session_state.pending_scenario = None

    main_left, main_right = st.columns([0.68, 0.32], gap="large")

    # =========================
    # LEFT
    # =========================
    with main_left:
        # ---- Hypothèses par transaction
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Hypothèses par transaction")
        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            vbar_widget(
                "Revenus / trx", "revenu_pct", 1.0, 6.0, 0.01,
                "Take-rate / commission sur le montant décaissé. Réel Q1 2026 : ~4.4%.", "rev"
            )
        with c2:
            vbar_widget(
                "Coût paiement / trx", "cout_paiement_pct", 0.0, 3.0, 0.01,
                "Frais rails paiement (Visa/MC/mobile money). Open Banking → 0.50%.", "cost"
            )
        with c3:
            vbar_widget(
                "Coût liquidité (10j)", "cout_liquidite_10j_pct", 0.0, 1.5, 0.01,
                "Coût du capital sur 10 jours (financement MFI en transit).", "cost"
            )
        with c4:
            vbar_widget(
                "Défaut 30j / trx", "defaut_30j_pct", 0.0, 5.0, 0.01,
                "Perte nette attendue (PAR30). Réel : ~1.5%. Cible WariBrain : <0.8%.", "cost"
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")

        # ---- Variables de volume
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Variables de volume")
        vcol1, vcol2 = st.columns([0.58, 0.42], gap="large")
        with vcol1:
            knob_simple_visual("Net loan portfolio (k€)", float(st.session_state["loan_book_k"]), 50.0, 5000.0)
            st.slider("", min_value=50.0, max_value=5000.0, value=float(st.session_state["loan_book_k"]),
                      step=5.0, key="loan_book_k", label_visibility="collapsed")
            st.caption("Réel Fév 2026 : 135k€ | Cible post-Seed : 460k€")
        with vcol2:
            st.markdown("**Cycles de liquidité / mois**")
            st.caption("Réel : ~2.6 | Théorique 10j : 3.0")
            st.slider("", min_value=1.0, max_value=4.0, value=float(st.session_state.get("cycles_per_month", 1.80)),
                      step=0.1, key="cycles_per_month", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")

        # ---- Hypothèses opérationnelles
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Hypothèses opérationnelles")
        o1, o2 = st.columns(2, gap="large")
        with o1:
            knob_simple_visual("Valeur moyenne par prêt (€)", float(st.session_state["avg_loan_value_eur"]), 150.0, 1000.0)
            st.slider("", min_value=150.0, max_value=1000.0, value=float(st.session_state["avg_loan_value_eur"]),
                      step=25.0, key="avg_loan_value_eur", label_visibility="collapsed")
            st.caption("Réel : ~338€ (354 367€ / 1 050 prêts en Fév)")
        with o2:
            st.markdown("**Transactions / retailer / mois**")
            st.caption("Réel : ~2.6 (1050 prêts / 400 retailers)")
            st.slider("", min_value=1.0, max_value=12.0, value=float(st.session_state["tx_per_client_per_month"]),
                      step=0.1, key="tx_per_client_per_month", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        # ---- Coûts variables & fixes
        st.markdown("")
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("⚙️ Coûts variables & fixes")
        cc1, cc2, cc3, cc4 = st.columns(4, gap="large")
        with cc1:
            st.markdown('<p style="font-size:11px; font-weight:700; margin-bottom:2px;">COGS / retailer servi (€)</p>', unsafe_allow_html=True)
            st.number_input("cogs_per_client_eur_input", min_value=0.0, max_value=500.0,
                            value=float(st.session_state.get("cogs_per_client_eur", 5.0)),
                            step=0.5, label_visibility="collapsed", key="cogs_per_client_eur")
            st.slider("cogs_per_client_slider", min_value=0.0, max_value=100.0,
                      value=float(st.session_state.get("cogs_per_client_eur", 5.0)),
                      step=0.5, key="_cogs_per_client_slider", label_visibility="collapsed",
                      on_change=lambda: st.session_state.update({"cogs_per_client_eur": st.session_state["_cogs_per_client_slider"]}))
            st.markdown('<p style="font-size:10px; opacity:0.6; margin-top:2px;">Infra, data, support / retailer actif</p>', unsafe_allow_html=True)
        with cc2:
            st.markdown('<p style="font-size:11px; font-weight:700; margin-bottom:2px;">CAC / nouveau retailer (€)</p>', unsafe_allow_html=True)
            st.number_input("cac_per_new_client_eur_input", min_value=0.0, max_value=5000.0,
                            value=float(st.session_state.get("cac_per_new_client_eur", 30.0)),
                            step=1.0, label_visibility="collapsed", key="cac_per_new_client_eur")
            st.slider("cac_per_new_client_slider", min_value=0.0, max_value=500.0,
                      value=float(st.session_state.get("cac_per_new_client_eur", 30.0)),
                      step=1.0, key="_cac_per_new_client_slider", label_visibility="collapsed",
                      on_change=lambda: st.session_state.update({"cac_per_new_client_eur": st.session_state["_cac_per_new_client_slider"]}))
            st.markdown('<p style="font-size:10px; opacity:0.6; margin-top:2px;">Marketing, sales, onboarding</p>', unsafe_allow_html=True)
        with cc3:
            st.markdown('<p style="font-size:11px; font-weight:700; margin-bottom:2px;">Horizon de croissance (mois)</p>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:10px; opacity:0.6; margin-bottom:2px;">Base : 420 retailers aujourd\'hui</p>', unsafe_allow_html=True)
            st.slider("growth_months_slider", min_value=1, max_value=36,
                      value=int(st.session_state.get("growth_months", 12)),
                      step=1, key="growth_months", label_visibility="collapsed")
        with cc4:
            st.markdown('<p style="font-size:11px; font-weight:700; margin-bottom:2px;">Opex — équipe actuelle (k€/mois)</p>', unsafe_allow_html=True)
            st.number_input("opex_current_input", min_value=0.0, max_value=1000.0,
                            value=float(st.session_state.get("opex_current_k", 12.0)),
                            step=1.0, label_visibility="collapsed", key="opex_current_k")
            st.markdown('<p style="font-size:10px; opacity:0.6; margin-top:2px;">Burn réel Jan-Fév 2026 : ~12-15k€</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # RIGHT
    # =========================
    with main_right:
        # --- CORE CALCULATIONS
        revenu_pct = float(st.session_state["revenu_pct"])
        cout_paiement_pct = float(st.session_state["cout_paiement_pct"])
        cout_liquidite_10j_pct = float(st.session_state["cout_liquidite_10j_pct"])
        defaut_30j_pct = float(st.session_state["defaut_30j_pct"])
        cycles_per_month = float(st.session_state["cycles_per_month"])
        loan_book_k = float(st.session_state["loan_book_k"])
        avg_loan_value_eur = float(st.session_state["avg_loan_value_eur"])
        tx_per_client_per_month = float(st.session_state["tx_per_client_per_month"])

        taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS
        cout_total_pct = cout_paiement_pct + cout_liquidite_10j_pct + defaut_30j_pct
        contribution_margin_pct = revenu_pct - cout_total_pct

        monthly_volume_eur = loan_book_k * 1000 * cycles_per_month
        monthly_revenue_eur = monthly_volume_eur * (revenu_pct / 100)
        annual_revenue_eur = monthly_revenue_eur * 12
        contribution_value_k = loan_book_k * cycles_per_month * contribution_margin_pct / 100

        nb_loans_per_month = monthly_volume_eur / avg_loan_value_eur if avg_loan_value_eur > 0 else 0.0
        nb_clients_per_month = nb_loans_per_month / tx_per_client_per_month if tx_per_client_per_month > 0 else 0.0
        revenue_per_loan_eur = avg_loan_value_eur * (revenu_pct / 100)
        revenue_per_client_month_eur = revenue_per_loan_eur * tx_per_client_per_month
        take_rate_effective_pct = (monthly_revenue_eur / monthly_volume_eur * 100) if monthly_volume_eur > 0 else 0.0

        # --- OUTPUTS
        st.subheader("Contribution")
        st.markdown(
            f"""
            <div style="border:2px solid #064C72; padding:16px; border-radius:12px;
                        font-size:28px; font-weight:900; text-align:center;
                        background-color:#FFDBCC; color:#064C72;">
              {contribution_margin_pct:.2f} %
              <div class="small-label">Contribution margin / trx</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        st.markdown(
            f"""
            <div style="border:2px solid #1B5A43; padding:14px; border-radius:12px;
                        font-size:22px; font-weight:900; text-align:center;
                        background-color:#D8ECFE; color:#1B5A43;">
              {contribution_value_k:.2f} k€
              <div class="small-label">Contribution value / mois</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f}%**")
        st.markdown("")

        st.subheader("Revenus")
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Revenue / mois", f"{monthly_revenue_eur:,.0f} €")
        with r2:
            st.metric("Revenue / an", f"{annual_revenue_eur:,.0f} €")
        r3, r4 = st.columns(2)
        with r3:
            st.metric("Revenue / prêt", f"{revenue_per_loan_eur:,.0f} €")
        with r4:
            st.metric("Revenue / retailer / mois", f"{revenue_per_client_month_eur:,.0f} €")
        st.caption(f"Take-rate effectif ≈ {take_rate_effective_pct:.2f}% sur {monthly_volume_eur:,.0f} € / mois.")
        st.markdown("")

        st.subheader("Volumes nécessaires / mois")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Prêts / mois", f"{nb_loans_per_month:,.0f}")
        with m2:
            st.metric("Retailers actifs", f"{nb_clients_per_month:,.0f}")
        st.markdown("---")

        # =========================
        # Bottom right panel
        # =========================
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.markdown("### Scénarios & Presets")
        scenario = st.selectbox("Scénarios rapides", list(SCENARIOS_PRESETS.keys()))
        st.caption("Charge un scénario pré-calibré — ajuste ensuite les curseurs.")

        if "pending_scenario" not in st.session_state:
            st.session_state.pending_scenario = None
        if scenario != "Custom":
            st.session_state.pending_scenario = scenario
            st.rerun()

        dcols = st.columns([0.72, 0.28])
        with dcols[1]:
            if st.button("Today"):
                st.session_state["scenario_date"] = DEFAULT_DATE
                apply_preset_for_date(DEFAULT_DATE, force=True)
        with dcols[0]:
            picked = st.date_input("Date", value=st.session_state.get("scenario_date", DEFAULT_DATE))
            st.session_state["scenario_date"] = picked
        apply_preset_for_date(st.session_state["scenario_date"], force=False)

        default_label = st.session_state.get("scenario_name_autofill", "Scenario")
        scenario_name = st.text_input("Label du scénario", value=default_label)

        if st.button("SAVE"):
            d = st.session_state["scenario_date"]
            cm_now = contribution_margin_pct
            replaced = False
            for i, s in enumerate(st.session_state.scenarios):
                if s.get("date") == d:
                    st.session_state.scenarios[i] = {"date": d, "name": scenario_name, "contribution_margin_pct": cm_now}
                    replaced = True
                    break
            if not replaced:
                st.session_state.scenarios.append({"date": d, "name": scenario_name, "contribution_margin_pct": cm_now})
            st.success(f"Scénario '{scenario_name}' sauvegardé ({d}).")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==================================================
    # P&L SECTION
    # ==================================================
    st.markdown("#### P&L — Cascade mensuelle")

    # --------------------------------------------------
    # Compute derived P&L values
    # --------------------------------------------------
    cogs_per_client_eur = float(st.session_state.get("cogs_per_client_eur", 5.0))
    cac_per_new_client_eur = float(st.session_state.get("cac_per_new_client_eur", 30.0))
    opex_current_k = float(st.session_state.get("opex_current_k", 12.0))
    growth_months = int(st.session_state.get("growth_months", 12))

    base_clients = 420.0  # retailers actifs Fév 2026 (MEMORY.md)
    new_clients_per_month = max(0.0, (nb_clients_per_month - base_clients) / growth_months)
    cogs_k = nb_clients_per_month * cogs_per_client_eur / 1000
    cac_k = new_clients_per_month * cac_per_new_client_eur / 1000

    rev_k = monthly_revenue_eur / 1000
    tx_cost_k = monthly_volume_eur * (cout_paiement_pct / 100) / 1000
    liq_cost_k = monthly_volume_eur * (cout_liquidite_10j_pct / 100) / 1000
    risk_cost_k = monthly_volume_eur * (defaut_30j_pct / 100) / 1000
    cm1_k = rev_k - tx_cost_k - liq_cost_k
    cm2_k = cm1_k - risk_cost_k - cogs_k
    cm3_k = cm2_k - cac_k
    ebitda_current_k = cm3_k - opex_current_k

    def color_val(v):
        c = "#1B5A43" if v >= 0 else "#C0392B"
        return f'<span style="color:{c}; font-weight:700;">{v:+,.1f} k€</span>'

    def neutral_val(v):
        return f'<span style="font-weight:600;">{v:,.1f} k€</span>'

    # --------------------------------------------------
    # P&L Table + EBITDA cards
    # --------------------------------------------------
    tbl_col, card_col = st.columns([0.52, 0.48], gap="large")

    with tbl_col:
        st.markdown(
            f"""
            <table class="pnl-table">
              <tr><td><b>Revenues</b></td><td>{neutral_val(rev_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Coût paiement (rails Visa/MC)</td><td>{color_val(-tx_cost_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Coût liquidité (10j)</td><td>{color_val(-liq_cost_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 1 — marge brute financière</td><td>{color_val(cm1_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Risk / Défaut 30j (PAR30)</td><td>{color_val(-risk_cost_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ COGS <span style="opacity:0.55;">({nb_clients_per_month:,.0f} retailers × {cogs_per_client_eur:.1f} €)</span></td><td>{color_val(-cogs_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 2 — après risque & infra</td><td>{color_val(cm2_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ CAC <span style="opacity:0.55;">({new_clients_per_month:,.0f} new × {cac_per_new_client_eur:.0f} €)</span></td><td>{color_val(-cac_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 3 — après acquisition</td><td>{color_val(cm3_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Opex (salaires, bureaux, outils)</td><td>{color_val(-opex_current_k)}</td></tr>
              <tr class="pnl-row-ebitda"><td>EBITDA</td><td>{color_val(ebitda_current_k)}</td></tr>
            </table>
            """,
            unsafe_allow_html=True,
        )

    with card_col:
        ebitda_cur_color = "#1B5A43" if ebitda_current_k >= 0 else "#C0392B"
        be_volume_k = (opex_current_k + cogs_k + cac_k) / (contribution_margin_pct / 100) if contribution_margin_pct > 0 else 0
        st.markdown(
            f"""
            <p style="font-size:11px; font-weight:700; margin-bottom:6px;">EBITDA — équipe actuelle</p>
            <div style="display:flex; gap:12px; margin-top:4px;">
              <div class="cost-card">
                <div class="cc-title">EBITDA / mois</div>
                <div class="cc-value" style="color:{ebitda_cur_color};">{ebitda_current_k:+,.1f} k€</div>
                <div class="cc-sub">Opex = {opex_current_k:,.0f} k€/mois</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if contribution_margin_pct > 0:
            be_book_k = be_volume_k / cycles_per_month if cycles_per_month > 0 else 0
            st.markdown(
                f"""
                <div class="narrative-box" style="margin-top:8px;">
                <strong>Break-even à ce CM% ({contribution_margin_pct:.2f}%)</strong><br>
                Volume nécessaire : <strong>{be_volume_k:,.0f} k€/mois</strong><br>
                → Loan book : <strong>{be_book_k:,.0f} k€</strong>
                (vs {loan_book_k:,.0f} k€ aujourd'hui)
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Cascade bar chart
        cascade_data = pd.DataFrame({
            "Étape": ["CM 1", "CM 2", "CM 3", "EBITDA"],
            "Valeur": [cm1_k, cm2_k, cm3_k, ebitda_current_k],
            "Couleur": [
                "pos" if cm1_k >= 0 else "neg",
                "pos" if cm2_k >= 0 else "neg",
                "pos" if cm3_k >= 0 else "neg",
                "pos" if ebitda_current_k >= 0 else "neg",
            ],
        })
        color_scale_cascade = alt.Scale(domain=["pos", "neg"], range=["#064C72", "#F83131"])
        cascade_chart = (
            alt.Chart(cascade_data)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                      cornerRadiusBottomLeft=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Étape:N", sort=list(cascade_data["Étape"]), title=None),
                y=alt.Y("Valeur:Q", title="k€"),
                color=alt.Color("Couleur:N", scale=color_scale_cascade, legend=None),
                tooltip=[alt.Tooltip("Étape:N"), alt.Tooltip("Valeur:Q", format=",.1f", title="k€")],
            )
        )
        cascade_labels = (
            alt.Chart(cascade_data).mark_text(dy=-8, fontSize=10, color="#333")
            .encode(
                x=alt.X("Étape:N", sort=list(cascade_data["Étape"])),
                y=alt.Y("Valeur:Q"),
                text=alt.Text("Valeur:Q", format=".1f"),
            )
        )
        st.altair_chart((cascade_chart + cascade_labels).properties(height=170), use_container_width=True)

    st.markdown("---")

    # --------------------------------------------------
    # WATERFALL (per transaction %)
    # --------------------------------------------------
    def make_waterfall_df(revenue, pay_cost, liq_cost, default_cost, margin):
        steps = ["Revenu", "Coût paiement", "Coût liquidité (10j)", "Défaut 30j", "Contribution"]
        values = [revenue, -pay_cost, -liq_cost, -default_cost, margin]
        start, end = [], []
        running = 0.0
        for v in values[:-1]:
            start.append(running)
            running += v
            end.append(running)
        start.append(0.0)
        end.append(margin)
        types = []
        for i, v in enumerate(values):
            if i == len(values) - 1:
                types.append("total")
            elif v >= 0:
                types.append("positive")
            else:
                types.append("negative")
        return pd.DataFrame({"step": steps, "value": values, "start": start, "end": end, "type": types})

    st.markdown("### Décomposition par transaction (waterfall)")
    wf_df = make_waterfall_df(
        revenu_pct, cout_paiement_pct, cout_liquidite_10j_pct, defaut_30j_pct, contribution_margin_pct
    )
    color_scale = alt.Scale(domain=["positive", "negative", "total"], range=["#1B5A43", "#F83131", "#064C72"])
    waterfall_chart = (
        alt.Chart(wf_df).mark_bar()
        .encode(
            x=alt.X("step:N", title=None, sort=list(wf_df["step"])),
            y=alt.Y("start:Q", axis=alt.Axis(title="%")),
            y2="end:Q",
            color=alt.Color("type:N", scale=color_scale, legend=None),
        )
    )
    wf_labels = (
        alt.Chart(wf_df).mark_text(dy=-6, color="#333", fontSize=11)
        .encode(
            x=alt.X("step:N", sort=list(wf_df["step"])),
            y="end:Q",
            text=alt.Text("value:Q", format=".2f"),
        )
    )
    st.altair_chart((waterfall_chart + wf_labels).properties(height=260), use_container_width=True)

    # --------------------------------------------------
    # SCÉNARIOS COMPARAISON
    # --------------------------------------------------
    if len(st.session_state.scenarios) > 1:
        st.markdown("---")
        st.markdown("### Évolution de la contribution margin dans le temps")
        scen_df = pd.DataFrame(st.session_state.scenarios)
        scen_df = scen_df.sort_values("date")
        scen_df["date_str"] = scen_df["date"].apply(lambda d: d.strftime("%b %Y"))
        scen_df["cm_fmt"] = scen_df["contribution_margin_pct"].apply(lambda v: f"{v:.2f}%")
        scen_df["color"] = scen_df["contribution_margin_pct"].apply(lambda v: "pos" if v >= 0 else "neg")

        line_chart = (
            alt.Chart(scen_df)
            .mark_line(point=True, strokeWidth=2.5, color="#064C72")
            .encode(
                x=alt.X("date_str:N", sort=list(scen_df["date_str"]), title=None),
                y=alt.Y("contribution_margin_pct:Q", title="CM %", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip("name:N", title="Scénario"),
                    alt.Tooltip("contribution_margin_pct:Q", format=".2f", title="CM %"),
                ],
            )
        )
        labels_chart = (
            alt.Chart(scen_df).mark_text(dy=-12, fontSize=10, color="#064C72", fontWeight="bold")
            .encode(
                x=alt.X("date_str:N", sort=list(scen_df["date_str"])),
                y="contribution_margin_pct:Q",
                text="cm_fmt:N",
            )
        )
        st.altair_chart((line_chart + labels_chart).properties(height=220), use_container_width=True)

        # Clear button
        if st.button("Effacer l'historique", type="secondary"):
            st.session_state.scenarios = []
            st.session_state.seeded_history = False
            st.rerun()
