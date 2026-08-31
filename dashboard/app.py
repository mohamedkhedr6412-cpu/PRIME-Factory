"""
PRIME-Factory Interactive Streamlit Dashboard
Real-Time Demonstration & Judging Interface for RoboDam 2026
"""
import sys
import os

# إضافة المسار الرئيسي للمشروع
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile
from energy.eci import calculate_eci
from energy.energy_model import calculate_total_energy_kwh, calculate_peak_demand_kw
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index, map_hi_to_decision
from maintenance.policies import PolicySimulator
from evaluation.kpis import calculate_oee, calculate_energy_kpi
from energy.peak_shaving import apply_peak_shaving

# إعداد الصفحة وتصميمها
st.set_page_config(page_title="PRIME-Factory | Industry 4.0 Dashboard", layout="wide")

st.title("🏭 PRIME-Factory: Smart Packaging Line Monitoring & EMS")
st.caption("National Competition for AI and Robotics (RoboDam 2026) | Team MSA")

# ==========================================
# القائمة الجانبية للتحكم (Sidebar Controls)
# ==========================================
st.sidebar.header("⚙️ Simulation Controls")

selected_product = st.sidebar.selectbox(
    "Operating Product Context:",
    options=["Product_A", "Product_B", "Product_C"],
    index=1,
    help="Changes load, speed, and expected baseline power."
)

inject_fault = st.sidebar.checkbox("Inject Bearing Degradation (M3 Sealer)", value=True)
fault_start = st.sidebar.slider("Degradation Start Time (Minute):", min_value=10, max_value=400, value=120)
max_deg = st.sidebar.slider("Max Degradation Level (%):", min_value=5, max_value=60, value=35) / 100.0

apply_dr = st.sidebar.checkbox("Enable Demand Response (Peak Shaving)", value=False)

# ==========================================
# تشغيل المحاكاة ومعالجة البيانات
# ==========================================
@st.cache_data
def run_full_pipeline(prod_key, fault_enabled, start_t, max_d, dr_enabled):
    schedule = [prod_key] * config.TOTAL_TIMESTEPS
    degradation_plan = None
    if fault_enabled:
        profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=start_t, max_degradation=max_d)
        degradation_plan = {"M3": profile}

    factory = PackagingFactory()
    df = factory.run_simulation(schedule, degradation_targets=degradation_plan)
    
    # تدريب الذكاء الاصطناعي على التشغيل السليم
    ai_model = PRIMEIsolationForest(contamination=0.02)
    ai_model.fit(df[df["degradation"] == 0.0])
    
    df["eci"] = df.apply(lambda row: calculate_eci(row["power_kw"], row["product"]), axis=1)
    df["ai_score"] = ai_model.predict_anomaly_score(df)
    
    # حساب HI والاستمرارية للماكينة M3
    m3_df = df[df["machine_id"] == "M3"].copy()
    processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
    hi_list, conf_list = [], []
    
    for _, row in m3_df.iterrows():
        p_info = processor.update(row["ai_score"], threshold=0.5)
        hi = calculate_health_index(row["ai_score"], p_info["persistence_ratio"], row["eci"], row["temperature_c"])
        hi_list.append(hi)
        conf_list.append(p_info["is_confirmed_anomaly"])
        
    m3_df["health_index"] = hi_list
    m3_df["confirmed_anomaly"] = conf_list
    return df, m3_df

df_all, df_m3 = run_full_pipeline(selected_product, inject_fault, fault_start, max_deg, apply_dr)

# ==========================================
# بطاقات مؤشرات الأداء الحية (Top KPI Metrics)
# ==========================================
total_energy = calculate_total_energy_kwh(df_all["power_kw"])
peak_kw = calculate_peak_demand_kw(df_all["power_kw"])
latest_hi = df_m3["health_index"].iloc[-1]
latest_eci = df_m3["eci"].iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Factory Total Energy", f"{total_energy:.2f} kWh")
col2.metric("Peak Demand", f"{peak_kw:.2f} kW")
col3.metric("M3 Health Index (HI)", f"{latest_hi:.1f} / 100", delta=f"{latest_hi - 100:.1f}", delta_color="inverse")
col4.metric("M3 Energy Dev. (ECI)", f"{latest_eci:+.3f}", delta=f"{(latest_eci)*100:+.1f}%")

# تنبيه حالة الماكينة
decision_state = map_hi_to_decision(latest_hi)
if latest_hi >= 70:
    st.success(f"🟢 **Machine Operational Status:** {decision_state}")
elif latest_hi >= 50:
    st.warning(f"🟡 **Machine Operational Status:** {decision_state}")
else:
    st.error(f"🔴 **Machine Operational Status:** {decision_state}")

st.divider()

# ==========================================
# الرسوم البيانية التفاعلية المنظمة
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Condition Monitoring & Health Index",
    "⚡ Energy & ECI Anomaly Tracking",
    "🏭 5-Machine Line Overview",
    "🏆 Policy Benchmark Comparison"
])

