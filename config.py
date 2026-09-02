"""
PRIME-Factory Master Configuration File v6.0
Centralized configuration, parameter taxonomy classification, calibrated physical constants,
financial inputs, and isolated RNG seeds (Section 5 & 6).
"""

# ==============================================================================
# 1. Simulation Run Settings & Time Horizons (Simulation-Control Parameters)
# ==============================================================================
TIME_STEP_MINUTES = 1.0
SHIFT_HOURS = 8
TOTAL_TIMESTEPS = int(SHIFT_HOURS * 60)  # 480 observation points
RANDOM_SEED = 42
RANDOM_SEEDS = [42, 101, 202]  # Multi-seed stochastic validation list

# ==============================================================================
# 2. Financial & ESG Operational Assumptions (Engineering Assumptions)
# ==============================================================================
ELECTRICITY_TARIFF_PER_KWH = 0.15       # USD per kWh (Standard industrial base tariff)
DOWNTIME_COST_PER_HOUR = 350.0          # USD per hour of unplanned stoppage
CARBON_EMISSION_FACTOR = 0.45           # kg CO2 per kWh (Grid emissions factor)

# ==============================================================================
# 3. Power Quality & Grid Parameters (Engineering Assumptions)
# ==============================================================================
PF_TARGET = 0.90                        # Utility penalty threshold
PF_ALERT_THRESHOLD = 0.85               # Early electrical warning threshold

# ==============================================================================
# 4. Physical Assets & Bearing Multipliers (Literature-Derived: Bruinsma et al., 2024)
# ==============================================================================
BEARING_MULTIPLIERS = {
    "BPFO": 3.037,  # Ball Pass Frequency Outer Race
    "BPFI": 4.963,  # Ball Pass Frequency Inner Race
    "BSF": 3.911    # Ball Spin Frequency
}

MACHINES = {
    "M1": {"name": "Conveyor",  "type": "Transport",          "has_vibration": False, "nominal_kw": 5.0},
    "M2": {"name": "Filler",    "type": "Rotating/Filling",   "has_vibration": False, "nominal_kw": 6.5},
    "M3": {"name": "Sealer",    "type": "Thermal/Mechanical", "has_vibration": True,  "nominal_kw": 6.0},
    "M4": {"name": "Labeler",   "type": "High-Speed",         "has_vibration": True,  "nominal_kw": 4.5},
    "M5": {"name": "Packaging", "type": "Integrated Drive",   "has_vibration": True,  "nominal_kw": 7.0}
}

# ==============================================================================
# 5. Multi-Product Operating Contexts (Simulation Assumptions - Section 5)
# ==============================================================================
PRODUCTS = {
    "Product_A": {
        "name": "Product A (Light)",
        "speed_factor": 0.8,
        "load_factor": 0.7,
        "base_cycle_time": 1.2,  # seconds / unit
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
# 6. Machine States & Decision Thresholds (Section 6)
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
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 10.0
}

# Normalized Health Indicator Penalty Weights (Section 9: Sum = 1.0)
HI_WEIGHTS = {
    "alpha": 0.30,  # AI Anomaly Score
    "beta": 0.25,   # Persistence Filter Ratio
    "gamma": 0.25,  # Context-Aware ECI Deviation
    "delta": 0.20   # Physical Thermal & Vibration Penalty
}

# ==============================================================================
# 7. Maintenance & Recovery Parameters (Section 16) - NEW
# ==============================================================================
MAINTENANCE_DURATION_MINUTES = 15
RECOVERY_DURATION_MINUTES = 15
REPAIR_EFFECTIVENESS = 0.90  # 90% recovery

# ==============================================================================
# 8. Decision Engine Thresholds (Section 15) - NEW
# ==============================================================================
DECISION_CONFIG = {
    "hi_healthy_threshold": 70.0,
    "hi_warning_threshold": 50.0,
    "hi_critical_threshold": 30.0,
    "hi_failure_threshold": 10.0,
    "rul_alert_threshold": 30.0,  # minutes
    "persistence_confirm_threshold": 0.8,
    "persistence_window": 5,
    "eci_deviation_threshold": 0.15,
    "hysteresis_count": 3,  # Number of samples required for state change
}

# ==============================================================================
# 9. Cost Parameters (Section 17) - NEW
# ==============================================================================
COST_PARAMETERS = {
    "maintenance_base_cost": 1000.0,  # USD
    "maintenance_hourly_rate": 150.0,  # USD/hour
    "downtime_cost_per_hour": 350.0,  # USD/hour
    "energy_cost_per_kwh": 0.15,  # USD
    "carbon_cost_per_kg": 0.05,  # USD per kg CO2
    "pf_penalty_per_point": 50.0,  # USD per 0.01 below target
}

# ==============================================================================
# 10. Benchmark Configuration (Section 18) - NEW
# ==============================================================================
BENCHMARK_CONFIG = {
    "fault_machine": "M3",
    "fault_type": "bearing_wear",
    "fault_start": 60,  # minutes
    "max_degradation": 0.85,
    "seed": 42,
    "product_schedule": ["Product_B"] * TOTAL_TIMESTEPS,
    "policy_comparison": [
        {"name": "Corrective", "predictive": False, "peak_shaving": False},
        {"name": "Predictive", "predictive": True, "peak_shaving": False},
        {"name": "Predictive+PeakShaving", "predictive": True, "peak_shaving": True},
    ]
}

# ==============================================================================
# 11. Evidence & Logging (Section 14) - NEW
# ==============================================================================
EVIDENCE_CONFIG = {
    "max_evidence_history": 1000,
    "export_format": "json",
    "include_raw_sensors": True,
    "include_context": True,
}

# ==============================================================================
# 12. Standard Benchmark Scenario Configuration (Section 18) - NEW
# ==============================================================================
BENCHMARK_SCENARIO = {
    "fault_machine": "M3",
    "fault_start": 60,
    "max_degradation": 0.85,
    "seed": 42,
    "product_schedule": ["Product_B"] * TOTAL_TIMESTEPS
}