"""
PRIME-Factory Interactive Industrial Control & Decision Center v4.1 (Master Edition)
Features: Multi-Product Contexts, Physical Telemetry, XAI Decision Trace, Deterministic What-If,
Causal PdM Execution, Calibrated Ablation, and Experiment Audit Trail.
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
from simulation.faults import (
    generate_degradation_profile,
    generate_friction_profile,
    generate_electrical_profile,
    generate_switching_schedule,
    inject_sensor_noise_spikes
)
from simulation.state_machine import AssetStateMachine
from simulation.events import EventLog
from energy.eci import calculate_eci, get_context_expected_power
from energy.energy_model import calculate_total_energy_kwh, calculate_peak_demand_kw, calculate_financial_and_esg_impact
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence, estimate_rolling_rul
from control.decision_engine import DecisionEngine
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study

st.set_page_config(
    page_title="PRIME-Factory | Control & Decision Center v4.1",
    layout="wide",
    page_icon="🏭"
)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "manual_maintenance_triggered" not in st.session_state:
    st.session_state.manual_maintenance_triggered = False

if "guided_demo_step" not in st.session_state:
    st.session_state.guided_demo_step = 0

st.title("🏭 PRIME-Factory: Industrial Control & Decision Center v4.1")
st.caption("National Competition for AI and Robotics (RoboDam 2026) | Team MSA")

# ---------------------------------------------------------
# Sidebar: Control Center
# ---------------------------------------------------------
st.sidebar.header("🕹️ Plant Control Center")

sim_mode = st.sidebar.radio(
    "Operating Schedule Context:",
    options=["Fixed Product Regime", "Multi-Product Switching (A → B → C)"],
    index=0
)

if sim_mode == "Fixed Product Regime":
    selected_product = st.sidebar.selectbox("Active Recipe Context:", options=["Product_A", "Product_B", "Product_C"], index=1)
else:
    selected_product = "Dynamic (A → B → C)"

st.sidebar.subheader("Asset & Fault Configuration")
selected_machine = st.sidebar.selectbox(
    "Target Machine Asset:",
    options=list(config.MACHINES.keys()),
    index=2,
    format_func=lambda m: f"{m} — {config.MACHINES[m]['name']} ({config.MACHINES[m]['type']})"
)

fault_type = st.sidebar.selectbox(
    "Injected Fault Modality:",
    options=[
        "None (Healthy Baseline)",
        "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)",
        "Mechanical Friction (Power Surge ↑ + High ECI)",
        "Electrical Anomaly (Current Distortion + PF Drop)"
    ],
    index=1
)

inject_fault = (fault_type != "None (Healthy Baseline)")
fault_start = st.sidebar.slider("Fault Inception (Minute):", min_value=10, max_value=400, value=120)
max_deg = st.sidebar.slider("Degradation Severity (%):", min_value=10, max_value=85, value=75) / 100.0

st.sidebar.subheader("Robustness & Grid Response")
enable_chaos = st.sidebar.checkbox("Chaos Stress-Test (Sensor Noise Spikes)", value=False)
apply_dr = st.sidebar.checkbox("Enable Demand Response (Peak Shaving)", value=False)

st.sidebar.divider()
st.sidebar.subheader("Live Operational Override")
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🔧 Execute PdM", type="primary", use_container_width=True):
        st.session_state.manual_maintenance_triggered = True
with col_btn2:
    if st.button("🔄 Reset Line", use_container_width=True):
        st.session_state.manual_maintenance_triggered = False

time_scrubber = st.sidebar.slider("Playback Horizon (Minutes):", min_value=30, max_value=config.TOTAL_TIMESTEPS, value=config.TOTAL_TIMESTEPS)

# ---------------------------------------------------------
# Master Simulation Pipeline Execution
# ---------------------------------------------------------
@st.cache_data
def run_master_pipeline(mode, prod_key, target_m, f_type, fault_enabled, start_t, max_d, chaos_enabled, dr_enabled, manual_pdm):
    event_log = EventLog()
    event_log.add_event(0, "SYSTEM_START", "INFO", "ALL", "PRIME-Factory production line initialized in healthy baseline state.")

    if mode == "Fixed Product Regime":
        schedule = [prod_key] * config.TOTAL_TIMESTEPS
    else:
        schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)
        event_log.add_event(0, "RECIPE_SCHEDULED", "INFO", "ALL", "Dynamic Multi-Product Switching Recipe (A -> B -> C) activated.")

    # 1. Fault Profile Synthesis
    degradation_plan = None
    if fault_enabled:
        if "Bearing" in f_type:
            profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=start_t, max_degradation=max_d)
            event_log.add_event(start_t, "BEARING_DEGRADATION", "WARNING", target_m, f"Mechanical bearing wear initiated on {target_m}.")
        elif "Friction" in f_type:
            profile = generate_friction_profile(config.TOTAL_TIMESTEPS, start_time=start_t, max_friction=max_d)
            event_log.add_event(start_t, "MECHANICAL_FRICTION", "WARNING", target_m, f"Mechanical friction / lubrication breakdown initiated on {target_m}.")
        else:
            profile = generate_electrical_profile(config.TOTAL_TIMESTEPS, start_time=start_t, max_severity=max_d)
            event_log.add_event(start_t, "ELECTRICAL_ANOMALY", "WARNING", target_m, f"Stator winding / electrical insulation anomaly initiated on {target_m}.")
        degradation_plan = {target_m: profile}

    # 2. Synchronous Factory Simulation
    factory = PackagingFactory()
    df = factory.run_simulation(schedule, degradation_targets=degradation_plan, seed=config.RANDOM_SEED)

    if chaos_enabled:
        vib_vals = df[df["machine_id"] == target_m]["vibration_rms"].values
        df.loc[df["machine_id"] == target_m, "vibration_rms"] = inject_sensor_noise_spikes(vib_vals, spike_probability=0.03, noise_magnitude=2.5)
        event_log.add_event(10, "CHAOS_INJECTED", "WARNING", target_m, "Transient electromagnetic noise spikes injected into sensor telemetry.")

    # 3. AI Training on Isolated Clean Baseline
    factory.reset_factory()
    healthy_training_df = factory.run_simulation(schedule, seed=config.RANDOM_SEED)
    
    df["expected_p"] = df.apply(lambda r: get_context_expected_power(r["machine_id"], r["product"]), axis=1)
    df["eci"] = df.apply(lambda r: calculate_eci(r["power_kw"], r["machine_id"], r["product"]), axis=1)
    df["power_residual"] = df["power_kw"] - df["expected_p"]

    ai_model_raw = PRIMEIsolationForest(contamination=0.02, seed=config.RANDOM_SEED)
    ai_model_raw.fit(healthy_training_df)
    df["raw_ai_score"] = ai_model_raw.predict_anomaly_score(df)

    healthy_training_df["expected_p"] = healthy_training_df.apply(lambda r: get_context_expected_power(r["machine_id"], r["product"]), axis=1)
    healthy_training_df["power_residual"] = healthy_training_df["power_kw"] - healthy_training_df["expected_p"]

    from sklearn.ensemble import IsolationForest
    c_model = IsolationForest(n_estimators=100, contamination=0.02, random_state=config.RANDOM_SEED)
    c_model.fit(healthy_training_df[["power_residual", "vibration_rms", "temperature_c"]])

    test_context_feat = df[["power_residual", "vibration_rms", "temperature_c"]].copy()
    c_raw_scores = c_model.decision_function(test_context_feat)
    df["context_ai_score"] = np.round(1.0 / (1.0 + np.exp(c_raw_scores * 5.0)), 4)

    # 4. Target Machine Telemetry Processing & Decision Flow
    target_df = df[df["machine_id"] == target_m].copy()
    processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
    state_machine = AssetStateMachine(machine_id=target_m)

    hi_list, conf_list, pers_list, rul_val_list, rul_str_list, states_list = [], [], [], [], [], []
    alert_timestep = None
    maint_timestep = None

    for idx, row in target_df.iterrows():
        t = int(row["timestep"])
        p_info = processor.update(row["context_ai_score"], threshold=0.5)

        hi_res = calculate_health_index_and_evidence(
            anomaly_score=row["context_ai_score"],
            persistence_ratio=p_info["persistence_ratio"],
            eci=row["eci"],
            temp_c=row["temperature_c"],
            vib_rms=row["vibration_rms"]
        )
        current_hi = hi_res["health_index"]

        # Causal Operator PdM Execution Logic
        in_maint = False
        if manual_pdm and t >= (start_t + 50) and t < (start_t + 65):
            in_maint = True
            if t == (start_t + 50):
                maint_timestep = t
                event_log.add_event(t, "MAINTENANCE_EXECUTED", "INFO", target_m, "Operator executed 15-minute Planned Predictive Maintenance (PdM).")

        eff_deg = row["degradation"] if not (manual_pdm and t >= start_t + 65) else 0.0
        eff_hi = current_hi if not (manual_pdm and t >= start_t + 65) else 96.0

        st_name = state_machine.update_state(
            degradation=eff_deg,
            health_index=eff_hi,
            is_confirmed_anomaly=bool(p_info["is_confirmed_anomaly"]),
            in_maintenance=in_maint
        )
        states_list.append(st_name)

        hi_list.append(eff_hi)
        pers_list.append(p_info["persistence_ratio"])
        conf_list.append(p_info["is_confirmed_anomaly"])

        r_val, r_str = estimate_rolling_rul(hi_list, current_state=st_name, current_t=t, window_size=15)
        rul_val_list.append(r_val if r_val is not None else -1)
        rul_str_list.append(r_str)

        if st_name == config.STATE_PREDICTIVE_ALERT and alert_timestep is None:
            alert_timestep = t
            event_log.add_event(t, "PREDICTIVE_ALERT", "PREDICTIVE", target_m, f"Health Index dropped to {eff_hi:.1f}. Predictive alert triggered.")

    target_df["health_index"] = hi_list
    target_df["persistence_ratio"] = pers_list
    target_df["confirmed_anomaly"] = conf_list
    target_df["rul_minutes"] = rul_val_list
    target_df["state"] = states_list

    latest_decision = DecisionEngine.evaluate_decision(
        machine_id=target_m,
        current_state=states_list[-1],
        health_index=hi_list[-1],
        rul_minutes=rul_val_list[-1],
        is_confirmed_anomaly=conf_list[-1],
        eci=target_df["eci"].iloc[-1],
        penalty_contributions=hi_res["penalty_contributions"],
        product_key=schedule[-1]
    )

    return df, target_df, event_log, latest_decision, rul_str_list[-1], alert_timestep, maint_timestep, states_list[-1]

df_all, df_target, event_log, decision, latest_rul_str, alert_t, maint_t, display_state = run_master_pipeline(
    sim_mode, selected_product, selected_machine, fault_type, inject_fault, fault_start, max_deg, enable_chaos, apply_dr, st.session_state.manual_maintenance_triggered
)

df_target_view = df_target[df_target["timestep"] <= time_scrubber].copy()
df_all_view = df_all[df_all["timestep"] <= time_scrubber].copy()

# ---------------------------------------------------------
# Header: Live Factory KPIs
# ---------------------------------------------------------
total_energy = calculate_total_energy_kwh(df_all_view)
peak_kw = calculate_peak_demand_kw(df_all_view)
latest_hi = df_target_view["health_index"].iloc[-1]
badge = AssetStateMachine.get_state_badge(display_state)

effective_downtime = 15.0 if st.session_state.manual_maintenance_triggered else (75.0 if display_state == config.STATE_FAILED else 0.0)
fin_metrics = calculate_financial_and_esg_impact(
    total_energy_kwh=total_energy,
    downtime_minutes=effective_downtime,
    good_units=int(16200 * (time_scrubber / config.TOTAL_TIMESTEPS)),
    avg_pf=float(df_target_view["pf"].mean())
)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("⚡ Factory Total Energy", f"{total_energy:.1f} kWh")
kpi2.metric("📈 Factory Peak Demand", f"{peak_kw:.1f} kW")
kpi3.metric(f"🛡️ {selected_machine} Health Index", f"{latest_hi:.1f} / 100", delta=f"{latest_hi - 100.0:.1f}", delta_color="normal")
kpi4.metric("⏳ Estimated RUL", latest_rul_str)
kpi5.metric("💰 Shift Operational Cost", f"${fin_metrics['total_operational_cost_usd']:.1f}", delta=f"{fin_metrics['carbon_kg']:.1f} kg CO2", delta_color="inverse")

# Alert Banner Routing (Corrected Colors)
if display_state in [config.STATE_CRITICAL, config.STATE_FAILED]:
    st.error(f"🚨 **{decision['title']}** | **Machine:** {selected_machine} ({config.MACHINES[selected_machine]['name']}) | **Action:** {decision['recommended_action']}")
elif display_state in [config.STATE_PREDICTIVE_ALERT, config.STATE_WARNING]:
    st.warning(f"⚠️ **{decision['title']}** | **Machine:** {selected_machine} ({config.MACHINES[selected_machine]['name']}) | **Action:** {decision['recommended_action']}")
elif display_state in [config.STATE_MAINTENANCE, config.STATE_RECOVERY]:
    st.info(f"🔄 **{badge['label']}** | **Machine:** {selected_machine} | **Action:** {badge['action']}")
else:
    st.success(f"✅ **{badge['label']}** | **Action:** {badge['action']}")

st.divider()

# ---------------------------------------------------------
# Operational Tabs
# ---------------------------------------------------------
t_live, t_dec, t_whatif, t_events, t_bench, t_ablation, t_report = st.tabs([
    "📈 Live Condition & Telemetry",
    "🔍 Decision Trace (XAI Card)",
    "⚖️ What-If Live Comparison",
    "📋 Chronological Event Log",
    "📊 Scientific Factory Benchmark",
    "🧪 Calibrated Ablation Study",
    "📑 Experiment Report & Evidence"
])

# Tab 1: Live Condition
with t_live:
    fig_cond = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=(f"Physical Telemetry ({selected_machine} — {config.MACHINES[selected_machine]['name']})", "Composite Health Index & Critical Operational Thresholds")
    )
    if config.MACHINES[selected_machine]["has_vibration"]:
        fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["vibration_rms"], name="Vibration (g RMS)", line=dict(color="#1f77b4")), row=1, col=1)
    fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["temperature_c"], name="Temperature (°C)", line=dict(color="#ff7f0e")), row=1, col=1)
    fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["power_kw"], name="Power (kW)", line=dict(color="#2ca02c")), row=1, col=1)
    fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["health_index"], name="Health Index (HI)", line=dict(color="#00cc96", width=2.5)), row=2, col=1)
    
    fig_cond.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Monitor Threshold (70)", row=2, col=1)
    fig_cond.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Intervention Threshold (50)", row=2, col=1)

    if inject_fault and fault_start <= time_scrubber:
        fig_cond.add_vline(x=fault_start, line_dash="dot", line_color="#ffbb00", annotation_text="Fault Inception", row="all")
    if alert_t is not None and alert_t <= time_scrubber:
        fig_cond.add_vline(x=alert_t, line_dash="dash", line_color="#fd7e14", annotation_text="Predictive Alert", row="all")
    if maint_t is not None and maint_t <= time_scrubber:
        fig_cond.add_vline(x=maint_t, line_dash="solid", line_color="#20c997", annotation_text="PdM Executed", row="all")

    fig_cond.update_layout(height=520, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    st.plotly_chart(fig_cond, use_container_width=True)

# Tab 2: Decision Trace (XAI Card)
with t_dec:
    st.subheader(f"🧠 Explainable AI & Decision Attribution for {selected_machine}")
    cx1, cx2 = st.columns([1, 1])
    with cx1:
        st.info(f"""
        **Causal Evidence Breakdown for Decision:**
        * **Target Asset:** `{selected_machine} — {config.MACHINES[selected_machine]['name']}`
        * **Active Operational State:** `{decision['current_state']}`
        * **Current Health Index:** `{decision['health_index']:.1f} / 100`
        * **Estimated Urgency:** `{decision['urgency']}`
        * **Persistence Confirmation:** `{decision['operating_context']['persistence_confirmed']}`
        * **Energy Deviation (ECI):** `{decision['operating_context']['eci_deviation_pct']}`
        * **Recommended Action:** `{decision['recommended_action']}`
        * **Consequence of Inaction:** `{decision['consequence_of_inaction']}`
        """)
    with cx2:
        attr_df = pd.DataFrame({
            "Evidence Modality": list(decision["penalty_contributions"].keys()),
            "Penalty Contribution (%)": list(decision["penalty_contributions"].values())
        })
        fig_attr = px.bar(
            attr_df, x="Evidence Modality", y="Penalty Contribution (%)", color="Evidence Modality",
            title="Relative Sensor & AI Modality Contribution to HI Penalty", text_auto=".1f"
        )
        st.plotly_chart(fig_attr, use_container_width=True)

# Tab 3: What-If Live Comparison
with t_whatif:
    st.subheader("⚖️ Dual-Branch What-If Analysis (Intervention vs No Intervention)")
    st.caption("Simulating identical shift horizon and random seed under both operational paths.")
    
    whatif_res = FactoryPolicySimulator.run_what_if_analysis(
        product_schedule=["Product_B"] * config.TOTAL_TIMESTEPS,
        fault_start_t=fault_start,
        max_deg=max_deg,
        seed=config.RANDOM_SEED
    )

    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    d_saved = whatif_res['savings']['downtime_saved_min']
    c_saved = whatif_res['savings']['cost_saved_usd']
    oee_gain = whatif_res['savings']['oee_gain_pct']
    co2_saved = whatif_res['savings']['carbon_saved_kg']

    col_w1.metric("Downtime Prevented", f"{d_saved:.1f} min", delta="Reliability Protection", delta_color="normal")
    col_w2.metric("Financial Savings", f"${c_saved:.2f}", delta="Cost Protection", delta_color="normal" if c_saved >= 0 else "inverse")
    col_w3.metric("OEE Efficiency Gain", f"+{oee_gain:.2f}%", delta="Productivity", delta_color="normal")
    col_w4.metric("Carbon Avoided", f"{co2_saved:.2f} kg CO2", delta="Sustainability", delta_color="normal")

    wi_df = pd.DataFrame([
        {
            "Operational Path": "🔴 No Intervention (Corrective Breakdown)",
            "Downtime (min)": whatif_res["no_intervention"]["downtime_min"],
            "OEE (%)": whatif_res["no_intervention"]["oee_pct"],
            "Good Units": whatif_res["no_intervention"]["good_units"],
            "Total Cost ($)": whatif_res["no_intervention"]["total_operational_cost_usd"],
            "Carbon (kg CO2)": whatif_res["no_intervention"]["carbon_kg"]
        },
        {
            "Operational Path": "🟢 Predictive Intervention (PRIME Action)",
            "Downtime (min)": whatif_res["predictive"]["downtime_min"],
            "OEE (%)": whatif_res["predictive"]["oee_pct"],
            "Good Units": whatif_res["predictive"]["good_units"],
            "Total Cost ($)": whatif_res["predictive"]["total_operational_cost_usd"],
            "Carbon (kg CO2)": whatif_res["predictive"]["carbon_kg"]
        }
    ])
    st.dataframe(wi_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Total Cost ($)", "Downtime (min)"], color="#d4edda"), use_container_width=True)

# Tab 4: Chronological Event Log & Export
with t_events:
    st.subheader("📋 Chronological Event Log & Audit Trail")
    ev_df = event_log.get_events_as_dataframe()
    st.dataframe(ev_df, use_container_width=True)
    st.divider()
    st.subheader("📦 Export Reproducibility Package")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📥 Download Event Audit Trail (CSV)",
            data=ev_df.to_csv(index=False).encode('utf-8'),
            file_name="prime_factory_events_log.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_exp2:
        st.download_button(
            label="📥 Download Asset Telemetry Stream (CSV)",
            data=df_target.to_csv(index=False).encode('utf-8'),
            file_name=f"prime_factory_{selected_machine}_telemetry.csv",
            mime="text/csv",
            use_container_width=True
        )

# Tab 5: Scientific Factory Benchmark
with t_bench:
    st.subheader("📊 Scientific Factory Policy Benchmark (Decoupled & Controlled)")
    pols = [("CORRECTIVE", False), ("PREVENTIVE", False), ("PREDICTIVE", False), ("PREDICTIVE", True)]
    b_res = []
    for p_name, p_dr in pols:
        sim = FactoryPolicySimulator(policy_type=p_name, enable_peak_shaving=p_dr, seed=config.RANDOM_SEED)
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
            "Total Cost ($)": r["total_operational_cost_usd"],
            "Carbon (kg)": r["carbon_kg"]
        })
    b_df = pd.DataFrame(b_res)
    st.dataframe(b_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Total Cost ($)", "Peak (kW)"], color="#d4edda"), use_container_width=True)

# Tab 6: Calibrated Ablation Study
with t_ablation:
    st.subheader("🧪 Calibrated Pure Detector Ablation Study")
    ab_df = run_ablation_study(df_target)
    st.dataframe(ab_df.style.highlight_max(subset=["Precision", "Recall", "F1-Score", "Early Lead Time (min)"], color="#d4edda").highlight_min(subset=["False Alarms/Hr"], color="#d4edda"), use_container_width=True)
    fig_f1 = px.bar(ab_df, x="Architecture Layer", y="F1-Score", color="Architecture Layer", title="F1-Score Progression Across Detector Architecture Layers", text_auto=".3f")
    st.plotly_chart(fig_f1, use_container_width=True)

# Tab 7: Experiment Report & Evidence Export
with t_report:
    st.subheader("📑 Formal Experiment & Evidence Summary (v4.1)")
    rep_col1, rep_col2 = st.columns(2)
    with rep_col1:
        st.write("#### Experiment Parameters & Metadata")
        st.json({
            "Scenario_ID": "EXP-2026-M3-BEARING",
            "Target_Machine": selected_machine,
            "Product_Regime": sim_mode,
            "Fault_Modality": fault_type,
            "Fault_Onset_Minute": fault_start if inject_fault else "N/A",
            "Max_Degradation_Severity": f"{max_deg*100:.1f}%" if inject_fault else "0.0%",
            "Random_Seed": config.RANDOM_SEED,
            "Software_Version": "PRIME-Factory v4.1 Master Edition"
        })
    with rep_col2:
        st.write("#### Achieved Operational Outcomes")
        st.json({
            "First_Predictive_Alert_Minute": alert_t if alert_t else "None",
            "Maintenance_Execution_Minute": maint_t if maint_t else "None",
            "Line_Availability_Pct": f"{((config.TOTAL_TIMESTEPS - effective_downtime)/config.TOTAL_TIMESTEPS)*100:.2f}%",
            "Total_Operational_Cost": f"${fin_metrics['total_operational_cost_usd']:.2f}",
            "Energy_Cost": f"${fin_metrics['energy_cost_usd']:.2f}",
            "Downtime_Cost": f"${fin_metrics['downtime_cost_usd']:.2f}",
            "Power_Factor_Penalty": f"${fin_metrics['pf_penalty_usd']:.2f}",
            "Carbon_Emissions": f"{fin_metrics['carbon_kg']:.2f} kg CO2"
        })