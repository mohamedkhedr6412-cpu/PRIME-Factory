"""
PRIME-Factory Demand Response & Peak Shaving Module v4.1
Applies dynamic speed derating to flexible VFD loads during grid peak tariff windows.
"""

def apply_peak_shaving(
    current_timestep: int, 
    peak_start: int = 240, 
    peak_end: int = 360, 
    derate_ratio: float = 0.90
) -> float:
    """
    Returns the motor speed modifier factor based on the electricity tariff schedule.
    Reduces commanded motor speed by 10% (derate_ratio = 0.90) strictly during the peak window.
    """
    if peak_start <= current_timestep < peak_end:
        return float(derate_ratio)
    return 1.0