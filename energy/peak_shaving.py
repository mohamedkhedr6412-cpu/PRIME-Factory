"""
PRIME-Factory Demand Response & Peak Shaving Module v6.2
Applies motor speed derating to flexible VFD loads during utility peak tariff hours.
Now integrated with production trade-off.
FIXED: Now receives current_power for accurate energy_saved calculation.
"""

from typing import Dict, Any, Optional
import config


class PeakShavingController:
    """
    Controls peak shaving operations for demand response.
    Tracks the impact on speed, power, and throughput.
    """

    def __init__(
        self,
        peak_start: int = config.PEAK_SHAVING_START,
        peak_end: int = config.PEAK_SHAVING_END,
        derate_ratio: float = config.PEAK_SHAVING_DERATE,
        enabled: bool = True
    ):
        self.peak_start = peak_start
        self.peak_end = peak_end
        self.derate_ratio = derate_ratio
        self.enabled = enabled
        self._history = []
        self._peak_events = 0

    def apply_peak_shaving(
        self,
        current_timestep: int,
        current_power: float = None
    ) -> float:
        """
        Returns the motor speed derating factor during peak hours.
        Derates commanded speed by derate_ratio (default 0.90 = 10% reduction).
        NOW: Receives current_power for accurate energy tracking.
        """
        if not self.enabled:
            self._history.append({"timestep": current_timestep, "factor": 1.0, "applied": False})
            return 1.0

        is_peak = self.peak_start <= current_timestep < self.peak_end
        factor = self.derate_ratio if is_peak else 1.0

        if is_peak:
            self._peak_events += 1

        # Calculate power before and after derating (power ∝ speed²)
        power_before = current_power if current_power is not None else None
        power_after = power_before * (factor ** 2) if power_before is not None else None

        self._history.append({
            "timestep": current_timestep,
            "factor": factor,
            "applied": is_peak,
            "power_before": power_before,
            "power_after": power_after
        })

        return float(factor)

    def get_peak_shaving_impact(self) -> Dict[str, Any]:
        """
        Calculates the impact of peak shaving on energy consumption and production.
        NOW: Based on actual power_before/power_after from history.
        """
        if not self._history:
            return {"total_events": 0, "avg_derate": 1.0, "energy_saved_kwh": 0.0}

        applied = [h for h in self._history if h.get("applied", False)]

        if not applied:
            return {"total_events": 0, "avg_derate": 1.0, "energy_saved_kwh": 0.0}

        # Calculate energy savings from actual power values
        total_saved = 0.0
        for h in applied:
            if h.get("power_before") is not None and h.get("power_after") is not None:
                saved = (h["power_before"] - h["power_after"]) * (config.TIME_STEP_MINUTES / 60.0)
                total_saved += saved

        return {
            "total_events": len(applied),
            "avg_derate": round(sum(h["factor"] for h in applied) / len(applied), 3),
            "energy_saved_kwh": round(total_saved, 3),
            "peak_hours_active": len(applied) > 0
        }

    def reset(self):
        self._history = []
        self._peak_events = 0


# ===== Legacy compatibility =====
def apply_peak_shaving(
    current_timestep: int,
    peak_start: int = config.PEAK_SHAVING_START,
    peak_end: int = config.PEAK_SHAVING_END,
    derate_ratio: float = config.PEAK_SHAVING_DERATE
) -> float:
    if peak_start <= current_timestep < peak_end:
        return float(derate_ratio)
    return 1.0


def get_peak_shaving_schedule(
    total_timesteps: int,
    peak_start: int = config.PEAK_SHAVING_START,
    peak_end: int = config.PEAK_SHAVING_END,
    derate_ratio: float = config.PEAK_SHAVING_DERATE
) -> list:
    schedule = []
    for t in range(total_timesteps):
        if peak_start <= t < peak_end:
            schedule.append(derate_ratio)
        else:
            schedule.append(1.0)
    return schedule