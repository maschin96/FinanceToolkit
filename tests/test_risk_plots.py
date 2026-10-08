"""Optional plotting adapter reads the same stress grid as numerical exports."""

import numpy as np
import pytest

from finance_toolkit.portfolio import Stock
from finance_toolkit.risk import PortfolioSnapshot, stress_grid
from finance_toolkit.risk_plots import plot_stress_heatmap


def test_heatmap_contains_numerical_grid(tmp_path):
    pytest.importorskip("matplotlib")
    snap = PortfolioSnapshot(0, (Stock(),), [10], [100], 0, 0)
    result = plot_stress_heatmap(
        snap, [-0.2, 0, 0.2], [0, 0.1], tmp_path / "stress.png"
    )
    np.testing.assert_array_equal(result, stress_grid(snap, [-0.2, 0, 0.2], [0, 0.1]))
    assert (tmp_path / "stress.png").read_bytes().startswith(b"\x89PNG")


def test_heatmap_does_not_change_global_backend(tmp_path, monkeypatch):
    matplotlib = pytest.importorskip("matplotlib")

    def forbidden(*args, **kwargs):
        raise AssertionError("global backend change")

    monkeypatch.setattr(matplotlib, "use", forbidden)
    plot_stress_heatmap(
        PortfolioSnapshot(0, (Stock(),), [1], [100], 0, 0),
        [0],
        [0],
        tmp_path / "stress.png",
    )
