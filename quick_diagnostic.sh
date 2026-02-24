#!/usr/bin/env bash
# Ghostclaw Quick Diagnostic - Check for running processes
# Run this to see current ghostclaw activity

echo "=== Ghostclaw Process Diagnostic ==="
echo ""

echo "1. Active ghostclaw processes:"
if pgrep -f ghostclaw > /dev/null; then
    echo "   PID   USER   COMMAND"
    pgrep -f ghostclaw -a | while read -r line; do
        pid=$(echo "$line" | awk '{print $1}')
        user=$(ps -o user= -p "$pid" 2>/dev/null || echo "?")
        cmd=$(echo "$line" | sed "s/^$pid //")
        printf "   %-6s %-8s %s\n" "$pid" "$user" "$cmd"
    done
else
    echo "   None"
fi
echo ""

echo "2. Process count by pattern:"
echo "   Total: $(pgrep -f ghostclaw | wc -l)"
echo "   python3 ghostclaw.py: $(pgrep -f "ghostclaw.py" | wc -l)"
echo "   ghostclaw-watcher: $(pgrep -f "ghostclaw-watcher" | wc -l)"
echo ""

echo "3. OpenClaw agent sessions (if any):"
if command -v sessions_list &>/dev/null; then
    sessions_list 2>/dev/null || echo "   Unable to list sessions"
else
    echo "   sessions_list command not available"
fi
echo ""

echo "4. Recent ghostclaw activity in system log (last 50 lines):"
if command -v journalctl &>/dev/null; then
    journalctl -u ghostclaw --no-pager -n 50 2>/dev/null || echo "   No systemd service found"
else
    echo "   journalctl not available"
fi
echo ""

echo "5. Check for zombie processes:"
zombies=$(ps aux | awk '$8=="Z" && $0~/ghostclaw/ {print}' | wc -l)
if [[ $zombies -gt 0 ]]; then
    echo "   ⚠️  $zombies zombie(s) found:"
    ps aux | awk '$8=="Z" && $0~/ghostclaw/ {print "   " $0}'
else
    echo "   ✓ None"
fi
echo ""

echo "6. Resource usage (if processes running):"
if pgrep -f ghostclaw > /dev/null; then
    echo "   By ghostclaw processes:"
    ps aux | grep -E "ghostclaw|python3.*ghostclaw" | grep -v grep | awk '{print "   PID="$1" CPU="$3"% MEM="$4"% CMD="$11" "$12" "$13" "$14}'
else
    echo "   No running processes"
fi
echo ""

echo "=== End Diagnostic ==="
echo ""
echo "To test process cleanup, run:"
echo "  $HOME/.agents/skills/ghostclaw/test_process_cleanup.sh /path/to/test/repo"
