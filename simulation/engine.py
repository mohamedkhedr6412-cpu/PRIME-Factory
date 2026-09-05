"""
PRIME-Factory Unified Simulation & KPI Engine v6.2 FINAL

Single Source of Truth for Live Telemetry, Benchmarks, and What-If Analysis.
Now uses Isolation Forest as the primary anomaly detector.
Predictive maintenance is now decision-driven and limited to one intervention.
Peak Shaving is now integrated with production trade-off.
FIXED: Action Trigger uses decision_code.
FIXED: Maintenance lifecycle uses state_machine.start_maintenance().
FIXED: ECI computed after speed_mod.
FIXED: Evidence chain single source of truth (EvidenceTracker only).
FIXED: failure_avoided = not machine_ever_failed (counterfactual handled in policies.py).
FIXED: Recovery tracking per-machine.
FIXED: force_pdm_now activates immediate maintenance.
FIXED: OEE uses actual production units by product.
FIXED: Evidence ACTION/OUTCOME linked to SAME trace via trace_id_by_machine.
FIXED: downtime_avoided_min = 0.0 (computed in counterfactual).
FIXED: production_loss_units = 0 (computed in counterfactual).
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

import config
from simulation.factory import PackagingFactory
from simulation.faults import build_fault_scenario
from simulation.state_machine import AssetStateMachine
from simulation.events import EventLog

from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import (
    calculate_health_index_and_evidence,
    estimate_rolling_rul,
    get_hi_confidence
)
from ai.decision import DecisionEngine, DecisionCode

from core.models import (
    ScenarioConfig,
    ResilienceMetrics,
    SimulationResult,
    DecisionRecord,
    EvidenceTrace
)
from core.evidence import EvidenceTracker

from energy.eci import calculate_eci, get_context_expected_power
from energy.peak_shaving import PeakShavingController, apply_peak_shaving
from energy.energy_model import calculate_financial_and_esg_impact
from evaluation.kpis import calculate_oee_multiproduct


class UnifiedSimulationEngine:
    """
    Unified engine for running PRIME-Factory simulations.
    Integrates factory, state machines, AI (Isolation Forest), decisions,
    evidence tracking, and KPIs.
    """

    @staticmethod
    def run(scenario: ScenarioConfig) -> SimulationResult:
        """
        Run a complete simulation scenario.
        Returns SimulationResult with all telemetry, events, decisions,
        and evidence traces.
        """
        rng = np.random.RandomState(scenario.seed)

        # ===== 1. Initialize components =====
        factory = PackagingFactory(seed=scenario.seed)
        event_log = EventLog()
        decision_engine = DecisionEngine()
        evidence_tracker = EvidenceTracker()

        timesteps = len(scenario.product_schedule)

        # ===== 1.5. Initialize Peak Shaving Controller =====
        peak_controller = None
        if scenario.enable_peak_shaving:
            peak_controller = PeakShavingController(
                peak_start=config.PEAK_SHAVING_START,
                peak_end=config.PEAK_SHAVING_END,
                derate_ratio=config.PEAK_SHAVING_DERATE,
                enabled=True
            )
            event_log.add_event(0, "PEAK_SHAVING_ENABLED", "INFO", "ALL",
                               "Peak Shaving activated (derate 10% during peak hours).")

        # ===== 2. Build fault scenario =====
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

        # ===== 3. Train Isolation Forest on healthy baseline =====
        factory.start()
        factory.reset_factory()

        healthy_limit = min(scenario.fault_start, timesteps)
        healthy_df = []
        for t in range(healthy_limit):
            prod_key = scenario.product_schedule[t]
            for mid, machine in factory.machines.items():
                record = machine.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES, rng=rng, speed_mod=1.0)
                healthy_df.append(record)

        healthy_df = pd.DataFrame(healthy_df)

        if len(healthy_df) >= 20:
            if_detector = PRIMEIsolationForest(
                contamination=0.02,
                seed=scenario.seed,
                threshold=0.50
            )
            if_detector.fit(healthy_df)
            if_ready = True
        else:
            if_ready = False
            if_detector = None

        # Reset factory for actual simulation
        factory.reset_factory()
        factory.start()

        # ===== 4. Initialize trackers =====
        state_machines = {mid: AssetStateMachine(mid) for mid in factory.machines}
        processors = {mid: AnomalyProcessor(config.PERSISTENCE_WINDOW) for mid in factory.machines}

        # ===== FIXED: Define maintenance tracking variables =====
        is_repairing = False
        repair_timer = 0
        machines_in_maintenance = set()
        maintenance_done_for_machine = {mid: False for mid in factory.machines}

        # ===== FIXED: Recovery tracking per-machine =====
        recovery_start_t_by_machine = {}
        recovery_end_t_by_machine = {}

        # ===== FIXED: Evidence trace tracking per-machine =====
        trace_id_by_machine = {}  # NEW: trace_id for each machine

        records = []
        hi_histories = {mid: [] for mid in factory.machines}
        decisions = []
        events = []

        # ===== 5. Tracking variables =====
        downtime_minutes = 0.0
        maintenance_events = 0
        total_units = 0
        good_units = 0
        scrap_units = 0

        actual_units_by_product = {p: 0 for p in config.PRODUCTS.keys()}
        actual_good_units_by_product = {p: 0 for p in config.PRODUCTS.keys()}

        production_accumulator = 0.0

        last_state_by_machine = {mid: config.STATE_NORMAL for mid in factory.machines}

        predictive_maintenance_executed = False
        forced_pdm_executed = False

        machine_ever_failed = {mid: False for mid in factory.machines}

        # ===== 6. Main simulation loop =====
        for t in range(timesteps):
            prod_key = scenario.product_schedule[t]

            # ----- 6a. Peak Shaving -----
            current_power = sum(m.power_kw for m in factory.machines.values())
            speed_mod = 1.0
            if peak_controller is not None:
                speed_mod = peak_controller.apply_peak_shaving(
                    current_timestep=t,
                    current_power=current_power
                )

            # ===== FIXED: Check for force_pdm_now =====
            if scenario.force_pdm_now and not predictive_maintenance_executed and not forced_pdm_executed:
                mid = scenario.fault_machine
                sm = state_machines[mid]
                if sm.current_state != config.STATE_MAINTENANCE:
                    is_repairing = True
                    repair_timer = config.MAINTENANCE_DURATION_MINUTES
                    machines_in_maintenance.add(mid)
                    sm.start_maintenance(config.MAINTENANCE_DURATION_MINUTES)
                    maintenance_events += 1
                    predictive_maintenance_executed = True
                    forced_pdm_executed = True
                    maintenance_done_for_machine[mid] = True
                    recovery_start_t_by_machine[mid] = t
                    event_log.add_event(t, "MAINTENANCE_EXECUTED", "FORCED", mid,
                                       f"Forced PdM executed at t={t} via Dashboard button.")
                    # ===== FIXED: Add ACTION evidence using trace_id_by_machine =====
                    UnifiedSimulationEngine._add_action_evidence(
                        evidence_tracker, mid, t, trace_id_by_machine,
                        action_type="Forced",
                        decision_id=None,
                        health_index=state_machines[mid].health_history[-1] if state_machines[mid].health_history else None,
                        rul_minutes=None
                    )

            # ===== FIXED: Force maintenance for PREVENTIVE only =====
            if scenario.policy_type == "PREVENTIVE":
                if not predictive_maintenance_executed and not forced_pdm_executed:
                    if t == 120:
                        mid = scenario.fault_machine
                        sm = state_machines[mid]
                        if sm.current_state != config.STATE_MAINTENANCE:
                            is_repairing = True
                            repair_timer = config.MAINTENANCE_DURATION_MINUTES
                            machines_in_maintenance.add(mid)
                            sm.start_maintenance(config.MAINTENANCE_DURATION_MINUTES)
                            maintenance_events += 1
                            predictive_maintenance_executed = True
                            maintenance_done_for_machine[mid] = True
                            recovery_start_t_by_machine[mid] = t
                            event_log.add_event(t, "MAINTENANCE_EXECUTED", "PREVENTIVE", mid,
                                               f"Preventive maintenance executed at t={t}.")
                            UnifiedSimulationEngine._add_action_evidence(
                                evidence_tracker, mid, t, trace_id_by_machine,
                                action_type="Preventive",
                                decision_id=None,
                                health_index=state_machines[mid].health_history[-1] if state_machines[mid].health_history else None,
                                rul_minutes=None
                            )

            # ----- 6b. Handle maintenance state -----
            if is_repairing:
                repair_timer -= 1
                downtime_minutes += 1.0

                for mid, machine in factory.machines.items():
                    sm = state_machines[mid]
                    sm.update_state_with_hysteresis(
                        degradation=machine.degradation_level,
                        health_index=machine.health_index,
                        is_confirmed_anomaly=False,
                        in_maintenance=(mid in machines_in_maintenance),
                        maintenance_duration=config.MAINTENANCE_DURATION_MINUTES
                    )
                    machine.current_state = sm.current_state

                    if sm.current_state == config.STATE_FAILED:
                        machine_ever_failed[mid] = True

                    records.append({
                        "machine_id": mid,
                        "timestep": t,
                        "product": prod_key,
                        "state": sm.current_state,
                        "degradation": machine.degradation_level,
                        "health_index": machine.health_index,
                        "speed_rpm": 0.0 if mid in machines_in_maintenance else machine.speed_rpm * speed_mod,
                        "load_factor": 0.0 if mid in machines_in_maintenance else machine.load_factor,
                        "vibration_rms": 0.0 if mid in machines_in_maintenance else machine.vibration_rms,
                        "temperature_c": 30.0 if mid in machines_in_maintenance else machine.temperature_c,
                        "current_a": 0.0 if mid in machines_in_maintenance else machine.current_a,
                        "power_kw": 0.2 if mid in machines_in_maintenance else machine.power_kw * (speed_mod ** 2),
                        "power_factor": 0.95 if mid in machines_in_maintenance else machine.power_factor,
                        "eci": 0.0 if mid in machines_in_maintenance else machine.eci,
                        "expected_power_kw": 0.2 if mid in machines_in_maintenance else machine.expected_power_kw,
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
                        "evidence_trace_id": None,
                        "cumulative_energy_kwh": machine.cumulative_energy_kwh
                    })

                if repair_timer <= 0:
                    is_repairing = False
                    mid = scenario.fault_machine
                    machines_in_maintenance.discard(mid)
                    machine = factory.machines[mid]
                    machine.degradation_level = 0.0
                    machine.health_index = 100.0
                    machine.current_state = config.STATE_RECOVERY
                    event_log.add_event(t, "RECOVERY_STARTED", "INFO", mid,
                                       "Post-repair stabilization phase initiated (full recovery).")
                continue

            # ----- 6c. Normal operation: step each machine -----
            step_records = []

            for mid, machine in factory.machines.items():
                if degradation_plan and mid in degradation_plan:
                    if maintenance_done_for_machine.get(mid, False):
                        machine.degradation_level = 0.0
                    else:
                        machine.degradation_level = degradation_plan[mid][t]
                else:
                    machine.degradation_level = 0.0

                record = machine.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES, rng=rng, speed_mod=speed_mod)
                step_records.append(record)

            # ----- 6d. Process each machine with AI and state machine -----
            for record in step_records:
                mid = record["machine_id"]
                machine = factory.machines[mid]

                context = {
                    "product": prod_key,
                    "speed_factor": record.get("speed_factor", 1.0) * speed_mod,
                    "load_factor": record.get("load_factor", 1.0),
                    "eci": record.get("eci", 0.0),
                    "degradation": record.get("degradation", 0.0)
                }

                if if_ready and if_detector is not None:
                    df_row = pd.DataFrame([record])
                    if_score = if_detector.predict_anomaly_score(df_row)[0]
                    anomaly_score = float(if_score)
                else:
                    anomaly_score = min(1.0, abs(record.get("eci", 0.0)) * 2.0)

                processor_result = processors[mid].update(
                    raw_anomaly_score=anomaly_score,
                    threshold=0.5,
                    context=context
                )

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

                rul_value, rul_str = estimate_rolling_rul(
                    hi_histories[mid],
                    current_state=machine.current_state,
                    current_t=t,
                    window_size=15
                )
                rul_confidence = get_hi_confidence(health_index, len(hi_histories[mid]))

                sm = state_machines[mid]
                is_confirmed = bool(processor_result.get("is_confirmed_anomaly", False))
                in_maintenance = (mid in machines_in_maintenance)

                new_state = sm.update_state_with_hysteresis(
                    degradation=record["degradation"],
                    health_index=health_index,
                    is_confirmed_anomaly=is_confirmed,
                    in_maintenance=in_maintenance,
                    maintenance_duration=config.MAINTENANCE_DURATION_MINUTES
                )
                machine.current_state = new_state

                if new_state == config.STATE_FAILED:
                    machine_ever_failed[mid] = True

                decision = decision_engine.evaluate(
                    machine_id=mid,
                    timestamp=t,
                    current_state=new_state,
                    health_index=health_index,
                    rul_minutes=rul_value,
                    eci=record["eci"],
                    is_confirmed_anomaly=is_confirmed,
                    persistence_ratio=processor_result["persistence_ratio"],
                    production_units=total_units,
                    context=context
                )

                # ===== PREDICTIVE MAINTENANCE (AI decision only) =====
                is_predictive_policy = scenario.policy_type == "PREDICTIVE"
                is_pdm_decision = (decision.decision_code == DecisionCode.SCHEDULE_PDM)
                is_pdm_priority = decision.priority in ["MEDIUM", "HIGH"]

                if (is_predictive_policy and is_pdm_decision and is_pdm_priority and
                    mid == scenario.fault_machine and
                    sm.current_state != config.STATE_MAINTENANCE and
                    not predictive_maintenance_executed and
                    not forced_pdm_executed):
                    is_repairing = True
                    repair_timer = config.MAINTENANCE_DURATION_MINUTES
                    machines_in_maintenance.add(mid)
                    sm.start_maintenance(config.MAINTENANCE_DURATION_MINUTES)
                    maintenance_events += 1
                    predictive_maintenance_executed = True
                    maintenance_done_for_machine[mid] = True
                    recovery_start_t_by_machine[mid] = t
                    event_log.add_event(
                        t, "MAINTENANCE_EXECUTED", "PREDICTIVE", mid,
                        f"AI-driven Predictive Maintenance executed at t={t}. "
                        f"HI={health_index:.1f}, RUL={rul_value if rul_value is not None else 'N/A'}min."
                    )
                    UnifiedSimulationEngine._add_action_evidence(
                        evidence_tracker, mid, t, trace_id_by_machine,
                        action_type="Predictive",
                        decision_id=decision.decision_id,
                        health_index=health_index,
                        rul_minutes=rul_value
                    )

                # ---- EVIDENCE TRACKING (append to tracker only) ----
                important_events = [
                    config.STATE_PREDICTIVE_ALERT,
                    config.STATE_MAINTENANCE,
                    config.STATE_RECOVERY
                ]

                create_trace = (
                    new_state in important_events or
                    (is_confirmed and health_index < 50.0) or
                    (abs(record.get("eci", 0.0)) > 0.30)
                )

                trace_id = None
                if create_trace:
                    trace = evidence_tracker.create_complete_chain(
                        machine_id=mid,
                        timestamp=t,
                        sensor_data={
                            "vibration_rms": record.get("vibration_rms", 0.0),
                            "temperature_c": record["temperature_c"],
                            "active_power_kw": record["power_kw"],
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
                    trace_id = trace.trace_id
                    # ===== FIXED: Store trace_id for this machine =====
                    if trace_id is not None:
                        trace_id_by_machine[mid] = trace_id

                # ---- TRACK STATE CHANGES ----
                prev_state = last_state_by_machine.get(mid)
                if prev_state != new_state:
                    event_log.add_event(
                        t, "STATE_CHANGE", "INFO", mid,
                        f"State transition: {prev_state} → {new_state}",
                        state_before=prev_state,
                        state_after=new_state
                    )
                    last_state_by_machine[mid] = new_state

                    # ===== RECOVERY COMPLETED: Add OUTCOME =====
                    if new_state == config.STATE_NORMAL:
                        if mid in recovery_start_t_by_machine and mid not in recovery_end_t_by_machine:
                            recovery_end_t_by_machine[mid] = t
                            event_log.add_event(
                                t, "RECOVERY_COMPLETED", "INFO", mid,
                                f"Asset recovered to healthy baseline (HI: {health_index:.1f})"
                            )
                            # ===== FIXED: Add OUTCOME using trace_id_by_machine =====
                            if mid in trace_id_by_machine:
                                trace_id_to_complete = trace_id_by_machine[mid]
                                completed_trace = evidence_tracker.get_trace(trace_id_to_complete)
                                if completed_trace:
                                    evidence_tracker.complete_trace(
                                        completed_trace,
                                        end_timestamp=t,
                                        action_taken="Recovery completed",
                                        outcome={"status": "recovered", "health_index": health_index}
                                    )

                decisions.append(DecisionRecord(
                    decision_id=decision.decision_id,
                    timestamp=decision.timestamp,
                    machine_id=decision.machine_id,
                    current_state=decision.current_state,
                    health_index=decision.health_index,
                    rul_minutes=decision.rul_minutes,
                    recommendation=decision.recommendation,
                    priority=decision.priority,
                    evidence_summary=decision.evidence_summary
                ))

                record["state"] = new_state
                record["health_index"] = health_index
                record["persistence_ratio"] = processor_result["persistence_ratio"]
                record["confirmed_anomaly"] = processor_result.get("is_confirmed_anomaly", 0)
                record["rul_minutes"] = rul_value if rul_value is not None else -1
                record["rul_str"] = rul_str
                record["rul_confidence"] = rul_confidence
                record["penalty_contributions"] = hi_result["penalty_contributions"]
                record["decision_id"] = decision.decision_id
                if trace_id:
                    record["evidence_trace_id"] = trace_id

                record["cumulative_energy_kwh"] = machine.cumulative_energy_kwh

                records.append(record)

            # ----- 6e. Production -----
            capacities = []
            line_down_due_to_failure = False

            for mid, machine in factory.machines.items():
                if machine.current_state == config.STATE_FAILED:
                    capacities.append(0.0)
                    line_down_due_to_failure = True
                elif machine.current_state == config.STATE_MAINTENANCE:
                    capacities.append(0.0)
                else:
                    prod_cfg = config.PRODUCTS[prod_key]
                    cycle_time = prod_cfg["base_cycle_time"]
                    speed_factor = prod_cfg["speed_factor"]
                    effective_speed = speed_factor * speed_mod
                    degradation_penalty = max(0.0, 1.0 - (0.5 * machine.degradation_level))
                    capacity = (effective_speed / cycle_time * 60.0) * degradation_penalty
                    capacities.append(capacity)

            if line_down_due_to_failure:
                line_rate = 0.0
                downtime_minutes += 1.0
                event_log.add_event(
                    t, "LINE_DOWN", "CRITICAL", "ALL",
                    f"Line stopped due to {scenario.fault_machine} failure at t={t}."
                )
            elif capacities:
                line_rate = min(capacities)
            else:
                line_rate = 0.0

            production_rate = line_rate * config.TIME_STEP_MINUTES
            production_accumulator += production_rate
            units_this_step = int(production_accumulator)
            production_accumulator -= units_this_step

            max_deg = max([m.degradation_level for m in factory.machines.values()])
            defect_rate = 0.005 + (0.04 * max_deg)

            good_this_step = int(units_this_step * (1.0 - defect_rate))
            scrap_this_step = units_this_step - good_this_step

            total_units += units_this_step
            good_units += good_this_step
            scrap_units += scrap_this_step

            if prod_key in actual_units_by_product:
                actual_units_by_product[prod_key] += units_this_step
                actual_good_units_by_product[prod_key] += good_this_step

        # ===== 7. Final calculations =====
        telemetry_df = pd.DataFrame(records)

        if not telemetry_df.empty:
            agg_power = telemetry_df.groupby("timestep")["power_kw"].sum()
            total_energy_kwh = float(np.sum(agg_power) * (config.TIME_STEP_MINUTES / 60.0))
            peak_demand_kw = float(np.max(agg_power)) if len(agg_power) > 0 else 0.0
            avg_pf = float(telemetry_df["power_factor"].mean()) if "power_factor" in telemetry_df.columns else 0.9
        else:
            total_energy_kwh = 0.0
            peak_demand_kw = 0.0
            avg_pf = 0.9

        operating_time_min = timesteps - downtime_minutes

        oee_result = calculate_oee_multiproduct(
            planned_time_min=timesteps,
            operating_time_min=operating_time_min,
            product_schedule=scenario.product_schedule,
            total_units=total_units,
            good_units=good_units,
            product_units=actual_units_by_product
        )
        oee = oee_result["oee_pct"]

        financial_result = calculate_financial_and_esg_impact(
            total_energy_kwh=total_energy_kwh,
            downtime_minutes=downtime_minutes,
            good_units=good_units,
            avg_pf=avg_pf,
            maintenance_events=maintenance_events
        )

        energy_cost = financial_result["energy_cost_usd"]
        downtime_cost = financial_result["downtime_cost_usd"]
        pf_penalty = financial_result["pf_penalty_usd"]
        maintenance_cost = financial_result["maintenance_cost_usd"]
        total_cost = financial_result["total_operational_cost_usd"]
        carbon_kg = financial_result["carbon_kg"]
        energy_per_unit = financial_result["energy_per_unit_wh"]

        # ===== FIXED: Build evidence_traces from EvidenceTracker at the end =====
        final_evidence_traces = []
        for trace in evidence_tracker.traces:
            final_evidence_traces.append(EvidenceTrace(
                trace_id=trace.trace_id,
                machine_id=trace.machine_id,
                start_timestamp=trace.start_timestamp,
                end_timestamp=trace.end_timestamp,
                steps=[{"step_type": s.step_type, "data": s.data, "description": s.description}
                       for s in trace.steps],
                decision_id=trace.decision_id,
                final_outcome=trace.final_outcome
            ))

        # ===== FIXED: Calculate failure_avoided as "not ever failed" =====
        mid = scenario.fault_machine
        failure_avoided = not machine_ever_failed.get(mid, False)

        recovery_success = mid in recovery_end_t_by_machine

        recovery_time = 0.0
        if mid in recovery_start_t_by_machine and mid in recovery_end_t_by_machine:
            recovery_time = recovery_end_t_by_machine[mid] - recovery_start_t_by_machine[mid]

        # ===== FIXED: downtime_avoided_min and production_loss_units are set to 0 (computed in policies.py) =====
        resilience = ResilienceMetrics(
            recovery_time_min=float(recovery_time),
            production_loss_units=0,  # FIXED: computed in counterfactual
            downtime_avoided_min=0.0,  # FIXED: computed in counterfactual
            recovery_success=recovery_success,
            failure_avoided=failure_avoided
        )

        # ===== 8. Return results =====
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
            availability_pct=oee_result["availability_pct"],
            performance_pct=oee_result["performance_pct"],
            quality_pct=oee_result["quality_pct"],
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
            evidence_traces=final_evidence_traces,
            evidence_tracker=evidence_tracker
        )

    # ===== Helper method to add ACTION evidence =====
    @staticmethod
    def _add_action_evidence(
        evidence_tracker: EvidenceTracker,
        machine_id: str,
        timestamp: int,
        trace_id_by_machine: Dict[str, str],
        action_type: str,
        decision_id: Optional[str],
        health_index: Optional[float],
        rul_minutes: Optional[int]
    ):
        """
        Add ACTION step to the relevant evidence trace.
        Uses trace_id_by_machine to find the correct trace for this machine.
        """
        trace_id = trace_id_by_machine.get(machine_id)
        if trace_id is None:
            # No trace found for this machine - this should not happen if the trace was created before action.
            # As a fallback, find the latest trace for this machine.
            traces = evidence_tracker.get_traces_by_machine(machine_id)
            if traces:
                trace_id = traces[-1].trace_id
            else:
                # No trace exists at all - return without adding action.
                return

        trace = evidence_tracker.get_trace(trace_id)
        if trace:
            # Check if ACTION already exists to avoid duplicates
            step_types = [s.step_type for s in trace.steps]
            if "ACTION" not in step_types:
                evidence_tracker.add_evidence_step(
                    trace,
                    step_type="ACTION",
                    timestamp=timestamp,
                    data={
                        "action": f"Start Maintenance ({action_type})",
                        "decision_id": decision_id,
                        "health_index": health_index,
                        "rul_minutes": rul_minutes
                    },
                    description=f"{action_type} maintenance initiated at t={timestamp}."
                )