"""
PRIME-Factory Interactive Industrial Control & Decision Center v6.0 (Master Edition)
Features: Multi-Product Contexts, Physical Telemetry, XAI Decision Trace, Deterministic What-If,
Causal PdM Execution Lifecycle, Industrial Resilience, and 3-Minute Judge Mode Wizard (Section 13, 20 & 21).
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
import json
from datetime import datetime

import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from simulation.state_machine import AssetStateMachine
from control.decision_engine import DecisionEngine
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study

# Import EvidenceTracker for display
from core.evidence import EvidenceTracker

def _get(obj, key, default=0.0):
    """Safely extracts value from either a dataclass object or a dictionary."""
    if hasattr(obj, key):
        return getattr(obj, key)
    elif isinstance(obj, dict):
        return obj.get(key, default)
    return default

def safe_column(df, col, default=0):
    """Safely get a column from DataFrame, return default Series if missing."""
    if col in df.columns:
        return df[col]
    return pd.Series(default, index=df.index)

st.set_page_config(page_title="PRIME-Factory | Control & Decision Center v6.0", layout="wide", page_icon="🏭")

# Session State for Interactive Controls & Judge Mode Flow
if "manual_pdm_timestep" not in st.session_state:
    st.session_state.manual_pdm_timestep = None
if "judge_mode_step" not in st.session_state:
    st.session_state.judge_mode_step = 0

st.title("🏭 PRIME-Factory: Industrial Control & Decision Center v6.0")
st.caption("National Competition for AI and Robotics (RoboDam 2026) | Team MSA")

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.header("🕹️ Plant Control Center")

# Automated Judge Mode Pitch Wizard (Section 21)
st.sidebar.subheader("🏆 Judge Mode (3-Minute Flow)")
col_j1, col_j2 = st.sidebar.columns(2)
with col_j1:
    if st.button("▶️ Next Demo Step", type="primary", use_container_width=True):
        st.session_state.judge_mode_step = (st.session_state.judge_mode_step + 1) % 4
with col_j2:
    if st.button("⏮️ Reset Pitch", use_container_width=True):
        st.session_state.judge_mode_step = 0
        st.session_state.manual_pdm_timestep = None

# Context Setup based on Judge Step or Manual Controls
j_step = st.session_state.judge_mode_step
if j_step == 1:
    st.sidebar.info("📌 **Step 1 (0:00-0:20):** Healthy Multi-Product Baseline (A→B→C).")
    sim_mode = "Multi-Product Switching (A → B → C)"
    fault_type = "None (Healthy Baseline)"
    fault_start = 120
    max_deg = 0.0
elif j_step == 2:
    st.sidebar.warning("📌 **Step 2 (0:20-1:35):** M3 Bearing Wear Onset & XAI Decision Trace.")
    sim_mode = "Fixed Product Regime"
    selected_product = "Product_B"
    fault_type = "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)"
    fault_start = 120
    max_deg = 0.85
elif j_step == 3:
    st.sidebar.success("📌 **Step 3 (1:35-3:00):** Causal PdM Intervention, Recovery & What-If ROI.")
    sim_mode = "Fixed Product Regime"
    selected_product = "Product_B"
    fault_type = "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)"
    fault_start = 120
    max_deg = 0.85
    st.session_state.manual_pdm_timestep = 175
else:
    sim_mode = st.sidebar.radio("Operating Schedule Context:", ["Fixed Product Regime", "Multi-Product Switching (A → B → C)"], index=0)
    if sim_mode == "Fixed Product Regime":
        selected_product = st.sidebar.selectbox("Active Recipe Context:", ["Product_A", "Product_B", "Product_C"], index=1)
    fault_type = st.sidebar.selectbox("Injected Fault Modality:", [
        "None (Healthy Baseline)",
        "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)",
        "Mechanical Friction (Power Surge ↑ + High ECI)",
        "Electrical Anomaly (Current Distortion + PF Drop)"
    ], index=1)
    fault_start = st.sidebar.slider("Fault Inception (Minute):", 10, 400, 120)
    max_deg = st.sidebar.slider("Degradation Severity (%):", 10, 85, 75) / 100.0

selected_machine = st.sidebar.selectbox("Target Machine Asset:", list(config.MACHINES.keys()), index=2, format_func=lambda m: f"{m} — {config.MACHINES[m]['name']}")
enable_chaos = st.sidebar.checkbox("Chaos Stress-Test (Sensor Noise)", value=False)
apply_dr = st.sidebar.checkbox("Enable Demand Response (Peak Shaving)", value=False)

st.sidebar.divider()
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🔧 Execute PdM", type="primary", use_container_width=True):
        st.session_state.manual_pdm_timestep = fault_start + 55
with col_btn2:
    if st.button("🔄 Reset Line", use_container_width=True):
        st.session_state.manual_pdm_timestep = None
        st.session_state.judge_mode_step = 0

time_scrubber = st.sidebar.slider("Playback Horizon (Minutes):", 30, config.TOTAL_TIMESTEPS, config.TOTAL_TIMESTEPS)

# ---------------------------------------------------------
# Execute Unified Engine (100% Causal Pipeline)
# ---------------------------------------------------------
if sim_mode == "Fixed Product Regime":
    schedule = [selected_product] * config.TOTAL_TIMESTEPS
else:
    from simulation.faults import generate_switching_schedule
    schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)

scenario_active = ScenarioConfig(
    scenario_id="LIVE_DASHBOARD_RUN",
    seed=config.RANDOM_SEED,
    product_schedule=schedule,
    fault_machine=selected_machine,
    fault_type=fault_type,
    fault_start=fault_start,
    max_degradation=max_deg if fault_type != "None (Healthy Baseline)" else 0.0,
    enable_chaos=enable_chaos,
    enable_peak_shaving=apply_dr,
    manual_pdm_timestep=st.session_state.manual_pdm_timestep
)

# Run Unified Engine
sim_result = UnifiedSimulationEngine.run(scenario_active)
df_all = sim_result.telemetry_df
df_target = df_all[df_all["machine_id"] == selected_machine].copy()

# Make sure we have data
if df_target.empty:
    st.error(f"No telemetry data found for machine {selected_machine}. Please check the simulation.")
    st.stop()

df_target_view = df_target[df_target["timestep"] <= time_scrubber].copy()
latest_row = df_target_view.iloc[-1]
display_state = latest_row["state"]
latest_hi = latest_row["health_index"]
badge = AssetStateMachine.get_state_badge(display_state)

# Decision Engine Trace - with safe value extraction
rul_minutes = latest_row.get("rul_minutes", -1)
if pd.isna(rul_minutes) or rul_minutes < 0:
    rul_minutes = -1

latest_decision = DecisionEngine.evaluate_decision(
    machine_id=selected_machine,
    current_state=display_state,
    health_index=latest_hi,
    rul_minutes=int(rul_minutes) if rul_minutes > 0 else -1,
    is_confirmed_anomaly=bool(latest_row.get("confirmed_anomaly", 0)),
    eci=latest_row.get("eci", 0.0),
    penalty_contributions=latest_row.get("penalty_contributions", {}),
    product_key=schedule[min(time_scrubber-1, len(schedule)-1)]
)

# ---------------------------------------------------------
# Header KPIs (Derived Directly from Unified Result)
# ---------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("⚡ Factory Energy", f"{_get(sim_result, 'total_energy_kwh'):.1f} kWh", delta=f"{_get(sim_result, 'energy_per_good_unit_wh'):.2f} Wh/unit")
kpi2.metric("📈 Peak Demand", f"{_get(sim_result, 'peak_demand_kw'):.1f} kW", delta="Demand Response" if apply_dr else "Standard")
kpi3.metric(f"🛡️ {selected_machine} Health Index", f"{latest_hi:.1f} / 100", delta=f"{latest_hi - 100.0:.1f}", delta_color="normal")
kpi4.metric("⏳ Trend-Based RUL", str(latest_row.get("rul_str", "Stable")), delta=f"Conf: {latest_row.get('rul_confidence', 1.0)*100:.0f}%")
kpi5.metric("💰 Total Operational Cost", f"${_get(sim_result, 'total_operational_cost_usd'):.2f}", delta=f"{_get(sim_result, 'carbon_kg'):.1f} kg CO2", delta_color="inverse")

# Alert Banner
if display_state in [config.STATE_CRITICAL, config.STATE_FAILED]:
    st.error(f"🚨 **{latest_decision['title']}** | **Machine:** {selected_machine} | **Action:** {latest_decision['recommended_action']}")
elif display_state in [config.STATE_PREDICTIVE_ALERT, config.STATE_WARNING]:
    st.warning(f"⚠️ **{latest_decision['title']}** | **Machine:** {selected_machine} | **Action:** {latest_decision['recommended_action']}")
elif display_state in [config.STATE_MAINTENANCE, config.STATE_RECOVERY]:
    st.info(f"🔄 **{badge['label']}** | **Machine:** {selected_machine} | **Action:** {badge['action']}")
else:
    st.success(f"✅ **{badge['label']}** | **Action:** {badge['action']}")

st.divider()

# ---------------------------------------------------------
# Operational Tabs
# ---------------------------------------------------------
t_live, t_dec, t_evidence, t_whatif, t_resilience, t_events, t_bench, t_ablation, t_report = st.tabs([
    "📈 Live Telemetry",
    "🔍 Decision Trace (XAI Card)",
    "🔗 Evidence Chain",
    "⚖️ What-If Live Comparison",
    "🛡️ Industrial Resilience",
    "📋 Audit Event Log",
    "📊 Scientific Benchmark",
    "🧪 Calibrated Ablation",
    "📑 Experiment Report"
])

with t_live:
    fig_cond = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=(f"Physical Telemetry ({selected_machine})", "Composite Health Index & Thresholds"))
    
    # Use safe_column to avoid KeyError
    if "vibration_rms" in df_target_view.columns and config.MACHINES[selected_machine]["has_vibration"]:
        fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["vibration_rms"], name="Vibration (g RMS)", line=dict(color="#1f77b4")), row=1, col=1)
    
    if "temperature_c" in df_target_view.columns:
        fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["temperature_c"], name="Temperature (°C)", line=dict(color="#ff7f0e")), row=1, col=1)
    
    if "active_power_kw" in df_target_view.columns:
        fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["active_power_kw"], name="Power (kW)", line=dict(color="#2ca02c")), row=1, col=1)
    
    if "health_index" in df_target_view.columns:
        fig_cond.add_trace(go.Scatter(x=df_target_view["timestep"], y=df_target_view["health_index"], name="Health Index (HI)", line=dict(color="#00cc96", width=2.5)), row=2, col=1)
        fig_cond.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Monitor (70)", row=2, col=1)
        fig_cond.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Intervention Threshold (50)", row=2, col=1)
    
    fig_cond.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    st.plotly_chart(fig_cond, use_container_width=True)

with t_dec:
    st.subheader(f"🧠 Explainable AI & Decision Attribution for {selected_machine}")
    cx1, cx2 = st.columns([1, 1])
    with cx1:
        st.info(f"""
        **Causal Decision Breakdown:**
        * **Target Machine:** `{selected_machine} — {config.MACHINES[selected_machine]['name']}`
        * **Operational State:** `{latest_decision['current_state']}`
        * **Health Index:** `{latest_decision['health_index']:.1f} / 100`
        * **Decision Urgency:** `{latest_decision['urgency']}`
        * **Persistence Confirmation:** `{latest_decision['operating_context']['persistence_confirmed']}`
        * **Context-Aware ECI:** `{latest_decision['operating_context']['eci_deviation_pct']}`
        * **Recommended Action:** `{latest_decision['recommended_action']}`
        * **Consequence of Inaction:** `{latest_decision['consequence_of_inaction']}`
        """)
    with cx2:
        attr_dict = latest_decision.get("penalty_contributions", {})
        if attr_dict:
            attr_df = pd.DataFrame({
                "Evidence Modality": list(attr_dict.keys()),
                "Penalty Contribution (%)": list(attr_dict.values())
            })
            if not attr_df.empty:
                st.plotly_chart(px.bar(attr_df, x="Evidence Modality", y="Penalty Contribution (%)", color="Evidence Modality", title="Sensor & Model Contribution to HI Penalty", text_auto=".1f"), use_container_width=True)

with t_evidence:
    st.subheader(f"🔗 Complete Evidence Chain for {selected_machine}")
    st.caption("Full causal trace: SENSE → CONTEXT → DETECT → CONFIRM → HEALTH → RUL → DECIDE → ACTION → OUTCOME")
    
    evidence_tracker = getattr(sim_result, 'evidence_tracker', None)
    
    if evidence_tracker and hasattr(evidence_tracker, 'traces'):
        machine_traces = evidence_tracker.get_traces_by_machine(selected_machine)
        
        if machine_traces:
            latest_trace = machine_traces[-1]
            
            col_meta1, col_meta2, col_meta3 = st.columns(3)
            col_meta1.metric("Trace ID", latest_trace.trace_id)
            col_meta2.metric("Start Time", f"t={latest_trace.start_timestamp} min")
            col_meta3.metric("Status", latest_trace.final_outcome if latest_trace.final_outcome else "In Progress")
            
            st.divider()
            st.write("### 📜 Evidence Chain Timeline")
            
            step_icons = {
                "SENSE": "📡", "CONTEXT": "📋", "DETECT": "⚠️",
                "CONFIRM": "✅", "HEALTH": "💚", "RUL": "⏳",
                "DECIDE": "🎯", "ACTION": "🔧", "OUTCOME": "📊"
            }
            
            for i, step in enumerate(latest_trace.steps):
                step_type = step.step_type
                icon = step_icons.get(step_type, "📌")
                with st.expander(f"{icon} **Step {i+1}: {step_type}** — {step.description[:60]}...", expanded=(i < 3)):
                    col_step1, col_step2 = st.columns([2, 1])
                    with col_step1:
                        st.write(f"**Description:** {step.description}")
                        st.write(f"**Timestamp:** t={step.timestamp} min")
                    with col_step2:
                        st.write(f"**Data:**")
                        st.json(step.data)
            
            st.divider()
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                trace_json = json.dumps(latest_trace.to_dict(), indent=2)
                st.download_button("📥 Export Trace as JSON", trace_json, f"evidence_trace_{latest_trace.trace_id}.json", "application/json")
            with col_exp2:
                df_trace = pd.DataFrame([{"Step": s.step_type, "Timestamp": s.timestamp, "Description": s.description, **s.data} for s in latest_trace.steps])
                st.download_button("📥 Export Trace as CSV", df_trace.to_csv(index=False).encode('utf-8'), f"evidence_trace_{latest_trace.trace_id}.csv", "text/csv")
        else:
            st.info(f"No evidence traces found for machine {selected_machine}.")
    else:
        st.warning("Evidence tracker not available.")

with t_whatif:
    st.subheader("⚖️ Dual-Branch What-If Analysis (Intervention vs No Intervention)")
    whatif_res = FactoryPolicySimulator.run_what_if_analysis(
        product_schedule=["Product_B"] * config.TOTAL_TIMESTEPS,
        fault_start_t=fault_start,
        max_deg=max_deg,
        seed=config.RANDOM_SEED
    )
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    savings = whatif_res.get("savings", {})
    col_w1.metric("Downtime Prevented", f"{savings.get('downtime_saved_min', 0.0)} min", delta="Reliability")
    col_w2.metric("Cost Savings", f"${savings.get('cost_saved_usd', 0.0):.2f}", delta="Financial Protection")
    col_w3.metric("OEE Gain", f"+{savings.get('oee_gain_pct', 0.0):.2f}%", delta="Productivity")
    col_w4.metric("Carbon Avoided", f"{savings.get('carbon_saved_kg', 0.0):.2f} kg CO2", delta="Sustainability")
    
    no_int = whatif_res["no_intervention"]
    pred = whatif_res["predictive"]
    
    wi_df = pd.DataFrame([
        {
            "Path": "🔴 No Intervention (Corrective Breakdown)",
            "Downtime (min)": _get(no_int, "downtime_min"),
            "OEE (%)": _get(no_int, "oee_pct"),
            "Good Units": _get(no_int, "good_units"),
            "Total Cost ($)": _get(no_int, "total_operational_cost_usd"),
            "Carbon (kg CO2)": _get(no_int, "carbon_kg")
        },
        {
            "Path": "🟢 Predictive Intervention (PRIME Action)",
            "Downtime (min)": _get(pred, "downtime_min"),
            "OEE (%)": _get(pred, "oee_pct"),
            "Good Units": _get(pred, "good_units"),
            "Total Cost ($)": _get(pred, "total_operational_cost_usd"),
            "Carbon (kg CO2)": _get(pred, "carbon_kg")
        }
    ])
    st.dataframe(wi_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Total Cost ($)", "Downtime (min)"], color="#d4edda"), use_container_width=True)

with t_resilience:
    st.subheader("🛡️ Industrial Resilience & Recovery Evaluation (Section 15)")
    r_metrics = _get(sim_result, "resilience", None)
    r_col1, r_col2, r_col3 = st.columns(3)
    r_col1.metric("⏱️ Recovery Duration", f"{_get(r_metrics, 'recovery_time_min', 15.0):.1f} min", delta="Post-repair check")
    r_col2.metric("📦 Production Loss", f"{_get(r_metrics, 'production_loss_units', 0)} units", delta="Scrap + downtime")
    rec_ok = _get(r_metrics, 'recovery_success', True)
    r_col3.metric("✅ Recovery Status", "SUCCESS (Stable)" if rec_ok else "PENDING", delta="Self-stabilized")

with t_events:
    st.subheader("📋 Chronological Audit Event Log (Section 14)")
    events_list = _get(sim_result, "events", [])
    ev_df = pd.DataFrame([{
        "Timestep (min)": _get(e, "timestep"),
        "Severity": _get(e, "severity"),
        "Machine": _get(e, "machine_id"),
        "Event Type": _get(e, "event_type"),
        "Message": _get(e, "message")
    } for e in events_list])
    st.dataframe(ev_df, use_container_width=True)
    st.download_button("📥 Download Audit Trail (CSV)", ev_df.to_csv(index=False).encode('utf-8'), "prime_factory_events.csv", "text/csv")

with t_bench:
    st.subheader("📊 Scientific Factory Policy Benchmark (Decoupled & Controlled)")
    pols = [("CORRECTIVE", False), ("PREVENTIVE", False), ("PREDICTIVE", False), ("PREDICTIVE", True)]
    b_res = []
    for p_name, p_dr in pols:
        sim = FactoryPolicySimulator(policy_type=p_name, enable_peak_shaving=p_dr, seed=config.RANDOM_SEED)
        r = sim.run_policy_benchmark()
        b_res.append({
            "Policy": p_name if not p_dr else "PREDICTIVE + PEAK SHAVING",
            "Downtime (min)": _get(r, "downtime_min"),
            "Events": _get(r, "maintenance_events"),
            "OEE (%)": _get(r, "oee_pct"),
            "Good Units": _get(r, "good_units"),
            "Energy (kWh)": _get(r, "total_energy_kwh"),
            "Peak (kW)": _get(r, "peak_demand_kw"),
            "Energy/Unit (Wh)": _get(r, "energy_per_good_unit_wh"),
            "Total Cost ($)": _get(r, "total_operational_cost_usd"),
            "Carbon (kg CO2)": _get(r, "carbon_kg")
        })
    st.dataframe(pd.DataFrame(b_res).style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Total Cost ($)", "Peak (kW)"], color="#d4edda"), use_container_width=True)

with t_ablation:
    st.subheader("🧪 Calibrated Pure Detector Ablation Study (Layers A–E)")
    
    # FIXED: Run ablation study only if we have enough data
    # Check if df_target has the required columns, or use the full df_all
    ablation_df = df_target.copy()
    
    # Ensure required columns exist for ablation study
    required_cols = ['degradation', 'timestep']
    missing_cols = [col for col in required_cols if col not in ablation_df.columns]
    
    if missing_cols:
        st.warning(f"Missing required columns for ablation study: {missing_cols}. Using fallback data.")
        # Create fallback data
        ablation_df['degradation'] = 0.0
        ablation_df['timestep'] = range(len(ablation_df))
    
    try:
        ab_df = run_ablation_study(ablation_df)
        st.dataframe(ab_df.style.highlight_max(subset=["Precision", "Recall", "F1-Score"], color="#d4edda").highlight_min(subset=["False Alarms/Hr"], color="#d4edda"), use_container_width=True)
        st.plotly_chart(px.bar(ab_df, x="Architecture Layer", y="F1-Score", color="Architecture Layer", title="F1-Score Across Detector Layers", text_auto=".3f"), use_container_width=True)
    except Exception as e:
        st.error(f"Error running ablation study: {e}")
        st.info("Ablation study requires telemetry data with degradation, vibration, temperature, and ECI columns.")

with t_report:
    st.subheader("📑 Formal Auto-Generated Experiment Report (Section 19 & 22)")
    rep1, rep2 = st.columns(2)
    with rep1:
        st.write("#### Experiment Metadata & Configuration")
        st.json({
            "Scenario_ID": scenario_active.scenario_id,
            "Target_Asset": scenario_active.fault_machine,
            "Fault_Type": scenario_active.fault_type,
            "Inception_Timestep": scenario_active.fault_start,
            "Max_Degradation": f"{scenario_active.max_degradation*100:.1f}%",
            "Random_Seed": scenario_active.seed,
            "Software_Version": "PRIME-Factory v6.0 Master Candidate"
        })
    with rep2:
        st.write("#### Quantified Production & ESG Outcomes")
        st.json({
            "Availability_OEE": f"{_get(sim_result, 'availability_pct')}%",
            "Performance_OEE": f"{_get(sim_result, 'performance_pct')}%",
            "Quality_Yield": f"{_get(sim_result, 'quality_pct')}%",
            "Overall_OEE": f"{_get(sim_result, 'oee_pct')}%",
            "Energy_Cost": f"${_get(sim_result, 'energy_cost_usd'):.2f}",
            "Downtime_Cost": f"${_get(sim_result, 'downtime_cost_usd'):.2f}",
            "PF_Penalty": f"${_get(sim_result, 'pf_penalty_usd'):.2f}",
            "Total_Operational_Cost": f"${_get(sim_result, 'total_operational_cost_usd'):.2f}",
            "Carbon_Emissions": f"{_get(sim_result, 'carbon_kg'):.2f} kg CO2"
        })