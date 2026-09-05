# PRIME-Factory

## An Industry 4.0 Platform for Predictive, Resilient, and Intelligent Manufacturing with Energy Efficiency

**Smart Multi-Product Packaging Factory — Simulation-Based Decision Support System**

> **Competition:** RoboDam 2026 — National Competition for AI and Robotics

---

## 1. Overview

**PRIME-Factory** is a simulation-based Industry 4.0 platform designed to demonstrate how **Artificial Intelligence, Predictive Maintenance, Energy Management, and Manufacturing Intelligence** can be integrated into a unified manufacturing decision-support system.

The platform models a **Smart Multi-Product Packaging Factory** and connects the complete operational chain:

**Machine Telemetry → Anomaly Detection → Health Assessment → Degradation/RUL Estimation → Decision → Maintenance Action → Recovery → Production & Energy KPIs**

Rather than evaluating each technology independently, PRIME-Factory demonstrates how these technologies can cooperate to support manufacturing decisions under equipment degradation and changing production conditions.

### Core Capabilities

* Predictive Maintenance & Anomaly Detection
* Machine Health Index (HI)
* Trend-based Remaining Useful Life (RUL) estimation
* AI-assisted maintenance decision making
* Multi-product production modeling
* Energy monitoring and optimization
* Peak-demand management
* OEE and manufacturing KPI analysis
* Maintenance and downtime cost modeling
* Resilience assessment
* Explainable AI decision traces
* Evidence-chain / auditability framework
* Controlled policy benchmarking
* AI ablation experiments
* Interactive Streamlit dashboard

---

# 2. Problem

Modern manufacturing systems must simultaneously address several interconnected challenges:

* Unexpected equipment failures
* Production downtime
* Maintenance cost
* Energy consumption
* Peak electrical demand
* Product-mix effects on production performance
* Limited visibility into machine degradation
* Difficulty connecting AI predictions to actionable maintenance decisions

A predictive-maintenance model alone does not solve these problems.

The practical challenge is to create a system that can transform machine data into a **traceable operational decision**, execute an appropriate intervention, and measure its effect on production, energy, cost, and resilience.

---

# 3. PRIME-Factory Solution

PRIME-Factory addresses this challenge through an integrated decision-support architecture.

### End-to-End Architecture

```text
┌───────────────────────┐
│   Factory Simulation  │
│ Machines + Production │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Machine Telemetry   │
│ Speed / Load / Temp   │
│ Vibration / Current   │
│ Power                 │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ AI Anomaly Detection  │
│   Isolation Forest    │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Health & Degradation  │
│     Assessment        │
└───────────┬───────────┘
            │
       ┌────┴────┐
       ▼         ▼
┌────────────┐ ┌────────────┐
│     HI     │ │    RUL     │
│ Assessment │ │ Estimation │
└─────┬──────┘ └─────┬──────┘
      └──────┬───────┘
             ▼
┌───────────────────────┐
│   Decision Engine     │
│ Confirm + Risk Gate   │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Maintenance Action    │
│ Predictive / Prevent. │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Recovery & Production │
└───────────┬───────────┘
            │
            ▼
┌────────────────────────────┐
│ KPI / Energy / Cost / OEE │
│ Resilience / Carbon       │
└────────────────────────────┘
```

---

# 4. Smart Factory Scenario

The platform models a **Smart Multi-Product Packaging Factory** containing multiple production stages and machines.

The simulation supports different products with different production requirements and cycle-time characteristics.

This allows PRIME-Factory to evaluate:

* Production throughput
* Product mix
* Machine utilization
* Equipment degradation
* Maintenance interventions
* Energy consumption
* Peak demand
* Production losses
* Overall Equipment Effectiveness
* Operational cost
* Carbon emissions
* Recovery behavior

---

# 5. AI & Predictive Maintenance

## 5.1 Anomaly Detection

PRIME-Factory uses **Isolation Forest** for unsupervised anomaly detection.

The model operates on machine telemetry including:

* Speed
* Load factor
* Vibration
* Temperature
* Current
* Power

The anomaly-detection model is trained using a healthy pre-fault period before being evaluated against the degraded operating condition.

This prevents the fault period from being directly used as training data.

---

## 5.2 Machine Health Index

The platform combines normalized machine indicators into a project-defined **Health Index (HI)**.

The HI provides a compact representation of machine condition and supports the downstream maintenance decision process.

The HI is used together with other risk indicators rather than being treated as a standalone failure predictor.

---

## 5.3 Degradation & RUL

PRIME-Factory provides a trend-based degradation and Remaining Useful Life (RUL) estimation for decision-support purposes.

The RUL component is intended to provide an operational estimate of remaining time before the simulated failure condition under the evaluated scenario.

It should therefore be interpreted as a **decision-support indicator**, not as a universally calibrated industrial RUL predictor.

