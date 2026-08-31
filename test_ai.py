"""
Test 3: AI Pipeline, Persistence, and Health Index Verification
Validates the full decision pipeline under degradation and product switching.
"""
import config
import pandas as pd
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile, generate_switching_schedule
from energy.eci import calculate_eci
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index, map_hi_to_decision

# 1. تدريب نموذج الذكاء الاصطناعي على خط الأساس السليم (Baseline Training)
print("\n[1/3] Training Isolation Forest on Healthy Baseline...")
baseline_schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
factory = PackagingFactory()
train_df = factory.run_simulation(baseline_schedule)

ai_model = PRIMEIsolationForest(contamination=0.02)
ai_model.fit(train_df)
print("       Model Training Completed Successfully.")

# 2. تشغيل سيناريو اختبار التدهور للماكينة M3 (Degradation Test)
print("[2/3] Simulating Degradation Scenario on Machine M3...")
m3_fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=120, max_degradation=0.35)
test_df = factory.run_simulation(baseline_schedule, degradation_targets={"M3": m3_fault_profile})
test_df["eci"] = test_df.apply(lambda row: calculate_eci(row["power_kw"], row["product"]), axis=1)

# تطبيق الذكاء الاصطناعي وحساب مؤشر الصحة للماكينة M3
test_df["ai_score"] = ai_model.predict_anomaly_score(test_df)
m3_eval = test_df[test_df["machine_id"] == "M3"].copy()

processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
hi_list = []
decision_list = []

for _, row in m3_eval.iterrows():
    p_info = processor.update(row["ai_score"], threshold=0.5)
    hi = calculate_health_index(row["ai_score"], p_info["persistence_ratio"], row["eci"], row["temperature_c"])
    hi_list.append(hi)
    decision_list.append(map_hi_to_decision(hi))

m3_eval["health_index"] = hi_list
m3_eval["action_decision"] = decision_list

print("       Degradation Pipeline Evaluated.")

# 3. اختبار تبديل المنتجات (Context-Aware Test: Product A -> B -> C)
print("[3/3] Simulating Multi-Product Switching (A -> B -> C)...")
switch_schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)
switch_df = factory.run_simulation(switch_schedule)
switch_df["ai_score"] = ai_model.predict_anomaly_score(switch_df)
switch_m3 = switch_df[switch_df["machine_id"] == "M3"].copy()

print("\n=======================================================================")
print("                   PRIME-FACTORY AI & HI TEST RESULTS                  ")
print("=======================================================================")
print(f"M3 Initial State (t=0)   -> HI: {m3_eval['health_index'].iloc[0]}  | Decision: {m3_eval['action_decision'].iloc[0]}")
print(f"M3 Mid Degradation (t=250)-> HI: {m3_eval['health_index'].iloc[250]} | Decision: {m3_eval['action_decision'].iloc[250]}")
print(f"M3 Final State (t=479)   -> HI: {m3_eval['health_index'].iloc[-1]}  | Decision: {m3_eval['action_decision'].iloc[-1]}")
print("-----------------------------------------------------------------------")
print("Product Switching Robustness Check:")
print(f"Max AI Anomaly Score during Normal Product Transitions: {switch_m3['ai_score'].max():.3f} (Threshold = 0.50)")
print("=======================================================================\n")
