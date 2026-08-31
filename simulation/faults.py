"""
PRIME-Factory Scenario & Degradation Engine v2.0
Generates deterministic faults, product transitions, and sensor noise stress-tests.
"""
import numpy as np
import config

def generate_degradation_profile(total_timesteps: int, start_time: int, max_degradation: float = 0.35) -> list:
    """توليد تآكل ميكانيكي تدريجي منتظم في المحامل (Bearing Degradation)"""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        profile[start_time:] = np.linspace(0.0, max_degradation, duration)
    return profile.tolist()

def generate_switching_schedule(total_timesteps: int) -> list:
    """توليد جدول تبديل منتجات طبيعي (Product A -> B -> C) لاختبار الوعي بالسياق"""
    schedule = []
    interval = total_timesteps // 3
    for t in range(total_timesteps):
        if t < interval:
            schedule.append("Product_A")
        elif t < 2 * interval:
            schedule.append("Product_B")
        else:
            schedule.append("Product_C")
    return schedule

def inject_sensor_noise_spikes(values: np.ndarray, spike_probability: float = 0.03, noise_magnitude: float = 2.0) -> np.ndarray:
    """
    محاكاة تشويش الحساسات الصناعية (Chaos Mode / Sensor Noise Injection):
    حقن قراءات شاذة لحظية مفاجئة لاختبار قدرة نافذة الاستمرارية على منع الإنذارات الكاذبة
    """
    noisy_values = values.copy()
    num_spikes = int(len(values) * spike_probability)
    spike_indices = np.random.choice(len(values), num_spikes, replace=False)
    
    for idx in spike_indices:
        noisy_values[idx] += np.random.uniform(1.5, noise_magnitude)
        
    return noisy_values