# ----------------- Tab 1: Condition Monitoring -----------------
with tab1:
    fig_cond = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Vibration RMS (g) & Temperature (°C)", "PRIME Health Index (HI) [0 - 100]")
    )
    
    # الصف العلوي: الاهتزاز والحرارة
    fig_cond.add_trace(
        go.Scatter(x=df_m3["timestep"], y=df_m3["vibration_rms"], name="Vibration RMS (g)", line=dict(color="#1f77b4", width=2)),
        row=1, col=1
    )
    fig_cond.add_trace(
        go.Scatter(x=df_m3["timestep"], y=df_m3["temperature_c"], name="Temperature (°C)", line=dict(color="#ff7f0e", dash="dot")),
        row=1, col=1
    )
    
    # الصف السفلي: مؤشر الصحة الهندسية
    fig_cond.add_trace(
        go.Scatter(x=df_m3["timestep"], y=df_m3["health_index"], name="Health Index (HI)", line=dict(color="#2ca02c", width=3)),
        row=2, col=1
    )
    # خطوط مستويات التحذير
    fig_cond.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Monitor Threshold (70)", row=2, col=1)
    fig_cond.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Degraded Threshold (50)", row=2, col=1)

    fig_cond.update_layout(height=520, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    fig_cond.update_xaxes(title_text="Simulation Time (Minutes)", row=2, col=1)
    st.plotly_chart(fig_cond, use_container_width=True)

# ----------------- Tab 2: Energy & ECI -----------------
with tab2:
    fig_energy = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Active Power Consumption (kW)", "Energy Condition Indicator (ECI) Deviation")
    )
    
    fig_energy.add_trace(
        go.Scatter(x=df_m3["timestep"], y=df_m3["power_kw"], name="Actual Power (kW)", line=dict(color="#d62728", width=2)),
        row=1, col=1
    )
    fig_energy.add_trace(
        go.Scatter(x=df_m3["timestep"], y=df_m3["eci"], name="ECI Deviation", line=dict(color="#9467bd", width=2)),
        row=2, col=1
    )
    fig_energy.add_hline(y=0.0, line_dash="dash", line_color="gray", annotation_text="Baseline (0.0)", row=2, col=1)

    fig_energy.update_layout(height=520, margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    fig_energy.update_xaxes(title_text="Simulation Time (Minutes)", row=2, col=1)
    st.plotly_chart(fig_energy, use_container_width=True)

# ----------------- Tab 3: Multi-Machine Overview -----------------
with tab3:
    fig_all = px.line(
        df_all, x="timestep", y="power_kw", color="machine_id",
        title="Active Power Consumption Across All 5 Production Assets",
        labels={"timestep": "Time (Minutes)", "power_kw": "Power (kW)", "machine_id": "Machine"}
    )
    fig_all.update_layout(height=480, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_all, use_container_width=True)

# ----------------- Tab 4: Policy Benchmark Comparison -----------------
with tab4:
    st.subheader("Maintenance Policy & Energy Optimization Benchmark")
    
    # حساب جدول المقارنة الفوري للسياسات
    policies = ["CORRECTIVE", "PREVENTIVE", "PREDICTIVE", "PREDICTIVE_PEAK_SHAVING"]
    benchmark_results = []
    
    for pol_name in policies:
        actual_pol = "PREDICTIVE" if "PREDICTIVE" in pol_name else pol_name
        sim = PolicySimulator(policy_type=actual_pol)
        is_ps = (pol_name == "PREDICTIVE_PEAK_SHAVING")
        deg_level = 0.0
        powers = []
        
        for t in range(config.TOTAL_TIMESTEPS):
            if not sim.is_under_repair and t >= 60:
                deg_level = min(0.85, deg_level + (0.85 / (config.TOTAL_TIMESTEPS - 60)))
            speed_mod = apply_peak_shaving(t) if is_ps else 1.0
            ai_score = min(1.0, deg_level * 1.3)
            persistence = 1.0 if deg_level > 0.25 else 0.0
            eci = deg_level * 0.35
            temp = 42.0 + (28.0 * deg_level)
            hi = calculate_health_index(ai_score, persistence, eci, temp)
            base_p = (config.PRODUCTS[selected_product]["nominal_power_kw"] * (1.0 + 0.35 * deg_level)) * (speed_mod ** 2)
            base_c = config.PRODUCTS[selected_product]["base_cycle_time"] / speed_mod
            step_res = sim.step(t, deg_level, hi, base_p, base_c)
            deg_level = step_res["current_degradation"]
            powers.append(step_res["power_kw"])
            
        oee_res = calculate_oee(config.TOTAL_TIMESTEPS, config.TOTAL_TIMESTEPS - sim.downtime_minutes, config.PRODUCTS[selected_product]["base_cycle_time"], sim.total_units_produced, sim.good_units_produced)
        eng_res = calculate_energy_kpi(sim.energy_consumed_kwh, sim.good_units_produced, max(powers))
        
        benchmark_results.append({
            "Maintenance Policy": pol_name,
            "Downtime (min)": sim.downtime_minutes,
            "Interventions": sim.maintenance_events,
            "OEE (%)": oee_res["oee_pct"],
            "Good Units": sim.good_units_produced,
            "Total Energy (kWh)": eng_res["total_energy_kwh"],
            "Energy/Unit (Wh)": eng_res["energy_per_unit_wh"]
        })
        
    bench_df = pd.DataFrame(benchmark_results)
    st.dataframe(bench_df.style.highlight_max(subset=["OEE (%)", "Good Units"], color="#d4edda").highlight_min(subset=["Downtime (min)", "Total Energy (kWh)", "Energy/Unit (Wh)"], color="#d4edda"), use_container_width=True)
    
    # رسم بياني للمقارنة
    col_a, col_b = st.columns(2)
    with col_a:
        fig_oee = px.bar(bench_df, x="Maintenance Policy", y="OEE (%)", color="Maintenance Policy", title="Overall Equipment Effectiveness (OEE %)")
        st.plotly_chart(fig_oee, use_container_width=True)
    with col_b:
        fig_eng = px.bar(bench_df, x="Maintenance Policy", y="Energy/Unit (Wh)", color="Maintenance Policy", title="Specific Energy Consumption (Wh/unit)")
        st.plotly_chart(fig_eng, use_container_width=True)