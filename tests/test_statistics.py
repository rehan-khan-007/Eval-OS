import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.statistics import calculate_bootstrap_ci

def test_bootstrap_significant_improvement():
    """Test that a clear improvement is statistically significant."""
    # Run A is always 1.0, Run B is always 0.0. Diff is always 1.0
    diffs = [1.0] * 10
    stats = calculate_bootstrap_ci(diffs)
    assert stats["mean_diff"] == 1.0
    assert stats["ci_lower"] > 0
    assert stats["ci_upper"] > 0
    assert stats["is_significant"] is True
    assert stats["paired_valid_examples"] == 10

def test_bootstrap_inconclusive():
    """Test that noisy data is not statistically significant."""
    # Half the time A is better, half the time B is better
    diffs = [0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5]
    stats = calculate_bootstrap_ci(diffs)
    # CI should cross zero
    assert stats["ci_lower"] <= 0
    assert stats["ci_upper"] >= 0
    assert stats["is_significant"] is False

def test_bootstrap_zero_variance():
    """Test that identical runs result in zero difference."""
    diffs = [0.0] * 10
    stats = calculate_bootstrap_ci(diffs)
    assert stats["mean_diff"] == 0.0
    assert stats["ci_lower"] == 0.0
    assert stats["ci_upper"] == 0.0
    assert stats["is_significant"] is False
