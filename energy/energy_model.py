"""
PRIME-Factory Energy & Sustainability Evaluation Engine v6.0
Calculates factory-level power demand, electricity costs, downtime stoppage costs,
power factor penalties, and carbon emissions with isolated financial keys (Section 10 & 17).
"""

import pandas as pd
import numpy as np
import config

def get_factory_aggregated_power(telemetry_df: pd.DataFrame) -> pd.Series:
    """Aggregates active power demand (kW) across all 5 machines per timestep."""
    return telemetry_df.groupby("timestep")["power_kw"].sum()

def calculate_total_energy_kwh(telemetry_df: pd.DataFrame, dt_minutes: float = 1.0) -> float:
    """Computes total active energy consumption in kWh."""
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.sum(factory_power) * (dt_minutes / 60.0))

def calculate_peak_demand_kw(telemetry_df: pd.DataFrame) -> float:
    """Identifies the peak active electrical demand in kW."""
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.max(factory_power))

def calculate_financial_and_esg_impact(
    total_energy_kwh: float, 
    downtime_minutes: float, 
    good_units: int, 
    avg_pf: float = 0.92
) -> dict:
    """
    Computes audited financial KPIs and ESG metrics with strict parameter labeling (Section 17).
    Total Operational Cost = Energy Cost + Downtime Cost + PF Penalty.
    """
    energy_cost = total_energy_kwh * config.ELECTRICITY_TARIFF_PER_KWH
    downtime_cost = (downtime_minutes / 60.0) * config.DOWNTIME_COST_PER_HOUR
    
    # Power Factor penalty calculation if average PF drops below target threshold
    pf_penalty = energy_cost * max(0.0, (config.PF_TARGET - avg_pf) * 1.2)
    
    total_operational_cost = energy_cost + downtime_cost + pf_penalty
    carbon_emissions_kg = total_energy_kwh * config.CARBON_EMISSION_FACTOR
    
    # Energy per good unit calculation strictly tied to actual accepted production
    energy_per_unit_wh = (total_energy_kwh / good_units * 1000.0) if good_units > 0 else 0.0

    return {
        "total_energy_kwh": round(float(total_energy_kwh), 2),
        "energy_cost_usd": round(float(energy_cost), 2),
        "downtime_cost_usd": round(float(downtime_cost), 2),
        "pf_penalty_usd": round(float(pf_penalty), 2),
        "total_operational_cost_usd": round(float(total_operational_cost), 2),
        "carbon_kg": round(float(carbon_emissions_kg), 2),
        "energy_per_unit_wh": round(float(energy_per_unit_wh), 3)
    }