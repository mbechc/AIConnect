#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PLATFORMIO_CORE_DIR="$SCRIPT_DIR/.platformio-core"
cd "$SCRIPT_DIR" || exit 1
exec /Users/morchris/Library/Python/3.9/bin/pio "$@"
