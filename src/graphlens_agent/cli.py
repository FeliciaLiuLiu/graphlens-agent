from __future__ import annotations

import argparse
import json
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Optional, Sequence, TextIO

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.io import load_graph_json
from graphlens_agent.validator import GraphValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graphlens-agent",
        description="Validate a GraphLens graph JSON file and print graph analytics as JSON.",
    )
    parser.add_argument("graph_json", type=Path, help="Path to a GraphLens graph JSON file.")
    return parser


def main(argv: Optional[Sequence[str]] = None, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        document = load_graph_json(args.graph_json)
        analysis = analyze_graph(document)
    except FileNotFoundError:
        print(f"error: file not found: {args.graph_json}", file=stderr)
        return 1
    except JSONDecodeError as error:
        print(f"error: invalid JSON in {args.graph_json}: {error}", file=stderr)
        return 1
    except GraphValidationError as error:
        print(f"error: graph validation failed: {error}", file=stderr)
        return 1
    except OSError as error:
        print(f"error: could not read {args.graph_json}: {error}", file=stderr)
        return 1

    json.dump(analysis, stdout, indent=2, sort_keys=True)
    stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
