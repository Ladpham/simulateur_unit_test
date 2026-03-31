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
# PRESETS HISTORIQUES (source : tableau financier réel)
#
# revenu_pct  = MRR / volume décaissé × 100
# cycles/mois = volume décaissé / net loan portfolio
#
# Déc 2025 : 440 578€ décaissés / 156 452€ net book = 2.82 cycles
# Jan 2026 : 407 904€ / 148 648€ = 2.74 cycles, MRR 17 530€ → 4.30%
# Fév 2026 : 354 367€ / 135 005€ = 2.63 cycles, MRR 16 203€ → 4.58%
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
        "loan_book_k": 156.5,
        "cycles_per_month": 2.82,
    },
    date(2026, 1, 1): {
        "name": "Réel — Jan 2026",
        "revenu_pct": 4.30,
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,
        "loan_book_k": 148.6,
        "cycles_per_month": 2.74,
    },
    date(2026, 2, 1): {
        "name": "Réel — Fév 2026",
        "revenu_pct": 4.58,
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,
        "loan_book_k": 135.0,
        "cycles_per_month": 2.63,
    },
    date(2026, 6, 1): {
        "name": "Projection — Jun 2026",
        "revenu_pct": 3.80,
        "cout_paiement_pct": 1.20,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 1.00,
        "loan_book_k": 250.0,
        "cycles_per_month": 2.60,
    },
}

DEFAULT_DATE = date(2026, 2, 1)
HISTORY_DATES = [
    date(2025, 6, 1),
    date(2025, 12, 1),
    date(2026, 1, 1),
    date(2026, 2, 1),
]

