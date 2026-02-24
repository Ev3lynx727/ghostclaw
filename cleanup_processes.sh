#!/usr/bin/env bash
# Ghostclaw Process Cleanup Utility
# Safely terminates all ghostclaw-related processes

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Get list of ghostclaw PIDs (excluding this script)
get_pids() {
    pgrep -f "ghostclaw" | grep -v "$$" || true
}

echo "=== Ghostclaw Process Cleanup ==="
echo ""

pids=($(get_pids))
count=${#pids[@]}

if [[ $count -eq 0 ]]; then
    info "No ghostclaw processes found."
    exit 0
fi

echo "Found $count ghostclaw-related process(es):"
for pid in "${pids[@]}"; do
    cmd=$(ps -o cmd= -p "$pid" 2>/dev/null || echo "???")
    printf "  PID %-6s %s\n" "$pid" "$cmd"
done
echo ""

# Ask for confirmation
read -p "Terminate these processes? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    info "Aborted."
    exit 0
fi

# Try graceful termination first
info "Sending SIGTERM to all processes..."
for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || warn "Failed to kill PID $pid (may have exited)"
done

# Wait up to 5 seconds
sleep 2

# Check what's still running
remaining=($(get_pids))
if [[ ${#remaining[@]} -gt 0 ]]; then
    warn "Some processes still running after SIGTERM:"
    for pid in "${remaining[@]}"; do
        cmd=$(ps -o cmd= -p "$pid" 2>/dev/null || echo "???")
        printf "  PID %-6s %s\n" "$pid" "$cmd"
    done
    echo ""

    read -p "Send SIGKILL to remaining processes? (y/N): " force_confirm
    if [[ "$force_confirm" =~ ^[Yy]$ ]]; then
        info "Sending SIGKILL..."
        for pid in "${remaining[@]}"; do
            kill -9 "$pid" 2>/dev/null || warn "Failed to kill PID $pid"
        done
        sleep 1
    else
        info "Leaving remaining processes."
    fi
fi

# Final check
final=($(get_pids))
if [[ ${#final[@]} -eq 0 ]]; then
    info "All ghostclaw processes terminated."
else
    error "Some processes could not be terminated:"
    for pid in "${final[@]}"; do
        cmd=$(ps -o cmd= -p "$pid" 2>/dev/null || echo "???")
        printf "  PID %-6s %s\n" "$pid" "$cmd"
    done
    exit 1
fi

# Also clean up any orphaned child processes that might have been detached
info "Checking for orphaned child processes..."
orphans=$(ps --no-headers -o pid,ppid,cmd | awk '$2==1 && /ghostclaw/ {print $1}')
if [[ -n "$orphans" ]]; then
    warn "Found orphaned ghostclaw process(es):"
    echo "$orphans" | while read -r pid; do
        cmd=$(ps -o cmd= -p "$pid" 2>/dev/null || echo "???")
        printf "  PID %-6s %s\n" "$pid" "$cmd"
    done
    read -p "Kill orphans? (y/N): " orphan_confirm
    if [[ "$orphan_confirm" =~ ^[Yy]$ ]]; then
        echo "$orphans" | xargs -r kill -9 2>/dev/null || true
        info "Orphans killed."
    fi
fi

echo ""
info "Cleanup complete."
