"""
PRIME-Factory Unified Simulation & KPI Engine v6.0
Single Source of Truth for Live Telemetry, Benchmarks, and What-If Analysis (Section 3, 11, 16 & 17).
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

import config
from simulation.factory import PackagingFactory
from simulation.faults import build_fault_scenario
from simulation.state_machine import AssetStateMachine
from simulation.events import EventLog, SimulationEvent

# Import AI components
from ai.anomaly import AnomalyProcessor
from ai.health_index import (
    calculate_health_index_and_evidence,
    estimate_rolling_rul,
    get_hi_confidence
)
from ai.decision import DecisionEngine

# Import core components
from core.models import (
    ScenarioConfig,
    ResilienceMetrics,
    SimulationResult,
    DecisionRecord,
    EvidenceTrace
)
from core.evidence import EvidenceTracker


class UnifiedSimulationEngine:
    """
    Unified engine for running PRIME-Factory simulations.
    Integrates factory, state machines, events, decision engine, and evidence tracking.
    """
    
    @staticmethod
    def run(scenario: ScenarioConfig) -> SimulationResult:
        """
        Run a complete simulation scenario.
        Returns SimulationResult with all telemetry, events, decisions, and evidence traces.
        """
        rng = np.random.RandomState(scenario.seed)
        
        # Initialize factory and event log
        factory = PackagingFactory(seed=scenario.seed)
        event_log = EventLog()
        
        # Initialize decision engine and evidence tracker
        decision_engine = DecisionEngine()
        evidence_tracker = EvidenceTracker()
        
        timesteps = len(scenario.product_schedule)
        events: List[SimulationEvent] = []
        decisions: List[DecisionRecord] = []
        evidence_traces: List[EvidenceTrace] = []
        
        # Build fault scenario if not healthy baseline
        degradation_plan = None
        if scenario.fault_type != "None (Healthy Baseline)":
            fault_scenario = build_fault_scenario(
                machine_id=scenario.fault_machine,
                fault_type=scenario.fault_type,
                severity=scenario.max_degradation,
                start_time=scenario.fault_start,
                total_timesteps=timesteps
            )
            degradation_plan = {scenario.fault_machine: fault_scenario["degradation_profile"]}
        
        # Start the factory
        factory.start()
        
        # Initialize state machines for each machine
        state_machines = {
            mid: AssetStateMachine(mid) for mid in factory.machines
        }
        
        # Initialize anomaly processors for each machine
        processors = {
            mid: AnomalyProcessor(config.PERSISTENCE_WINDOW) 
            for mid in factory.machines
        }
        
        # Tracking variables
        records = []
        hi_histories = {mid: [] for mid in factory.machines}
        
        is_repairing = False
        repair_timer = 0
        downtime_minutes = 0.0
        maintenance_events = 0
        total_units = 0
        good_units = 0
        scrap_units = 0
        
        recovery_start_t = None
        recovery_end_t = None
        alert_triggered_t = None
        trace_started_for_alert = None
        
        # Log system start
        event_log.add_event(0, "SYSTEM_START", "INFO", "ALL", 
                           "Line initialized in healthy nominal state.")
        
        # Main simulation loop
        for t in range(timesteps):
            prod_key = scenario.product_schedule[t]
            
            # Handle product switching if specified
            if scenario.product_switch_schedule and t < len(scenario.product_switch_schedule):
                prod_key = scenario.product_switch_schedule[t]
            
            # Check for manual PdM intervention
            if scenario.manual_pdm_timestep is not None and t == scenario.manual_pdm_timestep:
                is_repairing = True
                repair_timer = config.MAINTENANCE_DURATION_MINUTES
                maintenance_events += 1
                event_log.add_event(t, "MAINTENANCE_EXECUTED", "INFO", scenario.fault_machine,
                                   f"Targeted {config.MAINTENANCE_DURATION_MINUTES}-minute Predictive Intervention executed.",
                                   recommended_action="Monitor recovery")
            
            # Handle maintenance state
            if is_repairing:
                repair_timer -= 1
                downtime_minutes += 1.0
                
                if repair_timer <= 0:
                    is_repairing = False
                    factory.reset_machine(scenario.fault_machine)
                    recovery_start_t = t
                    event_log.add_event(t, "RECOVERY_STARTED", "INFO", scenario.fault_machine,
                                       "Post-repair stabilization phase initiated.",
                                       recommended_action="Monitor stabilization")
                
                # Log maintenance state for all machines
                for mid, machine in factory.machines.items():
                    records.append({
                        "timestep": t,
                        "machine_id": mid,
                        "state": config.STATE_MAINTENANCE,
                        "product": prod_key,
                        "degradation": 0.0,
                        "health_index": 100.0,
                        "vibration_rms": 0.0,
                        "temperature_c": machine.temperature_c if hasattr(machine, 'temperature_c') else 30.0,
                        "active_power_kw": 0.2,
                        "power_factor": 0.95,
                        "expected_p": 0.2,
                        "eci": 0.0,
                        "context_ai_score": 0.0,
                        "persistence_ratio": 0.0,
                        "confirmed_anomaly": 0,
                        "rul_minutes": -1,
                        "rul_str": "In Service",
                        "penalty_contributions": {
                            "AI Anomaly": 0.0,
                            "Persistence": 0.0,
                            "ECI Deviation": 0.0,
                            "Thermal/Vibration": 0.0
                        },
                        "decision_id": None,
                        "evidence_trace_id": None
                    })
                continue
            
            # Normal operation: step each machine
            step_records = []
            for mid, machine in factory.machines.items():
                # Apply degradation from fault plan
                if degradation_plan and mid in degradation_plan:
                    machine.degradation_level = degradation_plan[mid][t]
                else:
                    machine.degradation_level = 0.0
                
                # Step the machine
                record = machine.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES, rng=rng)
                
                # Add chaos if enabled
                if scenario.enable_chaos and mid == scenario.fault_machine:
                    if hasattr(machine, 'has_vibration') and machine.has_vibration:
                        if rng.uniform(0, 1) < 0.03:
                            record["vibration_rms"] += rng.uniform(1.2, 2.5)
                
                # Apply peak shaving if enabled
                if scenario.enable_peak_shaving:
                    speed_mod = 0.85  # Simple derating
                    record["active_power_kw"] = record["active_power_kw"] * (speed_mod ** 2)
                
                # Calculate expected power and ECI
                product_config = config.PRODUCTS.get(prod_key, config.PRODUCTS["Product_B"])
                expected_power = machine.nominal_kw * product_config["nominal_power_mult"]
                record["expected_p"] = expected_power
                
                # Simple ECI calculation
                eci = (record["active_power_kw"] - expected_power) / max(expected_power, 0.1)
                record["eci"] = eci
                
                step_records.append(record)
            
            # Process each machine's data with AI and Decision Engine
            for record in step_records:
                mid = record["machine_id"]
                machine = factory.machines[mid]
                
                # ===== ANOMALY DETECTION =====
                context = {
                    "product": prod_key,
                    "speed": record.get("speed_factor", 1.0),
                    "load": record.get("load_factor", 1.0),
                    "eci": record.get("eci", 0.0)
                }
                
                anomaly_score = record.get("context_ai_score", 0.0)
                if anomaly_score == 0.0:
                    anomaly_score = min(1.0, abs(record["eci"]) * 2.0)
                
                processor_result = processors[mid].update(
                    raw_anomaly_score=anomaly_score,
                    threshold=0.5,
                    context=context
                )
                
                # ===== HEALTH INDEX =====
                hi_result = calculate_health_index_and_evidence(
                    anomaly_score=anomaly_score,
                    persistence_ratio=processor_result["persistence_ratio"],
                    eci=record["eci"],
                    temp_c=record["temperature_c"],
                    vib_rms=record.get("vibration_rms", 0.0),
                    context=context
                )
                health_index = hi_result["health_index"]
                hi_histories[mid].append(health_index)
                
                # ===== RUL =====
                rul_value, rul_str = estimate_rolling_rul(
                    hi_histories[mid],
                    current_state=machine.current_state,
                    current_t=t,
                    window_size=15
                )
                
                # ===== STATE MACHINE =====
                sm = state_machines[mid]
                is_confirmed = bool(processor_result["is_confirmed_anomaly"])
                
                new_state = sm.update_state_with_hysteresis(
                    degradation=record["degradation"],
                    health_index=health_index,
                    is_confirmed_anomaly=is_confirmed,
                    in_maintenance=False,
                    maintenance_duration=config.MAINTENANCE_DURATION_MINUTES
                )
                
                machine.current_state = new_state
                
                # ===== DECISION ENGINE =====
                decision = decision_engine.evaluate(
                    machine_id=mid,
                    timestamp=t,
                    current_state=new_state,
                    health_index=health_index,
                    rul_minutes=rul_value,
                    eci=record["eci"],
                    is_confirmed_anomaly=is_confirmed,
                    production_units=total_units,
                    context=context
                )
                
                # Convert to DecisionRecord for storage
                decision_record = DecisionRecord(
                    decision_id=decision.decision_id,
                    timestamp=decision.timestamp,
                    machine_id=decision.machine_id,
                    current_state=decision.current_state,
                    health_index=decision.health_index,
                    rul_minutes=decision.rul_minutes,
                    recommendation=decision.recommendation,
                    priority=decision.priority,
                    evidence_summary=decision.evidence_summary
                )
                decisions.append(decision_record)
                
                # ===== EVIDENCE TRACKER =====
                trace = evidence_tracker.create_complete_chain(
                    machine_id=mid,
                    timestamp=t,
                    sensor_data={
                        "vibration_rms": record.get("vibration_rms", 0.0),
                        "temperature_c": record["temperature_c"],
                        "active_power_kw": record["active_power_kw"],
                        "power_factor": record.get("power_factor", 0.95)
                    },
                    context=context,
                    anomaly_score=anomaly_score,
                    persistence_ratio=processor_result["persistence_ratio"],
                    is_confirmed=is_confirmed,
                    health_index=health_index,
                    rul_minutes=rul_value,
                    eci=record["eci"],
                    state=new_state,
                    decision_recommendation=decision.recommendation,
                    decision_id=decision.decision_id
                )
                
                # Convert to EvidenceTrace for storage
                evidence_trace = EvidenceTrace(
                    trace_id=trace.trace_id,
                    machine_id=trace.machine_id,
                    start_timestamp=trace.start_timestamp,
                    end_timestamp=trace.end_timestamp,
                    steps=[{"step_type": s.step_type, "data": s.data, "description": s.description} for s in trace.steps],
                    decision_id=trace.decision_id,
                    final_outcome=trace.final_outcome
                )
                evidence_traces.append(evidence_trace)
                
                # Track predictive alerts for trace completion
                if new_state == config.STATE_PREDICTIVE_ALERT and alert_triggered_t is None:
                    alert_triggered_t = t
                    trace_started_for_alert = trace.trace_id
                    event_log.add_event(
                        t, "PREDICTIVE_ALERT", "PREDICTIVE", mid,
                        f"Actionable anomaly detected. Health Index: {health_index:.1f}",
                        recommended_action=decision.recommendation
                    )
                
                # Track recovery completion
                if new_state == config.STATE_NORMAL and recovery_start_t is not None and recovery_end_t is None:
                    recovery_end_t = t
                    event_log.add_event(
                        t, "RECOVERY_COMPLETED", "INFO", mid,
                        f"Asset fully recovered to healthy nominal baseline (HI: {health_index:.1f})"
                    )
                    # Complete the evidence trace
                    if trace_started_for_alert:
                        completed_trace = evidence_tracker.get_trace(trace_started_for_alert)
                        if completed_trace:
                            evidence_tracker.complete_trace(
                                completed_trace,
                                end_timestamp=t,
                                action_taken="Recovery completed",
                                outcome={"status": "recovered", "health_index": health_index}
                            )
                
                # ===== UPDATE RECORD =====
                record["state"] = new_state
                record["health_index"] = health_index
                record["persistence_ratio"] = processor_result["persistence_ratio"]
                record["confirmed_anomaly"] = processor_result["is_confirmed_anomaly"]
                record["rul_minutes"] = rul_value if rul_value is not None else -1
                record["rul_str"] = rul_str
                record["penalty_contributions"] = hi_result["penalty_contributions"]
                record["decision_id"] = decision.decision_id
                record["evidence_trace_id"] = trace.trace_id
                
                # Track state changes
                if len(records) > 0:
                    prev_record = records[-1]
                    if prev_record.get("machine_id") == mid:
                        prev_state = prev_record.get("state")
                        if prev_state != new_state:
                            event_log.add_event(
                                t, "STATE_CHANGE", "INFO", mid,
                                f"State transition: {prev_state} → {new_state}",
                                state_before=prev_state,
                                state_after=new_state
                            )
                
                records.append(record)
            
            # Update production metrics
            target_deg = 0.0
            if degradation_plan and scenario.fault_machine in degradation_plan:
                target_deg = degradation_plan[scenario.fault_machine][t]
            
            base_cycle = config.PRODUCTS[prod_key]["base_cycle_time"]
            m_units = int(60.0 / (base_cycle * (1.0 + 0.1 * target_deg)))
            defect_rate = 0.005 + (0.04 * target_deg)
            m_good = int(m_units * (1.0 - defect_rate))
            m_scrap = m_units - m_good
            
            total_units += m_units
            good_units += m_good
            scrap_units += m_scrap
        
        # Build final DataFrame
        telemetry_df = pd.DataFrame(records)
        
        # Calculate KPIs
        if not telemetry_df.empty:
            agg_power = telemetry_df.groupby("timestep")["active_power_kw"].sum()
            total_energy_kwh = float(np.sum(agg_power) * (config.TIME_STEP_MINUTES / 60.0))
            peak_demand_kw = float(np.max(agg_power)) if len(agg_power) > 0 else 0.0
            avg_pf = float(telemetry_df["power_factor"].mean()) if "power_factor" in telemetry_df.columns else 0.9
        else:
            total_energy_kwh = 0.0
            peak_demand_kw = 0.0
            avg_pf = 0.9
        
        # Calculate OEE
        operating_time_min = timesteps - downtime_minutes
        availability = (operating_time_min / timesteps) if timesteps > 0 else 0.0
        
        cycle_times = [config.PRODUCTS[p]["base_cycle_time"] for p in scenario.product_schedule]
        weighted_ideal_sec = sum(cycle_times) / len(cycle_times) if cycle_times else 1.5
        performance = ((weighted_ideal_sec * total_units) / (operating_time_min * 60.0)) if operating_time_min > 0 else 0.0
        quality = (good_units / total_units) if total_units > 0 else 0.0
        oee = availability * min(1.0, performance) * quality * 100.0
        
        # Financial calculations
        energy_cost = total_energy_kwh * config.ELECTRICITY_TARIFF_PER_KWH
        downtime_cost = downtime_minutes * (config.DOWNTIME_COST_PER_HOUR / 60.0)
        pf_penalty = max(0, (0.90 - avg_pf) * 100 * 50) if avg_pf < 0.90 else 0
        total_cost = energy_cost + downtime_cost + pf_penalty
        carbon_kg = total_energy_kwh * config.CARBON_EMISSION_FACTOR
        energy_per_unit = (total_energy_kwh * 1000) / good_units if good_units > 0 else 0
        
        # Resilience metrics
        resilience = ResilienceMetrics(
            recovery_time_min=float(recovery_end_t - recovery_start_t) if (recovery_start_t and recovery_end_t) else 15.0,
            production_loss_units=scrap_units + int(downtime_minutes * 35),
            downtime_avoided_min=60.0 if scenario.manual_pdm_timestep else 0.0,
            recovery_success=recovery_end_t is not None or scenario.manual_pdm_timestep is not None,
            failure_avoided=target_deg < 0.75 or scenario.manual_pdm_timestep is not None,
            total_decisions=len(decisions),
            critical_decisions=len([d for d in decisions if d.priority == "CRITICAL"])
        )
        
        # Return results with evidence tracker
        return SimulationResult(
            config=scenario,
            telemetry_df=telemetry_df,
            events=event_log.events,
            total_energy_kwh=round(total_energy_kwh, 2),
            peak_demand_kw=round(peak_demand_kw, 2),
            avg_pf=round(avg_pf, 3),
            downtime_min=downtime_minutes,
            maintenance_events=maintenance_events,
            total_units=total_units,
            good_units=good_units,
            scrap_units=scrap_units,
            availability_pct=round(availability * 100.0, 2),
            performance_pct=round(min(1.0, performance) * 100.0, 2),
            quality_pct=round(quality * 100.0, 2),
            oee_pct=round(oee, 2),
            energy_cost_usd=round(energy_cost, 2),
            downtime_cost_usd=round(downtime_cost, 2),
            pf_penalty_usd=round(pf_penalty, 2),
            total_operational_cost_usd=round(total_cost, 2),
            carbon_kg=round(carbon_kg, 2),
            energy_per_good_unit_wh=round(energy_per_unit, 2),
            cost_per_good_unit_usd=round(total_cost / good_units if good_units > 0 else 0, 4),
            resilience=resilience,
            decisions=decisions,
            evidence_traces=evidence_traces,
            evidence_tracker=evidence_tracker  # NEW: Store tracker for dashboard
        )