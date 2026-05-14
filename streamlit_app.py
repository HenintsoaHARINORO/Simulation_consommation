"""
Interface web Streamlit – Moteur PV (version simplifiee)
"""
import sys
from pathlib import Path
import tempfile

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))

from domain.entities.installation import SystemConfig, BatteryConfig, FinancialConfig
from domain.services.simulate_installation import SimulateInstallationUseCase
from application.dtos.simulation_dto import SimulationRequest
from infrastructure.adapters.synthetic_adapters import (
    SyntheticIrradianceAdapter,
    SyntheticConsumptionAdapter,
)
from pvgis_irradiance_adapter import PvgisIrradianceAdapter
from enedis_consumption_adapter import EnedisConsumptionAdapter

st.set_page_config(page_title="Moteur PV", layout="wide")

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configuration")

    data_mode = st.radio("Source des donnees", ["Synthetique (demo)", "Fichiers CSV reels"])

    irradiance_repo  = None
    consumption_repo = None

    if data_mode == "Fichiers CSV reels":
        pvgis_file  = st.file_uploader("Irradiance PVGIS (.csv)",    type=["csv"])
        enedis_file = st.file_uploader("Consommation Enedis (.csv)", type=["csv"])

        if pvgis_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(pvgis_file.read())
                irradiance_repo = PvgisIrradianceAdapter(tmp.name)

        if enedis_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(enedis_file.read())
                consumption_repo = EnedisConsumptionAdapter(tmp.name)
    else:
        irradiance_repo  = SyntheticIrradianceAdapter(year=2023)
        consumption_repo = SyntheticConsumptionAdapter(year=2023)

    st.markdown("---")

    peak_power = st.slider("Puissance crete (kWc)", 1.0, 36.0, 6.0, 0.5)
    target_kwh = st.number_input("Consommation annuelle (kWh)", 1000, 15000, 3500, 100)

    run_btn = st.button("Lancer la simulation", type="primary", use_container_width=True)

# ── Main ───────────────────────────────────────────────────────────
st.title("Moteur PV")

if not run_btn:
    st.info("Configurez vos parametres puis cliquez sur **Lancer la simulation**.")
    st.stop()

if data_mode == "Fichiers CSV reels" and (irradiance_repo is None or consumption_repo is None):
    st.error("Veuillez uploader les deux fichiers CSV avant de lancer.")
    st.stop()

# ── Simulation ─────────────────────────────────────────────────────
with st.spinner("Simulation en cours…"):
    try:
        result = SimulateInstallationUseCase(irradiance_repo, consumption_repo).execute(
            SimulationRequest(
                sys_config=SystemConfig(peak_power_kwp=float(peak_power), pr=0.80),
                bat_config=BatteryConfig(capacity_kwh=0.0),
                fin_config=FinancialConfig(
                    capex_per_kwp=1400,
                    grid_price_eur_kwh=0.2276,
                    sell_price_eur_kwh=0.1276,
                    discount_rate=0.05,
                    project_life_years=25,
                ),
                label=f"{peak_power} kWc",
                target_annual_kwh=float(target_kwh),
            )
        )
    except Exception as e:
        st.error(f"Erreur : {e}")
        st.stop()

ekpis = result.energy_kpis
fkpis = result.financial_kpis
flows = result.hourly_flows

# ── KPIs ───────────────────────────────────────────────────────────
st.subheader("Indicateurs cles")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Production",       f"{ekpis.production_kwh:,.0f} kWh")
c2.metric("Autoconsommation", f"{ekpis.self_consumption_rate * 100:.1f} %")
c3.metric("Autosuffisance",   f"{ekpis.self_sufficiency_rate  * 100:.1f} %")
c4.metric("VAN",              f"{fkpis.npv_eur:,.0f} €")
c5.metric("TRI",              f"{fkpis.irr_pct:.1f} %" if fkpis.irr_pct else "N/A")
c6.metric("Payback",          f"{fkpis.payback_years:.1f} ans" if fkpis.payback_years else "N/A")

st.markdown("---")

