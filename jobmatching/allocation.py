"""Fixed-budget bipartite allocation with a solver certificate."""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix


def capacity_matrix(workers, jobs, job_capacity):
    worker_ids, worker_index = np.unique(workers, return_inverse=True)
    job_ids, job_index = np.unique(jobs, return_inverse=True)
    n = len(workers)
    columns = np.tile(np.arange(n), 2)
    rows = np.r_[worker_index, len(worker_ids) + job_index]
    constraints = coo_matrix(
        (np.ones(2 * n), (rows, columns)),
        shape=(len(worker_ids) + len(job_ids), n),
    ).tocsr()
    capacities = np.r_[np.ones(len(worker_ids)), np.full(len(job_ids), job_capacity)]
    return constraints, capacities


def allocate(scores, constraints, capacities, budget):
    """Maximize the total score with one match per worker and a job capacity."""
    cost = -np.asarray(scores, dtype=float)
    result = linprog(
        cost,
        A_ub=constraints,
        b_ub=capacities,
        A_eq=csr_matrix(np.ones((1, len(cost)))),
        b_eq=[budget],
        bounds=(0, 1),
        method="highs",
        options={"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    )
    if not result.success:
        raise RuntimeError(f"Matching failed: {result.message}")
    selected = np.rint(result.x).astype(bool)
    dual = (
        capacities @ result.ineqlin.marginals
        + budget * result.eqlin.marginals[0]
        + result.upper.marginals.sum()
    )
    if (
        np.max(np.abs(result.x - selected)) > 1e-7
        or selected.sum() != budget
        or np.any(constraints @ selected.astype(int) > capacities)
        or abs(result.fun - dual) > 1e-8 * (1 + np.abs(cost).sum())
    ):
        raise RuntimeError("Matching failed its integrality, capacity or duality check")
    return selected
