"""Generated matching market and independent policy-owned feedback streams."""

from dataclasses import dataclass

import numpy as np
from scipy.special import expit, logit

from .allocation import allocate, capacity_matrix
from .learner import HALF_LIVES, INITIAL_DECAY_WEIGHT, adaptive_weight, fit, log_loss, predict

POLICIES = ("static", "uniform", "decay", "fixed_mix", "adaptive")
WORKER_COUNT = 72
JOB_COUNT = 24
JOB_CAPACITY = 3
BUDGET = 24
TEST_START = "2021-01-01"
# Thirty percent of each quarter's maximum feasible cardinality with job capacity 3.
JOBTALASH_BUDGETS = (17, 17, 21, 6, 37, 27, 18, 14)


def day_number(date):
    return int(np.datetime64(date, "D").astype(int))


@dataclass
class Market:
    workers: np.ndarray
    jobs: np.ndarray
    features: np.ndarray
    batch: np.ndarray
    delivery: np.ndarray
    dates: tuple
    tie_break: np.ndarray
    first_test_batch: int
    test_budgets: tuple
    dataset: str


@dataclass
class Feedback:
    label: np.ndarray
    natural_delay: np.ndarray


def generate(seed, drift, structure=None):
    """Simulate invitation times on a generated or recorded delivery graph."""
    rng = np.random.default_rng(seed)
    first_year = 2019
    if structure is not None:
        from .jobtalash import read_structure

        workers, jobs, recorded_delivery, quarters = read_structure(structure)
        first_year = int(str(recorded_delivery.min())[:4])
    dates = tuple(
        f"{year}-{month:02d}-01" for year in range(first_year, 2023) for month in (1, 4, 7, 10)
    )
    first_test_batch = dates.index(TEST_START)
    quarter_days = np.array([day_number(date) for date in dates])
    if structure is None:
        worker_features = rng.normal(size=(WORKER_COUNT, 3))
        job_features = rng.normal(size=(JOB_COUNT, 3))
        jobs = np.concatenate([
            rng.choice(JOB_COUNT, 3, replace=False) for _ in range(len(dates) * WORKER_COUNT)
        ])
        workers = np.tile(np.repeat(np.arange(WORKER_COUNT), 3), len(dates))
        batch = np.repeat(np.arange(len(dates)), WORKER_COUNT * 3)
        delivery = quarter_days[batch]
        test_budgets = (BUDGET,) * (len(dates) - first_test_batch)
        dataset = "synthetic"
    else:
        worker_features = rng.normal(size=(int(workers.max()) + 1, 3))
        job_features = rng.normal(size=(int(jobs.max()) + 1, 3))
        quarter_index = {
            f"{date[:4]}Q{(int(date[5:7]) - 1) // 3 + 1}": index
            for index, date in enumerate(dates)
        }
        batch = np.array([quarter_index[quarter] for quarter in quarters])
        # Historical labels follow recorded delivery days. Test candidates arrive as quarterly batches.
        delivery = np.where(batch < first_test_batch, recorded_delivery.astype(int), quarter_days[batch])
        test_budgets = JOBTALASH_BUDGETS
        dataset = "jobtalash_structure"
    w, j = worker_features[workers], job_features[jobs]
    features = np.column_stack([w, j, w[:, 0] * j[:, 0], np.abs(w[:, 1] - j[:, 1])])
    eta = -0.8 + features @ [0.7, -0.4, 0.25, -0.6, 0.35, 0.3, 0.5, -0.25]
    drift_scale = np.array([0 if date < TEST_START else (1 if date < "2022-01-01" else 1.5)
                            for date in dates])[batch] * drift
    eta += drift_scale * (-0.35 + features @ [-0.8, 0.25, 0, 0.8, -0.3, 0, -0.5, 0.2])
    draws = np.clip(rng.random(len(eta)), 1e-12, 1 - 1e-12)
    invitation_days = 30 * np.exp((logit(draws) - eta) / 1.6)
    label = invitation_days <= 30
    retained = rng.random(len(eta)) < 0.6
    natural_delay = np.where(retained, np.minimum(invitation_days, 30) + 7, np.inf)
    market = Market(workers, jobs, features, batch, delivery, dates, rng.random(len(eta)),
                    first_test_batch, test_budgets, dataset)
    return market, Feedback(label, natural_delay), expit(eta)


