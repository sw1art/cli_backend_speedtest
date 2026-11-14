"""Command-line interface for the download benchmark."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .benchmark import (
    DEFAULT_REQUESTS,
    DEFAULT_TIMEOUT_SECONDS,
    BenchmarkSummary,
    DownloadBenchmarker,
    validate_url,
)
from .errors import BenchmarkError
from .formatter import (
    format_result,
    render_footer,
    render_header,
    render_json,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_SUCCESS = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="download-benchmark",
        description=(
            "Measure download speed by performing sequential HTTP GET requests "
            "against a target URL and reporting average time, total bytes and "
            "average speed."
        ),
    )
    parser.add_argument(
        "url",
        help="Target URL to benchmark, e.g. https://example.com/image.jpg",
    )
    parser.add_argument(
        "-n",
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS,
        help=f"Number of sequential requests (default: {DEFAULT_REQUESTS}).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON document instead of the human-readable report.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Additionally write the JSON report to FILE.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(
    argv: Optional[List[str]] = None, benchmarker: Optional[DownloadBenchmarker] = None
) -> int:
    """Run the CLI and return a process exit code.

    ``benchmarker`` is injectable for testing purposes only.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.requests < 1:
        parser.error("--requests must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    try:
        url = validate_url(args.url)
    except BenchmarkError as exc:
        parser.error(str(exc))

    benchmarker = benchmarker or DownloadBenchmarker(timeout=args.timeout)
    summary = BenchmarkSummary(url=url, requested=args.requests)

    if not args.json:
        print(render_header(summary))

    try:
        for result in benchmarker.iter_results(url, args.requests):
            summary.results.append(result)
            if not args.json:
                print(format_result(result), flush=True)
    except KeyboardInterrupt:
        if not args.json:
            print(
                "\nInterrupted by user. Printing partial results...",
                file=sys.stderr,
            )
    except BenchmarkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(render_json(summary) + "\n")
        except OSError as exc:
            print(
                f"error: cannot write report to '{args.output}': {exc}",
                file=sys.stderr,
            )
            return EXIT_USAGE

    if args.json:
        print(render_json(summary))
    else:
        print()
        print(render_footer(summary))

    return EXIT_OK if summary.successful > 0 else EXIT_NO_SUCCESS
