"""Run the generated-data demo and export capacity-checked decisions."""

import argparse
import csv
import json
from pathlib import Path

from .allocation import allocate
from .simulation import BUDGET, JOB_CAPACITY, POLICIES, generate, run_policies


def evaluate(market, probability, decisions, rounds, seed, drift):
    oracle = {}
    for batch, _, candidates, constraints, capacities, budget in rounds:
        chosen = allocate(probability[candidates], constraints, capacities, budget)
        oracle[batch] = float(probability[candidates][chosen].sum())

    quarterly = []
    allocations = []
    for decision in decisions:
        selected = decision["selected"]
        expected = float(probability[selected].sum())
        bound = oracle[decision["batch"]]
        if expected > bound + 1e-8:
            raise RuntimeError("Policy yield exceeded the feasible oracle bound")
        quarterly.append({
            "policy": decision["policy"],
            "quarter_start": decision["quarter_start"],
            "allocated": len(selected),
            "decay_weight": decision["decay_weight"],
            "visible_labels": decision["visible_labels"],
            "visible_test_labels": decision["visible_test_labels"],
            "followup_attempts": decision["followup_attempts"],
            "expected_invitations": expected,
            "oracle_expected_invitations": bound,
        })
        for row, score in zip(selected, decision["scores"], strict=True):
            allocations.append({
                "policy": decision["policy"],
                "quarter_start": decision["quarter_start"],
                "worker": int(market.workers[row]),
                "job": int(market.jobs[row]),
                "predicted_invitation_probability": float(score),
            })

    totals = {}
    for policy in POLICIES:
        rows = [row for row in quarterly if row["policy"] == policy]
        allocated = sum(row["allocated"] for row in rows)
        expected = sum(row["expected_invitations"] for row in rows)
        bound = sum(row["oracle_expected_invitations"] for row in rows)
        totals[policy] = {
            "allocated": allocated,
            "expected_invitations": expected,
            "oracle_expected_invitations": bound,
            "expected_shortfall_per_100": 100 * max(0, bound - expected) / allocated,
            "followup_attempts": sum(row["followup_attempts"] for row in rows),
        }
    summary = {
        "dataset": market.dataset,
        "seed": seed,
        "drift": drift,
        "workers": int(market.workers.max()) + 1,
        "jobs": int(market.jobs.max()) + 1,
        "worker_capacity": 1,
        "job_capacity": JOB_CAPACITY,
        "budget_per_quarter": BUDGET,
        "test_quarters": len(rounds),
        "policies": totals,
    }
    if market.dataset == "jobtalash_structure":
        summary.pop("budget_per_quarter")
        summary.update({
            "structure_doi": "10.7910/DVN/6YLWJ1",
            "features_and_invitations": "synthetic",
            "historical_edges": int((market.batch < market.first_test_batch).sum()),
            "test_edges": int((market.batch >= market.first_test_batch).sum()),
            "budgets_by_quarter": {date: budget for _, date, _, _, _, budget in rounds},
        })
    return summary, quarterly, allocations


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Run five matching policies with simulated invitation feedback.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--drift", type=float, choices=(0, 0.5, 1), default=1)
    parser.add_argument("--output", type=Path, default=Path("demo-output"), help="A new output directory")
    parser.add_argument("--structure", type=Path, help="Verified JobTalash CSV prepared by jobmatching.jobtalash")
    args = parser.parse_args()
    if not 0 <= args.seed < 2**32:
        parser.error("--seed must be an integer from 0 through 4294967295")
    if args.output.exists():
        parser.error(f"Output directory already exists: {args.output}")

    try:
        market, feedback, probability = generate(args.seed, args.drift, args.structure)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    decisions, rounds = run_policies(market, feedback, args.seed)
    summary, quarterly, allocations = evaluate(market, probability, decisions, rounds, args.seed, args.drift)

    args.output.mkdir(parents=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_csv(args.output / "quarterly.csv", quarterly)
    write_csv(args.output / "allocations.csv", allocations)
    print(f"Wrote {len(quarterly)} policy-quarter rows and {len(allocations)} matches to {args.output}")


if __name__ == "__main__":
    main()
