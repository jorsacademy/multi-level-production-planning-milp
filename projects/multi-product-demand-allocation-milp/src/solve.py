"""Generate data when necessary, validate inputs, solve the MILP, and write reports."""

from pathlib import Path

from generate_data import generate
from model import load_data, solve_model
from reporting import build_reports, write_reports
from validation import validate_model_data

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    required = DATA_DIR / "facilities.csv"
    if not required.exists():
        generate()

    data = load_data(DATA_DIR)
    validate_model_data(data)
    result, variables, crf = solve_model(data)

    if not result.success:
        raise RuntimeError(f"Optimization failed: {result.message}")

    allocation_df, expansion_df, utilization_df = build_reports(
        data, variables, result.x
    )
    write_reports(OUTPUT_DIR, allocation_df, expansion_df, utilization_df)

    print("Optimization completed successfully.")
    print(f"Objective value: {result.fun:,.2f}")
    print(f"Capital-recovery factor: {crf:.6f}")
    print(f"Allocation rows: {len(allocation_df)}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
