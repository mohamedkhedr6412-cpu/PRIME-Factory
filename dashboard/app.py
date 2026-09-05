"""
PRIME-Factory Interactive Industrial Control & Decision Center v6.2 (Ultra-Fast)
Features: Multi-Product Contexts, Physical Telemetry, XAI Decision Trace, Deterministic What-If,
Causal PdM Execution Lifecycle, Industrial Resilience, and 3-Minute Judge Mode Wizard.
Now with explicit force_pdm_now for interactive control and lazy-loaded heavy computations.
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
import hashlib
import time
import functools

import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from simulation.state_machine import AssetStateMachine
from control.decision_engine import DecisionEngine
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study
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


st.set_page_config(
    page_title="PRIME-Factory | Control & Decision Center v6.2",
    layout="wide",
    page_icon="🏭"
)

# ===== Session State =====
if "manual_pdm_timestep" not in st.session_state:
    st.session_state.manual_pdm_timestep = None
if "judge_mode_step" not in st.session_state:
    st.session_state.judge_mode_step = 0
if "sim_result" not in st.session_state:
    st.session_state.sim_result = None
if "scenario_hash" not in st.session_state:
    st.session_state.scenario_hash = None
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "whatif_result" not in st.session_state:
    st.session_state.whatif_result = None
if "whatif_hash" not in st.session_state:
    st.session_state.whatif_hash = None
if "force_pdm_now" not in st.session_state:
    st.session_state.force_pdm_now = False
if "benchmark_result" not in st.session_state:
    st.session_state.benchmark_result = None
if "ablation_result" not in st.session_state:
    st.session_state.ablation_result = None
if "whatif_cached" not in st.session_state:
    st.session_state.whatif_cached = False
# ===== NEW: Track if PdM has been triggered in Step 3 =====
if "pdm_triggered_in_step3" not in st.session_state:
    st.session_state.pdm_triggered_in_step3 = False


st.title("🏭 PRIME-Factory: Industrial Control & Decision Center v6.2")
st.caption("National Competition for AI and Robotics (RoboDam 2026) | Team MSA")


# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.header("🕹️ Plant Control Center")

# ---- Judge Mode ----
st.sidebar.subheader("🏆 Judge Mode (3-Minute Flow)")
col_j1, col_j2 = st.sidebar.columns(2)
with col_j1:
    if st.button("▶️ Next Demo Step", type="primary", use_container_width=True):
        st.session_state.judge_mode_step = (st.session_state.judge_mode_step + 1) % 4
        st.session_state.manual_pdm_timestep = None
        st.session_state.sim_result = None
        st.session_state.scenario_hash = None
        st.session_state.whatif_result = None
        st.session_state.whatif_hash = None
        st.session_state.force_pdm_now = False
        st.session_state.benchmark_result = None
        st.session_state.ablation_result = None
        st.session_state.whatif_cached = False
        # ===== NEW: Reset PdM trigger flag =====
        st.session_state.pdm_triggered_in_step3 = False
        st.rerun()
with col_j2:
    if st.button("⏮️ Reset Pitch", use_container_width=True):
        st.session_state.judge_mode_step = 0
        st.session_state.manual_pdm_timestep = None
        st.session_state.sim_result = None
        st.session_state.scenario_hash = None
        st.session_state.whatif_result = None
        st.session_state.whatif_hash = None
        st.session_state.force_pdm_now = False
        st.session_state.benchmark_result = None
        st.session_state.ablation_result = None
        st.session_state.whatif_cached = False
        # ===== NEW: Reset PdM trigger flag =====
        st.session_state.pdm_triggered_in_step3 = False
        st.rerun()

# ---- Judge Step Display ----
j_step = st.session_state.judge_mode_step

if j_step == 1:
    st.sidebar.info("📌 **Step 1 (0:00-0:20):** Healthy Multi-Product Baseline (A→B→C).")
    sim_mode = "Multi-Product Switching (A → B → C)"
    selected_product = "Product_B"
    fault_type = "None (Healthy Baseline)"
    fault_start = 120
    max_deg = 0.0
    enable_chaos = False
    apply_dr = False
    # ===== NEW: Reset PdM trigger flag when entering Step 1 =====
    st.session_state.pdm_triggered_in_step3 = False
elif j_step == 2:
    st.sidebar.warning("📌 **Step 2 (0:20-1:35):** M3 Bearing Wear Onset & XAI Decision Trace.")
    sim_mode = "Fixed Product Regime"
    selected_product = "Product_B"
    fault_type = "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)"
    fault_start = 120
    max_deg = 0.85
    enable_chaos = False
    apply_dr = False
    # ===== NEW: Reset PdM trigger flag when entering Step 2 =====
    st.session_state.pdm_triggered_in_step3 = False
elif j_step == 3:
    st.sidebar.success("📌 **Step 3 (1:35-3:00):** Causal PdM Intervention, Recovery & What-If ROI.")
    sim_mode = "Fixed Product Regime"
    selected_product = "Product_B"
    fault_type = "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)"
    fault_start = 120
    max_deg = 0.85
    enable_chaos = False
    apply_dr = False
    # ===== FIXED: Auto-trigger PdM in Step 3 =====
    if not st.session_state.get("pdm_triggered_in_step3", False):
        st.session_state.force_pdm_now = True
        st.session_state.pdm_triggered_in_step3 = True
        # Force a rerun to execute the simulation with force_pdm_now=True
        st.rerun()
else:
    # Manual mode
    st.sidebar.subheader("⚙️ Manual Configuration")
    sim_mode = st.sidebar.radio(
        "Operating Schedule:",
        ["Fixed Product Regime", "Multi-Product Switching (A → B → C)"],
        index=0
    )
    if sim_mode == "Fixed Product Regime":
        selected_product = st.sidebar.selectbox(
            "Active Product:",
            ["Product_A", "Product_B", "Product_C"],
            index=1
        )
    fault_type = st.sidebar.selectbox(
        "Fault Type:",
        [
            "None (Healthy Baseline)",
            "Bearing Wear (Vibration ↑ + Temp ↑ + ECI ↑)",
            "Mechanical Friction (Power Surge ↑ + High ECI)",
            "Electrical Anomaly (Current Distortion + PF Drop)"
        ],
        index=1
    )
    fault_start = st.sidebar.slider("Fault Start (min):", 10, 400, 120)
    max_deg = st.sidebar.slider("Severity (%):", 10, 85, 75) / 100.0
    enable_chaos = st.sidebar.checkbox("Chaos Stress-Test (Sensor Noise)", value=False)
    apply_dr = st.sidebar.checkbox("Enable Peak Shaving", value=False)
    # ===== NEW: Reset PdM trigger flag when entering manual mode =====
    st.session_state.pdm_triggered_in_step3 = False

# ---- Machine Selection ----
selected_machine = st.sidebar.selectbox(
    "Target Machine:",
    list(config.MACHINES.keys()),
    index=2,
    format_func=lambda m: f"{m} — {config.MACHINES[m]['name']}"
)

# ---- Action Buttons ----
st.sidebar.divider()
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🔧 Apply Recommended PdM", type="primary", use_container_width=True):
        st.session_state.force_pdm_now = True
        st.session_state.sim_result = None
        st.session_state.scenario_hash = None
        st.session_state.whatif_result = None
        st.session_state.whatif_hash = None
        st.session_state.benchmark_result = None
        st.session_state.ablation_result = None
        st.session_state.whatif_cached = False
        st.session_state.pdm_triggered_in_step3 = True  # Mark as triggered manually
        st.rerun()
with col_btn2:
    if st.button("🔄 Reset Line", use_container_width=True):
        st.session_state.manual_pdm_timestep = None
        st.session_state.judge_mode_step = 0
        st.session_state.sim_result = None
        st.session_state.scenario_hash = None
        st.session_state.whatif_result = None
        st.session_state.whatif_hash = None
        st.session_state.force_pdm_now = False
        st.session_state.benchmark_result = None
        st.session_state.ablation_result = None
        st.session_state.whatif_cached = False
        st.session_state.pdm_triggered_in_step3 = False
        st.rerun()

# ---- Playback ----
time_scrubber = st.sidebar.slider(
    "Playback Horizon (min):",
    30,
    config.TOTAL_TIMESTEPS,
    config.TOTAL_TIMESTEPS
)


# ============================================================
# EXECUTE SIMULATION - OPTIMIZED
# ============================================================

# Build schedule
if sim_mode == "Fixed Product Regime":
    schedule = [selected_product] * config.TOTAL_TIMESTEPS
else:
    from simulation.faults import generate_switching_schedule
    schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)

# ---- Improved Hashing: include full schedule, fault_type, enable_chaos ----
def compute_scenario_hash(scenario):
    """Compute a deterministic hash for the scenario, excluding force_pdm_now."""
    hash_input = (
        scenario.fault_machine,
        scenario.fault_type,
        scenario.fault_start,
        scenario.max_degradation,
        scenario.policy_type,
        scenario.enable_peak_shaving,
        scenario.enable_chaos,
        tuple(scenario.product_schedule),
    )
    return hashlib.md5(str(hash_input).encode()).hexdigest()

# Build scenario (without force_pdm_now for hashing)
scenario_base = ScenarioConfig(
    scenario_id="LIVE_DASHBOARD_RUN",
    seed=config.RANDOM_SEED,
    product_schedule=schedule,
    fault_machine=selected_machine,
    fault_type=fault_type,
    fault_start=fault_start,
    max_degradation=max_deg if fault_type != "None (Healthy Baseline)" else 0.0,
    enable_chaos=enable_chaos,
    enable_peak_shaving=apply_dr,
    manual_pdm_timestep=None,
    policy_type="PREDICTIVE",
    force_pdm_now=False  # Will be set separately
)

current_hash = compute_scenario_hash(scenario_base)

# ---- Check if results are cached ----
if st.session_state.scenario_hash != current_hash:
    st.session_state.sim_result = None
    st.session_state.scenario_hash = current_hash
    st.session_state.whatif_result = None
    st.session_state.whatif_hash = None
    st.session_state.benchmark_result = None
    st.session_state.ablation_result = None
    st.session_state.sim_running = True
    st.session_state.whatif_cached = False

# ===== Cached simulation function =====
@st.cache_data(ttl=3600, show_spinner=False)
def run_cached_simulation(scenario_hash, scenario_dict, force_pdm):
    """
    Run the simulation with caching based on scenario hash and force_pdm flag.
    scenario_dict contains all scenario parameters.
    """
    # Reconstruct ScenarioConfig from dict
    scenario = ScenarioConfig(
        scenario_id=scenario_dict["scenario_id"],
        seed=scenario_dict["seed"],
        product_schedule=scenario_dict["product_schedule"],
        fault_machine=scenario_dict["fault_machine"],
        fault_type=scenario_dict["fault_type"],
        fault_start=scenario_dict["fault_start"],
        max_degradation=scenario_dict["max_degradation"],
        enable_chaos=scenario_dict["enable_chaos"],
        enable_peak_shaving=scenario_dict["enable_peak_shaving"],
        manual_pdm_timestep=scenario_dict["manual_pdm_timestep"],
        policy_type=scenario_dict["policy_type"],
        force_pdm_now=force_pdm
    )
    result = UnifiedSimulationEngine.run(scenario)
    return result

# ===== Cached What-If function =====
@st.cache_data(ttl=3600, show_spinner=False)
def run_what_if_cached(fault_start_val, max_deg_val, seed_val):
    """Cached What-If analysis for the same inputs."""
    return FactoryPolicySimulator.run_what_if_analysis(
        product_schedule=["Product_B"] * config.TOTAL_TIMESTEPS,
        fault_start_t=fault_start_val,
        max_deg=max_deg_val,
        seed=seed_val
    )


# ===== DISPLAY SIMULATION STATUS =====
if st.session_state.sim_running:
    # ===== FIXED: Replace fake progress bar with real spinner =====
    with st.spinner("🔄 Running PRIME-Factory simulation... This may take 30-60 seconds."):
        # Prepare scenario dict for caching
        scenario_dict = {
            "scenario_id": scenario_base.scenario_id,
            "seed": scenario_base.seed,
            "product_schedule": scenario_base.product_schedule,
            "fault_machine": scenario_base.fault_machine,
            "fault_type": scenario_base.fault_type,
            "fault_start": scenario_base.fault_start,
            "max_degradation": scenario_base.max_degradation,
            "enable_chaos": scenario_base.enable_chaos,
            "enable_peak_shaving": scenario_base.enable_peak_shaving,
            "manual_pdm_timestep": scenario_base.manual_pdm_timestep,
            "policy_type": scenario_base.policy_type,
        }
        force_pdm = st.session_state.get('force_pdm_now', False)
        st.session_state.sim_result = run_cached_simulation(current_hash, scenario_dict, force_pdm)
        # ===== FIXED: Reset force_pdm_now without extra rerun =====
        st.session_state.force_pdm_now = False
        st.session_state.sim_running = False
        st.rerun()

# ===== IF SIMULATION DONE, SHOW RESULTS =====
if st.session_state.sim_result is not None:
    sim_result = st.session_state.sim_result

    df_all = sim_result.telemetry_df
    df_target = df_all[df_all["machine_id"] == selected_machine].copy()

    if df_target.empty:
        st.error(f"No telemetry data found for machine {selected_machine}.")
        st.stop()

    df_target_view = df_target[df_target["timestep"] <= time_scrubber].copy()
    latest_row = df_target_view.iloc[-1]

    MAX_POINTS = 500
    if len(df_target_view) > MAX_POINTS:
        step = len(df_target_view) // MAX_POINTS
        df_plot = df_target_view.iloc[::step]
    else:
        df_plot = df_target_view

    display_state = latest_row["state"]
    latest_hi = latest_row["health_index"]
    badge = AssetStateMachine.get_state_badge(display_state)

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
        product_key=schedule[min(time_scrubber - 1, len(schedule) - 1)],
        persistence_ratio=latest_row.get("persistence_ratio", 0.0)
    )

    # ============================================================
    # HEADER KPIs
    # ============================================================
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        st.metric(
            "⚡ Factory Energy",
            f"{_get(sim_result, 'total_energy_kwh'):.1f} kWh",
            delta=f"{_get(sim_result, 'energy_per_good_unit_wh'):.2f} Wh/unit"
        )
    with kpi2:
        st.metric(
            "📈 Peak Demand",
            f"{_get(sim_result, 'peak_demand_kw'):.1f} kW",
            delta="Peak Shaving" if apply_dr else "Standard"
        )
    with kpi3:
        st.metric(
            f"🛡️ {selected_machine} HI",
            f"{latest_hi:.1f} / 100",
            delta=f"{latest_hi - 100.0:.1f}",
            delta_color="normal"
        )
    with kpi4:
        st.metric(
            "⏳ RUL",
            str(latest_row.get("rul_str", "Stable")),
            delta=f"Conf: {latest_row.get('rul_confidence', 1.0) * 100:.0f}%"
        )
    with kpi5:
        st.metric(
            "💰 Total Cost",
            f"${_get(sim_result, 'total_operational_cost_usd'):.2f}",
            delta=f"{_get(sim_result, 'carbon_kg'):.1f} kg CO2",
            delta_color="inverse"
        )

    # ---- Alert Banner ----
    if display_state in [config.STATE_CRITICAL, config.STATE_FAILED]:
        st.error(f"🚨 **{latest_decision['title']}** | **Machine:** {selected_machine} | **Action:** {latest_decision['recommended_action']}")
    elif display_state in [config.STATE_PREDICTIVE_ALERT, config.STATE_WARNING]:
        st.warning(f"⚠️ **{latest_decision['title']}** | **Machine:** {selected_machine} | **Action:** {latest_decision['recommended_action']}")
    elif display_state in [config.STATE_MAINTENANCE, config.STATE_RECOVERY]:
        st.info(f"🔄 **{badge['label']}** | **Machine:** {selected_machine} | **Action:** {badge['action']}")
    else:
        st.success(f"✅ **{badge['label']}** | **Action:** {badge['action']}")

    if j_step > 0:
        progress_text = {
            1: "🟢 Step 1/3: Healthy Baseline (0:00-0:20)",
            2: "🟡 Step 2/3: Fault Detection & XAI (0:20-1:35)",
            3: "🔵 Step 3/3: PdM & Recovery (1:35-3:00)"
        }
        st.progress(j_step / 3.0, text=progress_text.get(j_step, ""))

    st.divider()

    # ============================================================
    # TABS
    # ============================================================
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

    # ===== TAB 1: Live Telemetry =====
    with t_live:
        fig_cond = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f"Physical Telemetry ({selected_machine})", "Composite Health Index & Thresholds")
        )

        if "vibration_rms" in df_plot.columns and config.MACHINES[selected_machine]["has_vibration"]:
            fig_cond.add_trace(
                go.Scatter(x=df_plot["timestep"], y=df_plot["vibration_rms"],
                           name="Vibration (g RMS)", line=dict(color="#1f77b4", shape='hv')),
                row=1, col=1
            )

        if "temperature_c" in df_plot.columns:
            fig_cond.add_trace(
                go.Scatter(x=df_plot["timestep"], y=df_plot["temperature_c"],
                           name="Temperature (°C)", line=dict(color="#ff7f0e", shape='hv')),
                row=1, col=1
            )

        if "power_kw" in df_plot.columns or "active_power_kw" in df_plot.columns:
            power_col = "power_kw" if "power_kw" in df_plot.columns else "active_power_kw"
            fig_cond.add_trace(
                go.Scatter(x=df_plot["timestep"], y=df_plot[power_col],
                           name="Power (kW)", line=dict(color="#2ca02c", shape='hv')),
                row=1, col=1
            )

        if "health_index" in df_plot.columns:
            fig_cond.add_trace(
                go.Scatter(x=df_plot["timestep"], y=df_plot["health_index"],
                           name="Health Index (HI)", line=dict(color="#00cc96", width=2.5, shape='hv')),
                row=2, col=1
            )
            fig_cond.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Monitor (70)", row=2, col=1)
            fig_cond.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Intervention (50)", row=2, col=1)

        fig_cond.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
        st.plotly_chart(fig_cond, use_container_width=True)

    # ===== TAB 2: Decision Trace =====
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
                st.plotly_chart(
                    px.bar(attr_df, x="Evidence Modality", y="Penalty Contribution (%)",
                           color="Evidence Modality", title="HI Penalty Attribution", text_auto=".1f"),
                    use_container_width=True
                )

    # ===== TAB 3: Evidence Chain =====
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
                        col_s1, col_s2 = st.columns([2, 1])
                        with col_s1:
                            st.write(f"**Description:** {step.description}")
                            st.write(f"**Timestamp:** t={step.timestamp} min")
                        with col_s2:
                            st.write("**Data:**")
                            st.json(step.data)

                st.divider()

                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    trace_json = json.dumps(latest_trace.to_dict(), indent=2)
                    st.download_button(
                        "📥 Export Trace as JSON",
                        trace_json,
                        f"evidence_trace_{latest_trace.trace_id}.json",
                        "application/json"
                    )
                with col_exp2:
                    df_trace = pd.DataFrame([
                        {"Step": s.step_type, "Timestamp": s.timestamp, "Description": s.description, **s.data}
                        for s in latest_trace.steps
                    ])
                    st.download_button(
                        "📥 Export Trace as CSV",
                        df_trace.to_csv(index=False).encode('utf-8'),
                        f"evidence_trace_{latest_trace.trace_id}.csv",
                        "text/csv"
                    )
            else:
                st.info(f"No evidence traces found for machine {selected_machine}.")
        else:
            st.warning("Evidence tracker not available.")

    # ===== TAB 4: What-If (Lazy + Cached) =====
    with t_whatif:
        st.subheader("⚖️ Dual-Branch What-If Analysis (Intervention vs No Intervention)")

        if st.button("▶️ Run What-If Analysis", key="run_whatif"):
            with st.spinner("Running What-If analysis..."):
                st.session_state.whatif_result = run_what_if_cached(
                    fault_start_val=fault_start,
                    max_deg_val=max_deg,
                    seed_val=config.RANDOM_SEED
                )
                st.session_state.whatif_cached = True
                st.rerun()

        if st.session_state.whatif_result is not None:
            whatif_res = st.session_state.whatif_result

            col_w1, col_w2, col_w3, col_w4 = st.columns(4)
            savings = whatif_res.get("savings", {})

            col_w1.metric("⏱️ Downtime Prevented", f"{savings.get('downtime_saved_min', 0.0):.1f} min", delta="Reliability")
            col_w2.metric("💰 Cost Savings", f"${savings.get('cost_saved_usd', 0.0):.2f}", delta="Financial Protection")
            col_w3.metric("📈 OEE Gain", f"+{savings.get('oee_gain_pct', 0.0):.2f}%", delta="Productivity")
            col_w4.metric("🌍 Carbon Avoided", f"{savings.get('carbon_saved_kg', 0.0):.2f} kg CO2", delta="Sustainability")

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

            st.dataframe(
                wi_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda")
                       .highlight_min(subset=["Total Cost ($)", "Downtime (min)"], color="#d4edda"),
                use_container_width=True
            )
        else:
            st.info("Click the button above to run the What-If analysis.")

    # ===== TAB 5: Resilience =====
    with t_resilience:
        st.subheader("🛡️ Industrial Resilience & Recovery Evaluation")

        r_metrics = _get(sim_result, "resilience", None)
        r_col1, r_col2, r_col3, r_col4 = st.columns(4)

        r_col1.metric("⏱️ Recovery Duration", f"{_get(r_metrics, 'recovery_time_min', 15.0):.1f} min", delta="Post-repair")
        r_col2.metric("📦 Production Loss", f"{_get(r_metrics, 'production_loss_units', 0)} units", delta="Scrap + downtime")
        rec_ok = _get(r_metrics, 'recovery_success', False)
        r_col3.metric("✅ Recovery Status", "SUCCESS" if rec_ok else "PENDING", delta="Self-stabilized")
        r_col4.metric(
            "🛡️ Failure Avoided",
            "✅ Yes" if _get(r_metrics, 'failure_avoided', False) else "❌ No",
            delta="Predictive benefit"
        )

    # ===== TAB 6: Events =====
    with t_events:
        st.subheader("📋 Chronological Audit Event Log")

        events_list = _get(sim_result, "events", [])
        ev_df = pd.DataFrame([{
            "Timestep (min)": _get(e, "timestep"),
            "Severity": _get(e, "severity"),
            "Machine": _get(e, "machine_id"),
            "Event Type": _get(e, "event_type"),
            "Message": _get(e, "message")
        } for e in events_list])

        st.dataframe(ev_df, use_container_width=True)
        st.download_button(
            "📥 Download Audit Trail (CSV)",
            ev_df.to_csv(index=False).encode('utf-8'),
            "prime_factory_events.csv",
            "text/csv"
        )

    # ===== TAB 7: Benchmark (Lazy) =====
    with t_bench:
        st.subheader("📊 Scientific Factory Policy Benchmark")

        if st.button("▶️ Run Scientific Benchmark", key="run_benchmark"):
            with st.spinner("Running benchmark simulations..."):
                pols = [("CORRECTIVE", False), ("PREVENTIVE", False), ("PREDICTIVE", False), ("PREDICTIVE", True)]
                b_res = []
                for p_name, p_dr in pols:
                    sim = FactoryPolicySimulator(policy_type=p_name, enable_peak_shaving=p_dr, seed=config.RANDOM_SEED)
                    r = sim.run_policy_benchmark()
                    fail_avoided = False
                    if hasattr(r, 'resilience') and r.resilience:
                        if hasattr(r.resilience, 'failure_avoided'):
                            fail_avoided = r.resilience.failure_avoided
                        elif isinstance(r.resilience, dict):
                            fail_avoided = r.resilience.get('failure_avoided', False)
                    b_res.append({
                        "Policy": p_name if not p_dr else "PREDICTIVE + PEAK SHAVING",
                        "Downtime (min)": _get(r, "downtime_min"),
                        "Events": _get(r, "maintenance_events"),
                        "OEE (%)": _get(r, "oee_pct"),
                        "Good Units": _get(r, "good_units"),
                        "Energy (kWh)": _get(r, "total_energy_kwh"),
                        "Peak (kW)": _get(r, "peak_demand_kw"),
                        "Total Cost ($)": _get(r, "total_operational_cost_usd"),
                        "Carbon (kg CO2)": _get(r, "carbon_kg"),
                        "Failure Avoided": "✅ Yes" if fail_avoided else "❌ No"
                    })
                st.session_state.benchmark_result = pd.DataFrame(b_res)
                st.rerun()

        if st.session_state.benchmark_result is not None:
            st.dataframe(
                st.session_state.benchmark_result.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda")
                                   .highlight_min(subset=["Total Cost ($)", "Peak (kW)"], color="#d4edda"),
                use_container_width=True
            )
        else:
            st.info("Click the button above to run the benchmark.")

    # ===== TAB 8: Ablation (Lazy) =====
    with t_ablation:
        st.subheader("🧪 Calibrated Pure Detector Ablation Study (Layers A–E)")

        if st.button("▶️ Run Ablation Study", key="run_ablation"):
            with st.spinner("Running ablation study..."):
                try:
                    ab_df = run_ablation_study(df_target)
                    st.session_state.ablation_result = ab_df
                except Exception as e:
                    st.warning(f"Ablation study failed: {e}")
                st.rerun()

        if st.session_state.ablation_result is not None:
            ab_df = st.session_state.ablation_result
            st.dataframe(
                ab_df.style.highlight_max(subset=["Precision", "Recall", "F1-Score"], color="#d4edda")
                      .highlight_min(subset=["False Alarms/Hr"], color="#d4edda"),
                use_container_width=True
            )
            st.plotly_chart(
                px.bar(ab_df, x="Architecture Layer", y="F1-Score",
                       color="Architecture Layer", title="F1-Score Across Detector Layers", text_auto=".3f"),
                use_container_width=True
            )
        else:
            st.info("Click the button above to run the ablation study.")

    # ===== TAB 9: Report =====
    with t_report:
        st.subheader("📑 Auto-Generated Experiment Report")

        rep1, rep2 = st.columns(2)

        with rep1:
            st.write("#### Experiment Metadata")
            st.json({
                "Scenario_ID": scenario_base.scenario_id,
                "Target_Asset": scenario_base.fault_machine,
                "Fault_Type": scenario_base.fault_type,
                "Inception": scenario_base.fault_start,
                "Max_Degradation": f"{scenario_base.max_degradation * 100:.1f}%",
                "Random_Seed": scenario_base.seed,
                "Policy": scenario_base.policy_type,
                "Version": "PRIME-Factory v6.2"
            })

        with rep2:
            maint_cost = 0.0
            if hasattr(sim_result, 'maintenance_cost_usd'):
                maint_cost = sim_result.maintenance_cost_usd
                
            fail_avoided = False
            if hasattr(sim_result, 'resilience') and sim_result.resilience:
                if hasattr(sim_result.resilience, 'failure_avoided'):
                    fail_avoided = sim_result.resilience.failure_avoided
                elif isinstance(sim_result.resilience, dict):
                    fail_avoided = sim_result.resilience.get('failure_avoided', False)
            
            st.write("#### Quantified Outcomes")
            st.json({
                "OEE": f"{_get(sim_result, 'oee_pct'):.1f}%",
                "Availability": f"{_get(sim_result, 'availability_pct'):.1f}%",
                "Performance": f"{_get(sim_result, 'performance_pct'):.1f}%",
                "Quality": f"{_get(sim_result, 'quality_pct'):.1f}%",
                "Energy Cost": f"${_get(sim_result, 'energy_cost_usd'):.2f}",
                "Downtime Cost": f"${_get(sim_result, 'downtime_cost_usd'):.2f}",
                "Maintenance Cost": f"${_get(sim_result, 'maintenance_cost_usd', maint_cost):.2f}",
                "PF Penalty": f"${_get(sim_result, 'pf_penalty_usd'):.2f}",
                "Total Cost": f"${_get(sim_result, 'total_operational_cost_usd'):.2f}",
                "Carbon": f"{_get(sim_result, 'carbon_kg'):.2f} kg CO2",
                "Good Units": _get(sim_result, 'good_units'),
                "Failure Avoided": "✅ Yes" if fail_avoided else "❌ No"
            })

    # ============================================================
    # FOOTER
    # ============================================================
    st.divider()
    st.caption("🏭 PRIME-Factory v6.2 | Team MSA | RoboDam 2026")