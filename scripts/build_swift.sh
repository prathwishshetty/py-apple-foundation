#!/bin/bash
# Build Swift binaries for py-apple-foundation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SWIFT_SRC="$PROJECT_ROOT/src/apple_foundation/swift"
BIN_DIR="$PROJECT_ROOT/bin"

echo "Building Swift binaries..."

mkdir -p "$BIN_DIR"

echo "  Compiling generate.swift..."
swiftc "$SWIFT_SRC/generate.swift" -o "$BIN_DIR/generate"

echo "  Compiling transcribe.swift..."
swiftc "$SWIFT_SRC/transcribe.swift" -o "$BIN_DIR/transcribe"

echo "Done! Binaries installed to $BIN_DIR"
