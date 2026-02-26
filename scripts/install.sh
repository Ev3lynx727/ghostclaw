#!/usr/bin/env bash
# Installation script for Ghostclaw skill
# This registers the skill with OpenClaw

set -e

# Find OpenClaw skills dir (try common locations)
if [[ -d "$HOME/.openclaw/skills" ]]; then
    SKILLS_DIR="$HOME/.openclaw/skills"
elif command -v openclaw &>/dev/null; then
    SKILLS_DIR="$(openclaw config get skills.dir 2>/dev/null || echo "$HOME/.openclaw/skills")"
else
    SKILLS_DIR="$HOME/.openclaw/skills"
fi

mkdir -p "$SKILLS_DIR"

# Copy skill
mkdir -p "$SKILLS_DIR/ghostclaw"
# Explicitly copy root-level modules and scripts
for dir in core lib stacks scripts cli references; do
    if [[ -d "$(dirname "$0")/../$dir" ]]; then
        cp -r "$(dirname "$0")/../$dir" "$SKILLS_DIR/ghostclaw/"
    fi
done
cp "$(dirname "$0")/../SKILL.md" "$SKILLS_DIR/ghostclaw/" 2>/dev/null || true
cp "$(dirname "$0")/../README.md" "$SKILLS_DIR/ghostclaw/" 2>/dev/null || true

chmod +x "$SKILLS_DIR/ghostclaw/scripts/"*.sh 2>/dev/null || true
chmod +x "$SKILLS_DIR/ghostclaw/scripts/"*.py 2>/dev/null || true

echo "👻 Ghostclaw skill installed to: $SKILLS_DIR/ghostclaw"
echo ""
echo "Next steps:"
echo "1. Configure repos to watch: edit $SKILLS_DIR/ghostclaw/scripts/repos.txt"
echo "2. Set GH_TOKEN for PR automation (optional): export GH_TOKEN=..."
echo "3. Test review mode: $SKILLS_DIR/ghostclaw/scripts/ghostclaw.sh review /path/to/repo"
echo "4. Add cron: 0 9 * * * $SKILLS_DIR/ghostclaw/scripts/watcher.sh"
