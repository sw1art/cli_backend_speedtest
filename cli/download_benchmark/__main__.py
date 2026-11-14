"""Allow running the benchmark with ``python -m download_benchmark``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
