"""
PRIME-Factory Interactive Streamlit Dashboard v3.0
Calibrated, Audited & Competition-Ready Interface for RoboDam 2026
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile, generate_switching_schedule, inject_sensor_noise_spikes
from energy.eci import calculate_eci
from energy.energy_model import calculate_total_energy_kwh, calculate_peak_demand_kw, calculate_financial_and_esg_impact
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence, map_hi_to_decision, estimate_rolling_rul
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study

st.set_page_config(page_title="PRIME-Factory | Industry 4.0 Platform", layout="wide", page_icon="🏭")

st.title("🏭 PRIME-Factory: Predictive, Resilient & Energy-Efficient Industry 4.0 Platform")
st.caption("National Competition for AI and Robotics (RoboDam 2026) | Team MSA")

# ==========================================
# Sidebar Interactive Demo Controls
# ==========================================
st.sidebar.header("⚙️ Interactive Demonstration Controls")

sim_mode = st.sidebar.radio(
    "Operating Schedule Mode:",
    options=["Fixed Product Regime", "Multi-Product Switching (A -> B -> C)"],
    index=0,
    help="Tests contextual intelligence and zero false alarms during production recipe transitions."
)

if sim_mode == "Fixed Product Regime":
    selected_product = st.sidebar.selectbox("Operating Product Context:", options=["Product_A", "Product_B", "Product_C"], index=1)
else:
    selected_product = "Dynamic (A -> B -> C)"

st.sidebar.subheader("Live Fault & Stress Injection")
inject_fault = st.sidebar.checkbox("Inject Bearing Degradation (M3 Sealer)", value=True)
fault_start = st.sidebar.slider("Degradation Start Time (Minute):", min_value=10, max_value=400, value=120)
max_deg = st.sidebar.slider("Max Degradation Level (%):", min_value=10, max_value=85, value=40) / 100.0

enable_chaos = st.sidebar.checkbox("Chaos Stress-Test (Sensor Noise Spikes)", value=False)
apply_dr = st.sidebar.checkbox("Enable Peak Shaving (Demand Response)", value=False)

# ==========================================
# Run Master Live Pipeline
# ==========================================
@st.cache_data
def run_master_pipeline(mode, prod_key, fault_enabled, start_t, max_d, chaos_enabled, dr_enabled):
    if mode == "Fixed Product Regime":
        schedule = [prod_key] * config.TOTAL_TIMESTEPS
    else:
        schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)

    degradation_plan = None
    if fault_enabled:
        profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=start_t, max_degradation=max_d)
        degradation_plan = {"M3": profile}

    factory = PackagingFactory()
    df = factory.run_simulation(schedule, degradation_targets=degradation_plan)

    if chaos_enabled:
        vib_vals = df[df["machine_id"] == "M3"]["vibration_rms"].values
        df.loc[df["machine_id"] == "M3", "vibration_rms"] = inject_sensor_noise_spikes(vib_vals, spike_probability=0.04)

    ai_model = PRIMEIsolationForest(contamination=0.02)
    ai_model.fit(df[df["degradation"] == 0.0])

    df["eci"] = df.apply(lambda r: calculate_eci(r["power_kw"], r["machine_id"], r["product"]), axis=1)
    df["ai_score"] = ai_model.predict_anomaly_score(df)

    m3_df = df[df["machine_id"] == "M3"].copy()
    processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
    hi_list, conf_list, pers_list, rul_str_list, attr_list = [], [], [], [], []

    for _, row in m3_df.iterrows():
        p_info = processor.update(row["ai_score"], threshold=0.5)
        hi_res = calculate_health_index_and_evidence(
            anomaly_score=row["ai_score"],
            persistence_ratio=p_info["persistence_ratio"],
            eci=row["eci"],
            temp_c=row["temperature_c"],
            vib_rms=row["vibration_rms"]
        )
        hi_list.append(hi_res["health_index"])
        pers_list.append(p_info["persistence_ratio"])
        conf_list.append(p_info["is_confirmed_anomaly"])
        attr_list.append(hi_res["penalty_contributions"])
        
        _, r_str = estimate_rolling_rul(hi_list, window_size=15)
        rul_str_list.append(r_str)

    m3_df["health_index"] = hi_list
    m3_df["persistence_ratio"] = pers_list
    m3_df["confirmed_anomaly"] = conf_list
    m3_df["raw_ai_score"] = m3_df["ai_score"]
    m3_df["context_ai_score"] = m3_df["ai_score"]

    return df, m3_df, attr_list[-1], rul_str_list[-1]

df_all, df_m3, latest_attr, latest_rul_str = run_master_pipeline(sim_mode, selected_product, inject_fault, fault_start, max_deg, enable_chaos, apply_dr)

total_energy = calculate_total_energy_kwh(df_all)
peak_kw = calculate_peak_demand_kw(df_all)
latest_hi = df_m3["health_index"].iloc[-1]
latest_eci = df_m3["eci"].iloc[-1]

fin_metrics = calculate_financial_and_esg_impact(total_energy, downtime_minutes=0, good_units=16000)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Factory Total Energy", f"{total_energy:.1f} kWh")
c2.metric("Factory Peak Demand", f"{peak_kw:.1f} kW")
c3.metric("M3 Health Index (HI)", f"{latest_hi:.1f} / 100", delta=f"{latest_hi - 100:.1f}", delta_color="inverse")
c4.metric("Estimated RUL", latest_rul_str)
c5.metric("Est. Energy Cost", f"${fin_metrics['energy_cost_usd']:.1f}", delta=f"{fin_metrics['carbon_kg']:.1f} kg CO2", delta_color="off")

decision_state = map_hi_to_decision(latest_hi)
if latest_hi >= 70:
    st.success(f"🟢 **Machine Status:** {decision_state}")
elif latest_hi >= 50:
    st.warning(f"🟡 **Machine Status:** {decision_state}")
else:
    st.error(f"🔴 **Machine Status:** {decision_state}")

st.divider()

t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Asset Condition & RUL",
    "⚡ Energy Intelligence & ECI",
    "🧠 Explainable AI & Evidence",
    "🏭 5-Machine Line Overview",
    "🏆 Scientific Policy Benchmark",
    "🔬 Calibrated Ablation Study"
])

with t1:
    fig_cond = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Physical Telemetry: Vibration RMS (g) & Temperature (°C)", "PRIME Composite Health Index (HI)")
    )
    fig_cond.add_trace(go.Scatter(x=df_m3["timestep"], y=df_m3["vibration_rms"], name="Vibration RMS (g)", line=dict(color="#1f77b4", width=2)), row=1, col=1)
    fig_cond.add_trace(go.Scatter(x=df_m3["timestep"], y=df_m3["temperature_c"], name="Temperature (°C)", line=dict(color="#ff7f0e", dash="dot")), row=1, col=1)
    fig_cond.add_trace(go.Scatter(x=df_m3["timestep"], y=df_m3["health_index"], name="Health Index (HI)", line=dict(color="#2ca02c", width=3)), row=2, col=1)
    fig_cond.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Monitor Threshold (70)", row=2, col=1)
    fig_cond.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Maintenance Threshold (50)", row=2, col=1)
    fig_cond.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    st.plotly_chart(fig_cond, use_container_width=True)

with t2:
    fig_e = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("M3 Active Power vs Expected Power Baseline (kW)", "Context-Aware Energy Condition Indicator (ECI)")
    )
    fig_e.add_trace(go.Scatter(x=df_m3["timestep"], y=df_m3["power_kw"], name="Actual Power (kW)", line=dict(color="#d62728", width=2)), row=1, col=1)
    fig_e.add_trace(go.Scatter(x=df_m3["timestep"], y=df_m3["eci"], name="ECI Deviation", line=dict(color="#9467bd", width=2)), row=2, col=1)
    fig_e.add_hline(y=0.0, line_dash="dash", line_color="gray", annotation_text="Healthy Baseline (0.0)", row=2, col=1)
    fig_e.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    st.plotly_chart(fig_e, use_container_width=True)

with t3:
    st.subheader("🔍 Explainable AI & Normalized Penalty Contributions")
    col_x1, col_x2 = st.columns([1, 1])
    with col_x1:
        st.info(f"""
        **Active Maintenance Decision Rationale:**
        * **Target Machine:** M3 Sealer (Thermal/Mechanical Asset)
        * **Operational Decision:** `{decision_state}`
        * **Current Health Index:** `{latest_hi:.1f} / 100`
        * **Persistence Confirmation:** `{'CONFIRMED' if df_m3['confirmed_anomaly'].iloc[-1] == 1 else 'UNCONFIRMED'}`
        * **Energy Deviation (ECI):** `{latest_eci * 100:+.1f}%`
        * **Remaining Useful Life:** `{latest_rul_str}`
        """)
    with col_x2:
        attr_df = pd.DataFrame({
            "Evidence Modality": list(latest_attr.keys()),
            "Penalty Contribution (%)": list(latest_attr.values())
        })
        fig_attr = px.bar(
            attr_df, x="Evidence Modality", y="Penalty Contribution (%)", color="Evidence Modality",
            title="Relative Modality Contribution to Health Index Penalty",
            text_auto=".1f"
        )
        st.plotly_chart(fig_attr, use_container_width=True)

with t4:
    agg_p = df_all.groupby("timestep")["power_kw"].sum().reset_index()
    fig_agg = px.line(agg_p, x="timestep", y="power_kw", title="Factory-Level Aggregated Power Demand (All 5 Machines)")
    st.plotly_chart(fig_agg, use_container_width=True)
    
    fig_all = px.line(df_all, x="timestep", y="power_kw", color="machine_id", title="Individual Machine Power Profiles")
    st.plotly_chart(fig_all, use_container_width=True)

with t5:
    st.subheader("Scientific Factory Policy Benchmark (Decoupled & Controlled)")
    st.caption("Evaluated on a controlled 5-machine factory benchmark (Max Degradation = 0.85, Reachable Failure Threshold).")
    
    pols = [("CORRECTIVE", False), ("PREVENTIVE", False), ("PREDICTIVE", False), ("PREDICTIVE", True)]
    b_res = []
    for p_name, p_dr in pols:
        sim = FactoryPolicySimulator(policy_type=p_name, enable_peak_shaving=p_dr)
        r = sim.run_policy_benchmark()
        b_res.append({
            "Policy": r["policy"],
            "Downtime (min)": r["downtime_min"],
            "Events": r["events"],
            "OEE (%)": r["oee_pct"],
            "Good Units": r["good_units"],
            "Energy (kWh)": r["total_energy_kwh"],
            "Peak (kW)": r["peak_demand_kw"],
            "Energy/Unit (Wh)": r["energy_per_unit_wh"],
            "Total Cost ($)": r["total_cost_usd"],
            "Carbon (kg)": r["carbon_kg"]
        })
    b_df = pd.DataFrame(b_res)
    st.dataframe(b_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Downtime (min)", "Total Cost ($)", "Carbon (kg)"], color="#d4edda"), use_container_width=True)
    
    c_a, c_b = st.columns(2)
    with c_a:
        fig_oee = px.bar(b_df, x="Policy", y="OEE (%)", color="Policy", title="Overall Equipment Effectiveness (OEE %)")
        st.plotly_chart(fig_oee, use_container_width=True)
    with c_b:
        fig_cost = px.bar(b_df, x="Policy", y="Total Cost ($)", color="Policy", title="Total Operational Cost ($ per Shift)")
        st.plotly_chart(fig_cost, use_container_width=True)

with t6:
    st.subheader("Calibrated Detector Ablation Study")
    ab_df = run_ablation_study(df_m3)
    st.dataframe(ab_df.style.highlight_max(subset=["Precision", "Recall", "F1-Score", "Early Lead Time (min)"], color="#d4edda").highlight_min(subset=["False Alarms/Hr"], color="#d4edda"), use_container_width=True)
    
    fig_f1 = px.bar(ab_df, x="Architecture Layer", y="F1-Score", color="Architecture Layer", title="F1-Score Across System Detector Layers")
    st.plotly_chart(fig_f1, use_container_width=True)
    