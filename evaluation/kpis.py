"""
PRIME-Factory KPI Evaluation Engine
Computes OEE (Availability, Performance, Quality), Downtime, and Energy Efficiency.
"""
import numpy as np

def calculate_oee(planned_time_min: float, operating_time_min: float, ideal_cycle_sec: float, total_units: int, good_units: int) -> dict:
    """
    حساب مؤشر الفاعلية الشاملة للمعدات (OEE):
    OEE = Availability * Performance * Quality
    """
    # 1. التوافرية (Availability)
    availability = (operating_time_min / planned_time_min) if planned_time_min > 0 else 0.0
    availability = min(1.0, max(0.0, availability))

    # 2. الأداء (Performance)
    operating_time_sec = operating_time_min * 60.0
    performance = ((ideal_cycle_sec * total_units) / operating_time_sec) if operating_time_sec > 0 else 0.0
    performance = min(1.0, max(0.0, performance))

    # 3. الجودة (Quality)
    quality = (good_units / total_units) if total_units > 0 else 0.0
    quality = min(1.0, max(0.0, quality))

    # الحساب الإجمالي
    oee = availability * performance * quality

    return {
        "availability_pct": round(availability * 100.0, 2),
        "performance_pct": round(performance * 100.0, 2),
        "quality_pct": round(quality * 100.0, 2),
        "oee_pct": round(oee * 100.0, 2)
    }

def calculate_energy_kpi(total_kwh: float, good_units: int, peak_kw: float) -> dict:
    """حساب مؤشرات كفاءة الطاقة"""
    kwh_per_unit = (total_kwh / good_units) if good_units > 0 else 0.0
    return {
        "total_energy_kwh": round(total_kwh, 2),
        "peak_demand_kw": round(peak_kw, 2),
        "energy_per_unit_wh": round(kwh_per_unit * 1000.0, 3)
    }
