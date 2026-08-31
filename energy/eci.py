"""
PRIME-Factory Energy Condition Indicator (ECI)
Calculates real-time normalized energy deviation:
ECI_t = (P_actual - P_expected) / max(P_expected, epsilon)
"""
import config

def get_expected_power(product_key: str) -> float:
    """حساب القدرة الطبيعية المتوقعة بناءً على نوع المنتج المشغّل حاليًا"""
    prod = config.PRODUCTS[product_key]
    return prod["nominal_power_kw"] * prod["load_factor"]

def calculate_eci(actual_power_kw: float, product_key: str, epsilon: float = 1e-3) -> float:
    """
    حساب مؤشر انحراف الطاقة اللحظي
    - القيمة القريبة من 0 تعني تشغيلاً سليمًا مطابقًا للمتوقع.
    - القيمة الموجبة المستمرة تدل على زيادة الاحتكاك والتدهور الميكانيكي.
    """
    expected_power = get_expected_power(product_key)
    denom = max(expected_power, epsilon)
    eci = (actual_power_kw - expected_power) / denom
    return round(float(eci), 4)
