"""
PRIME-Factory Energy & Sustainability Evaluation Engine
Computes factory-level aggregated power, peak demand, energy costs, and CO2 emissions.
"""
import pandas as pd
import numpy as np
import config

def get_factory_aggregated_power(telemetry_df: pd.DataFrame) -> pd.Series:
    """
    حساب منحنى القدرة الكلية المستهلكة للمصنع ككل لكل دقيقة:
    P_factory(t) = Sum_{m=1..5} P_m(t)
    """
    return telemetry_df.groupby("timestep")["power_kw"].sum()

def calculate_total_energy_kwh(telemetry_df: pd.DataFrame, dt_minutes: float = 1.0) -> float:
    """حساب إجمالي الطاقة المستهلكة للمصنع بالكامل بالكيلوواط ساعة (kWh)"""
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.sum(factory_power) * (dt_minutes / 60.0))

def calculate_peak_demand_kw(telemetry_df: pd.DataFrame) -> float:
    """
    حساب أقصى ذروة طلب مجمعة للمصنع بالكامل:
    Peak_Demand = max_t ( P_factory(t) )
    """
    factory_power = get_factory_aggregated_power(telemetry_df)
    return float(np.max(factory_power))

def calculate_financial_and_esg_impact(total_energy_kwh: float, downtime_minutes: float, good_units: int) -> dict:
    """
    تحويل المؤشرات الهندسية إلى أرقام مالية واستدامة بيئية (ROI & ESG)
    """
    energy_cost = total_energy_kwh * config.ELECTRICITY_TARIFF_PER_KWH
    downtime_cost = (downtime_minutes / 60.0) * config.DOWNTIME_COST_PER_HOUR
    total_cost = energy_cost + downtime_cost
    carbon_emissions_kg = total_energy_kwh * config.CARBON_EMISSION_FACTOR
    energy_per_unit_wh = (total_energy_kwh / good_units * 1000.0) if good_units > 0 else 0.0

    return {
        "total_energy_kwh": round(total_energy_kwh, 2),
        "peak_demand_kw": 0.0, # يتم إسناده منفصلاً
        "energy_cost_usd": round(total_cost, 2),
        "downtime_cost_usd": round(downtime_cost, 2),
        "carbon_kg": round(carbon_emissions_kg, 2),
        "energy_per_unit_wh": round(energy_per_unit_wh, 3)
    }
