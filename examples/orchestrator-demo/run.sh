#!/usr/bin/env bash
# Demo runner for orchestrator

set -e

# Ensure orchestrator plugin installed
pip show ghost-orchestrator >/dev/null 2>&1 || {
    echo "Installing ghost-orchestrator..."
    pip install ghost-orchestrator
}

# Optional: create local config
mkdir -p .ghostclaw
cat > .ghostclaw/ghostclaw.json <<'EOF'
{
  "orchestrate": true,
  "orchestrator": {
    "use_llm": false,
    "max_plugins": 4,
    "verbose": true
  },
  "use_qmd": true
}
EOF

# Run analysis
echo "Running Ghostclaw with orchestrator enabled..."
ghostclaw sample_project --use-qmd --orchestrate --orchestrate-verbose

echo "Report generated in .ghostclaw/storage/reports/"