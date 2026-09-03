"""
PRIME-Factory KPI Evaluation Engine v6.2
Single source of truth for OEE and production KPIs.
"""

import config
from typing import List, Dict


def calculate_oee_multiproduct(
    planned_time_min: float,
    operating_time_min: float,
    product_schedule: List[str],
    total_units: int,
    good_units: int,
    product_units: Dict[str, int] = None
) -> Dict:
    """
    Computes overall equipment effectiveness (OEE = Availability * Performance * Quality)

    FIXED: Performance is now calculated based on actual production mix,
    not just schedule duration.
    """
    # 1. Availability Ratio
    availability = (operating_time_min / planned_time_min) if planned_time_min > 0 else 0.0
    availability = min(1.0, max(0.0, availability))

    # 2. Performance Ratio
    # FIXED: Use actual production mix for ideal cycle time
    if product_units and total_units > 0:
        # Calculate weighted ideal cycle time based on actual units produced
        total_ideal_time = 0.0
        for product, units in product_units.items():
            if product in config.PRODUCTS:
                total_ideal_time += units * config.PRODUCTS[product]["base_cycle_time"]
        weighted_ideal_cycle_sec = total_ideal_time / total_units if total_units > 0 else 1.5
    else:
        # Fallback: use schedule-based weighting
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
        "oee_pct": round(float(oee), 2),
        "weighted_ideal_cycle_sec": round(weighted_ideal_cycle_sec, 3)
    }


def calculate_throughput(
    good_units: int,
    operating_time_min: float
) -> float:
    """Calculate throughput in units per hour."""
    if operating_time_min <= 0:
        return 0.0
    return round(float(good_units / (operating_time_min / 60.0)), 2)


def calculate_factory_efficiency(
    total_energy_kwh: float,
    good_units: int
) -> Dict:
    """Calculate energy efficiency metrics."""
    if good_units <= 0:
        return {
            "energy_per_unit_wh": 0.0,
            "energy_productivity": 0.0
        }

    energy_per_unit_wh = (total_energy_kwh * 1000) / good_units
    energy_productivity = good_units / max(total_energy_kwh, 0.001)

    return {
        "energy_per_unit_wh": round(energy_per_unit_wh, 3),
        "energy_productivity": round(energy_productivity, 3)
    }


def calculate_oee_with_details(
    planned_time_min: float,
    operating_time_min: float,
    product_schedule: List[str],
    total_units: int,
    good_units: int,
    product_units: Dict[str, int] = None,
    downtime_minutes: float = 0.0
) -> Dict:
    """
    Calculate OEE with detailed breakdown including lost time analysis.
    """
    # Availability
    availability = (operating_time_min / planned_time_min) if planned_time_min > 0 else 0.0
    availability = min(1.0, max(0.0, availability))

    # Performance
    if product_units and total_units > 0:
        total_ideal_time = 0.0
        for product, units in product_units.items():
            if product in config.PRODUCTS:
                total_ideal_time += units * config.PRODUCTS[product]["base_cycle_time"]
        weighted_ideal_cycle_sec = total_ideal_time / total_units if total_units > 0 else 1.5
    else:
        cycle_times = [config.PRODUCTS[p]["base_cycle_time"] for p in product_schedule]
        weighted_ideal_cycle_sec = sum(cycle_times) / len(cycle_times) if len(cycle_times) > 0 else 1.5

    operating_time_sec = operating_time_min * 60.0
    if operating_time_sec > 0:
        performance = (weighted_ideal_cycle_sec * total_units) / operating_time_sec
    else:
        performance = 0.0
    performance = min(1.0, max(0.0, performance))

    # Quality
    quality = (good_units / total_units) if total_units > 0 else 0.0
    quality = min(1.0, max(0.0, quality))

    # OEE
    oee = availability * performance * quality * 100.0

    # Lost time analysis
    planned_time_hours = planned_time_min / 60.0
    operating_time_hours = operating_time_min / 60.0
    downtime_hours = downtime_minutes / 60.0

    return {
        "oee_pct": round(float(oee), 2),
        "availability_pct": round(float(availability * 100.0), 2),
        "performance_pct": round(float(performance * 100.0), 2),
        "quality_pct": round(float(quality * 100.0), 2),
        "weighted_ideal_cycle_sec": round(weighted_ideal_cycle_sec, 3),
        "planned_time_hours": round(planned_time_hours, 2),
        "operating_time_hours": round(operating_time_hours, 2),
        "downtime_hours": round(downtime_hours, 2),
        "lost_time_availability_hours": round(planned_time_hours - operating_time_hours, 2),
        "lost_time_performance_hours": round(
            operating_time_hours * (1 - performance), 2
        ) if operating_time_hours > 0 else 0.0,
        "lost_time_quality_hours": round(
            operating_time_hours * performance * (1 - quality), 2
        ) if operating_time_hours > 0 else 0.0
    }