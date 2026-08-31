"""
PRIME-Factory Maintenance Policies Simulator
Simulates and benchmarks:
1. Corrective (Run-to-failure)
2. Preventive (Fixed time-based)
3. Predictive (PRIME HI-triggered condition-based)
"""
import numpy as np
import config

class PolicySimulator:
    def __init__(self, policy_type: str = "PREDICTIVE"):
        self.policy_type = policy_type.upper()
        self.downtime_minutes = 0.0
        self.maintenance_events = 0
        self.total_units_produced = 0
        self.good_units_produced = 0
        self.energy_consumed_kwh = 0.0
        self.is_under_repair = False
        self.repair_timer = 0

    def step(self, t: int, current_degradation: float, hi: float, base_power_kw: float, base_cycle_sec: float) -> dict:
        """محاكاة استجابة الصيانة لكل دقيقة زمنية"""
        dt_min = config.TIME_STEP_MINUTES
        effective_power = base_power_kw
        units_this_min = 0
        good_units_this_min = 0

        # في حال كانت الماكينة في حالة صيانة حاليًا
        if self.is_under_repair:
            self.repair_timer -= dt_min
            self.downtime_minutes += dt_min
            effective_power = 0.5  # استهلاك طاقة خامل أثناء الإصلاح
            
            if self.repair_timer <= 0:
                self.is_under_repair = False
                current_degradation = 0.0  # استعادة الماكينة لحالتها السليمة تمامًا

            self.energy_consumed_kwh += effective_power * (dt_min / 60.0)
            return {
                "in_maintenance": True,
                "current_degradation": current_degradation,
                "power_kw": effective_power,
                "units": 0,
                "good_units": 0
            }

        # منطق اتخاذ قرار الصيانة وفق كل سياسة
        trigger_repair = False
        repair_duration = 0

        if self.policy_type == "CORRECTIVE":
            # صيانة تصحيحية: العمل حتى الانهيار الكامل (Degradation >= 0.75)
            if current_degradation >= 0.75:
                trigger_repair = True
                repair_duration = 60  # توقف مفاجئ يستغرق 60 دقيقة للإصلاح

        elif self.policy_type == "PREVENTIVE":
            # صيانة وقائية: إجراء صيانة كل 160 دقيقة بغض النظر عن الحالة
            if t > 0 and (t % 160 == 0):
                trigger_repair = True
                repair_duration = 25  # صيانة مجدولة تستغرق 25 دقيقة

        elif self.policy_type == "PREDICTIVE":
            # صيانة تنبؤية: التدخل عند وصول مؤشر الصحة إلى مستوى التحذير والتدهور
            if hi <= config.HI_THRESHOLDS["MONITOR"]:
                trigger_repair = True
                repair_duration = 15  # تدخل مبكر سريع يستغرق 15 دقيقة فقط

        if trigger_repair:
            self.is_under_repair = True
            self.repair_timer = repair_duration
            self.maintenance_events += 1
            self.downtime_minutes += dt_min
            effective_power = 0.5
        else:
            # تشغيل طبيعي وإنتاج
            units_this_min = int((dt_min * 60.0) / (base_cycle_sec * (1.0 + 0.1 * current_degradation)))
            # انخفاض بسيط في جودة المنتجات مع زيادة التآكل
            defect_rate = 0.005 + (0.04 * current_degradation)
            good_units_this_min = int(units_this_min * (1.0 - defect_rate))

            self.total_units_produced += units_this_min
            self.good_units_produced += good_units_this_min

        self.energy_consumed_kwh += effective_power * (dt_min / 60.0)

        return {
            "in_maintenance": self.is_under_repair,
            "current_degradation": current_degradation,
            "power_kw": effective_power,
            "units": units_this_min,
            "good_units": good_units_this_min
        }
    