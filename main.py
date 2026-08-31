"""
PRIME-Factory Master Simulation & Evidence Generator
"""
import os
import matplotlib
matplotlib.use('Agg')  # تشغيل سريع في الخلفية لحفظ الصور بدون واجهة
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile
from energy.eci import calculate_eci
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index
from evaluation.ablation import run_ablation_study

# إنشاء مجلد لحفظ مخرجات الصور
os.makedirs("exports", exist_ok=True)

print("\n=======================================================")
print("   PRIME-FACTORY MASTER EXPERIMENT ENGINE RUNNING      ")
print("=======================================================")

# 1. تشغيل المحاكاة الكاملة وتدريب الذكاء الاصطناعي
schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=120, max_degradation=0.35)
factory = PackagingFactory()
df = factory.run_simulation(schedule, degradation_targets={"M3": fault_profile})

ai_model = PRIMEIsolationForest(contamination=0.02)
ai_model.fit(df[df["degradation"] == 0.0])

df["eci"] = df.apply(lambda row: calculate_eci(row["power_kw"], row["product"]), axis=1)
df["ai_score"] = ai_model.predict_anomaly_score(df)

m3_df = df[df["machine_id"] == "M3"].copy()
processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
hi_list = []

for _, row in m3_df.iterrows():
    p_info = processor.update(row["ai_score"], threshold=0.5)
    hi = calculate_health_index(row["ai_score"], p_info["persistence_ratio"], row["eci"], row["temperature_c"])
    hi_list.append(hi)
m3_df["health_index"] = hi_list

# 2. تشغيل دراسة الاستئصال
print("\n[+] Running Architectural Ablation Study...")
ablation_df = run_ablation_study(m3_df)
print(ablation_df.to_string(index=False))

# 3. حفظ مخططات البحث العلمي عالية الدقة (300 DPI)
print("\n[+] Generating & Exporting High-Resolution Figures...")

# الشكل 1: الاستجابة المتعددة وتغير مؤشر الصحة
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)
ax1.plot(m3_df["timestep"], m3_df["vibration_rms"], label="Vibration RMS (g)", color="#1f77b4", lw=1.5)
ax1.set_ylabel("Vibration (g)", color="#1f77b4")
ax1_t = ax1.twinx()
ax1_t.plot(m3_df["timestep"], m3_df["temperature_c"], label="Temperature (°C)", color="#ff7f0e", ls="--", lw=1.5)
ax1_t.set_ylabel("Temp (°C)", color="#ff7f0e")
ax1.set_title("PRIME-Factory: Multi-Modal Physical Telemetry Response")

ax2.plot(m3_df["timestep"], m3_df["health_index"], label="Health Index (HI)", color="#2ca02c", lw=2)
ax2.axhline(70, color="orange", ls=":", label="Monitor Threshold (70)")
ax2.axhline(50, color="red", ls=":", label="Degraded Threshold (50)")
ax2.set_xlabel("Simulation Time (Minutes)")
ax2.set_ylabel("Health Index [0-100]")
ax2.legend(loc="lower left")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig("exports/figure1_health_response.png", dpi=300)
plt.close()

# الشكل 2: انحراف الطاقة اللحظي
fig, ax = plt.subplots(figsize=(10, 4), dpi=300)
ax.plot(m3_df["timestep"], m3_df["power_kw"], label="Active Power (kW)", color="#d62728", lw=1.5)
ax.set_ylabel("Power (kW)", color="#d62728")
ax_e = ax.twinx()
ax_e.plot(m3_df["timestep"], m3_df["eci"], label="ECI Deviation", color="#9467bd", lw=1.5)
ax_e.axhline(0.0, color="gray", ls="--")
ax_e.set_ylabel("ECI Index", color="#9467bd")
ax.set_title("PRIME-Factory: Energy Condition Indicator (ECI) Deviation")
ax.set_xlabel("Simulation Time (Minutes)")
plt.tight_layout()
fig.savefig("exports/figure2_energy_eci.png", dpi=300)
plt.close()

print("    ✓ Figure 1 saved to: exports/figure1_health_response.png")
print("    ✓ Figure 2 saved to: exports/figure2_energy_eci.png")
print("\n=======================================================")
print("            ALL EXPERIMENTS COMPLETED 100%             ")
print("=======================================================\n")