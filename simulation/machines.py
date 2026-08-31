"""
PRIME-Factory Machine Model v2.0
Defines the 5 core physical assets with distinct nominal ratings and electro-mechanical responses.
"""
import numpy as np
import config

class Machine:
    def __init__(self, machine_id: str, name: str, has_vibration: bool = False, nominal_kw: float = 5.0):
        self.machine_id = machine_id
        self.name = name
        self.has_vibration = has_vibration
        self.nominal_kw = nominal_kw
        self.state = config.STATE_NORMAL
        self.degradation_level = 0.0  # من 0.0 (سليم تمامًا) إلى 1.0 (عطل كامل)
        
        # خطوط الأساس الفيزيائية
        self.base_temp_c = 42.0
        self.base_vib_rms = 0.8 if has_vibration else 0.0
        self.voltage_v = 400.0
        self.current_temp = self.base_temp_c

    def step(self, product_key: str, dt_minutes: float = 1.0) -> dict:
        prod = config.PRODUCTS[product_key]
        
        # 1. تحديد السرعة والحمل الطبيعيين بناءً على قدرة الماكينة والمنتج
        speed_rpm = 1500.0 * prod["speed_factor"] * (1.0 - 0.05 * self.degradation_level)
        load_kw = self.nominal_kw * prod["load_factor"]
        
        # 2. تأثير التدهور الميكانيكي على زيادة الاحتكاك واستهلاك القدرة
        power_penalty = load_kw * (0.35 * self.degradation_level)
        actual_power_kw = load_kw + power_penalty + np.random.normal(0, 0.05)
        
        # 3. حساب معامل القدرة (PF) والتيار المسحوب
        pf = 0.88 - (0.08 * self.degradation_level)
        actual_current_a = (actual_power_kw * 1000) / (np.sqrt(3) * self.voltage_v * pf)
        
        # 4. محاكاة القصور الحراري (Thermal Lag)
        target_temp = self.base_temp_c + (28.0 * self.degradation_level) + (prod["load_factor"] * 4.0)
        thermal_tau = 15.0
        self.current_temp += (target_temp - self.current_temp) * (dt_minutes / thermal_tau) + np.random.normal(0, 0.1)
        
        # 5. محاكاة الاهتزازات الميكانيكية
        if self.has_vibration:
            vib_rms = self.base_vib_rms + (3.5 * (self.degradation_level ** 1.5)) + np.random.normal(0, 0.04)
        else:
            vib_rms = 0.0

        # 6. تحديث الحالة الهندسية
        if self.degradation_level >= 0.8:
            self.state = config.STATE_FAILED
        elif self.degradation_level >= 0.4:
            self.state = config.STATE_CRITICAL
        elif self.degradation_level >= 0.15:
            self.state = config.STATE_WARNING
        elif self.degradation_level > 0.0:
            self.state = config.STATE_DEGRADING
        else:
            self.state = config.STATE_NORMAL

        return {
            "machine_id": self.machine_id,
            "machine_name": self.name,
            "state": self.state,
            "product": product_key,
            "speed_rpm": round(speed_rpm, 2),
            "load_factor": prod["load_factor"],
            "vibration_rms": round(max(0.0, vib_rms), 3),
            "temperature_c": round(self.current_temp, 2),
            "current_a": round(actual_current_a, 2),
            "voltage_v": round(self.voltage_v, 1),
            "power_kw": round(max(0.0, actual_power_kw), 3),
            "pf": round(pf, 3),
            "degradation": round(self.degradation_level, 3)
        }
    