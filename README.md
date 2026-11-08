# Job Matching Lab

[![Synthetic demo](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml/badge.svg)](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml)

[English](#english) · [简体中文](#简体中文) · [Interactive demo / 交互演示](https://gloriashang.github.io/jobmatching-lab/)　( •̀ᴗ•́ )و

**Capacity-constrained worker–job matching with delayed feedback.**  
**在岗位容量有限、反馈延迟的情况下，比较不同的人岗匹配策略。**

## English

Job Matching Lab simulates a platform that recommends a limited number of worker–job pairs each quarter. It estimates each pair’s invitation probability, then optimizes the **whole batch** under worker, job, and recommendation limits. A policy updates from feedback on the pairs it selected, once that feedback becomes available.

### What this project contributes

1. **Prediction to decision.** Turn invitation scores into a batch allocation with explicit worker capacity, job capacity, and quarterly budgets. Measure decision quality against the best feasible allocation using the simulator’s probabilities.
2. **A controlled comparison under delayed feedback.** Compare five policies on the same scenario and resource constraints. Fixed and adaptive mixtures start at the same weight, and each policy updates using the feedback available from its own prior selections.
3. **Reproducible evaluation on two graph types.** Run the same pipeline on a generated graph or a checksum-verified JobTalash delivery graph. The benchmark reports all five policies over ten paired seeds per drift setting, and the bilingual explorer shows how one scenario unfolds quarter by quarter.

### 📊 Explore the interactive demo

Switch the candidate graph, drift strength, and policy to compare the oracle gap, quarterly invitation yield, and adaptive weight. The dashboard uses seed 42 and policy-level aggregates. [Open the interactive demo](https://gloriashang.github.io/jobmatching-lab/)

### 🔎 Choose a data mode

| Mode | Where the worker–job graph comes from | Features and invitations |
|---|---|---|
| **Synthetic demo** | Generated from a seed | Simulated |
| **JobTalash graph** | Public JobTalash worker–job delivery records | Simulated on the observed graph |

The JobTalash mode uses the delivered pairs and dates as the candidate structure. The verified extraction for the research project contains **8,233 delivered pairs, 2,443 workers, and 1,117 jobs**. These counts describe the source graph. Model features, invitation probabilities, and feedback come from the simulator in both modes. Download the original archive from Harvard Dataverse and keep the input and generated records local. [JobTalash replication data](https://doi.org/10.7910/DVN/6YLWJ1)

### Run it

Use Python 3.12. Clone the repository and install the pinned dependencies. The default demo runs offline after installation.

```sh
git clone https://github.com/GloriaShang/jobmatching-lab.git
cd jobmatching-lab
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m jobmatching --output demo-output
```

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv` and use `.venv\Scripts\python.exe` as the interpreter. Use a new output directory for each run. Choose `--seed` to reproduce a scenario and `--drift 0`, `--drift 0.5`, or `--drift 1` to vary how much the simulated market changes over time.

**Run with the JobTalash graph**

Download the public V1 `Data.zip` archive (approximately 1.09 GB), then extract the verified graph locally. Substitute your archive path in the command below. [Download JobTalash Data.zip](https://dataverse.harvard.edu/api/access/datafile/11910436)

```sh
source .venv/bin/activate
python -m pip install -r requirements-jobtalash.txt
python -m jobmatching.jobtalash --archive path/to/Data.zip --output data/jobtalash-structure.csv
python -m jobmatching --structure data/jobtalash-structure.csv --seed 42 --drift 1 --output jobtalash-output
```

If you already extracted the original delivery `.dta`, use `--delivery-dta PATH` in place of `--archive`. On Windows, omit the `source` line and run the `python` commands with `.venv\Scripts\python.exe`.

The experiment uses the observed delivery dates before 2021 for historical training. The eight test quarters in 2021–2022 expose each quarter’s candidates at its start. Quarterly budgets are 17, 17, 21, 6, 37, 27, 18, and 14 pairs per policy. The run produces 40 policy–quarter rows and **785 selected-pair rows** across five policies. This demonstration adapts the research method to a single scenario.

### Read the results

| File | What to look for |
|---|---|
| `summary.json` | Run settings and policy totals |
| `quarterly.csv` | Policy performance and visible feedback by quarter |
| `allocations.csv` | Selected worker–job pairs by policy and quarter |

The five strategies are a static model, equal-weight updates, time-decayed updates, a fixed mixture, and an adaptive mixture. The fixed and adaptive mixtures start with the same weight. **Oracle gap** measures how many fewer expected invitations a policy earns per 100 allocated pairs than the best feasible allocation under the simulator’s true probabilities. Lower is better.

The default synthetic run uses seed 42 and strong drift. It creates 72 workers and 24 jobs and selects 24 pairs per quarter for each policy over eight quarters. The resulting **40 policy–quarter rows and 960 selected-pair rows** cover all five policies. The table shows this particular synthetic run.

| Policy | Expected invitations | Oracle gap per 100 pairs |
|---|---:|---:|
| Static | 40.50 | 19.98 |
| Equal weight | 40.28 | 20.09 |
| Time decay | 44.27 | 18.01 |
| Fixed mixture | 40.51 | 19.97 |
| Adaptive mixture | 46.38 | 16.91 |

### JobTalash benchmark

The table averages 10 paired seeds, 42–51, in each drift setting on the same JobTalash graph. The five policy columns show the mean oracle gap per 100 selected pairs, where lower is better. The last column gives the adaptive policy’s extra simulated expected invitations relative to the fixed mixture, per 100 selected pairs.

| Drift | Static | Equal weight | Time decay | Fixed mixture | Adaptive mixture | Adaptive − fixed |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0.160 | 0.158 | 0.628 | 0.161 | 0.164 | -0.003 |
| 0.5 | 2.689 | 2.672 | 2.343 | 2.656 | 2.482 | +0.175 |
| 1 | 24.521 | 24.524 | 22.766 | 24.518 | 23.168 | +1.350 |

The adaptive mixture beats the fixed mixture on average under strong drift in this benchmark. Time decay has the smallest mean gap in the same setting. To reproduce the table, run the JobTalash CLI for seeds 42–51 at each drift level, then average each policy’s `expected_shortfall_per_100` from `summary.json`. Each run uses 157 allocated pairs per policy. The dashboard shows one seed, while this table summarizes ten.

### Explore the code

| Module | Role |
|---|---|
| [`jobmatching/jobtalash.py`](jobmatching/jobtalash.py) | Validates the source archive and extracts the delivery graph locally |
| [`jobmatching/simulation.py`](jobmatching/simulation.py) | Builds the experiment and runs the policies quarter by quarter |
| [`jobmatching/learner.py`](jobmatching/learner.py) | Fits the prediction models and updates the adaptive mixture |
| [`jobmatching/allocation.py`](jobmatching/allocation.py) | Solves the capacity-constrained assignment and checks feasibility |
| [`jobmatching/__main__.py`](jobmatching/__main__.py) | Runs the CLI and writes experiment outputs |

GitHub Actions installs the dependencies and runs the synthetic demo. The data archive is acquired separately for the JobTalash run. [Workflow runs](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml)

**Topics** `job-matching` · `jobtalash` · `bipartite-matching` · `operations-research` · `linear-programming` · `delayed-feedback` · `concept-drift` · `simulation` · `reproducible-research` · `python` · `scipy`

[简体中文](#简体中文) · [Back to top](#job-matching-lab)

## 简体中文

Job Matching Lab 模拟一个按季度推荐岗位的平台。系统先估计每对「求职者—岗位」收到邀请的概率，再考虑求职者容量、岗位容量和推荐总量，求出**整批推荐方案**。每种策略只能用自己选中的配对已经返回的反馈更新模型。

### 这个项目贡献了什么

1. **把预测接到分配决策。** 将邀请概率用于整批推荐，明确约束求职者容量、岗位容量和每季度推荐名额，并计算策略与模拟最优可行分配的差距。
2. **把延迟反馈做成可比较的实验。** 五种策略面对同一场景和资源约束，固定混合与自适应混合从相同权重起步。每种策略只用自己选中、且已经返回的反馈更新。
3. **让实验能在两种候选图上复跑。** 同一套流程支持合成图和经校验的 JobTalash 投递图。基准表汇报每档漂移下五种策略在十个种子上的均值，双语交互页展示其中一个种子的季度变化。

### 📊 在线交互演示

在页面中切换数据模式、漂移强度和匹配策略，即可查看最优分配差距、季度预期邀请走势和自适应权重。页面显示种子 42 的策略汇总。[打开交互演示](https://gloriashang.github.io/jobmatching-lab/)

### 🔎 选择数据模式

| 模式 | 人岗配对结构 | 特征与邀请结果 |
|---|---|---|
| **合成演示** | 按随机种子生成 | 模拟生成 |
| **JobTalash 真实结构** | 公开数据中的岗位推送记录 | 在真实配对结构上模拟生成 |

JobTalash 模式把记录中的人岗配对和日期作为候选结构。原研究经核验提取出 **8,233 条推送配对、2,443 名求职者和 1,117 个岗位**，这些数字描述的是来源图。在两种模式中，模型特征、邀请概率和反馈均由模拟器生成。输入文件和运行结果保存在本地。[JobTalash 复现数据](https://doi.org/10.7910/DVN/6YLWJ1)

### ▶️ 快速运行

先按上方 [Quick start](#run-it) 安装 Python 3.12 环境及固定版本依赖。之后可离线运行演示。

```sh
.venv/bin/python -m jobmatching --output demo-output
```

Windows PowerShell 中用 `.venv\Scripts\python.exe` 替换解释器路径。每次运行请选择新的输出目录。`--seed` 用于复现同一情景，`--drift 0`、`--drift 0.5` 和 `--drift 1` 分别对应稳定、中等变化和强变化的模拟市场。

**使用 JobTalash 真实结构运行**

下载 V1 公开归档 `Data.zip`（约 1.09 GB），然后在本地提取经校验的配对结构。运行时将示例中的路径替换成自己的归档路径。[下载 JobTalash Data.zip](https://dataverse.harvard.edu/api/access/datafile/11910436)

```sh
source .venv/bin/activate
python -m pip install -r requirements-jobtalash.txt
python -m jobmatching.jobtalash --archive path/to/Data.zip --output data/jobtalash-structure.csv
python -m jobmatching --structure data/jobtalash-structure.csv --seed 42 --drift 1 --output jobtalash-output
```

如果已经解压出原始推送 `.dta` 文件，可用 `--delivery-dta PATH` 替代 `--archive`。Windows 用户可以跳过 `source` 这行，用 `.venv\Scripts\python.exe` 执行后面的 Python 命令。

历史训练使用 2021 年前的实际推送日期，2021–2022 年的八个测试季度按季初开放该季候选配对。每种策略各季度的推荐名额为 17、17、21、6、37、27、18、14 对。五种策略合计输出 40 条策略季度汇总和 **785 条配对记录**。这是根据研究方法搭建的单情景演示。

### 📊 怎么读结果

| 文件 | 内容 |
|---|---|
| `summary.json` | 运行设定与各策略总指标 |
| `quarterly.csv` | 各策略每季度的表现及已返回反馈 |
| `allocations.csv` | 各策略每季度选中的人岗配对 |

项目比较静态、等权更新、时间衰减、固定混合和自适应混合五种策略。固定混合和自适应混合从相同权重起步。**最优分配差距**表示每推荐 100 对，某策略相对于知道模拟真实概率的最优可行方案少获得多少次期望邀请，越低越好。

默认演示以种子 42 和强变化情景运行。它生成 72 名求职者和 24 个岗位，每种策略每季度选择 24 对。五种策略运行八个季度后，输出 **40 条策略季度汇总和 960 条配对记录**。具体指标见上方 [Example run](#read-the-results)。

真实图基准对每档漂移使用了 10 个种子（42–51）。强漂移下，自适应混合比固定混合每百对平均多 1.350 次模拟期望邀请。时间衰减策略在同一设置下的平均差距最小。[查看五种策略的完整基准表](#jobtalash-benchmark)

代码结构见上方 [Explore the code](#explore-the-code)。GitHub Actions 会安装依赖并运行合成演示。[验证记录](https://github.com/GloriaShang/jobmatching-lab/actions/workflows/smoke.yml)

**关键词** 人岗匹配 · JobTalash · 二部图匹配 · 运筹优化 · 线性规划 · 延迟反馈 · 概念漂移 · 仿真实验 · 可复现研究 · Python · SciPy

[English](#english) · [返回顶部](#job-matching-lab)

This repository is a public research preview. A software license has not yet been selected.  
本仓库为公开研究预览，软件许可证待定。
