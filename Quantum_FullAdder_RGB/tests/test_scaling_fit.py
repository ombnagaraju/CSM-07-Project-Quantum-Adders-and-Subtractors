"""Phase 3 tests: measured scaling law and the linear-fit report.

The logical costs are exactly linear in the bit width (4n+1 and 3n+1 qubits,
6n and 3n gate blocks, 14n and 9n NCV-L cost), so the fit must recover the
slopes with R^2 = 1 and a zero-width confidence interval. The transpiled counts
are measured, not assumed, and are only required to be lower for the optimised
style.
"""

import numpy as np
import pytest

import config
from performance import scaling_law


@pytest.fixture(scope="module")
def fitted():
    rows, fits = scaling_law.verify(write=False, widths=(1, 2, 3, 4, 5))
    return rows, {(fit["style"], fit["metric"]): fit for fit in fits}


def test_logical_metrics_scale_exactly(fitted):
    rows, fits = fitted
    assert len(rows) == 10
    by_key = {(row["width"], row["style"]): row for row in rows}
    for width in (1, 2, 3, 4, 5):
        assert int(by_key[(width, "baseline")]["qubits"]) == 4 * width + 1
        assert int(by_key[(width, "optimized")]["qubits"]) == 3 * width + 1
        assert int(by_key[(width, "baseline")]["total_gates"]) == 6 * width
        assert int(by_key[(width, "optimized")]["total_gates"]) == 3 * width
        assert int(by_key[(width, "baseline")]["quantum_cost"]) == 14 * width
        assert int(by_key[(width, "optimized")]["quantum_cost"]) == 9 * width

    expected = {
        ("baseline", "qubits"): (4, 1),
        ("optimized", "qubits"): (3, 1),
        ("baseline", "total_gates"): (6, 0),
        ("optimized", "total_gates"): (3, 0),
        ("baseline", "quantum_cost"): (14, 0),
        ("optimized", "quantum_cost"): (9, 0),
    }
    for key, (slope, intercept) in expected.items():
        assert fits[key]["slope"] == pytest.approx(slope)
        assert fits[key]["intercept"] == pytest.approx(intercept, abs=1e-9)
        assert fits[key]["r_squared"] == 1.0
        assert fits[key]["slope_stderr"] == 0.0
        assert fits[key]["n_points"] == 5


def test_optimized_slopes_are_lower_on_both_logical_cost_measures(fitted):
    _, fits = fitted
    assert fits[("optimized", "total_gates")]["slope"] < fits[
        ("baseline", "total_gates")]["slope"]
    assert fits[("optimized", "quantum_cost")]["slope"] < fits[
        ("baseline", "quantum_cost")]["slope"]


def test_linear_fit_recovers_a_known_line_and_a_confidence_interval():
    x = np.arange(1, 9)
    y = 2.5 * x + 7.0
    fit = scaling_law.linear_fit(x, y)
    assert fit["slope"] == pytest.approx(2.5)
    assert fit["intercept"] == pytest.approx(7.0)
    assert fit["r_squared"] == 1.0
    noisy = y + np.array([0.0, 1.0, -1.0, 0.5, -0.5, 1.5, -1.5, 0.2])
    noisy_fit = scaling_law.linear_fit(x, noisy)
    assert noisy_fit["r_squared"] < 1.0
    assert noisy_fit["slope_ci_low"] < noisy_fit["slope"] < noisy_fit["slope_ci_high"]


def test_persisted_scaling_csvs_hold_the_full_sweep():
    rows = config.read_rows("scaling_vs_n")
    fits = config.read_rows("scaling_fit")
    assert len(rows) == len(config.RIPPLE_WIDTHS) * 2
    assert {int(row["width"]) for row in rows} == set(config.RIPPLE_WIDTHS)
    assert len(fits) == 2 * len(scaling_law.FIT_METRICS)
    by_key = {(row["style"], row["metric"]): row for row in fits}
    assert float(by_key[("baseline", "quantum_cost")]["slope"]) == 14.0
    assert float(by_key[("optimized", "quantum_cost")]["slope"]) == 9.0
    assert float(by_key[("baseline", "total_gates")]["r_squared"]) == 1.0
    transpiled = by_key[("optimized", "transpiled_cx_gates")]
    assert (float(transpiled["slope_ci_low"]) < float(transpiled["slope"])
            < float(transpiled["slope_ci_high"]))
    assert float(transpiled["slope"]) < float(
        by_key[("baseline", "transpiled_cx_gates")]["slope"])


def test_verify_rejects_a_fit_where_the_optimized_slope_is_not_lower(monkeypatch):
    rows = scaling_law.measure(widths=(1, 2, 3))
    for row in rows:
        if row["style"] == "optimized":
            row["total_gates"] = 7 * row["width"]
            row["quantum_cost"] = 15 * row["width"]
    monkeypatch.setattr(scaling_law, "measure", lambda widths=None: rows)
    with pytest.raises(AssertionError, match="not lower"):
        scaling_law.verify(write=False, widths=(1, 2, 3))
