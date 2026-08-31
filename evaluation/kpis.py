"""
PRIME-Factory KPI Evaluation Engine v3.0
Fixes P1-1: Computes weighted ideal cycle time for dynamic multi-product schedules.
"""
import config

def calculate_oee_multiproduct(
    planned_time_min: float,
    operating_time_min: float,
    product_schedule: list,
    total_units: int,
    good_units: int
) -> dict:
    availability = (operating_time_min / planned_time_min) if planned_time_min > 0 else 0.0
    availability = min(1.0, max(0.0, availability))

    # حساب زمن الدورة المثالي الموزون لسياق المنتجات المشغلة
    cycle_times = [config.PRODUCTS[p]["base_cycle_time"] for p in product_schedule]
    weighted_ideal_cycle_sec = sum(cycle_times) / len(cycle_times) if len(cycle_times) > 0 else 1.5

    operating_time_sec = operating_time_min * 60.0
    performance = ((weighted_ideal_cycle_sec * total_units) / operating_time_sec) if operating_time_sec > 0 else 0.0
    performance = min(1.0, max(0.0, performance))

    quality = (good_units / total_units) if total_units > 0 else 0.0
    quality = min(1.0, max(0.0, quality))

    oee = availability * performance * quality * 100.0

    return {
        "availability_pct": round(availability * 100.0, 2),
        "performance_pct": round(performance * 100.0, 2),
        "quality_pct": round(quality * 100.0, 2),
        "oee_pct": round(oee, 2)
    }
