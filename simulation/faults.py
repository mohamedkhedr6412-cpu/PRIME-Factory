"""
PRIME-Factory Fault & Degradation Injection Engine
Generates controlled physical degradation and operational switching profiles.
"""
import numpy as np
import config

def generate_degradation_profile(total_timesteps: int, start_time: int, max_degradation: float = 0.35) -> list:
    """
    توليد منحنى تدهور ميكانيكي تدريجي منتظم (Monotonic Bearing Degradation)
    :param total_timesteps: إجمالي زمن المحاكاة (480 دقيقة)
    :param start_time: الدقيقة التي يبدأ عندها التآكل الميكانيكي
    :param max_degradation: أقصى نسبة تدهور مطلوبة (0.35 = 35% تآكل)
    """
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        # تدرج تدريجي من 0 حتى أقصى قيمة
        profile[start_time:] = np.linspace(0.0, max_degradation, duration)
    return profile.tolist()

def generate_switching_schedule(total_timesteps: int) -> list:
    """
    توليد جدول تشغيلي يحتوي على تبديل دوري للمنتجات (A -> B -> C)
    لاختبار قدرة النظام على التعامل مع التغير الطبيعي للتشغيل (Context Awareness)
    """
    schedule = []
    # تقسيم الـ 8 ساعات بالتساوي بين المنتجات الثلاثة
    interval = total_timesteps // 3
    for t in range(total_timesteps):
        if t < interval:
            schedule.append("Product_A")
        elif t < 2 * interval:
            schedule.append("Product_B")
        else:
            schedule.append("Product_C")
    return schedule