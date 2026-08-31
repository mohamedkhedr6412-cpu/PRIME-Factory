"""
PRIME-Factory Context-Aware Energy Condition Indicator (ECI)
Calculates normalized power deviation relative to expected physical regime:
ECI_t = (P_actual - P_expected(m, product, speed, load)) / P_expected
"""
import config

def get_context_expected_power(machine_id: str, product_key: str, speed_rpm: float = 1500.0) -> float:
    """
    حساب القدرة الطبيعية المتوقعة للماكينة بالاعتماد على سياق المنتج وسرعة التشغيل:
    P_expected = P_nominal(m) * Load_Factor(prod) * (Speed / 1500)
    """
    machine_nominal = config.MACHINES[machine_id]["nominal_kw"]
    prod = config.PRODUCTS[product_key]
    
    # تناسب القدرة مع سرعة المحرك والحمل التصميمي للمنتج
    speed_ratio = speed_rpm / (1500.0 * prod["speed_factor"])
    expected_power = machine_nominal * prod["load_factor"] * speed_ratio
    return max(0.5, expected_power)

def calculate_eci(actual_power_kw: float, machine_id: str, product_key: str, speed_rpm: float = 1500.0, epsilon: float = 1e-3) -> float:
    """
    حساب مؤشر انحراف الطاقة اللحظي:
    - تشغيل طبيعي ومثالي: ECI يقترب من 0.0
    - زيادة احتكاك وتآكل ميكانيكي: ECI موجب تصاعدي (+10% إلى +30%)
    - تغير طبيعي في المنتج: ECI يظل مستقرًا حول الصفر لأن P_expected تتكيف تلقائيًا مع السياق
    """
    expected_power = get_context_expected_power(machine_id, product_key, speed_rpm)
    denom = max(expected_power, epsilon)
    eci = (actual_power_kw - expected_power) / denom
    return round(float(eci), 4)
