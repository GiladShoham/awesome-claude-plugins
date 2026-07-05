#!/usr/bin/env bash
# Add one or more media files to a booted iOS Simulator's Photos library.
#
# Usage:
#   ./add_to_simulator.sh <SIMULATOR_UDID> <file1> [file2 ...]
#   ./add_to_simulator.sh booted            <file1> [file2 ...]   # currently booted device
#
# Find a UDID with:  xcrun simctl list devices booted
#
# The Photos library is per-simulator, so re-run this against each new simulator UDID.
# The Assets.xcassets copy stays the durable source of truth.
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: $0 <SIMULATOR_UDID|booted> <file...>" >&2
  exit 2
fi

udid="$1"; shift
count="$#"

xcrun simctl addmedia "$udid" "$@"
echo "added ${count} file(s) to simulator ${udid}"
