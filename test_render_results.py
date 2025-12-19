"""Quick helper to render a results JSON file with the local output helper."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Prefer the local fusesell package in this repo
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fusesell_local.utils.output_helpers import write_full_output_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Render results.json to HTML using output_helpers.")
    parser.add_argument(
        "--input",
        default=r"C:\Users\Admins\Downloads\results.json",
        help="Path to the results JSON file (default: %(default)s)",
    )
    parser.add_argument(
        "--flow-name",
        default="results_snapshot",
        help="Flow name to tag the rendered output (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default="tmp_output_test",
        help="Directory to write the rendered HTML (default: %(default)s)",
    )
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Missing file: {src}", file=sys.stderr)
        return 1

    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {src}: {exc}", file=sys.stderr)
        return 1

    data_dir = Path(args.out_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    output = write_full_output_html(
        data,
        flow_name=args.flow_name,
        data_dir=data_dir,
    )

    if output is None:
        print("Failed to render HTML; see stderr.", file=sys.stderr)
        return 1

    print(f"Rendered HTML: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
