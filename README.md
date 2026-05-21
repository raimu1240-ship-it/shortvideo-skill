# shortvideo-skill

A Claude Code skill set that turns a one-line brief into a short empathy-first vertical video (720x1280 or 1080x1920) with Japan-only stock footage, irasutoya inserts, two-line captions, and auto-switched narration.

Built on the Anthropic [Agent Skills](https://code.claude.com/docs/en/skills) standard. Designed around the [Orchestrator-Subagent + Generator-Verifier](https://claude.com/blog/multi-agent-coordination-patterns) coordination patterns.

## Components

| Path | Role |
|---|---|
| `.claude/skills/shortvideo-planner/` | Turn user brief into a frozen `input.json` (sprint contract) |
| `.claude/skills/shortvideo-generator/` | 7-stage pipeline: lint → fetch → curate → narrate → caption → render → probe |
| `.claude/skills/shortvideo-reviewer/` | Independent reviewer running in a forked subagent context |
| `.claude/agents/shortvideo-reviewer.md` | 26-point rubric (V/T/A/P/L/Q) used by the reviewer |
| `.claude/commands/shortvideo-loop.md` | End-to-end orchestrator with bound autonomy (max 3 rounds) |
| `scripts/` | 8 Python utilities (lint, fetch, render, probe, captions, contact-sheet, tts) |
| `evaluations/` | 3 eval scenarios (replay, overseas-bg rejection, PR-tone rejection) |
| `examples/` | Frozen passing examples used by the reviewer for few-shot calibration |

## Install

```bash
git clone https://github.com/raimu1240-ship-it/shortvideo-skill.git ~/code/shortvideo-skill
cd ~/code/shortvideo-skill && ./install.sh
cp .env.example .env   # optional: set ELEVENLABS_API_KEY for ElevenLabs narration
```

`install.sh` creates symlinks under `~/.claude/skills/`, `~/.claude/agents/`, and `~/.claude/commands/`. Re-run anytime; `git pull` reflects updates without reinstall.

## Usage

**Launch Claude Code from inside this repository** so the project-level
`.claude/agents/shortvideo-reviewer.md` is discovered:

```bash
cd ~/code/shortvideo-skill
claude
```

Then in the session:

```
/shortvideo-loop my-first-project
```

The orchestrator will plan, generate, review, and self-correct up to 3 rounds. Output lands at `projects/my-first-project/output.mp4`.

For manual control, run the stages separately: `/shortvideo-planner`, `/shortvideo-generator`, then invoke `shortvideo-reviewer` as a skill.

### Why the cwd matters (reviewer recognition)

Claude Code discovers custom subagents from the **project-level**
`.claude/agents/` directory (relative to cwd at launch). Phase 4.D.0.b
confirmed empirically that the Personal-scope symlink at
`~/.claude/agents/shortvideo-reviewer.md` that `install.sh` creates is
**not** sufficient on its own: when `claude` is launched from a different
directory, the host runtime returns
`Agent type 'shortvideo-reviewer' not found`.

If you must launch Claude Code from another directory, `/shortvideo-loop`
auto-falls back to `subagent_type="general-purpose"` with a prompt body
that loads the reviewer spec. This works but loses `context: fork`
strict purity (the reviewer shares one context with the orchestrator).

## Requirements

- macOS (tested on 14+)
- `ffmpeg`, `ffprobe` (`brew install ffmpeg`)
- Python 3.9+ with `Pillow` (`pip3 install Pillow`)
- A Japanese bold font (Hiragino Sans W7 ships with macOS)
- Optional: ElevenLabs API key for higher-quality narration

## Design principles

- **No BGM, no PR badges, no brand bars** in the produced video. The empathy-first format is opinionated; PR-style overlays belong to a different skill.
- **Japan-only backgrounds.** Pexels search results are filtered through a Vision contact-sheet pass before render.
- **Deterministic render.** Same `input.json` + same fonts → same `output.mp4` md5sum (per host).
- **Independent reviewer.** Runs in a forked subagent context so it cannot see how the generator reasoned.
- **Bound autonomy.** Hard cap at 3 generate-review rounds; escalates rather than looping forever.

## Status

Phase 0/1 (minimum viable harness). Author: raimu1240-ship-it, personal validation prior to org migration. Issues and PRs welcome.

## License

MIT. See `LICENSE`.
