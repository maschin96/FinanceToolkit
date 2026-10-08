"""Optional plotting adapters; numerical risk module never imports Matplotlib."""

from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit.risk import PortfolioSnapshot, stress_grid


def plot_stress_heatmap(
    snapshot: PortfolioSnapshot,
    spot_shocks: ArrayLike,
    volatility_shocks: ArrayLike,
    output: Path,
) -> NDArray[np.float64]:
    """Save PNG and return its P&L grid (volatility, spot), in snapshot currency.

    Requires optional plots dependency. ImportError propagates when unavailable;
    invalid shock axes raise ValueError through the same numerical stress API.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = stress_grid(snapshot, spot_shocks, volatility_shocks)
    fig, ax = plt.subplots()
    try:
        plotted = ax.imshow(values, origin="lower", aspect="auto", cmap="RdYlGn")
        ax.set_xticks(
            range(values.shape[1]), [f"{x:.0%}" for x in np.asarray(spot_shocks)]
        )
        ax.set_yticks(
            range(values.shape[0]), [f"{x:.1%}" for x in np.asarray(volatility_shocks)]
        )
        ax.set_xlabel("Relative spot shock")
        ax.set_ylabel("Volatility change (percentage points)")
        ax.set_title("Hypothetical stress P&L")
        fig.colorbar(plotted, ax=ax, label="P&L (portfolio currency)")
        fig.tight_layout()
        fig.savefig(output)
    finally:
        plt.close(fig)
    return values
