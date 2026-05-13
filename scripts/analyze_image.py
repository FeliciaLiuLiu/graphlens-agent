from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from afc_network_narrative.harness.app.pipeline import analyze_image_file
from afc_network_narrative.harness.reporting.pdf_report import write_report_pdf
from afc_network_narrative.model import create_vlm_adapter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full image -> VLM extraction -> AFC narrative pipeline."
    )
    parser.add_argument("image_path", help="Path to a PNG/JPEG network graph image.")
    parser.add_argument(
        "--backend",
        default=None,
        choices=["pixtral"],
        help="VLM backend. Only pixtral is supported.",
    )
    parser.add_argument(
        "--pixtral-model-path",
        default=None,
        help="Local Pixtral 12B model directory. Defaults to PIXTRAL_MODEL_PATH.",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Alias for the selected local model path.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=None,
        help="Maximum graph-extraction generation tokens.",
    )
    parser.add_argument(
        "--extraction-prompt-path",
        default=None,
        help="Path to the graph extraction prompt skill file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument("--json-out", help="Optional path to write JSON output.")
    parser.add_argument("--pdf-out", help="Optional path to write PDF report.")
    args = parser.parse_args()

    adapter = create_vlm_adapter(
        backend=args.backend,
        config={
            "pixtral_model_path": args.pixtral_model_path or args.model_path,
            "max_new_tokens": args.max_new_tokens,
            "extraction_prompt_path": args.extraction_prompt_path,
        },
    )
    output = analyze_image_file(args.image_path, adapter).to_dict()
    if args.json_out:
        json_text = json.dumps(output, indent=2 if args.pretty else None, ensure_ascii=False)
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json_text, encoding="utf-8")
    if args.pdf_out:
        write_report_pdf(output, args.pdf_out, input_name=Path(args.image_path).name)
    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
