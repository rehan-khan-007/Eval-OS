# This is a facade that imports from the modular analysis/ directory
# to ensure backwards compatibility with the CLI commands.
from analysis.aggregation import analyze_run, analyze_run_slices
from analysis.statistics import compare_runs
from analysis.diagnosis import diagnose_run
from analysis.regression import check_regression
from analysis.calibration import calculate_calibration

class AnalysisEngine:
    analyze_run = staticmethod(analyze_run)
    analyze_run_slices = staticmethod(analyze_run_slices)
    compare_runs = staticmethod(compare_runs)
    diagnose_run = staticmethod(diagnose_run)
    check_regression = staticmethod(check_regression)
    calculate_calibration = staticmethod(calculate_calibration)
