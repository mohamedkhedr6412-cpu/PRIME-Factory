"""
PRIME-Factory Simulation: Packaging Line Integration
"""
import pandas as pd
from simulation.machines import Machine
import config

class PackagingFactory:
    def __init__(self):
        self.machines = [
            Machine("M1", "Conveyor", has_vibration=False),
            Machine("M2", "Filler", has_vibration=False),
            Machine("M3", "Sealer", has_vibration=True),
            Machine("M4", "Labeler", has_vibration=True),
            Machine("M5", "Packaging", has_vibration=True)
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
    