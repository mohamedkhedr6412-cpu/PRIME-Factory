"""
PRIME-Factory Master Configuration File v6.2
"""

# ==============================================================================
# 1. Simulation Run Settings & Time Horizons
# ==============================================================================
TIME_STEP_MINUTES = 1.0
SHIFT_HOURS = 8
TOTAL_TIMESTEPS = int(SHIFT_HOURS * 60)
RANDOM_SEED = 42
RANDOM_SEEDS = [42, 101, 202]

# ==============================================================================
# 2. Financial & ESG Operational Assumptions
# ==============================================================================
ELECTRICITY_TARIFF_PER_KWH = 0.15
DOWNTIME_COST_PER_HOUR = 350.0
CARBON_EMISSION_FACTOR = 0.45
MAINTENANCE_COST_BASE = 250.0

# ==============================================================================
# 3. Power Quality & Grid Parameters
# ==============================================================================
PF_TARGET = 0.90
PF_ALERT_THRESHOLD = 0.85
PF_PENALTY_MULTIPLIER = 1.2

# ==============================================================================
# 4. Calibrated Physical Assets & Bearing Multipliers
# ==============================================================================
BEARING_MULTIPLIERS = {
    "BPFO": 3.037,
    "BPFI": 4.963,
    "BSF": 3.911
}

MACHINES = {
    "M1": {"name": "Conveyor", "type": "Transport", "has_vibration": False, "nominal_kw": 5.0},
    "M2": {"name": "Filler", "type": "Rotating/Filling", "has_vibration": False, "nominal_kw": 6.5},
    "M3": {"name": "Sealer", "type": "Thermal/Mechanical", "has_vibration": True, "nominal_kw": 6.0},
    "M4": {"name": "Labeler", "type": "High-Speed", "has_vibration": True, "nominal_kw": 4.5},
    "M5": {"name": "Packaging", "type": "Integrated Drive", "has_vibration": True, "nominal_kw": 7.0}
}

# ==============================================================================
# 5. Multi-Product Operating Contexts
# ==============================================================================
PRODUCTS = {
    "Product_A": {
        "name": "Product A (Light)",
        "speed_factor": 0.8,
        "load_factor": 0.7,
        "base_cycle_time": 1.2,
        "nominal_power_mult": 0.75
    },
    "Product_B": {
        "name": "Product B (Medium)",
        "speed_factor": 1.0,
        "load_factor": 1.0,
        "base_cycle_time": 1.5,
        "nominal_power_mult": 1.00
    },
    "Product_C": {
        "name": "Product C (Heavy)",
        "speed_factor": 1.2,
        "load_factor": 1.3,
        "base_cycle_time": 2.0,
        "nominal_power_mult": 1.30
    }
}

# ==============================================================================
# 6. Machine States & Decision Thresholds
# ==============================================================================
STATE_NORMAL = "NORMAL"
STATE_DEGRADING = "DEGRADING"
STATE_WARNING = "WARNING"
STATE_PREDICTIVE_ALERT = "PREDICTIVE_ALERT"
STATE_CRITICAL = "CRITICAL"
STATE_FAILED = "FAILED"
STATE_MAINTENANCE = "MAINTENANCE"
STATE_RECOVERY = "RECOVERY"

PERSISTENCE_WINDOW = 5
PERSISTENCE_THRESHOLD = 0.40
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 10.0
}

PREDICTIVE_ALERT_HI_THRESHOLD = 75.0

HI_WEIGHTS = {
    "alpha": 0.30,
    "beta": 0.25,
    "gamma": 0.25,
    "delta": 0.20
}

# ==============================================================================
# 7. Maintenance & Recovery Parameters
# ==============================================================================
MAINTENANCE_DURATION_MINUTES = 10
RECOVERY_DURATION_MINUTES = 15
RECOVERY_RATE = 0.02
REPAIR_EFFECTIVENESS = 0.85

# ==============================================================================
# 8. PdM Trigger Configuration
# ==============================================================================
PDM_TRIGGER_HI = 75.0
PDM_TRIGGER_RUL = 50.0
PDM_TRIGGER_DEGRADATION = 0.45
PDM_REQUIRE_CONFIRMED_ANOMALY = False
PDM_REQUIRE_PERSISTENCE = True
PDM_MIN_LEAD_TIME_MIN = 10.0

# ==============================================================================
# 9. Decision Engine Thresholds
# ==============================================================================
DECISION_CONFIG = {
    "hi_healthy_threshold": 70.0,
    "hi_warning_threshold": 50.0,
    "hi_critical_threshold": 30.0,
    "hi_failure_threshold": 10.0,
    "rul_alert_threshold": 50.0,
    "persistence_confirm_threshold": 0.40,
    "persistence_window": 5,
    "eci_deviation_threshold": 0.15,
    "hysteresis_count": 3,
}

# ==============================================================================
# 10. Cost Parameters
# ==============================================================================
COST_PARAMETERS = {
    "maintenance_base_cost": 250.0,
    "maintenance_hourly_rate": 150.0,
    "downtime_cost_per_hour": 350.0,
    "energy_cost_per_kwh": 0.15,
    "carbon_cost_per_kg": 0.05,
    "pf_penalty_per_point": 50.0,
}

# ==============================================================================
# 11. Peak Shaving Configuration
# ==============================================================================
PEAK_SHAVING_START = 240
PEAK_SHAVING_END = 360
PEAK_SHAVING_DERATE = 0.90

# ==============================================================================
# 12. Benchmark Configuration (FINAL - guaranteed failure for CORRECTIVE)
# ==============================================================================
BENCHMARK_CONFIG = {
    "fault_machine": "M3",
    "fault_type": "Bearing Wear",
    "fault_start": 100,
    "max_degradation": 0.95,   # قيمة كافية لإحداث فشل في CORRECTIVE
    "seed": 42,
    "product_schedule": ["Product_B"] * TOTAL_TIMESTEPS,
}

# ==============================================================================
# 13. Canonical Telemetry Schema
# ==============================================================================
CANONICAL_TELEMETRY_COLS = [
    "machine_id", "timestep", "product", "speed_rpm", "load_factor",
    "vibration_rms", "temperature_c", "current_a", "power_kw",
    "power_factor", "degradation", "health_index", "state", "eci",
    "expected_power_kw"
]

# ==============================================================================
# 14. Bottleneck Production Parameters
# ==============================================================================
PRODUCTION_BOTTLENECK_ENABLED = True
PRODUCTION_USE_MULTIPRODUCT_CYCLE = True