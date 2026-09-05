# 🏭 PRIME-Factory v6.2

**Smart Multi-Product Packaging Factory - Decision Support System**

> National Competition for AI and Robotics (RoboDam 2026) | Team MSA

---

## 📖 Overview

PRIME-Factory is a simulation-based Industry 4.0 decision-support prototype for a Smart Multi-Product Packaging Factory. It demonstrates system-level integration of:

Predictive Maintenance – Detect and predict equipment failures (Decision-driven, with explicit action codes)

Production Context – Multi-product scheduling and tracking with bottleneck logic

Energy Monitoring – Real-time power consumption, ECI, and unified PF penalty

Decision Support – Explainable AI recommendations with full evidence chain (SENSE → OUTCOME)

Maintenance & Recovery – Causal intervention lifecycle with full recovery after maintenance

Factory KPIs – OEE, throughput, cost, carbon, and resilience metrics

### Core Evidence Chain


SENSE → CONTEXT → DETECT → CONFIRM → HEALTH → RUL → DECIDE → ACTION → OUTCOME


---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip (Python package manager)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/mohamedkhedr6412-cpu/PRIME-Factory.git
cd PRIME-Factory

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # On Windows
# source venv/bin/activate     # On Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

Running the Application

# Run the interactive dashboard
streamlit run dashboard/app.py

# Or use the convenience script
run.bat      # Windows
# ./run.sh   # Linux/Mac

Running Tests

# Run Phase 1 tests (Core simulation)
python test_phase1.py

# Run Phase 2 tests (AI & Decision Engine)
python test_phase2.py

# Run Phase 3 tests (Integration)
python test_phase3.py

# Run all tests
python test_phase1.py && python test_phase2.py && python test_phase3.py

📁 Project Structure

PRIME-Factory/
├── ai/                        # AI & Anomaly Detection
│   ├── anomaly.py            # Persistence & temporal filtering
│   ├── baseline.py           # Layer A: Static thresholds
│   ├── decision.py           # Canonical Decision Engine (v6.2)
│   ├── health_index.py       # HI, RUL, and RUL Validation
│   └── isolation_forest.py   # Layer B: Isolation Forest
│
├── control/                   # Control & decision wrapper
│   └── decision_engine.py    # Dashboard compatibility wrapper
│
├── core/                      # Core models & evidence
│   ├── models.py             # Data models (ScenarioConfig, etc.)
│   └── evidence.py           # Evidence tracker (SENSE → ... → OUTCOME)
│
├── dashboard/                 # Streamlit UI
│   └── app.py                # Main interactive dashboard
│
├── energy/                    # Energy management (Single Source of Truth)
│   ├── eci.py                # Energy Condition Indicator
│   ├── energy_model.py       # Unified Financial & ESG calculations
│   └── peak_shaving.py       # Demand response & Peak Shaving Controller
│
├── evaluation/                # Evaluation & benchmarking
│   ├── kpis.py               # Canonical OEE calculation
│   └── ablation.py           # Layer A-E ablation study (v6.2)
│
├── maintenance/               # Maintenance policies
│   └── policies.py           # What-if analysis & policy comparison
│
├── simulation/                # Factory simulation (Unified Engine)
│   ├── engine.py             # **Unified Simulation Engine** (Core)
│   ├── factory.py            # Packaging line orchestrator (Bottleneck)
│   ├── machines.py           # Individual machine model (Gradual Recovery)
│   ├── state_machine.py      # 8-state asset state machine (Hysteresis fixed)
│   ├── faults.py             # Fault injection profiles
│   └── events.py             # Event logging
│
├── config.py                  # Central configuration (v6.2)
├── main.py                    # Master experiment runner
├── requirements.txt           # Python dependencies
├── test_phase1.py             # Phase 1 tests
├── test_phase2.py             # Phase 2 tests
├── test_phase3.py             # Phase 3 tests
└── README.md                  # This file

🎮 Using the Dashboard

Sidebar Controls
Judge Mode: 3-minute demo flow (Next Demo Step / Reset Pitch)

Product Selection: Choose Product A/B/C

Fault Injection: Select fault type, start time, severity

Machine Selection: Target specific machine

Controls: `Apply Recommended PdM` (immediate), Reset Line

Dashboard Tabs

Tab	Description
📈 Live Telemetry	Real-time sensor data and health index
🔍 Decision Trace	XAI decision card with evidence
🔗 Evidence Chain	Complete SENSE → ... → OUTCOME chain
⚖️ What-If	Intervention vs No intervention comparison
🛡️ Resilience	Recovery and resilience metrics
📋 Events	Audit event log
📊 Benchmark	Policy comparison
🧪 Ablation	Layer A-E detector comparison
📑 Report	Auto-generated experiment report

🧪 Demo: 3-Minute Judge Mode

Time	Action
0:00-0:20	Healthy multi-product baseline
0:20-0:50	Inject M3 bearing degradation
0:50-1:15	Telemetry → anomaly → persistence → HI/RUL
1:15-1:35	Decision Trace: why PdM
1:35-1:55	Apply Recommended PdM (intervention)
1:55-2:15	MAINTENANCE → RECOVERY → NORMAL
2:15-2:45	Show OEE/energy/downtime/cost/carbon impact
2:45-3:00	Paired What-if: intervention vs no intervention

