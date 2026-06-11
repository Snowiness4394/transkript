#!/usr/bin/env bash
# Run the built transkript executable
cd "$(dirname "$0")"
echo "Starting transkript..."
echo "Press Ctrl+C to quit"
echo ""
./dist/transkript/transkript
