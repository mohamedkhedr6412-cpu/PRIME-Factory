"""
PRIME-Factory Packaging Line Orchestrator v6.0
Coordinates synchronized multi-machine execution and provides clean state reset hooks.
"""

import pandas as pd
import numpy as np
import config
from simulation.machines import Machine

class PackagingFactory:
    def __init__(self):
        self.machines = [
            Machine(
                machine_id=m_id,
                name=meta["name"],
                has_vibration=meta["has_vibration"],
                nominal_kw=meta["nominal_kw"]
            )
            for m_id, meta in config.MACHINES.items()
        ]

    def reset_factory(self):
        """Resets all 5 machines in the line to initial healthy baselines."""
        for m in self.machines:
            m.reset()

    def reset_machine(self, machine_id: str):
        """Resets a single target machine following completed maintenance recovery."""
        for m in self.machines:
            if m.machine_id == machine_id:
                m.reset()
                break

    def run_simulation(self, product_schedule: list, degradation_targets: dict = None, seed: int = config.RANDOM_SEED) -> pd.DataFrame:
        """Runs synchronized factory production over the schedule horizon using isolated RNG."""
        rng = np.random.RandomState(seed)
        records = []
        timesteps = len(product_schedule)

        for t in range(timesteps):
            prod_key = product_schedule[t]
            for m in self.machines:
                if degradation_targets and m.machine_id in degradation_targets:
                    m.degradation_level = degradation_targets[m.machine_id][t]
                
                m_data = m.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES, rng=rng)
                m_data["timestep"] = t
                records.append(m_data)

        return pd.DataFrame(records)