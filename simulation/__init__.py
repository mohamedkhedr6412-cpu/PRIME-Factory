"""
PRIME-Factory Simulation Package
Exports all simulation components for easy import.
"""

from simulation.machines import Machine
from simulation.factory import PackagingFactory, FactoryKPIs
from simulation.state_machine import AssetStateMachine
from simulation.faults import (
    generate_degradation_profile,
    generate_friction_profile,
    generate_electrical_profile,
    generate_switching_schedule,
    inject_sensor_noise_spikes,
    build_fault_scenario
)
from simulation.events import EventLog, SimulationEvent
from simulation.engine import UnifiedSimulationEngine, ScenarioConfig, SimulationResult

__all__ = [
    'Machine',
    'PackagingFactory',
    'FactoryKPIs',
    'AssetStateMachine',
    'generate_degradation_profile',
    'generate_friction_profile',
    'generate_electrical_profile',
    'generate_switching_schedule',
    'inject_sensor_noise_spikes',
    'build_fault_scenario',
    'EventLog',
    'SimulationEvent',
    'UnifiedSimulationEngine',
    'ScenarioConfig',
    'SimulationResult',
]