class FeedbackWorld:
    """Own exposures and return only mature labels reported before a decision."""

    def __init__(self, market, feedback):
        self.market = market
        self._feedback = feedback
        history = market.batch < market.first_test_batch
        self.delivery = np.where(history, market.delivery, np.inf)
        self.report = self.delivery + feedback.natural_delay

    def expose(self, indices, cutoff):
        if np.isfinite(self.delivery[indices]).any() or np.any(self.market.delivery[indices] != cutoff):
            raise RuntimeError("A policy can expose only current candidates it has never exposed")
        self.delivery[indices] = cutoff
        self.report[indices] = cutoff + self._feedback.natural_delay[indices]

    def view(self, cutoff):
        visible = np.flatnonzero((self.delivery + 30 < cutoff) & (self.report < cutoff))
        return visible, self._feedback.label[visible].astype(float), self.delivery[visible]

    def follow_up(self, cutoff, seed, batch, budget):
        request = cutoff - 14
        eligible = np.flatnonzero(
            (self.market.batch >= self.market.first_test_batch)
            & (self.delivery >= request - 180)
            & (self.delivery + 30 < request)
            & (self.report >= request)
        )
        rng = np.random.default_rng([seed, batch])
        priority = rng.random(len(self.delivery))
        response = rng.random(len(self.delivery))
        chosen = eligible[np.argsort(priority[eligible])[: budget // 2]]
        successful = chosen[response[chosen] < 0.75]
        self.report[successful] = np.minimum(self.report[successful], request + 7)
        return len(chosen)


def fit_initial_experts(market, feedback):
    world = FeedbackWorld(market, feedback)
    validation_start = day_number("2020-01-01")
    test_start = day_number(TEST_START)
    past = market.delivery + 30 < validation_start
    training_features = market.features[past]
    features = (market.features - training_features.mean(axis=0)) / training_features.std(axis=0)
    train, train_labels, train_delivery = world.view(validation_start)
    refit, refit_labels, refit_delivery = world.view(test_start)
    validation = refit_delivery >= validation_start
    experts = []
    for half_life in HALF_LIVES:
        penalty = 0.01
        if len(np.unique(refit_labels[validation])) == 2:
            scores = []
            for candidate in (0.001, 0.01, 0.1):
                theta = fit(
                    features[train], train_labels, train_delivery, validation_start, candidate, half_life,
                )
                prediction = predict(theta, features[refit[validation]])
                scores.append(log_loss(refit_labels[validation], prediction).mean())
            penalty = (0.001, 0.01, 0.1)[int(np.argmin(scores))]
        theta = fit(features[refit], refit_labels, refit_delivery, test_start, penalty, half_life)
        experts.append((theta, penalty))
    return features, refit, experts


def run_policies(market, feedback, seed):
    """Choose every allocation before evaluation receives oracle probabilities."""
    features, initial_rows, experts = fit_initial_experts(market, feedback)
    decisions = []
    rounds = []
    test_dates = market.dates[market.first_test_batch:]
    for offset, (date, budget) in enumerate(zip(test_dates, market.test_budgets, strict=True)):
        batch = market.first_test_batch + offset
        candidates = np.flatnonzero(market.batch == batch)
        constraints, capacities = capacity_matrix(market.workers[candidates], market.jobs[candidates], JOB_CAPACITY)
        rounds.append((batch, date, candidates, constraints, capacities, budget))
    for policy in POLICIES:
        world = FeedbackWorld(market, feedback)
        active = {"static": (0,), "uniform": (0,), "decay": (1,)}.get(policy, (0, 1))
        parameters = [theta.copy() for theta, _ in experts]
        previous = initial_rows
        saved_predictions = np.full((2, len(features)), np.nan)
        for batch, date, candidates, constraints, capacities, budget in rounds:
            cutoff = day_number(date)
            attempts = world.follow_up(cutoff, seed, batch, budget)
            visible, known_labels, known_delivery = world.view(cutoff)
            is_test = market.batch[visible] >= market.first_test_batch
            visible_test = visible[is_test]
            if policy != "static" and not np.array_equal(previous, visible):
                for expert in active:
                    parameters[expert] = fit(
                        features[visible], known_labels, known_delivery, cutoff,
                        experts[expert][1], HALF_LIVES[expert], parameters[expert],
                    )
                previous = visible
            predictions = {expert: predict(parameters[expert], features[candidates]) for expert in active}
            weight = 1.0 if policy == "decay" else 0.0
            if len(active) == 2:
                weight = INITIAL_DECAY_WEIGHT
                if policy == "adaptive":
                    weight = adaptive_weight(
                        *saved_predictions[:, visible_test], known_labels[is_test],
                        known_delivery[is_test], cutoff,
                    )
                score = (1 - weight) * predictions[0] + weight * predictions[1]
            else:
                score = predictions[active[0]]
            chosen = allocate(score + 1e-10 * market.tie_break[candidates], constraints, capacities, budget)
            selected = candidates[chosen]
            for expert in active:
                saved_predictions[expert, selected] = predictions[expert][chosen]
            world.expose(selected, cutoff)
            decisions.append({
                "policy": policy,
                "batch": batch,
                "quarter_start": date,
                "decay_weight": weight,
                "visible_labels": len(visible),
                "visible_test_labels": len(visible_test),
                "followup_attempts": attempts,
                "selected": selected,
                "scores": score[chosen],
            })
    return decisions, rounds
