"""
Test 2: Fault Injection & Energy Condition Indicator (ECI) Verification
Injects bearing degradation into Machine M3 (Sealer) and monitors telemetry & ECI.
"""
import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile
from energy.eci import calculate_eci
from energy.energy_model import calculate_total_energy_kwh, calculate_peak_demand_kw

# 1. إعداد الوردية وحقن التدهور في الماكينة M3 بدءًا من الدقيقة 120 حتى 35% تآكل
schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
m3_fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=120, max_degradation=0.35)
degradation_plan = {"M3": m3_fault_profile}

# 2. تشغيل المحاكاة
factory = PackagingFactory()
df = factory.run_simulation(schedule, degradation_targets=degradation_plan)

# 3. حساب مؤشر ECI لكل قراءة
df["eci"] = df.apply(lambda row: calculate_eci(row["power_kw"], row["product"]), axis=1)

# 4. مقارنة سلوك الماكينة السليمة M1 بالماكينة المتدهورة M3
m1_data = df[df["machine_id"] == "M1"]
m3_data = df[df["machine_id"] == "M3"]

print("\n=======================================================")
print("      PRIME-FACTORY FAULT & ECI INJECTION TEST         ")
print("=======================================================")
print(f"Machine M1 (Healthy)  -> Avg Power: {m1_data['power_kw'].mean():.2f} kW | Max ECI: {m1_data['eci'].max():.3f} | Final Vib: {m1_data['vibration_rms'].iloc[-1]:.3f} RMS")
print(f"Machine M3 (Degraded) -> Avg Power: {m3_data['power_kw'].mean():.2f} kW | Max ECI: {m3_data['eci'].max():.3f} | Final Vib: {m3_data['vibration_rms'].iloc[-1]:.3f} RMS")
print("-------------------------------------------------------")
print(f"Total Factory Energy: {calculate_total_energy_kwh(df['power_kw']):.2f} kWh")
print(f"Factory Peak Demand:  {calculate_peak_demand_kw(df['power_kw']):.2f} kW")
print("-------------------------------------------------------")
print("Sample M3 Telemetry after degradation starts (Timestep 400):")
print(df[(df["machine_id"] == "M3") & (df["timestep"] == 400)][["timestep", "machine_id", "state", "vibration_rms", "temperature_c", "power_kw", "eci"]])
print("=======================================================\n")