# ── Charts ─────────────────────────────────────────────────────────
st.subheader("Flux energetiques")

months_fr = ["Jan","Fev","Mar","Avr","Mai","Jun","Jul","Aou","Sep","Oct","Nov","Dec"]

tab_week, tab_month, tab_year = st.tabs(["Semaine type", "Vue mensuelle", "Vue annuelle"])

with tab_week:
    july = flows[flows.index.month == 7].iloc[:7 * 24]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=july.index, y=july["production_kwh"],    name="Production",      fill="tozeroy", line=dict(color="#f59e0b", width=1.5)))
    fig.add_trace(go.Scatter(x=july.index, y=july["consumption_kwh"],   name="Consommation",                    line=dict(color="#6366f1", width=1.5)))
    fig.add_trace(go.Scatter(x=july.index, y=july["self_consumed_kwh"], name="Autoconsommee",   fill="tozeroy", line=dict(color="#10b981", width=1)))
    fig.add_trace(go.Scatter(x=july.index, y=july["injected_kwh"],      name="Injectee reseau", fill="tozeroy", line=dict(color="#f97316", width=1)))
    fig.add_trace(go.Scatter(x=july.index, y=july["from_grid_kwh"],     name="Soutirage reseau",fill="tozeroy", line=dict(color="#ef4444", width=1)))
    fig.update_layout(height=400, xaxis_title="Date", yaxis_title="kWh",
                      hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with tab_month:
    monthly  = flows.resample("ME").sum()
    x_labels = [months_fr[m - 1] for m in monthly.index.month]

    peak_idx   = monthly["production_kwh"].idxmax()
    peak_month = months_fr[peak_idx.month - 1]
    peak_val   = monthly["production_kwh"].max()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_labels, y=monthly["production_kwh"],    name="Production",    marker_color="#f59e0b", marker_line_width=0))
    fig.add_trace(go.Bar(x=x_labels, y=monthly["consumption_kwh"],   name="Consommation",  marker_color="#6366f1", marker_line_width=0))
    fig.add_trace(go.Bar(x=x_labels, y=monthly["self_consumed_kwh"], name="Autoconsommee", marker_color="#10b981", marker_line_width=0))
    fig.add_trace(go.Bar(x=x_labels, y=monthly["injected_kwh"],      name="Injection",     marker_color="#f97316", marker_line_width=0))
    fig.add_annotation(
        x=peak_month, y=peak_val,
        text=f"Pic : {peak_val:,.0f} kWh",
        showarrow=True, arrowhead=2, arrowcolor="#f59e0b",
        ax=0, ay=-40,
        font=dict(size=11, color="#92400e"),
        bgcolor="white", bordercolor="#f59e0b", borderwidth=1, borderpad=5,
    )
    fig.update_layout(
        title=dict(text="Flux energetiques mensuels", font=dict(size=15), x=0),
        barmode="group", height=420,
        xaxis=dict(title="Mois", tickfont=dict(size=12)),
        yaxis=dict(title="kWh", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white", bargap=0.2, bargroupgap=0.05,
        hovermode="x unified", margin=dict(t=70, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_year:
    weekly = flows.resample("W").sum()
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Production vs Consommation (hebdomadaire)", "Injection et Soutirage reseau"),
        vertical_spacing=0.12,
    )
    fig.add_trace(go.Scatter(x=weekly.index, y=weekly["production_kwh"],  name="Production",  line=dict(color="#f59e0b")), row=1, col=1)
    fig.add_trace(go.Scatter(x=weekly.index, y=weekly["consumption_kwh"], name="Consommation",line=dict(color="#6366f1")), row=1, col=1)
    fig.add_trace(go.Bar(x=weekly.index, y=weekly["injected_kwh"],        name="Injection",   marker_color="#f97316"),     row=2, col=1)
    fig.add_trace(go.Bar(x=weekly.index, y=weekly["from_grid_kwh"],       name="Soutirage",   marker_color="#ef4444"),     row=2, col=1)
    fig.update_layout(height=520, template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)