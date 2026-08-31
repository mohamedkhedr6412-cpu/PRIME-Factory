"""
PRIME-Factory Simulation: Packaging Line Integration v2.0
"""
import pandas as pd
from simulation.machines import Machine
import config

class PackagingFactory:
    def __init__(self):
        # إنشاء الماكينات الخمس تلقائيًا مع قدراتها الاسمية المحددة في config
        self.machines = [
            Machine(
                machine_id=m_id,
                name=meta["name"],
                has_vibration=meta["has_vibration"],
                nominal_kw=meta["nominal_kw"]
            )
            for m_id, meta in config.MACHINES.items()
        ]

    def run_simulation(self, product_schedule: list, degradation_targets: dict = None) -> pd.DataFrame:
        records = []
        timesteps = len(product_schedule)

        for t in range(timesteps):
            prod_key = product_schedule[t]
            
            for m in self.machines:
                if degradation_targets and m.machine_id in degradation_targets:
                    m.degradation_level = degradation_targets[m.machine_id][t]
                
                m_data = m.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES)
                m_data["timestep"] = t
                records.append(m_data)

        return pd.DataFrame(records)
    