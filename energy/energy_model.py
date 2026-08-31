"""
PRIME-Factory Energy Calculations
Computes cumulative energy consumption, peak demand, and energy per unit.
"""
import pandas as pd
import numpy as np

def calculate_total_energy_kwh(power_series_kw: pd.Series, dt_minutes: float = 1.0) -> float:
    """حساب إجمالي الطاقة المستهلكة بالكيلوواط ساعة (kWh): E = Sum(P * dt)"""
    return float(np.sum(power_series_kw) * (dt_minutes / 60.0))

def calculate_peak_demand_kw(power_series_kw: pd.Series) -> float:
    """حساب أقصى ذروة طلب للقدرة المسحوبة (P_peak)"""
    return float(np.max(power_series_kw))

def calculate_energy_per_unit(total_energy_kwh: float, good_units: int) -> float:
    """حساب مؤشر كفاءة الطاقة لكل وحدة مقبولة تم إنتاجها (kWh/unit)"""
    if good_units <= 0:
        return 0.0
    return total_energy_kwh / good_units
