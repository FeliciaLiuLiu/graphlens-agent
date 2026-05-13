from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from afc_network_narrative.vlm import create_vlm_adapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test visual graph extraction.")
    parser.add_argument("image_path")
    parser.add_argument(
        "--backend",
        default=None,
        choices=["ollama", "qwen", "florence2", "approved_endpoint", "llama", "gemini", "openai", "claude", "granite"],
    )
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--ollama-timeout-seconds", type=int, default=None)
    parser.add_argument("--qwen-model-path", default=None)
    parser.add_argument("--florence-model-path", default=None)
    parser.add_argument("--model-path", default=None, help="Alias for the selected local model path.")
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--extraction-prompt-path", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adapter = create_vlm_adapter(
        backend=args.backend,
        config={
            "ollama_model": args.ollama_model,
            "ollama_host": args.ollama_host,
            "ollama_timeout_seconds": args.ollama_timeout_seconds,
            "qwen_model_path": args.qwen_model_path or args.model_path,
            "florence_model_path": args.florence_model_path or args.model_path,
            "max_new_tokens": args.max_new_tokens,
            "extraction_prompt_path": args.extraction_prompt_path,
        },
    )
    graph = adapter.extract_graph(args.image_path)
    print(json.dumps(graph.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
