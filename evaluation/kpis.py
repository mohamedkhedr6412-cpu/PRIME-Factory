"""
PRIME-Factory KPI Evaluation Engine v4.2
Calculates multi-product weighted OEE, production availability, performance efficiency,
and quality yield as the single source of truth across all views (P0-03, P1-07).
"""

import config

def calculate_oee_multiproduct(
    planned_time_min: float,
    operating_time_min: float,
    product_schedule: list,
    total_units: int,
    good_units: int
) -> dict:
    """
    Computes overall equipment effectiveness (OEE = Availability * Performance * Quality)
    weighted by the product mix ideal cycle times.
    """
    # 1. Availability Ratio
    availability = (operating_time_min / planned_time_min) if planned_time_min > 0 else 0.0
    availability = min(1.0, max(0.0, availability))

    # 2. Performance Ratio (Weighted Ideal Cycle Time)
    cycle_times = [config.PRODUCTS[p]["base_cycle_time"] for p in product_schedule]
    weighted_ideal_cycle_sec = sum(cycle_times) / len(cycle_times) if len(cycle_times) > 0 else 1.5
    operating_time_sec = operating_time_min * 60.0
    
    if operating_time_sec > 0:
        performance = (weighted_ideal_cycle_sec * total_units) / operating_time_sec
    else:
        performance = 0.0
    performance = min(1.0, max(0.0, performance))

    # 3. Quality Ratio
    quality = (good_units / total_units) if total_units > 0 else 0.0
    quality = min(1.0, max(0.0, quality))

    # 4. Composite OEE
    oee = availability * performance * quality * 100.0

    return {
        "availability_pct": round(float(availability * 100.0), 2),
        "performance_pct": round(float(performance * 100.0), 2),
        "quality_pct": round(float(quality * 100.0), 2),
        "oee_pct": round(float(oee), 2)
    }