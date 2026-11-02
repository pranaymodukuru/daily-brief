#!/usr/bin/env bash
# Local install: puts the `daily-brief` CLI on PATH and links the skill into
# every coding agent's skills folder found on this machine.
#   ./install.sh               install, or update after a git pull
#   ./install.sh --uninstall   remove the CLI and the skill links (keeps ~/.daily-brief)
set -euo pipefail

repo="$(cd "$(dirname "$0")" && pwd -P)"
skill="$repo/skills/daily-brief"
# Skills folders of agents that read SKILL.md: Claude Code, Codex, and the shared ~/.agents.
dirs=("$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.agents/skills")

if [[ "${1:-}" == "--uninstall" ]]; then
  uv tool uninstall daily-brief || true
  for d in "${dirs[@]}"; do
    [[ -L "$d/daily-brief" ]] && rm "$d/daily-brief" && echo "unlinked $d/daily-brief"
  done
  exit 0
fi

command -v uv >/dev/null || { echo "needs uv: https://docs.astral.sh/uv/" >&2; exit 1; }
uv tool install --editable --force "$repo"

for d in "${dirs[@]}"; do
  [[ -d "$(dirname "$d")" ]] || continue  # that agent isn't installed
  mkdir -p "$d"
  if [[ -e "$d/daily-brief" && ! -L "$d/daily-brief" ]]; then
    echo "skipped $d/daily-brief: a folder that isn't this skill is already there"
    continue
  fi
  ln -sfn "$skill" "$d/daily-brief" && echo "linked $d/daily-brief"
done

daily-brief init