# --------------------------------------------------
# SCÉNARIOS RAPIDES
# --------------------------------------------------
SCENARIOS_PRESETS = {
    "Custom": None,
    "Réalité — Fév 2026": {
        "revenu_pct": 4.58,
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.30,
        "defaut_30j_pct": 1.50,
        "loan_book_k": 135.0,
        "cycles_per_month": 2.63,
        "avg_loan_value_eur": 338.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 12.0,
        "scenario_name_autofill": "Réalité — Fév 2026",
    },
    "Break-even — Open Banking": {
        "revenu_pct": 4.40,
        "cout_paiement_pct": 0.50,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.80,
        "loan_book_k": 250.0,
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 12.0,
        "scenario_name_autofill": "Break-even — Open Banking",
    },
    "Post-Seed — 12 mois": {
        "revenu_pct": 4.40,
        "cout_paiement_pct": 0.80,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.90,
        "loan_book_k": 460.0,
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 18.0,
        "scenario_name_autofill": "Post-Seed — 12 mois",
    },
    "Series A target": {
        "revenu_pct": 4.00,
        "cout_paiement_pct": 0.50,
        "cout_liquidite_10j_pct": 0.35,
        "defaut_30j_pct": 0.60,
        "loan_book_k": 1150.0,
        "cycles_per_month": 2.60,
        "avg_loan_value_eur": 350.0,
        "tx_per_client_per_month": 2.6,
        "opex_current_k": 35.0,
        "scenario_name_autofill": "Series A target",
    },
    "Scénario Seed (deck)": {
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
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = DEFAULT_DATE
if "last_loaded_date" not in st.session_state:
    st.session_state.last_loaded_date = None

for k, default_val in [
    ("revenu_pct", 4.58),
    ("cout_paiement_pct", 1.75),
    ("cout_liquidite_10j_pct", 0.30),
    ("defaut_30j_pct", 1.50),
    ("cycles_per_month", 2.63),
    ("loan_book_k", 135.0),
    ("avg_loan_value_eur", 338.0),
    ("tx_per_client_per_month", 2.6),
    ("cogs_per_client_eur", 5.0),
    ("cac_per_new_client_eur", 30.0),
    ("growth_months", 12),
    ("opex_current_k", 12.0),
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
# CSS
# --------------------------------------------------
st.markdown("""
<style>
/* Global */
div.block-container { padding-top: 2rem; padding-bottom: 1rem; }
.stSidebar > div:first-child { padding-top: 1rem; }

/* Typography */
h1 { font-size: 1.25rem !important; font-weight: 800 !important; letter-spacing: -0.03em; margin-bottom: 0 !important; margin-top: 0 !important; }
h2, h3 { font-size: 0.9rem !important; font-weight: 700 !important; letter-spacing: -0.02em; margin-top: 0.5rem !important; }
p, li, .stMarkdown p { font-size: 12px !important; }
.stMetric label { font-size: 10px !important; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.6; }
.stMetric [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 800 !important; }

/* KPI bar */
.kpi-card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 12px;
  padding: 12px 16px 10px 16px;
  background: white;
  text-align: center;
}
.kpi-card .kpi-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.55;
  margin-bottom: 4px;
}
.kpi-card .kpi-value {
  font-size: 22px;
  font-weight: 900;
  line-height: 1;
  color: #064C72;
}
.kpi-card .kpi-value.pos { color: #1B5A43; }
.kpi-card .kpi-value.neg { color: #C0392B; }
.kpi-card .kpi-sub { font-size: 10px; opacity: 0.5; margin-top: 3px; }
.kpi-card .kpi-sub2 { font-size: 10px; opacity: 0.35; margin-top: 1px; font-style: italic; }

/* CM equation pill */
.cm-equation {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(6,76,114,0.05);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  flex-wrap: wrap;
  margin-top: 6px;
}
.cm-equation .rev { color: #1B5A43; }
.cm-equation .cost { color: #C0392B; }
.cm-equation .result { font-size: 15px; padding: 2px 10px; border-radius: 6px; background: rgba(6,76,114,0.10); color: #064C72; }
.cm-equation .result.pos { background: rgba(27,90,67,0.12); color: #1B5A43; }
.cm-equation .result.neg { background: rgba(192,57,43,0.10); color: #C0392B; }

/* Section cards */
.wb-card {
  border: 1px solid rgba(0,0,0,0.09);
  border-radius: 12px;
  padding: 14px 16px 12px 16px;
  background: white;
  margin-bottom: 10px;
}
.section-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  opacity: 0.45;
  margin-bottom: 8px;
}

/* Slider labels */
.slider-row-label {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: -8px;
  color: #333;
}
.slider-hint { font-size: 10px; opacity: 0.5; margin-top: -4px; }

/* P&L Table */
.pnl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.pnl-table td { padding: 5px 10px; border-bottom: 1px solid rgba(0,0,0,0.06); }
.pnl-table td:last-child { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
.pnl-row-sub td { opacity: 0.70; font-size: 11px; }
.pnl-row-sub td:first-child { padding-left: 22px; }
.pnl-row-margin td {
  font-weight: 800; font-size: 12px;
  background: rgba(6,76,114,0.06);
  border-top: 1.5px solid rgba(6,76,114,0.20) !important;
  border-bottom: 1.5px solid rgba(6,76,114,0.20) !important;
  color: #064C72;
}
.pnl-row-ebitda td {
  font-weight: 900; font-size: 13px;
  background: rgba(27,90,67,0.08);
  border-top: 2px solid rgba(27,90,67,0.30) !important;
  color: #1B5A43;
  padding-top: 8px; padding-bottom: 8px;
}
.pnl-row-neg td:last-child { color: #C0392B; }
.pnl-row-pos td:last-child { color: #1B5A43; }

/* Sidebar scenario chip */
.scenario-chip {
  font-size: 11px; padding: 3px 8px;
  border-radius: 20px;
  background: rgba(6,76,114,0.08);
  color: #064C72;
  font-weight: 600;
  display: inline-block;
  margin-bottom: 6px;
}

/* Narrative explanation boxes */
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
""", unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    try:
        st.image("logo_waribei_icon@2x.png", width=110)
    except Exception:
        st.markdown("### Waribei")

    st.markdown("---")
    page = st.radio("", ["📊 Simulateur", "📖 Le modèle"], label_visibility="collapsed")

    if page == "📊 Simulateur":
        st.markdown("---")
        st.markdown('<div class="section-label">Scénario</div>', unsafe_allow_html=True)

        def _on_scenario_change():
            s = st.session_state["_scenario_select"]
            if s != "Custom":
                apply_scenario_preset(s)

        st.selectbox(
            "",
            list(SCENARIOS_PRESETS.keys()),
            key="_scenario_select",
            label_visibility="collapsed",
            on_change=_on_scenario_change,
        )

        st.markdown("")
        st.markdown('<div class="section-label">Date de référence</div>', unsafe_allow_html=True)
        dcols = st.columns([0.65, 0.35])
        with dcols[0]:
            picked = st.date_input("", value=st.session_state.get("scenario_date", DEFAULT_DATE),
                                   label_visibility="collapsed")
            st.session_state["scenario_date"] = picked
            apply_preset_for_date(picked, force=False)
        with dcols[1]:
            if st.button("Today", use_container_width=True):
                st.session_state["scenario_date"] = DEFAULT_DATE
                apply_preset_for_date(DEFAULT_DATE, force=True)
                st.rerun()

        st.markdown("")
        st.markdown('<div class="section-label">Sauvegarder</div>', unsafe_allow_html=True)
        scenario_label = st.text_input(
            "",
            value=st.session_state.get("scenario_name_autofill", "Scenario"),
            label_visibility="collapsed",
            placeholder="Nom du scénario",
        )
        if st.button("💾 Sauvegarder", use_container_width=True, type="primary"):
            # read live CM from session (will be computed below)
            d = st.session_state["scenario_date"]
            rev = float(st.session_state["revenu_pct"])
            c_p = float(st.session_state["cout_paiement_pct"])
            c_l = float(st.session_state["cout_liquidite_10j_pct"])
            c_d = float(st.session_state["defaut_30j_pct"])
            cm_now = rev - c_p - c_l - c_d
            replaced = False
            for i, s in enumerate(st.session_state.scenarios):
                if s.get("date") == d:
                    st.session_state.scenarios[i] = {"date": d, "name": scenario_label, "contribution_margin_pct": cm_now}
                    replaced = True
                    break
            if not replaced:
                st.session_state.scenarios.append({"date": d, "name": scenario_label, "contribution_margin_pct": cm_now})
            st.success(f"✓ Sauvegardé")

        if len(st.session_state.scenarios) > 0:
            st.markdown("---")
            st.markdown('<div class="section-label">Points sauvegardés</div>', unsafe_allow_html=True)
            for s in sorted(st.session_state.scenarios, key=lambda x: x["date"]):
                cm_val = s["contribution_margin_pct"]
                color = "#1B5A43" if cm_val >= 0 else "#C0392B"
                st.markdown(
                    f'<div style="font-size:11px; margin-bottom:3px;">'
                    f'<span style="opacity:0.5;">{s["date"].strftime("%b %y")}</span> '
                    f'<span style="font-weight:700; color:{color};">{cm_val:+.2f}%</span> '
                    f'<span style="opacity:0.6;">{s["name"][:20]}</span></div>',
                    unsafe_allow_html=True,
                )
            if st.button("Effacer", use_container_width=True):
                st.session_state.scenarios = []
                st.session_state.seeded_history = False
                st.rerun()


# ==================================================
# PAGE 2 — EXPLICATION DU MODÈLE
# ==================================================
if page == "📖 Le modèle":
    st.title("Le modèle économique de Waribei")

    st.markdown("---")
    st.subheader("🏗️ Qui est Waribei ?")
    st.markdown("""
    <div class="narrative-box">
    Waribei est l'<strong>OS du crédit marchand court terme</strong> en Afrique francophone.
    On connecte les <strong>détaillants informels</strong> aux <strong>microfinances (MFIs)</strong>
    via notre stack : WariStock (commandes), WariBrain (scoring), WariPortal (MFI dashboard).<br><br>
    <strong>On n'est pas un prêteur.</strong> Le capital vient des MFIs. On est l'infrastructure.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💰 La mécanique de revenus")
    col_a, col_b = st.columns([0.55, 0.45])
    with col_a:
        st.markdown("""
        **Revenu = % du montant décaissé à chaque prêt**

        Prêt moyen ~338€, durée 10 jours, ~2.6 cycles/mois sur le net book.
        Take-rate ~4.58% du volume décaissé → **MRR ~16k€** sur un net book de 135k€.

        **Les 3 coûts qui érodent la CM :**
        - **Paiement (1.75%)** : frais rails Visa/MC/mobile money → Open Banking → 0.50%
        - **Liquidité (0.30%)** : coût du capital sur 10j (dette MFI)
        - **Défaut (1.50%)** : PAR30 → WariBrain → cible <0.80%
        """)
    with col_b:
        st.markdown("""
        <div class="narrative-box green">
        <strong>Données exactes Q1 2026</strong><br><br>
        Jan : 407 904€ disbursed, 1 134 prêts, 449 retailers → MRR 17 530€<br>
        Fév : 354 367€ disbursed, 1 050 prêts, 400 retailers → MRR 16 203€<br><br>
        Net book : 135k€ | PAR30 &lt;1.5% | EBITDA −10.6k€ | Burn 12k€/mois
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🚀 Les 3 leviers")
    st.markdown("""
    | Levier | Impact CM | Timeline | Statut |
    |---|---|---|---|
    | **Open Banking** | Paiement 1.75% → 0.50% → **+1.25%** | 6-12 mois | En cours (FMCI/BCEAO) |
    | **Scoring WariBrain** | Défaut 1.50% → 0.80% → **+0.70%** | 12-18 mois | En dev |
    | **Scale net book** | Revenu ×3-8× sur opex fixe | Post-Seed | Priorité #1 |

    **L'opex est fixe.** 135k → 460k net book = même équipe. C'est là qu'est le levier.
    """)

    st.markdown("---")
    st.subheader("🎯 Les 4 scénarios")
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("""
        **Réalité Fév 2026** — Net book 135k€, cycles 2.63, vol 354k€. EBITDA −10.8k€.

        **Break-even OB** — Net book 250k + Open Banking (pay 0.50%) + scoring (défaut 0.80%).
        Volume 650k. EBITDA ~+1.5k€ à opex 12k.
        """)
    with s2:
        st.markdown("""
        **Post-Seed 12 mois** — Net book 460k via facility MFI, OB partiel.
        Volume 1.2M. EBITDA ~+1.3k€ à opex 18k (1-2 embauches).

        **Series A target** — Net book 1.15M, full OB, score mature.
        Volume 3M. MRR 120k. EBITDA +18k à opex 35k.
        """)

    st.markdown("---")
    st.markdown("""
    <div class="narrative-box">
    <strong>Méthodologie</strong><br>
    revenu_pct = MRR / volume décaissé × 100 | cycles/mois = volume / net loan portfolio |
    volume = net book × cycles | CM% = revenu − paiement − liquidité − défaut
    </div>
    """, unsafe_allow_html=True)

# ==================================================
# PAGE 1 — SIMULATEUR
# ==================================================
else:
    # -------- CALCULATIONS (needed before KPI bar) --------
    revenu_pct = float(st.session_state["revenu_pct"])
    cout_paiement_pct = float(st.session_state["cout_paiement_pct"])
    cout_liquidite_10j_pct = float(st.session_state["cout_liquidite_10j_pct"])
    defaut_30j_pct = float(st.session_state["defaut_30j_pct"])
    cycles_per_month = float(st.session_state["cycles_per_month"])
    loan_book_k = float(st.session_state["loan_book_k"])
    avg_loan_value_eur = float(st.session_state["avg_loan_value_eur"])
    tx_per_client_per_month = float(st.session_state["tx_per_client_per_month"])
    cogs_per_client_eur = float(st.session_state.get("cogs_per_client_eur", 5.0))
    cac_per_new_client_eur = float(st.session_state.get("cac_per_new_client_eur", 30.0))
    opex_current_k = float(st.session_state.get("opex_current_k", 12.0))
    growth_months = int(st.session_state.get("growth_months", 12))

    taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS
    contribution_margin_pct = revenu_pct - cout_paiement_pct - cout_liquidite_10j_pct - defaut_30j_pct
    monthly_volume_eur = loan_book_k * 1000 * cycles_per_month
    monthly_revenue_eur = monthly_volume_eur * (revenu_pct / 100)
    annual_revenue_eur = monthly_revenue_eur * 12
    contribution_value_k = loan_book_k * cycles_per_month * contribution_margin_pct / 100
    nb_loans_per_month = monthly_volume_eur / avg_loan_value_eur if avg_loan_value_eur > 0 else 0.0
    nb_clients_per_month = nb_loans_per_month / tx_per_client_per_month if tx_per_client_per_month > 0 else 0.0
    revenue_per_loan_eur = avg_loan_value_eur * (revenu_pct / 100)
    revenue_per_client_month_eur = revenue_per_loan_eur * tx_per_client_per_month

    base_clients = 420.0
    new_clients_per_month = max(0.0, (nb_clients_per_month - base_clients) / growth_months)
    rev_k = monthly_revenue_eur / 1000
    tx_cost_k = monthly_volume_eur * (cout_paiement_pct / 100) / 1000
    liq_cost_k = monthly_volume_eur * (cout_liquidite_10j_pct / 100) / 1000
    risk_cost_k = monthly_volume_eur * (defaut_30j_pct / 100) / 1000
    cogs_k = nb_clients_per_month * cogs_per_client_eur / 1000
    cac_k = new_clients_per_month * cac_per_new_client_eur / 1000
    cm1_k = rev_k - tx_cost_k - liq_cost_k
    cm2_k = cm1_k - risk_cost_k - cogs_k
    cm3_k = cm2_k - cac_k
    ebitda_current_k = cm3_k - opex_current_k

    # -------- HEADER --------
    st.markdown(
        '<h1 style="margin-bottom:2px;">Unit Economics — Waribei</h1>'
        '<p style="opacity:0.45; font-size:11px; margin-top:0;">Net loan portfolio · Données réelles Fév 2026</p>',
        unsafe_allow_html=True,
    )

    # -------- KPI BAR --------
    arr_k = annual_revenue_eur / 1000
    k1, k2, k3, k4, k5 = st.columns(5)
    cm_cls = "pos" if contribution_margin_pct >= 0 else "neg"
    eb_cls = "pos" if ebitda_current_k >= 0 else "neg"

    with k1:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">Net book</div>
          <div class="kpi-value">{loan_book_k:,.0f}<span style="font-size:13px;"> k€</span></div>
          <div class="kpi-sub">{cycles_per_month:.2f} cycles/mois</div>
          <div class="kpi-sub2">{nb_loans_per_month:,.0f} prêts/mois</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">Volume mensuel</div>
          <div class="kpi-value">{monthly_volume_eur/1000:,.0f}<span style="font-size:13px;"> k€</span></div>
          <div class="kpi-sub">{nb_clients_per_month:,.0f} retailers actifs</div>
          <div class="kpi-sub2">{new_clients_per_month:.0f} new retailers/mois</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">MRR</div>
          <div class="kpi-value">{monthly_revenue_eur/1000:,.1f}<span style="font-size:13px;"> k€</span></div>
          <div class="kpi-sub">{revenu_pct:.2f}% take-rate</div>
          <div class="kpi-sub2">ARR {arr_k:,.0f} k€</div>
        </div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">Contribution</div>
          <div class="kpi-value {cm_cls}">{contribution_margin_pct:+.2f}<span style="font-size:13px;">%</span></div>
          <div class="kpi-sub">{contribution_value_k:+.1f} k€/mois</div>
        </div>""", unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">EBITDA</div>
          <div class="kpi-value {eb_cls}">{ebitda_current_k:+.1f}<span style="font-size:13px;"> k€</span></div>
          <div class="kpi-sub">opex {opex_current_k:,.0f} k€/mois</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

    # -------- TABS --------
    tab_sim, tab_pnl, tab_evol = st.tabs(["⚙️ Simulation", "📊 P&L cascade", "📈 Évolution"])

    # ==================================================
    # TAB 1 — SIMULATION
    # ==================================================
    with tab_sim:
        inp_col, out_col = st.columns([0.52, 0.48], gap="large")

        # ---- INPUTS (LEFT) ----
        with inp_col:

            # Section 1: Par transaction
            st.markdown('<div class="section-label">Par transaction — % du volume décaissé</div>', unsafe_allow_html=True)
            r1c1, r1c2 = st.columns(2, gap="medium")
            with r1c1:
                st.slider("Revenus / trx (%)", 1.0, 7.0, step=0.01, key="revenu_pct",
                          help="Take-rate effectif sur montant décaissé.")
                st.caption("Réel Fév 2026 : 4.58%")

                st.slider("Coût liquidité 10j (%)", 0.0, 1.5, step=0.01, key="cout_liquidite_10j_pct",
                          help=f"Coût capital 10j. Annualisé : {taux_liquidite_annuel_pct:.1f}%")
                st.caption(f"Annualisé : {taux_liquidite_annuel_pct:.1f}% — réel : 0.30%")

            with r1c2:
                st.slider("Coût paiement (%)", 0.0, 3.0, step=0.01, key="cout_paiement_pct",
                          help="Rails paiement Visa/MC/MoMo. Open Banking → 0.50%")
                st.caption("OB cible : 0.50% — réel : 1.75%")

                st.slider("Défaut 30j — PAR30 (%)", 0.0, 5.0, step=0.01, key="defaut_30j_pct",
                          help="Perte nette sur portefeuille. WariBrain → cible <0.80%")
                st.caption("WariBrain cible : 0.80% — réel : 1.50%")

            # CM equation (live)
            cm_cls2 = "pos" if contribution_margin_pct >= 0 else "neg"
            st.markdown(f"""
            <div class="cm-equation">
              <span class="rev">+{revenu_pct:.2f}%</span>
              <span style="opacity:0.4;">−</span>
              <span class="cost">{cout_paiement_pct:.2f}%</span>
              <span style="opacity:0.4;">−</span>
              <span class="cost">{cout_liquidite_10j_pct:.2f}%</span>
              <span style="opacity:0.4;">−</span>
              <span class="cost">{defaut_30j_pct:.2f}%</span>
              <span style="opacity:0.4;">=</span>
              <span class="result {cm_cls2}">CM {contribution_margin_pct:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            # Section 2: Volume
            st.markdown('<div class="section-label">Volume &amp; portefeuille</div>', unsafe_allow_html=True)
            v1, v2 = st.columns(2, gap="medium")
            with v1:
                st.slider("Net loan portfolio (k€)", 10.0, 5000.0, step=5.0, key="loan_book_k")
                st.caption(f"Réel Fév : 135k€")
            with v2:
                st.slider("Cycles / mois", 1.0, 4.0, step=0.01, key="cycles_per_month")
                st.caption(f"Réel Fév : 2.63")

            vol_display = monthly_volume_eur / 1000
            st.markdown(f"""
            <div style="font-size:11px; padding:7px 10px; background:rgba(6,76,114,0.04);
                        border-radius:8px; margin-top:4px;">
              Volume = {loan_book_k:,.0f} k€ × {cycles_per_month:.2f} =
              <strong>{vol_display:,.0f} k€/mois</strong>
              ({nb_loans_per_month:,.0f} prêts · {nb_clients_per_month:,.0f} retailers)
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            # Section 3: Par prêt, coûts fixes & acquisition
            st.markdown('<div class="section-label">Par prêt, coûts fixes &amp; acquisition</div>', unsafe_allow_html=True)
            p1, p2, p3 = st.columns(3, gap="small")
            with p1:
                st.slider("Prêt moyen (€)", 100.0, 1000.0, step=10.0, key="avg_loan_value_eur")
                st.caption(f"Réel : 338€")
                st.slider("Opex (k€/mois)", 0.0, 200.0, step=1.0, key="opex_current_k")
                st.caption(f"Réel : 12k€/mois")
            with p2:
                st.slider("Prêts / retailer", 1.0, 8.0, step=0.1, key="tx_per_client_per_month")
                st.caption(f"Réel : 2.6 prêts/mois")
                st.slider("CAC / new retailer (€)", 0.0, 200.0, step=1.0, key="cac_per_new_client_eur")
            with p3:
                st.slider("COGS / retailer (€)", 0.0, 50.0, step=0.5, key="cogs_per_client_eur")
                st.slider("Horizon croissance (mois)", 1, 36, step=1, key="growth_months")
                st.caption(f"Base : {base_clients:.0f} retailers actifs")

        # ---- OUTPUTS (RIGHT) ----
        with out_col:

            # P&L cascade bar (replaces waterfall)
            st.markdown('<div class="section-label" style="margin-bottom:14px;">P&L cascade</div>', unsafe_allow_html=True)
            cascade_data_sim = pd.DataFrame({
                "Étape": ["CM 1", "CM 2", "CM 3", "EBITDA"],
                "Valeur": [cm1_k, cm2_k, cm3_k, ebitda_current_k],
                "c": ["pos" if v >= 0 else "neg" for v in [cm1_k, cm2_k, cm3_k, ebitda_current_k]],
            })
            cs_sim = alt.Scale(domain=["pos", "neg"], range=["#064C72", "#F83131"])
            casc_bar_sim = (
                alt.Chart(cascade_data_sim)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6,
                          cornerRadiusBottomLeft=6, cornerRadiusBottomRight=6)
                .encode(
                    x=alt.X("Étape:N", sort=["CM 1", "CM 2", "CM 3", "EBITDA"],
                            title=None, axis=alt.Axis(labelFontSize=13, labelPadding=6)),
                    y=alt.Y("Valeur:Q", title="k€", axis=alt.Axis(labelFontSize=11)),
                    color=alt.Color("c:N", scale=cs_sim, legend=None),
                    tooltip=[alt.Tooltip("Étape:N"), alt.Tooltip("Valeur:Q", format=",.1f", title="k€")],
                )
            )
            casc_lbl_sim = (
                alt.Chart(cascade_data_sim)
                .mark_text(dy=-14, fontSize=13, fontWeight="bold", color="#333")
                .encode(
                    x=alt.X("Étape:N", sort=["CM 1", "CM 2", "CM 3", "EBITDA"]),
                    y="Valeur:Q",
                    text=alt.Text("Valeur:Q", format=".1f"),
                )
            )
            st.altair_chart(
                (casc_bar_sim + casc_lbl_sim).properties(height=220),
                use_container_width=True,
            )

            st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

            # Retailers — prominent 3-metric row
            st.markdown('<div class="section-label" style="margin-bottom:10px;">Retailers & volumes</div>', unsafe_allow_html=True)
            rr1, rr2, rr3 = st.columns(3)
            with rr1:
                delta_retailers = nb_clients_per_month - base_clients
                st.metric(
                    "Retailers servis",
                    f"{nb_clients_per_month:,.0f}",
                    delta=f"{delta_retailers:+.0f} vs base",
                    delta_color="normal",
                )
            with rr2:
                st.metric("Prêts / mois", f"{nb_loans_per_month:,.0f}")
            with rr3:
                st.metric("Rev / retailer", f"{revenue_per_client_month_eur:.0f} €")

            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

            # Break-even progress bar
            # Analytical fixed-point solution: solve book_be such that EBITDA=0
            # accounting for cogs and cac scaling with book size.
            # α = clients per k€ of net book
            # Case A (no new client acq): book_be = opex / (cycles×cm% - α×cogs/1000)
            # Case B (with new client acq): book_be = (opex+D) / (cycles×cm% - α×cogs/1000 - α×cac/(gm×1000))
            #   where D = base_clients × cac / (gm × 1000)
            if contribution_margin_pct > 0 and avg_loan_value_eur > 0 and tx_per_client_per_month > 0:
                alpha = 1000 * cycles_per_month / (avg_loan_value_eur * tx_per_client_per_month)
                A_coeff = cycles_per_month * (contribution_margin_pct / 100)
                B_coeff = alpha * cogs_per_client_eur / 1000
                net_A = A_coeff - B_coeff
                # Case A: no new client acquisition
                be_book_case_a = opex_current_k / net_A if net_A > 0 else float("inf")
                nb_clients_at_a = be_book_case_a * alpha
                if nb_clients_at_a <= base_clients:
                    be_book_k_fixed = be_book_case_a
                else:
                    # Case B: new client acquisition costs scale with book
                    C_coeff = alpha * cac_per_new_client_eur / (growth_months * 1000)
                    D_offset = base_clients * cac_per_new_client_eur / (growth_months * 1000)
                    net_B = net_A - C_coeff
                    be_book_k_fixed = (opex_current_k + D_offset) / net_B if net_B > 0 else float("inf")
            else:
                be_book_k_fixed = float("inf")

            if be_book_k_fixed < float("inf") and be_book_k_fixed > 0:
                be_book_k = be_book_k_fixed
                ratio = loan_book_k / be_book_k if be_book_k > 0 else 0
                bar_pct = min(100, ratio * 100)
                bar_color = "#1B5A43" if ratio >= 1.0 else "#064C72"
                st.markdown(
                    '<div class="section-label" style="margin-bottom:10px;">Progression vers le break-even</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.07); border-radius:8px; height:14px; overflow:hidden;">
                  <div style="width:{bar_pct:.1f}%; height:100%; background:{bar_color}; border-radius:8px;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:baseline;
                            margin-top:10px; font-size:12px;">
                  <span style="font-size:20px; font-weight:900; color:{bar_color}; line-height:1;">{bar_pct:.0f}%</span>
                  <span style="opacity:0.7;">
                    <strong>{loan_book_k:,.0f} k€</strong> actuel
                    &nbsp;→&nbsp;
                    cible <strong>{be_book_k:,.0f} k€</strong> net book
                  </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="font-size:11px; color:#C0392B; padding:10px 14px; '
                    'background:rgba(192,57,43,0.06); border-radius:8px;">'
                    '⚠️ CM négative — ajuste les curseurs de coûts</div>',
                    unsafe_allow_html=True,
                )

    # ==================================================
    # TAB 2 — P&L
    # ==================================================
    with tab_pnl:

        def color_val(v):
            c = "#1B5A43" if v >= 0 else "#C0392B"
            return f'<span style="color:{c}; font-weight:700;">{v:+,.1f} k€</span>'

        def neutral_val(v):
            return f'<span style="font-weight:600;">{v:,.1f} k€</span>'

        tbl_col, chart_col = st.columns([0.50, 0.50], gap="large")

        with tbl_col:
            st.markdown('<div class="section-label">P&L mensuelle</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <table class="pnl-table">
              <tr><td><b>Revenues</b></td><td>{neutral_val(rev_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Coût paiement (rails)</td><td>{color_val(-tx_cost_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Coût liquidité (10j)</td><td>{color_val(-liq_cost_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 1 — marge brute financière</td><td>{color_val(cm1_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Défaut 30j (PAR30)</td><td>{color_val(-risk_cost_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ COGS <span style="opacity:0.5;">({nb_clients_per_month:,.0f} ret. × {cogs_per_client_eur:.1f}€)</span></td><td>{color_val(-cogs_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 2 — après risque &amp; infra</td><td>{color_val(cm2_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ CAC <span style="opacity:0.5;">({new_clients_per_month:,.0f} new × {cac_per_new_client_eur:.0f}€)</span></td><td>{color_val(-cac_k)}</td></tr>
              <tr class="pnl-row-margin"><td>CM 3 — après acquisition</td><td>{color_val(cm3_k)}</td></tr>
              <tr class="pnl-row-sub"><td>↳ Opex</td><td>{color_val(-opex_current_k)}</td></tr>
              <tr class="pnl-row-ebitda"><td>EBITDA</td><td>{color_val(ebitda_current_k)}</td></tr>
            </table>
            """, unsafe_allow_html=True)


        with chart_col:
            # EBITDA big display
            eb_color = "#1B5A43" if ebitda_current_k >= 0 else "#C0392B"
            st.markdown(f"""
            <div style="text-align:center; padding:20px; border:2px solid {eb_color};
                        border-radius:14px; background:{'rgba(27,90,67,0.06)' if ebitda_current_k >= 0 else 'rgba(192,57,43,0.06)'};
                        margin-bottom:16px;">
              <div style="font-size:11px; font-weight:700; text-transform:uppercase;
                          letter-spacing:0.06em; opacity:0.55; margin-bottom:6px;">EBITDA / mois</div>
              <div style="font-size:36px; font-weight:900; color:{eb_color}; line-height:1;">
                {ebitda_current_k:+,.1f} k€
              </div>
              <div style="font-size:11px; opacity:0.5; margin-top:6px;">
                opex {opex_current_k:,.0f} k€ · {nb_clients_per_month:,.0f} retailers
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Cascade bar
            st.markdown('<div class="section-label">Cascade CM → EBITDA</div>', unsafe_allow_html=True)
            cascade_data = pd.DataFrame({
                "Étape": ["CM 1", "CM 2", "CM 3", "EBITDA"],
                "Valeur": [cm1_k, cm2_k, cm3_k, ebitda_current_k],
                "c": ["pos" if v >= 0 else "neg" for v in [cm1_k, cm2_k, cm3_k, ebitda_current_k]],
            })
            cs2 = alt.Scale(domain=["pos", "neg"], range=["#064C72", "#F83131"])
            casc_bar = (
                alt.Chart(cascade_data)
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5,
                          cornerRadiusBottomLeft=5, cornerRadiusBottomRight=5)
                .encode(
                    x=alt.X("Étape:N", sort=["CM 1", "CM 2", "CM 3", "EBITDA"],
                            title=None, axis=alt.Axis(labelFontSize=11)),
                    y=alt.Y("Valeur:Q", title="k€", axis=alt.Axis(labelFontSize=10)),
                    color=alt.Color("c:N", scale=cs2, legend=None),
                    tooltip=[alt.Tooltip("Étape:N"), alt.Tooltip("Valeur:Q", format=",.1f", title="k€")],
                )
            )
            casc_lbl = (
                alt.Chart(cascade_data).mark_text(dy=-9, fontSize=11, fontWeight="bold", color="#333")
                .encode(
                    x=alt.X("Étape:N", sort=["CM 1", "CM 2", "CM 3", "EBITDA"]),
                    y="Valeur:Q",
                    text=alt.Text("Valeur:Q", format=".1f"),
                )
            )
            st.altair_chart((casc_bar + casc_lbl).properties(height=200), use_container_width=True)

            # Waterfall per transaction (moved from Tab 1)
            st.markdown(
                '<div class="section-label" style="margin-top:20px; margin-bottom:14px;">Décomposition par transaction (%)</div>',
                unsafe_allow_html=True,
            )
            wf_steps = ["Revenu", "Paiement", "Liquidité", "Défaut 30j", "CM nette"]
            wf_values = [revenu_pct, -cout_paiement_pct, -cout_liquidite_10j_pct, -defaut_30j_pct, contribution_margin_pct]
            wf_starts, wf_ends = [], []
            running = 0.0
            for v in wf_values[:-1]:
                wf_starts.append(running)
                running += v
                wf_ends.append(running)
            wf_starts.append(0.0)
            wf_ends.append(contribution_margin_pct)
            wf_df = pd.DataFrame({
                "step": wf_steps, "value": wf_values,
                "start": wf_starts, "end": wf_ends,
                "type": ["positive", "negative", "negative", "negative", "total"],
            })
            wf_cs = alt.Scale(domain=["positive", "negative", "total"], range=["#1B5A43", "#F83131", "#064C72"])
            wf_bar = (
                alt.Chart(wf_df)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                          cornerRadiusBottomLeft=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("step:N", sort=wf_steps, title=None,
                            axis=alt.Axis(labelFontSize=11, labelPadding=6)),
                    y=alt.Y("start:Q", axis=alt.Axis(title="%", labelFontSize=10)),
                    y2="end:Q",
                    color=alt.Color("type:N", scale=wf_cs, legend=None),
                    tooltip=[alt.Tooltip("step:N"), alt.Tooltip("value:Q", format=".2f", title="%")],
                )
            )
            wf_lbl = (
                alt.Chart(wf_df)
                .mark_text(dy=-13, fontSize=12, fontWeight="bold", color="#333")
                .encode(
                    x=alt.X("step:N", sort=wf_steps),
                    y="end:Q",
                    text=alt.Text("value:Q", format="+.2f"),
                )
            )
            st.altair_chart((wf_bar + wf_lbl).properties(height=200), use_container_width=True)

    # ==================================================
    # TAB 3 — ÉVOLUTION
    # ==================================================
    with tab_evol:
        if len(st.session_state.scenarios) > 1:
            scen_df = pd.DataFrame(st.session_state.scenarios).sort_values("date")
            scen_df["date_str"] = scen_df["date"].apply(lambda d: d.strftime("%b %Y"))
            scen_df["cm_fmt"] = scen_df["contribution_margin_pct"].apply(lambda v: f"{v:+.2f}%")
            scen_df["color"] = scen_df["contribution_margin_pct"].apply(lambda v: "pos" if v >= 0 else "neg")

            st.markdown('<div class="section-label">Évolution de la contribution margin</div>', unsafe_allow_html=True)
            line_chart = (
                alt.Chart(scen_df)
                .mark_line(point=alt.OverlayMarkDef(size=80), strokeWidth=2.5, color="#064C72")
                .encode(
                    x=alt.X("date_str:N", sort=list(scen_df["date_str"]), title=None,
                            axis=alt.Axis(labelFontSize=12)),
                    y=alt.Y("contribution_margin_pct:Q", title="CM %",
                            scale=alt.Scale(zero=False), axis=alt.Axis(labelFontSize=11)),
                    tooltip=[
                        alt.Tooltip("name:N", title="Scénario"),
                        alt.Tooltip("contribution_margin_pct:Q", format=".2f", title="CM %"),
                    ],
                )
            )
            labels_chart = (
                alt.Chart(scen_df).mark_text(dy=-14, fontSize=11, fontWeight="bold", color="#064C72")
                .encode(
                    x=alt.X("date_str:N", sort=list(scen_df["date_str"])),
                    y="contribution_margin_pct:Q",
                    text="cm_fmt:N",
                )
            )
            st.altair_chart(
                (line_chart + labels_chart).properties(height=280),
                use_container_width=True,
            )

            # Table des points
            st.markdown('<div class="section-label">Points enregistrés</div>', unsafe_allow_html=True)
            display_df = scen_df[["date_str", "name", "contribution_margin_pct"]].copy()
            display_df.columns = ["Date", "Label", "CM %"]
            display_df["CM %"] = display_df["CM %"].apply(lambda v: f"{v:+.2f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:60px 20px; opacity:0.4;">
              <div style="font-size:32px;">📈</div>
              <div style="font-size:13px; margin-top:8px;">
                Sauvegarde des scénarios via la sidebar pour voir l'évolution dans le temps.
              </div>
            </div>
            """, unsafe_allow_html=True)
