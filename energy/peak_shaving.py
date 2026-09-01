"""
PRIME-Factory Demand Response & Peak Shaving Module v4.2
Applies motor speed derating to flexible VFD loads during utility peak tariff hours (P1-06).
"""

def apply_peak_shaving(
    current_timestep: int, 
    peak_start: int = 240, 
    peak_end: int = 360, 
    derate_ratio: float = 0.90
) -> float:
    """
    Returns the motor speed derating factor during peak electricity tariff windows.
    Derates commanded speed by 10% (derate_ratio = 0.90) strictly between peak_start and peak_end.
    """
    if peak_start <= current_timestep < peak_end:
        return float(derate_ratio)
    return 1.0