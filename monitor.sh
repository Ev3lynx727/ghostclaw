#!/usr/bin/env bash
# Ghostclaw Process Monitor — watch process count over time
# Usage: ./monitor.sh [interval_seconds] [duration_seconds]

INTERVAL="${1:-5}"
DURATION="${2:-60}"

echo "Monitoring ghostclaw processes every $INTERVAL seconds for $DURATION seconds..."
echo "Press Ctrl+C to stop early"
echo ""

start_time=$(date +%s)
end_time=$((start_time + DURATION))

while [ $(date +%s) -lt $end_time ]; do
    timestamp=$(date '+%H:%M:%S')
    count=$(pgrep -f ghostclaw | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "$timestamp: $count process(es) running"
        pgrep -f ghostclaw -a | sed 's/^/  /'
    else
        echo "$timestamp: 0"
    fi
    sleep "$INTERVAL"
done

echo ""
echo "=== Final count ==="
pgrep -f ghostclaw -a || echo "No ghostclaw processes running"