---

# 6. Decision Intelligence

One of the main contributions of PRIME-Factory is the connection between AI detection and an explicit maintenance decision.

The system does not execute predictive maintenance simply because an anomaly is detected.

Instead, the decision process considers:

```text
Anomaly
   +
Persistence
   +
Risk Indicator
   +
Machine / State Validation
   ↓
Maintenance Decision
```

A predictive maintenance action is executed only when the required decision conditions are satisfied.

This creates a clear separation between:

**Detection → Risk Assessment → Decision → Action**

---

# 7. Evidence Chain

PRIME-Factory provides an auditable evidence chain for maintenance decisions.

```text
SENSE
  ↓
CONTEXT
  ↓
DETECT
  ↓
CONFIRM
  ↓
HEALTH
  ↓
RUL
  ↓
DECIDE
  ↓
ACTION
  ↓
OUTCOME
```

This enables the user or evaluator to understand:

1. What the machine was doing
2. What abnormal behavior was detected
3. Whether the anomaly was confirmed
4. How machine health was evaluated
5. What degradation/RUL indicators showed
6. Why the decision engine selected an action
7. What maintenance action was executed
8. What happened afterward

This traceability is particularly important when AI is used for operational decision support.

---

# 8. Maintenance Policies

PRIME-Factory evaluates three maintenance strategies:

### Corrective Maintenance

Maintenance is performed after the simulated failure occurs.

### Preventive Maintenance

Maintenance is performed according to a predefined maintenance schedule.

### Predictive Maintenance

Maintenance is triggered through the AI-based decision process after sufficient evidence of degradation/risk is established.

The system also evaluates:

### Predictive Maintenance + Peak Shaving

This combines predictive maintenance with an energy-management strategy designed to reduce demand during the configured peak window.

---

# 9. Energy Management

Energy behavior is explicitly modeled as part of the factory simulation.

The platform tracks:

* Total energy consumption
* Energy per produced unit
* Peak power demand
* Energy cost
* Power-factor penalty
* Carbon emissions
* Peak-shaving impact

The energy-management layer is connected to production decisions rather than being treated as an isolated energy calculator.

---

## Peak Shaving

During the configured peak period, the Peak Shaving Controller can apply a controlled production-speed reduction.

The objective is to reduce electrical demand while measuring the associated production trade-off.

Therefore, peak shaving is evaluated using multiple KPIs rather than assuming that lower energy consumption is automatically better.

---

# 10. Manufacturing KPIs

PRIME-Factory evaluates manufacturing performance using several operational KPIs.

### OEE

Overall Equipment Effectiveness is calculated from:

* Availability
* Performance
* Quality

The production model accounts for the actual product mix and the corresponding ideal cycle-time characteristics.

### Additional KPIs

* Good Units
* Downtime
* Throughput
* Energy Consumption
* Energy per Unit
* Peak Demand
* Total Operational Cost
* Carbon Emissions
* Maintenance Events
* Failure Avoidance
* Production Loss Avoidance
* Downtime Avoidance

---

# 11. Operational Cost Model

The total operational cost is modeled as:

```text
Total Cost
=
Energy Cost
+ Downtime Cost
+ Power-Factor Penalty
+ Maintenance Cost
```

This allows the system to evaluate maintenance strategies using an economic perspective in addition to purely technical KPIs.

---

# 12. Resilience Evaluation

PRIME-Factory evaluates the ability of the predictive strategy to avoid or mitigate the consequences of the simulated failure.

The resilience analysis considers:

* Failure avoided
* Downtime avoided
* Production loss avoided
* Cost saved
* Recovery success

The comparison is performed under controlled simulation conditions using the same general scenario configuration for the evaluated policies.

---

# 13. Scientific Benchmark

The platform includes a controlled benchmark comparing:

1. Corrective Maintenance
2. Preventive Maintenance
3. Predictive Maintenance
4. Predictive Maintenance + Peak Shaving

### Benchmark Results

| Policy                    | Downtime (min) | OEE (%) | Good Units | Energy (kWh) | Peak (kW) | Total Cost ($) | Carbon (kg CO₂) | Failure Avoided |
| ------------------------- | -------------: | ------: | ---------: | -----------: | --------: | -------------: | --------------: | --------------- |
| Corrective                |          181.0 |   50.99 |      9,791 |       216.30 |     29.87 |       1,089.38 |           97.34 | ❌ No            |
| Preventive                |           10.0 |   95.32 |     18,302 |       231.01 |     52.28 |         343.80 |          103.95 | ✅ Yes           |
| Predictive                |           10.0 |   95.26 |     18,290 |       231.05 |     52.38 |         343.82 |          103.97 | ✅ Yes           |
| Predictive + Peak Shaving |           10.0 |   92.76 |     17,810 |       220.03 |     52.38 |         342.13 |           99.01 | ✅ Yes           |

