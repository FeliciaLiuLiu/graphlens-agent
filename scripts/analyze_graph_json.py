from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from afc_network_narrative.app.pipeline import analyze_graph
from afc_network_narrative.reporting.pdf_report import write_report_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AFC network narrative pipeline on GraphExtraction JSON.")
    parser.add_argument("graph_json", help="Path to GraphExtraction JSON file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--json-out", help="Optional path to write JSON output.")
    parser.add_argument("--pdf-out", help="Optional path to write PDF report.")
    args = parser.parse_args()

    payload = json.loads(Path(args.graph_json).read_text(encoding="utf-8"))
    output = analyze_graph(payload).to_dict()
    if args.json_out:
        json_text = json.dumps(output, indent=2 if args.pretty else None, ensure_ascii=False)
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json_text, encoding="utf-8")
    if args.pdf_out:
        write_report_pdf(output, args.pdf_out, input_name=Path(args.graph_json).name)
    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