📊 Key Metrics
Metric	Description
OEE	Overall Equipment Effectiveness (Availability × Performance × Quality)
Throughput	Good units per hour
Energy/Unit	Energy consumption per good unit
Health Index (HI)	0-100 composite health score
RUL	Remaining Useful Life (trend-based)
ECI	Energy Condition Indicator (context-aware)
Carbon	CO2 emissions (kg)

🧠 AI Architecture (Layers A-E)
Layer	Description
A	Static thresholds (vibration, temperature, ECI, PF)
B	Raw Isolation Forest (no context)
C	Context-conditioned Isolation Forest
D	Context IF + ECI fusion
E	Full PRIME (Context IF + ECI + Persistence)

📊 Final Benchmark Results (v6.2)
The following table shows the performance of different maintenance policies under identical fault conditions (fault start at t=100, max degradation=0.95).



Policy	Downtime (min)	Events	OEE (%)	Good Units	Energy (kWh)	Peak (kW)	Total Cost ($)	Carbon (kg CO2)	Failure Avoided
CORRECTIVE	181.0	0	50.99%	9,791	216.30	29.87	$1,089.38	97.34	❌ No
PREVENTIVE	10.0	1	95.32%	18,302	231.01	52.28	$343.80	103.95	✅ Yes
PREDICTIVE	10.0	1	95.26%	18,290	231.05	52.38	$343.82	103.97	✅ Yes
PREDICTIVE + PEAK SHAVING	10.0	1	92.76%	17,810	220.03	52.38	$342.13	99.01	✅ Yes

Key Insights

Predictive and Preventive achieve ~95% OEE compared to only ~51% for Corrective.

Total cost is reduced from ~$1,089 to ~$344 (68% reduction).

Peak Shaving reduces energy and carbon footprint, with a slight trade-off in OEE.

Failure Avoided is ✅ Yes for Predictive policies (the asset never entered FAILED state), while Corrective policy fails.

🧪 Running the Master Experiment

python main.py

This generates:

exports/ablation_results.csv - Layer A-E comparison
exports/benchmark_results.csv - Policy comparison
exports/figure1_health_response.png - Publication-grade plot

📦 Dependencies
streamlit>=1.30.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.15.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
pytest>=7.4.0

🎯 Key Features
1. Multi-Product Context
Product A (Light): 0.8 speed, 0.7 load, 0.75 power multiplier

Product B (Medium): 1.0 speed, 1.0 load, 1.00 power multiplier

Product C (Heavy): 1.2 speed, 1.3 load, 1.30 power multiplier

2. 8-State Asset State Machine
NORMAL → DEGRADING → WARNING → PREDICTIVE_ALERT → CRITICAL → FAILED
         ↑                                                    ↓
         └────────────────── RECOVERY ← MAINTENANCE ←─────────┘

3. Health Index Calculation
HI = 100 - (α·anomaly + β·persistence + γ·ECI + δ·physics)

α = 0.30 (AI Anomaly Model)

β = 0.25 (Persistence Filter)

γ = 0.25 (Energy Deviation ECI)

δ = 0.20 (Thermal & Vibration Physics)

4. Evidence Chain
SENSE     → Raw sensor data (vibration, temperature, power)
CONTEXT   → Operating context (product, speed, load)
DETECT    → Raw anomaly score
CONFIRM   → Persistence confirmation (5-sample window)
HEALTH    → Health Index calculation (0-100)
RUL       → Remaining Useful Life (trend-based)
DECIDE    → Decision recommendation
ACTION    → Action taken (maintenance, derating, etc.)
OUTCOME   → Result of action (recovered, failed, etc.)

5. PdM Decision Logic (PRIME Action Gate)

Predictive Maintenance is triggered only when all of the following conditions are met:

Confirmed Anomaly – The anomaly has persisted over the confirmation window.

Persistence Ratio ≥ 0.40 (configurable in config.py).

Risk Indicator – HI ≤ 75 OR RUL ≤ 50 OR Degradation ≥ 0.45.

If an anomaly is confirmed but risk is not yet critical, the system recommends ELEVATE_INSPECTION instead of PdM. This ensures actionable decisions are based on temporal evidence, not single-point alerts.

✅ Acceptance Tests (All Pass)
Criterion	Pass Condition	Status
Baseline	Production, energy, OEE internally consistent	✅
Control	Judge can run scenario without code editing	✅
Causality	Controls/faults/decisions create visible events	✅
State	Machine state changes logically	✅
Prediction	Predictive alert precedes simulated failure	✅
Explainability	Alert has readable evidence	✅
Action	Maintenance executes from UI (immediate)	✅
Recovery	Telemetry/state/KPIs change and machine returns to full health	✅
Energy	Energy/ECI changes consistently	✅
Impact	Paired outcomes are comparable	✅
Integrity	Demo cannot alter benchmark tables	✅
Reproducibility	Exact scenario can be rerun	✅
Presentation	Full causal story understandable in <5 minutes	✅
Test Results: Phase 1 (12/12), Phase 2 (21/21), Phase 3 (6/6) – all pass.

📄 License
This project is for educational and research purposes. All rights reserved.

👥 Team
MSA Team - National Competition for AI and Robotics (RoboDam 2026)

🏆 Competition Presentation Sentence
"PRIME does not only detect a problem — it explains it, predicts its consequence, recommends an action, executes the action in simulation, and measures the result."

Made with ❤️ by Team MSA | PRIME-Factory v6.2