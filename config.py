"""
PRIME-Factory Simulation: Master Configuration File v2.0
Governed by PRIME-Factory Simulation Constitution & Master Plan v1.0
"""

# ==========================================
# 1. Simulation Time & Run Settings
# ==========================================
TIME_STEP_MINUTES = 1               # دقة المحاكاة: قراءة واحدة لكل دقيقة
SHIFT_HOURS = 8                     # مدة الوردية: 8 ساعات
TOTAL_TIMESTEPS = SHIFT_HOURS * 60  # 480 نقطة زمنية
RANDOM_SEED = 42                    # تثبيت بذرة العشوائية لضمان تكرار النتائج

# ==========================================
# 2. Financial & ESG Parameters (الأثر المالي والاستدامة)
# ==========================================
ELECTRICITY_TARIFF_PER_KWH = 0.15    # سعر الكيلوواط/ساعة بالدولار ($/kWh)
DOWNTIME_COST_PER_HOUR = 350.0       # تكلفة ساعة التوقف غير المخطط للمصنع ($/hr)
CARBON_EMISSION_FACTOR = 0.45        # انبعاثات الكربون (kg CO2 لكل kWh)

# ==========================================
# 3. Machine Identities & Physical Baselines
# ==========================================
MACHINES = {
    "M1": {"name": "Conveyor", "type": "Transport", "has_vibration": False, "nominal_kw": 5.0},
    "M2": {"name": "Filler", "type": "Rotating/Filling", "has_vibration": False, "nominal_kw": 6.5},
    "M3": {"name": "Sealer", "type": "Thermal/Mechanical", "has_vibration": True, "nominal_kw": 6.0},
    "M4": {"name": "Labeler", "type": "High-Speed", "has_vibration": True, "nominal_kw": 4.5},
    "M5": {"name": "Packaging", "type": "Integrated Drive", "has_vibration": True, "nominal_kw": 7.0}
}

# ==========================================
# 4. Multi-Product Operating Regimes (السياق التشغيلي)
# ==========================================
PRODUCTS = {
    "Product_A": {
        "name": "Product A (Light)",
        "speed_factor": 0.8,
        "load_factor": 0.7,
        "base_cycle_time": 1.2,     # ثانية لكل وحدة
        "line_power_factor": 0.75
    },
    "Product_B": {
        "name": "Product B (Medium)",
        "speed_factor": 1.0,
        "load_factor": 1.0,
        "base_cycle_time": 1.5,
        "line_power_factor": 1.00
    },
    "Product_C": {
        "name": "Product C (Heavy)",
        "speed_factor": 1.2,
        "load_factor": 1.3,
        "base_cycle_time": 2.0,
        "line_power_factor": 1.30
    }
}

# ==========================================
# 5. Machine States
# ==========================================
STATE_NORMAL = "NORMAL"
STATE_DEGRADING = "DEGRADING"
STATE_WARNING = "WARNING"
STATE_CRITICAL = "CRITICAL"
STATE_FAILED = "FAILED"
STATE_MAINTENANCE = "MAINTENANCE"

# ==========================================
# 6. AI, Persistence & Decision Parameters
# ==========================================
PERSISTENCE_WINDOW = 5              # عدد العينات لتأكيد الشذوذ
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 10.0
}

HI_WEIGHTS = {
    "alpha": 0.30,  # وزن نموذج كشف الشذوذ (Isolation Forest)
    "beta": 0.25,   # وزن مؤشر الاستمرارية (Persistence)
    "gamma": 0.25,  # وزن مؤشر انحراف الطاقة (ECI)
    "delta": 0.20   # وزن الاستجابة الحرارية والاهتزازية
}
