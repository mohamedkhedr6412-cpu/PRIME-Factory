"""
PRIME-Factory Simulation: Master Configuration File v3.0 (Calibrated & Audited)
Governed by PRIME-Factory Scientific Perfection Plan v2.0
"""

# ==========================================
# 1. Simulation Run Settings & Seeds
# ==========================================
TIME_STEP_MINUTES = 1
SHIFT_HOURS = 8
TOTAL_TIMESTEPS = SHIFT_HOURS * 60  # 480 Points
RANDOM_SEED = 42
RANDOM_SEEDS = [42, 101, 202]       # Multi-seed validation list

# ==========================================
# 2. Scientific Benchmark Isolation Config (Fixed & Decoupled from UI)
# ==========================================
BENCHMARK_CONFIG = {
    "fault_machine": "M3",
    "fault_start": 60,
    "max_degradation": 0.85,         # Reaches critical failure (>= 0.75)
    "seed": 42,
    "product_schedule": ["Product_B"] * (SHIFT_HOURS * 60)
}

# ==========================================
# 3. Financial & ESG Parameters
# ==========================================
ELECTRICITY_TARIFF_PER_KWH = 0.15    # $/kWh
DOWNTIME_COST_PER_HOUR = 350.0       # $/hr
CARBON_EMISSION_FACTOR = 0.45        # kg CO2 per kWh

# ==========================================
# 4. Calibrated Physical Assets & Bearing Multipliers (Bruinsma et al., 2024)
# ==========================================
BEARING_MULTIPLIERS = {
    "BPFO": 3.037,  # Ball Pass Frequency Outer Race
    "BPFI": 4.963,  # Ball Pass Frequency Inner Race
    "BSF": 3.911    # Ball Spin Frequency
}

MACHINES = {
    "M1": {"name": "Conveyor", "type": "Transport", "has_vibration": False, "nominal_kw": 5.0},
    "M2": {"name": "Filler", "type": "Rotating/Filling", "has_vibration": False, "nominal_kw": 6.5},
    "M3": {"name": "Sealer", "type": "Thermal/Mechanical", "has_vibration": True, "nominal_kw": 6.0},
    "M4": {"name": "Labeler", "type": "High-Speed", "has_vibration": True, "nominal_kw": 4.5},
    "M5": {"name": "Packaging", "type": "Integrated Drive", "has_vibration": True, "nominal_kw": 7.0}
}

# ==========================================
# 5. Multi-Product Operating Contexts
# ==========================================
PRODUCTS = {
    "Product_A": {
        "name": "Product A (Light)",
        "speed_factor": 0.8,
        "load_factor": 0.7,
        "base_cycle_time": 1.2,     # Seconds / unit
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

# ==========================================
# 6. Machine States & Decision Thresholds
# ==========================================
STATE_NORMAL = "NORMAL"
STATE_DEGRADING = "DEGRADING"
STATE_WARNING = "WARNING"
STATE_CRITICAL = "CRITICAL"
STATE_FAILED = "FAILED"
STATE_MAINTENANCE = "MAINTENANCE"

PERSISTENCE_WINDOW = 5
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 10.0
}

HI_WEIGHTS = {
    "alpha": 0.30,  # AI Anomaly Contribution
    "beta": 0.25,   # Persistence Filter
    "gamma": 0.25,  # ECI Energy Deviation
    "delta": 0.20   # Physics (Thermal & Vibration)
}
