"""
PRIME-Factory Simulation: Master Configuration File
Governed by PRIME-Factory Simulation Constitution v1.0
"""

# ==========================================
# 1. Simulation Time & Run Settings
# ==========================================
TIME_STEP_MINUTES = 1               # دقة المحاكاة: قراءة واحدة لكل دقيقة
SHIFT_HOURS = 8                     # مدة الوردية: 8 ساعات
TOTAL_TIMESTEPS = SHIFT_HOURS * 60  # 480 نقطة زمنية
RANDOM_SEED = 42                    # تثبيت بذرة العشوائية لضمان تكرار النتائج

# ==========================================
# 2. Machine Identities
# ==========================================
MACHINES = {
    "M1": {"name": "Conveyor", "type": "Transport", "has_vibration": False},
    "M2": {"name": "Filler", "type": "Rotating/Filling", "has_vibration": False},
    "M3": {"name": "Sealer", "type": "Thermal/Mechanical", "has_vibration": True},
    "M4": {"name": "Labeler", "type": "High-Speed", "has_vibration": True},
    "M5": {"name": "Packaging", "type": "Integrated Drive", "has_vibration": True}
}

# ==========================================
# 3. Multi-Product Operating Regimes
# ==========================================
PRODUCTS = {
    "Product_A": {
        "name": "Product A (Light)",
        "speed_factor": 0.8,
        "load_factor": 0.7,
        "base_cycle_time": 1.2,     # ثانية لكل وحدة
        "nominal_power_kw": 4.5
    },
    "Product_B": {
        "name": "Product B (Medium)",
        "speed_factor": 1.0,
        "load_factor": 1.0,
        "base_cycle_time": 1.5,
        "nominal_power_kw": 6.0
    },
    "Product_C": {
        "name": "Product C (Heavy)",
        "speed_factor": 1.2,
        "load_factor": 1.3,
        "base_cycle_time": 2.0,
        "nominal_power_kw": 8.5
    }
}

# ==========================================
# 4. Machine States
# ==========================================
STATE_NORMAL = "NORMAL"
STATE_DEGRADING = "DEGRADING"
STATE_WARNING = "WARNING"
STATE_CRITICAL = "CRITICAL"
STATE_FAILED = "FAILED"
STATE_MAINTENANCE = "MAINTENANCE"

# ==========================================
# 5. AI & Decision Parameters
# ==========================================
PERSISTENCE_WINDOW = 5              # عدد العينات الشاذة المتتالية لتأكيد الإنذار
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 0.0
}

HI_WEIGHTS = {
    "alpha": 0.35,  # وزن نتيجة كشف الشذوذ (Isolation Forest)
    "beta": 0.25,   # وزن مؤشر الاستمرارية (Persistence)
    "gamma": 0.25,  # وزن مؤشر انحراف الطاقة (ECI)
    "delta": 0.15   # وزن السياق التشغيلي والحراري
}
