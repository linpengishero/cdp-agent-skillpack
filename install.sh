#!/bin/bash
# CDP Agent Skill Pack Installer
# Usage: bash install.sh [target_dir]

TARGET="${1:-$HOME/.hermes/skills}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing CDP Agent Skill Pack to $TARGET"
echo ""

mkdir -p "$TARGET/cdp-agent"
mkdir -p "$TARGET/boss-zhipin/scripts"

cp "$SCRIPT_DIR/skills/cdp-agent/SKILL.md" "$TARGET/cdp-agent/"
cp "$SCRIPT_DIR/skills/cdp-agent/cdp_agent_client.py" "$TARGET/cdp-agent/"
cp "$SCRIPT_DIR/skills/cdp-agent/cdp_agent_win.py" "$TARGET/cdp-agent/"

cp "$SCRIPT_DIR/skills/boss-zhipin/SKILL.md" "$TARGET/boss-zhipin/"
cp "$SCRIPT_DIR/skills/boss-zhipin/scripts/run.py" "$TARGET/boss-zhipin/scripts/"

echo "Done!"
echo ""
echo "Next steps:"
echo "  1. On Windows: cd $TARGET/cdp-agent && python cdp_agent_win.py"
echo "  2. Load skills in your AI agent (Hermes/OpenClaude/OpenClaw)"
echo "  3. For BOSS直聘: python3 $TARGET/boss-zhipin/scripts/run.py --help"
