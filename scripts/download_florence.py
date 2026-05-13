from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Florence-2 locally under ./models/.")
    parser.add_argument("--model-id", default="microsoft/Florence-2-base-ft")
    parser.add_argument("--local-dir", default="./models/Florence-2-base-ft")
    parser.add_argument("--revision", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    local_dir = Path(args.local_dir)
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    final_path = snapshot_download(
        repo_id=args.model_id,
        revision=args.revision,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    print(Path(final_path).resolve())


if __name__ == "__main__":
    main()
