"""
PRIME-Factory Factory-Level Maintenance Policies Engine v2.0
Simulates a synchronized 5-machine production line across 4 maintenance paradigms.
"""
import numpy as np
import pandas as pd
import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile
from energy.eci import calculate_eci
from energy.peak_shaving import apply_peak_shaving
from energy.energy_model import get_factory_aggregated_power, calculate_financial_and_esg_impact
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence

class FactoryPolicySimulator:
    def __init__(self, policy_type: str = "PREDICTIVE", enable_peak_shaving: bool = False):
        self.policy_type = policy_type.upper()
        self.enable_peak_shaving = enable_peak_shaving
        self.factory = PackagingFactory()
        
    def run_policy_benchmark(self, product_schedule: list, fault_machine: str = "M3", start_fault_t: int = 60, max_deg: float = 0.85) -> dict:
        timesteps = len(product_schedule)
        fault_profile = generate_degradation_profile(timesteps, start_time=start_fault_t, max_degradation=max_deg)
        
        # تدريب نموذج الذكاء الاصطناعي على التشغيل السليم للماكينات
        train_df = self.factory.run_simulation(product_schedule)
        ai_model = PRIMEIsolationForest(contamination=0.02)
        ai_model.fit(train_df)
        
        # تتبع مؤشرات الخط وحالته
        current_deg = 0.0
        is_repairing = False
        repair_timer = 0
        downtime_minutes = 0.0
        maintenance_events = 0
        
        factory_records = []
        processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
        prev_hi = 100.0
        
        total_units = 0
        good_units = 0
        
        for t in range(timesteps):
            prod_key = product_schedule[t]
            speed_mod = apply_peak_shaving(t) if self.enable_peak_shaving else 1.0
            
            # 1. معالجة حالة الصيانة الجارية
            if is_repairing:
                repair_timer -= 1
                downtime_minutes += 1.0
                if repair_timer <= 0:
                    is_repairing = False
                    current_deg = 0.0  # عودة الماكينة لحالتها السليمة بالكامل
                
                # أثناء التوقف: استهلاك طاقة خامل فقط وتوقف الإنتاج
                for m in self.factory.machines:
                    factory_records.append({
                        "timestep": t,
                        "machine_id": m.machine_id,
                        "power_kw": 0.3,
                        "state": config.STATE_MAINTENANCE,
                        "degradation": current_deg
                    })
                continue
            
            # 2. تحديث التدهور الميكانيكي الطبيعي
            if t >= start_fault_t:
                current_deg = min(max_deg, current_deg + (max_deg / (timesteps - start_fault_t)))
            
            # تشغيل الماكينات الخمس
            m_step_data = []
            for m in self.factory.machines:
                if m.machine_id == fault_machine:
                    m.degradation_level = current_deg
                else:
                    m.degradation_level = 0.0
                
                rec = m.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES)
                # تعديل السرعة والقدرة إن كان خفض الذروة مفعلاً
                rec["power_kw"] = round(rec["power_kw"] * (speed_mod ** 2), 3)
                rec["timestep"] = t
                rec["eci"] = calculate_eci(rec["power_kw"], rec["machine_id"], prod_key, rec["speed_rpm"])
                m_step_data.append(rec)
                factory_records.append(rec)
            
            # 3. تغذية مسار الذكاء الاصطناعي الحقيقي بالبيانات
            step_df = pd.DataFrame(m_step_data)
            step_df["ai_score"] = ai_model.predict_anomaly_score(step_df)
            
            fault_m_row = step_df[step_df["machine_id"] == fault_machine].iloc[0]
            p_info = processor.update(fault_m_row["ai_score"], threshold=0.5)
            
            hi_info = calculate_health_index_and_evidence(
                anomaly_score=fault_m_row["ai_score"],
                persistence_ratio=p_info["persistence_ratio"],
                eci=fault_m_row["eci"],
                temp_c=fault_m_row["temperature_c"],
                vib_rms=fault_m_row["vibration_rms"],
                prev_hi=prev_hi
            )
            current_hi = hi_info["health_index"]
            prev_hi = current_hi
            
            # 4. منطق اتخاذ القرار وفق سياسة الصيانة
            trigger_repair = False
            duration = 0
            
            if self.policy_type == "CORRECTIVE":
                # انتظار الانهيار الحرج
                if current_deg >= 0.75:
                    trigger_repair = True
                    duration = 60
            elif self.policy_type == "PREVENTIVE":
                # صيانة دورية ثابتة
                if t > 0 and (t % 160 == 0):
                    trigger_repair = True
                    duration = 25
            elif "PREDICTIVE" in self.policy_type:
                # صيانة تنبؤية معتمدة على مؤشر الصحة الحقيقي المؤكد
                if current_hi <= config.HI_THRESHOLDS["MONITOR"] and p_info["is_confirmed_anomaly"]:
                    trigger_repair = True
                    duration = 15
            
            if trigger_repair:
                is_repairing = True
                repair_timer = duration
                maintenance_events += 1
                downtime_minutes += 1.0
            else:
                # حساب الوحدات المنتجة للخط المتزامن
                base_cycle = config.PRODUCTS[prod_key]["base_cycle_time"] / speed_mod
                units_min = int(60.0 / (base_cycle * (1.0 + 0.1 * current_deg)))
                defect_rate = 0.005 + (0.04 * current_deg)
                good_min = int(units_min * (1.0 - defect_rate))
                
                total_units += units_min
                good_units += good_min
                
        # 5. حساب المؤشرات الإجمالية للمصنع ككل (Factory-Level KPIs)
        res_df = pd.DataFrame(factory_records)
        agg_power = get_factory_aggregated_power(res_df)
        total_energy_kwh = float(np.sum(agg_power) * (config.TIME_STEP_MINUTES / 60.0))
        peak_demand_kw = float(np.max(agg_power))
        
        operating_time_min = timesteps - downtime_minutes
        availability = operating_time_min / timesteps
        ideal_cycle = config.PRODUCTS[product_schedule[0]]["base_cycle_time"]
        performance = ((ideal_cycle * total_units) / (operating_time_min * 60.0)) if operating_time_min > 0 else 0.0
        quality = (good_units / total_units) if total_units > 0 else 0.0
        oee = availability * performance * quality * 100.0
        
        fin_impact = calculate_financial_and_esg_impact(total_energy_kwh, downtime_minutes, good_units)
        
        return {
            "policy": self.policy_type if not self.enable_peak_shaving else "PREDICTIVE_PEAK_SHAVING",
            "downtime_min": downtime_minutes,
            "events": maintenance_events,
            "oee_pct": round(oee, 2),
            "good_units": good_units,
            "total_energy_kwh": round(total_energy_kwh, 2),
            "peak_demand_kw": round(peak_demand_kw, 2),
            "energy_per_unit_wh": fin_impact["energy_per_unit_wh"],
            "total_cost_usd": fin_impact["energy_cost_usd"],
            "carbon_kg": fin_impact["carbon_kg"],
            "telemetry_df": res_df
        }