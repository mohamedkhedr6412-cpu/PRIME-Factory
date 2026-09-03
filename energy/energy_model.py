"""
PRIME-Factory Energy & Sustainability Evaluation Engine v6.2
Calculates factory-level power demand, electricity costs, downtime stoppage costs,
power factor penalties, and carbon emissions with isolated financial keys (Section 10 & 17).
Integrated with decision engine and evidence tracking.
"""

import pandas as pd
import numpy as np
import config
from typing import Dict, Any, Optional


def get_factory_aggregated_power(telemetry_df: pd.DataFrame) -> pd.Series:
    """Aggregates active power demand (kW) across all 5 machines per timestep."""
    return telemetry_df.groupby("timestep")["power_kw"].sum()


def calculate_total_energy_kwh(telemetry_df: pd.DataFrame, dt_minutes: float = 1.0) -> float:
    """Computes total active energy consumption in kWh."""
    if telemetry_df.empty:
        return 0.0
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.sum(factory_power) * (dt_minutes / 60.0))


def calculate_peak_demand_kw(telemetry_df: pd.DataFrame) -> float:
    """Identifies the peak active electrical demand in kW."""
    if telemetry_df.empty:
        return 0.0
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.max(factory_power))


def calculate_financial_and_esg_impact(
    total_energy_kwh: float,
    downtime_minutes: float,
    good_units: int,
    avg_pf: float = 0.92,
    maintenance_events: int = 0
) -> Dict[str, float]:
    """
    Computes audited financial KPIs and ESG metrics with strict parameter labeling (Section 17).
    Total Operational Cost = Energy Cost + Downtime Cost + PF Penalty + Maintenance Cost.
    """
    energy_cost = total_energy_kwh * config.ELECTRICITY_TARIFF_PER_KWH

    # Downtime cost (converted from minutes to hours)
    downtime_cost = (downtime_minutes / 60.0) * config.DOWNTIME_COST_PER_HOUR

    # FIXED: Unified PF Penalty Calculation
    # Single source of truth for PF penalty
    if avg_pf < config.PF_TARGET:
        # Penalty increases as PF drops below target
        pf_penalty = energy_cost * max(0.0, (config.PF_TARGET - avg_pf) * config.PF_PENALTY_MULTIPLIER)
    else:
        pf_penalty = 0.0

    pf_penalty = round(pf_penalty, 2)

    # Maintenance cost
    maintenance_cost = maintenance_events * config.MAINTENANCE_COST_BASE

    total_operational_cost = energy_cost + downtime_cost + pf_penalty + maintenance_cost
    carbon_emissions_kg = total_energy_kwh * config.CARBON_EMISSION_FACTOR

    # Energy per good unit calculation strictly tied to actual accepted production
    energy_per_unit_wh = (total_energy_kwh / good_units * 1000.0) if good_units > 0 else 0.0

    return {
        "total_energy_kwh": round(float(total_energy_kwh), 2),
        "energy_cost_usd": round(float(energy_cost), 2),
        "downtime_cost_usd": round(float(downtime_cost), 2),
        "pf_penalty_usd": round(float(pf_penalty), 2),
        "maintenance_cost_usd": round(float(maintenance_cost), 2),
        "total_operational_cost_usd": round(float(total_operational_cost), 2),
        "carbon_kg": round(float(carbon_emissions_kg), 2),
        "energy_per_unit_wh": round(float(energy_per_unit_wh), 3)
    }


def calculate_financial_with_evidence(
    total_energy_kwh: float,
    downtime_minutes: float,
    good_units: int,
    avg_pf: float = 0.92,
    maintenance_events: int = 0
) -> Dict[str, Any]:
    """
    Calculates financial impact with detailed evidence for decision tracing.
    """
    base_costs = calculate_financial_and_esg_impact(
        total_energy_kwh, downtime_minutes, good_units, avg_pf, maintenance_events
    )

    # Calculate per-unit costs
    cost_per_unit = base_costs["total_operational_cost_usd"] / good_units if good_units > 0 else 0.0

    # Calculate carbon per unit
    carbon_per_unit = base_costs["carbon_kg"] / good_units if good_units > 0 else 0.0

    return {
        **base_costs,
        "cost_per_good_unit_usd": round(cost_per_unit, 4),
        "carbon_per_good_unit_kg": round(carbon_per_unit, 4),
    }


def calculate_factory_efficiency_metrics(
    telemetry_df: pd.DataFrame,
    total_energy_kwh: float,
    good_units: int
) -> Dict[str, float]:
    """
    Calculates factory-level efficiency metrics.
    """
    if telemetry_df.empty or good_units == 0:
        return {
            "overall_efficiency": 0.0,
            "energy_productivity": 0.0,
            "power_efficiency": 0.0
        }

    # Overall efficiency: units per kWh
    overall_efficiency = good_units / max(total_energy_kwh, 0.001)

    # Energy productivity: kWh per 1000 units
    energy_productivity = (total_energy_kwh / good_units) * 1000

    # Power efficiency: average power per unit
    avg_power = telemetry_df["power_kw"].mean() if "power_kw" in telemetry_df.columns else 0
    power_efficiency = avg_power / max(good_units, 1)

    return {
        "overall_efficiency": round(overall_efficiency, 3),
        "energy_productivity": round(energy_productivity, 2),
        "power_efficiency": round(power_efficiency, 4)
    }