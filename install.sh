#!/usr/bin/env bash
# Install shortvideo-skill into ~/.claude/ via symlinks.
# Re-run safely; symlinks are atomically replaced.
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"
claude_dir="${HOME}/.claude"

mkdir -p "${claude_dir}/skills" "${claude_dir}/agents" "${claude_dir}/commands"

# Skills
for s in shortvideo-planner shortvideo-generator shortvideo-reviewer; do
  ln -sfn "${repo_dir}/.claude/skills/${s}" "${claude_dir}/skills/${s}"
  echo "  linked skills/${s}"
done

# Agents
ln -sfn "${repo_dir}/.claude/agents/shortvideo-reviewer.md" \
        "${claude_dir}/agents/shortvideo-reviewer.md"
echo "  linked agents/shortvideo-reviewer.md"

# Commands
ln -sfn "${repo_dir}/.claude/commands/shortvideo-loop.md" \
        "${claude_dir}/commands/shortvideo-loop.md"
echo "  linked commands/shortvideo-loop.md"

# Dependency check
echo ""
echo "Dependency check:"

check() {
  local name=$1; shift
  if "$@" >/dev/null 2>&1; then
    echo "  OK    ${name}"
  else
    echo "  MISS  ${name}"
    missing=1
  fi
}

missing=0
check "ffmpeg"     command -v ffmpeg
check "ffprobe"    command -v ffprobe
check "python3"    command -v python3
check "Pillow"     python3 -c "import PIL"
check "fc-match"   command -v fc-match
check "say"        command -v say

if [ "${missing:-0}" = "1" ]; then
  echo ""
  echo "Some dependencies missing. Install with:"
  echo "  brew install ffmpeg fontconfig"
  echo "  pip3 install Pillow"
  exit 1
fi

# .env
if [ ! -f "${repo_dir}/.env" ]; then
  cp "${repo_dir}/.env.example" "${repo_dir}/.env"
  echo ""
  echo "Created .env. Set ELEVENLABS_API_KEY there if you want ElevenLabs;"
  echo "otherwise narration falls back to macOS say -v Otoya (free)."
fi

echo ""
echo "Install complete. Try in Claude Code:"
echo "  /shortvideo-loop my-first-project"