### Interpretation

The benchmark demonstrates the expected trade-offs within the evaluated scenario.

Compared with corrective maintenance, predictive maintenance substantially reduces simulated downtime and improves production performance.

The peak-shaving configuration reduces energy consumption and carbon emissions further, while introducing a measurable production/OEE trade-off.

These results should be interpreted as **controlled simulation results for the defined factory scenario**, rather than universal claims about all industrial environments.

---

# 14. AI Ablation Study

PRIME-Factory includes an ablation framework for evaluating the contribution of different AI architecture components.

The evaluated architecture progressively incorporates additional information and processing layers.

The ablation study is intended to answer:

> Which components of the AI pipeline contribute most effectively to anomaly detection and maintenance decision support?

The results are exported automatically for further analysis.

Importantly, the ablation results are interpreted as **functional trade-offs between detection behavior, false alarms, and lead time**, rather than assuming that every additional layer must monotonically improve every metric.

---

# 15. Interactive Dashboard

PRIME-Factory includes a Streamlit-based interactive dashboard.

### Dashboard Features

* Live machine telemetry
* Machine Health Index
* RUL estimation
* Fault injection
* Product selection
* Machine selection
* Predictive maintenance decisions
* XAI decision trace
* Evidence chain
* What-If analysis
* Resilience analysis
* Audit event log
* Scientific benchmark
* AI ablation study
* Experiment report
* CSV/JSON exports

---

# 16. Judge Mode

A dedicated **3-minute Judge Mode** is provided for rapid demonstration.

### Step 1 — Healthy Baseline

Demonstrate normal multi-product factory operation and baseline KPIs.

### Step 2 — Machine Degradation

Inject a degradation scenario into the selected machine and observe:

* Telemetry changes
* Anomaly detection
* Health deterioration
* RUL trend
* AI decision reasoning

### Step 3 — Predictive Intervention

Demonstrate:

* Predictive maintenance decision
* Maintenance execution
* Recovery
* Production continuity
* KPI impact
* What-If / ROI comparison

The purpose of Judge Mode is to demonstrate the complete **Sense → Decide → Act → Recover → Measure** loop within a short presentation.

---

# 17. Explainable AI

PRIME-Factory provides an XAI-oriented decision trace showing the information used by the decision layer.

The system separates:

```text
Observed Data
      ↓
Detected Anomaly
      ↓
Confirmed Condition
      ↓
Health / Risk Indicators
      ↓
Decision
      ↓
Action
```

This improves transparency and allows evaluators to inspect why a maintenance action was triggered.

---

# 18. Reproducibility

The project includes automated validation and experiment-export mechanisms.

### Acceptance Tests

* Phase 1: **12/12 PASS**
* Phase 2: **21/21 PASS**
* Phase 3: **6/6 PASS**

The tests cover core simulation behavior, maintenance logic, energy functionality, KPI calculations, decision logic, and related system components. Phase 3 contains a long-running integration test for end-to-end validation.

Generated experiment outputs include:

```text
exports/
├── benchmark_results.csv
├── ablation_results.csv
└── ...
```

---

# 19. Project Structure

PRIME-Factory/
├── ai/                                # AI & Anomaly Detection
│   ├── anomaly.py                     # Persistence & temporal filtering
│   ├── baseline.py                    # Layer A: Static thresholds
│   ├── decision.py                    # Canonical Decision Engine (v6.2)
│   ├── health_index.py                # HI, RUL, and RUL Validation
│   └── isolation_forest.py            # Layer B: Isolation Forest
│
├── control/                           # Control & decision wrapper
│   └── decision_engine.py             # Dashboard compatibility wrapper
│
├── core/                              # Core models & evidence
│   ├── evidence.py                    # Evidence tracker (SENSE → ... → OUTCOME)
│   └── models.py                      # Data models (ScenarioConfig, etc.)
│
├── dashboard/                         # Streamlit UI
│   └── app.py                         # Main interactive dashboard
│
├── energy/                            # Energy management (Single Source of Truth)
│   ├── eci.py                         # Energy Condition Indicator
│   ├── energy_model.py                # Unified Financial & ESG calculations
│   └── peak_shaving.py                # Demand response & Peak Shaving Controller
│
├── evaluation/                        # Evaluation & benchmarking
│   ├── ablation.py                    # Layer A-E ablation study (v6.2)
│   └── kpis.py                        # Canonical OEE calculation
│
├── maintenance/                       # Maintenance policies
│   └── policies.py                    # What-if analysis & policy comparison
│
├── simulation/                        # Factory simulation (Unified Engine)
│   ├── engine.py                      # Unified Simulation Engine (Core)
│   ├── events.py                      # Event logging
│   ├── factory.py                     # Packaging line orchestrator (Bottleneck)
│   ├── faults.py                      # Fault injection profiles
│   ├── machines.py                    # Individual machine model (Gradual Recovery)
│   └── state_machine.py               # 8-state asset state machine (Hysteresis fixed)
│
├── config.py                          # Central configuration (v6.2)
├── main.py                            # Master experiment runner
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── test_phase1.py                     # Phase 1 tests
├── test_phase2.py                     # Phase 2 tests
└── test_phase3.py                     # Phase 3 tests


