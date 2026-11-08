# Job Matching Lab

[![Synthetic demo](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml/badge.svg)](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml)

An offline Python lab for studying how delayed feedback affects worker–job matching. Each quarter, the allocator ranks eligible worker–job pairs and selects a fixed number of matches under worker and job capacity limits. Five policies receive feedback on their own selections and are compared against a simulated oracle.

本项目用合成数据演示容量约束下的人岗匹配，比较五种策略在反馈延迟时的表现。安装依赖后可离线运行。

## Quick start

Use Python 3.12. In the project folder, create an environment and install the pinned dependencies.

```sh
git clone https://github.com/GloriaShang/jobmatching-lab.git
cd jobmatching-lab
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m jobmatching --output demo-output
```

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv` and use `.venv\Scripts\python.exe` for the last two commands. The simulation runs offline after dependency installation. Choose a new output directory for each run.

```sh
.venv/bin/python -m jobmatching --seed 2026121000 --drift 1 --output strong-drift-output
```

## Results

| File | Contents |
|---|---|
| `summary.json` | Run configuration and policy-level scores |
| `quarterly.csv` | Policy performance and feedback by quarter |
| `allocations.csv` | Selected synthetic worker–job pairs for each policy and quarter |

The demo compares a static model, equal-weight updates, time-decayed updates, a fixed mixture and an adaptive mixture. Each policy generates its own feedback from the pairs it selects. Five policies over eight quarters produce 40 summary rows and 960 selected pairs. The evaluator uses simulated invitation probabilities to calculate expected yield and regret against the capacity-constrained oracle allocation. In `summary.json`, `expected_shortfall_per_100` expresses the oracle gap per 100 selected pairs. Lower values indicate a smaller gap.

## Example run

The default scenario uses seed 42 and strong drift. It generates 72 workers and 24 jobs, selects 24 pairs per policy each quarter, and scores eight test quarters.

| Policy | Expected invitations | Oracle gap per 100 pairs |
|---|---:|---:|
| `static` | 40.50 | 19.98 |
| `uniform` | 40.28 | 20.09 |
| `decay` | 44.27 | 18.01 |
| `fixed_mix` | 40.51 | 19.97 |
| `adaptive` | 46.38 | 16.91 |

Each row uses 192 selected pairs. These figures describe one simulated scenario. Use `--drift 0`, `--drift 0.5`, or `--drift 1` to compare stable, moderate, and strong drift.

## How the code is organized

| File | Role |
|---|---|
| `jobmatching/simulation.py` | Generates the market and delayed feedback, and runs the five policies |
| `jobmatching/learner.py` | Fits the equal-weight and recency-weighted experts and updates their mixture |
| `jobmatching/allocation.py` | Solves the capacity-constrained allocation and checks feasibility |
| `jobmatching/__main__.py` | Evaluates the oracle gap and writes JSON and CSV outputs |

## Data and provenance

The CLI generates the entire demonstration from the requested seed. The demo adapts the policy and allocation code from the matched-initialization experiment in the Job Matching research draft. The draft’s larger experiments use a delivered-edge graph from the JobTalash replication dataset. The results from this repository describe the generated demonstration. [JobTalash data record](https://doi.org/10.7910/DVN/6YLWJ1)

## Release status

This public preview provides the synthetic demonstration from version `0.1.0-rc1`. A software license has not yet been selected.
