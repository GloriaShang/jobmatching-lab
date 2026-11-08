"""Equal-weight and time-decayed logistic experts from the research prototype."""

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

HALF_LIVES = (np.inf, 180)
INITIAL_DECAY_WEIGHT = 0.1


def predict(parameters, features):
    return expit(parameters[0] + features @ parameters[1:])


def log_loss(labels, probabilities):
    p = np.clip(probabilities, 1e-12, 1 - 1e-12)
    return -labels * np.log(p) - (1 - labels) * np.log1p(-p)


def fit(features, labels, delivery, cutoff, penalty, half_life, initial=None):
    """Fit on already-visible records and check that each label has matured."""
    if np.any(delivery + 30 >= cutoff):
        raise ValueError("Training requires mature labels")
    if not len(labels):
        return np.zeros(features.shape[1] + 1)
    constant = logit((labels.sum() + 0.5) / (len(labels) + 1))
    if len(np.unique(labels)) < 2:
        return np.r_[constant, np.zeros(features.shape[1])]
    weights = np.exp2(-(cutoff - delivery) / half_life)
    weights /= weights.sum()

    def objective(parameters):
        coefficients = parameters[1:]
        eta = parameters[0] + features @ coefficients
        loss = weights @ (np.logaddexp(0, eta) - labels * eta)
        residual = weights * (expit(eta) - labels)
        return (
            loss + penalty / 2 * (coefficients @ coefficients),
            np.r_[residual.sum(), features.T @ residual + penalty * coefficients],
        )

    if initial is None:
        initial = np.r_[constant, np.zeros(features.shape[1])]
    result = minimize(
        objective,
        np.clip(initial, -8, 8),
        jac=True,
        bounds=[(-8, 8)] * len(initial),
        method="L-BFGS-B",
        options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-7},
    )
    _, gradient = objective(result.x)
    lower = result.x <= -8 + 1e-7
    upper = result.x >= 8 - 1e-7
    gradient[lower] = np.minimum(gradient[lower], 0)
    gradient[upper] = np.maximum(gradient[upper], 0)
    if not np.isfinite(result.fun) or np.max(np.abs(gradient)) > 1e-4:
        raise RuntimeError(f"Expert optimization failed: {result.message}")
    return result.x


def adaptive_weight(equal_predictions, decay_predictions, labels, delivery, cutoff):
    """Score both experts' exposure-time predictions on visible test labels."""
    if not len(labels):
        return INITIAL_DECAY_WEIGHT
    if not np.isfinite(equal_predictions).all() or not np.isfinite(decay_predictions).all():
        raise ValueError("Expert scores require predictions saved at exposure")
    age_weight = np.exp2(-(cutoff - delivery) / 180)
    ess = age_weight.sum() ** 2 / (age_weight @ age_weight)
    if ess < 10:
        return INITIAL_DECAY_WEIGHT
    difference = log_loss(labels, equal_predictions) - log_loss(labels, decay_predictions)
    score = age_weight @ np.clip(difference, -1, 1)
    return float(np.clip(expit(logit(INITIAL_DECAY_WEIGHT) + score), 0.05, 0.95))