---

# 20. Installation

Clone the repository and install the required dependencies:

```bash
pip install -r requirements.txt
```

---

# 21. Run the Dashboard

Start the Streamlit dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard provides the complete interactive environment for exploring the factory simulation and its decision-support capabilities.

The dashboard is also hosted online for demonstration:
https://prime-factory-demo.streamlit.app/

---

# 22. Run Experiments

The project includes an experiment runner:

```bash
python main.py
```

The experiment runner generates the following outputs:
- `exports/benchmark_results.csv` – Policy comparison
- `exports/ablation_results.csv` – AI layer comparison
- `exports/figure1_health_response.png` – Health index and telemetry plot
---

# 23. Testing

Run the project's automated tests using the configured test command.

The current validation status is:

```text
Phase 1     12/12 PASS
Phase 2     21/21 PASS
Phase 3      6/6 PASS
-----------------------
TOTAL       39/39 PASS
```

These tests validate the implemented software components and do not replace industrial field validation.

---

# 24. Scope & Limitations

PRIME-Factory is a **simulation-based Industry 4.0 proof-of-concept** developed for research demonstration and competition evaluation.

The following limitations should be considered:

### Simulation-Based Model

The factory, machine behavior, degradation, energy consumption, and failure behavior are simulated.

Therefore, the results should not be interpreted as direct measurements from a real production plant.

### Trend-Based RUL

The RUL module provides a trend-based estimate intended for decision support.

It is not presented as a universally calibrated industrial RUL model.

### Engineering Parameters

Some model parameters, including Health Index weights and decision thresholds, are engineering design choices for the project scenario.

They should be calibrated using real industrial datasets before production deployment.

### Scenario-Based Benchmark

The benchmark compares maintenance strategies under controlled simulation conditions.

It demonstrates system behavior within the defined scenario rather than providing universal causal evidence for all factories.

### Industrial Deployment

PRIME-Factory is not claimed to be a production-ready industrial control or maintenance system.

Deployment in a real factory would require:

* Real sensor data
* Industrial communication interfaces
* PLC/SCADA/MES integration
* Historical failure datasets
* Model validation
* Cybersecurity controls
* Safety validation
* Site-specific calibration
* Hardware-in-the-loop or field testing

---

# 25. Research & Engineering Contribution

The main contribution of PRIME-Factory is not a single isolated AI algorithm.

Instead, the project demonstrates an integrated architecture connecting:

**AI → Machine Health → Maintenance Decision → Physical/Operational Action → Recovery → Production → Energy → Cost → Resilience**

This integration provides a practical framework for demonstrating how Industry 4.0 technologies can work together within a manufacturing environment.

---

# 26. Why PRIME-Factory?

Traditional predictive-maintenance demonstrations often stop at:

```text
Sensor Data → AI Model → Prediction
```

PRIME-Factory extends this concept to:

```text
Sensor Data
     ↓
AI Detection
     ↓
Health & Risk Assessment
     ↓
Maintenance Decision
     ↓
Maintenance Action
     ↓
Recovery
     ↓
Production Impact
     ↓
Energy Impact
     ↓
Cost Impact
     ↓
Resilience Evaluation
```

This makes the platform a **decision-support demonstration**, rather than simply an anomaly-detection model.

---

# 27. Competition Demonstration Message

### PRIME-Factory demonstrates:

> **How AI can move from detecting machine degradation to supporting an actionable, traceable, and measurable manufacturing decision.**

The system connects predictive maintenance with:

* Smart manufacturing
* Energy management
* Production optimization
* Operational cost
* Resilience
* Explainability
* Auditability

within one integrated simulation environment.

---

# 28. Final Project Positioning

PRIME-Factory should be presented as:

**A simulation-based Industry 4.0 decision-support platform and research proof-of-concept.**

It demonstrates the integration of:

**Predictive Maintenance + AI + Smart Manufacturing + Energy Management + Resilience**

within a unified manufacturing scenario.

The project intentionally focuses on demonstrating the **architecture, decision logic, measurable KPIs, and integration of Industry 4.0 concepts**, while clearly distinguishing simulation results from real-world industrial validation.

---

## License

This project is developed for educational, research, and competition purposes.

---

## Team

**PRIME-Factory Team**

**RoboDam 2026 — National Competition for AI and Robotics**
