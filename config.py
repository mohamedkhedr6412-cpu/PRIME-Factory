"""
PRIME-Factory Master Configuration File v4.1
Centralized configuration, calibrated physical constants, financial inputs, and RNG seeds.
"""

# Simulation Run Settings & Time Horizons
TIME_STEP_MINUTES = 1.0
SHIFT_HOURS = 8
TOTAL_TIMESTEPS = int(SHIFT_HOURS * 60)  # 480 observation points
RANDOM_SEED = 42
RANDOM_SEEDS = [42, 101, 202]  # For multi-seed stochastic validation

# Financial & ESG Operational Assumptions
ELECTRICITY_TARIFF_PER_KWH = 0.15       # USD per kWh
DOWNTIME_COST_PER_HOUR = 350.0          # USD per hour of unplanned line stoppage
CARBON_EMISSION_FACTOR = 0.45           # kg CO2 per kWh

# Power Quality & Grid Parameters
PF_TARGET = 0.90                        # Utility penalty threshold
PF_ALERT_THRESHOLD = 0.85               # Early electrical warning threshold

# Physical Asset Specifications & Bearing Multipliers (Bruinsma et al., 2024)
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

# Multi-Product Operating Contexts
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

# Machine State Machine Identifiers
STATE_NORMAL = "NORMAL"
STATE_DEGRADING = "DEGRADING"
STATE_WARNING = "WARNING"
STATE_PREDICTIVE_ALERT = "PREDICTIVE_ALERT"
STATE_CRITICAL = "CRITICAL"
STATE_FAILED = "FAILED"
STATE_MAINTENANCE = "MAINTENANCE"
STATE_RECOVERY = "RECOVERY"

# Anomaly Detection, Persistence & Decision Thresholds
PERSISTENCE_WINDOW = 5
HEALTH_INDEX_MAX = 100.0
HEALTH_INDEX_MIN = 0.0

HI_THRESHOLDS = {
    "HEALTHY": 70.0,
    "MONITOR": 50.0,
    "DEGRADED": 30.0,
    "CRITICAL": 10.0
}

# Normalized Health Indicator Penalty Weights (Sum = 1.0)
HI_WEIGHTS = {
    "alpha": 0.30,  # AI Anomaly Score
    "beta": 0.25,   # Persistence Filter Ratio
    "gamma": 0.25,  # Context-Aware ECI Deviation
    "delta": 0.20   # Physical Thermal & Vibration Penalty
}

# Standard Benchmark Scenario Configuration (Decoupled & Isolated)
BENCHMARK_CONFIG = {
    "fault_machine": "M3",
    "fault_start": 60,
    "max_degradation": 0.85,
    "seed": 42,
    "product_schedule": ["Product_B"] * TOTAL_TIMESTEPS
}