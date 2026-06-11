"""CLI entry point for transkript."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="transkript",
        description="Local meeting transcriber — records mic + system audio, transcribes with Whisper.",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size (default: base, ~74MB)",
    )
    parser.add_argument(
        "--output", "-o",
        default="./transcripts",
        help="Output directory for transcripts (default: ./transcripts)",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="transkript 0.1.0",
    )
    args = parser.parse_args()

    from transkript.app import TranskriptApp

    app = TranskriptApp(model_name=args.model, output_dir=args.output)
    app.run()


if __name__ == "__main__":
    main()
