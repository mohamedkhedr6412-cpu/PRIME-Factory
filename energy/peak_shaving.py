"""
PRIME-Factory Demand Response & Peak Shaving Module
Applies VFD Speed Derating during utility peak-tariff hours to cut peak demand costs.
"""
import config

def apply_peak_shaving(current_timestep: int, peak_start: int = 240, peak_end: int = 360, derate_ratio: float = 0.85) -> float:
    """
    تعديل مرجع سرعة محركات الـ VFD خلال ساعات الذروة السعرية:
    f_derated = f_nominal * derate_ratio
    :return: معامل تعديل السرعة والقدرة (1.0 خارج الذروة، 0.85 أثناء الذروة)
    """
    if peak_start <= current_timestep <= peak_end:
        return derate_ratio
    return 1.0
