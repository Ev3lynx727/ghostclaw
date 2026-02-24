#!/usr/bin/env bash
# Ghostclaw Process Cleanup Test Script
# Usage: ./test_process_cleanup.sh [repo_path]
# This script tests whether ghostclaw leaves orphaned processes behind.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[TEST]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check prerequisites
check_deps() {
    local missing=0
    for cmd in python3 pgrep pkill ps jq; do
        if ! command -v "$cmd" &>/dev/null; then
            error "Missing required command: $cmd"
            missing=1
        fi
    done
    if [[ $missing -eq 1 ]]; then
        exit 1
    fi
}

# Get all ghostclaw-related processes (Python modules cli.ghostclaw or cli.watcher)
# Excludes this test script itself
get_ghostclaw_processes() {
    pgrep -f "python3.*-m cli\.(ghostclaw|watcher)" -a || true
}

# Count ghostclaw processes
count_ghostclaw_processes() {
    pgrep -f "python3.*-m cli\.(ghostclaw|watcher)" | wc -l
}

# Test 1: One-shot review should not leave processes
test_oneshot() {
    local repo_path="$1"
    log "Test 1: One-shot review process cleanup"
    log "Repository: $repo_path"

    # Get initial count
    local before
    before=$(count_ghostclaw_processes)
    log "Ghostclaw processes before: $before"

    # Run ghostclaw one-shot
    log "Running: (cd \"$REPO_ROOT\" && python3 -m cli.ghostclaw \"$repo_path\")"
    local exit_code
    if (cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" python3 -m cli.ghostclaw "$repo_path") > /dev/null 2>&1; then
        log "Analysis completed"
    else
        error "Analysis failed with exit code $?"
    fi

    # Give processes a moment to clean up
    sleep 1

    # Get after count
    local after
    after=$(count_ghostclaw_processes)
    log "Ghostclaw processes after: $after"

    # Get list of processes for debugging
    log "Current ghostclaw processes:"
    get_ghostclaw_processes | sed 's/^/  /' || warn "None"

    if [[ $after -gt $before ]]; then
        error "LEAK DETECTED: $((after - before)) process(es) remain after one-shot"
        return 1
    else
        log "✓ No processes leaked from one-shot"
        return 0
    fi
}

# Test 2: Watcher mode should clean up after finishing
test_watcher() {
    local repo_path="$1"
    log "Test 2: Watcher mode cleanup"

    # Start watcher in background
    log "Starting watcher in background..."
    (cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" python3 -m cli.watcher --repos-file <(echo "$repo_path") --dry-run) > /tmp/ghostclaw-watcher-test.log 2>&1 &
    local watcher_pid=$!
    log "Watcher PID: $watcher_pid"

    # Wait for it to finish (with timeout)
    local waited=0
    while kill -0 "$watcher_pid" 2>/dev/null && [[ $waited -lt 30 ]]; do
        sleep 1
        waited=$((waited + 1))
        if [[ $((waited % 5)) -eq 0 ]]; then
            log "Waiting... ($waited s)"
        fi
    done

    # Check exit status
    local exit_code
    wait "$watcher_pid" 2>/dev/null
    exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "Watcher exited cleanly (code 0) after ${waited}s"
    else
        warn "Watcher exited with code $exit_code after ${waited}s"
    fi

    # Count processes after a brief wait
    sleep 2
    local after
    after=$(count_ghostclaw_processes)
    log "Ghostclaw processes after watcher completed: $after"

    # Check for any remaining ghostclaw processes (except this test script itself)
    if [[ $after -gt 1 ]]; then
        error "ORPHANED PROCESSES DETECTED:"
        get_ghostclaw_processes | sed 's/^/  /'
        return 1
    else
        log "✓ No orphaned processes (only test script remains)"
        return 0
    fi
}

# Test 3: Check for zombie processes
test_zombies() {
    log "Test 3: Checking for zombie processes"
    local zombies
    zombies=$(ps aux | awk '$8=="Z" && $0~/python3.*-m cli\.(ghostclaw|watcher)/ {print $0}' | wc -l)
    if [[ $zombies -gt 0 ]]; then
        error "ZOMBIE PROCESSES DETECTED: $zombies"
        ps aux | awk '$8=="Z" && $0~/python3.*-m cli\.(ghostclaw|watcher)/ {print "  " $0}'
        return 1
    else
        log "✓ No zombie processes"
        return 0
    fi
}

# Test 4: Stress test (multiple rapid runs)
test_stress() {
    local repo_path="$1"
    log "Test 4: Stress test (10 rapid runs)"
    local initial
    initial=$(count_ghostclaw_processes)

    for i in {1..10}; do
        if (cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" python3 -m cli.ghostclaw "$repo_path") > /dev/null 2>&1; then
            : # success
        else
            local rc=$?
            warn "Run $i exited with code $rc"
        fi
        sleep 0.5
    done

    sleep 1
    local final
    final=$(count_ghostclaw_processes)
    local diff=$((final - initial))

    if [[ $diff -gt 0 ]]; then
        error "STRESS LEAK: $diff process(es) accumulated after 10 runs"
        get_ghostclaw_processes | sed 's/^/  /'
        return 1
    else
        log "✓ No accumulation after stress test"
        return 0
    fi
}

# Main
main() {
    log "Ghostclaw Process Cleanup Test"
    log "=============================="

    check_deps

    # Find a test repository
    local repo_path="${1:-}"
    if [[ -z "$repo_path" ]]; then
        # Try to find a suitable test repo
        if [[ -d "$HOME/projects" ]]; then
            repo_path=$(find "$HOME/projects" -name "*.py" -o -name "*.js" | head -1 | xargs dirname)
        fi
        if [[ -z "$repo_path" ]]; then
            error "No repository path provided and couldn't find a default"
            error "Usage: $0 <repo_path>"
            exit 1
        fi
    fi

    if [[ ! -d "$repo_path" ]]; then
        error "Directory not found: $repo_path"
        exit 1
    fi

    log "Using repository: $repo_path"
    echo ""

    # Run all tests
    local failed=0

    test_oneshot "$repo_path" || failed=1
    echo ""

    test_watcher "$repo_path" || failed=1
    echo ""

    test_zombies || failed=1
    echo ""

    test_stress "$repo_path" || failed=1
    echo ""

    if [[ $failed -eq 0 ]]; then
        log "All tests PASSED ✓"
        log "Ghostclaw appears to clean up processes correctly."
    else
        error "Some tests FAILED ✗"
        error "Process leaks detected. See details above."
        exit 1
    fi
}

# Show current processes for baseline
log "Baseline ghostclaw processes:"
get_ghostclaw_processes | sed 's/^/  /' || log "  None"

main "$@"
