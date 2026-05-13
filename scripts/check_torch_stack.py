from __future__ import annotations

import sys


EXPECTED = {
    "torch": "2.8.0",
    "torchvision": "0.23.0",
    "torchaudio": "2.8.0",
}


def main() -> int:
    for module_name, expected_version in EXPECTED.items():
        module = __import__(module_name)
        actual_version = module.__version__.split("+", 1)[0]
        print(f"{module_name}={module.__version__}")
        if actual_version != expected_version:
            print(f"Expected {module_name}=={expected_version}, got {module.__version__}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
