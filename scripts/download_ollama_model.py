from __future__ import annotations

import argparse
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull an Ollama model for local VLM extraction.")
    parser.add_argument("--model", default="qwen2.5vl:3b")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    subprocess.run(["ollama", "pull", args.model], check=True)
    print(args.model)


if __name__ == "__main__":
    main()
