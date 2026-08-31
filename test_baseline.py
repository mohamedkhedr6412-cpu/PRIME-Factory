"""
Test 1: Run Normal 8-hour Production Baseline (E1)
"""
import config
from simulation.factory import PackagingFactory

# محاكاة وردية عمل كاملة (8 ساعات = 480 دقيقة) للمنتج B في الحالة الطبيعية
schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
factory = PackagingFactory()
df = factory.run_simulation(schedule)

print("\n========================================")
print("   PRIME-FACTORY BASELINE TEST (E1)     ")
print("========================================")
print(f"Status: COMPLETED SUCCESSFULLY")
print(f"Total Telemetry Records: {len(df)}")
print(f"Machines Monitored: {df['machine_id'].nunique()} (M1 to M5)")
print(f"Shift Duration: {config.SHIFT_HOURS} Hours ({config.TOTAL_TIMESTEPS} Minutes)")
print("----------------------------------------")
print("Sample Data (First 5 records):")
print(df[["timestep", "machine_id", "state", "temperature_c", "power_kw", "vibration_rms"]].head(5))
print("========================================\n")
