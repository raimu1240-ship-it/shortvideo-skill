---
name: shortvideo-loop
description: Orchestrates the full plan→generate→review→fix loop for a shortvideo project. Drives shortvideo-planner, shortvideo-generator, and shortvideo-reviewer in sequence, merges JSON patches automatically, and retries until blocker=0 or 3 rounds reached. Use to fully automate one video end-to-end.
allowed-tools: Read, Write, Edit, Bash(python3 *), Bash(ffmpeg *), Bash(ffprobe *), Bash(mkdir *), WebFetch, Skill
argument-hint: [project-name]
---

# shortvideo-loop

End-to-end orchestrator for a single project. The user gives a project name; this command takes care of everything until `output.mp4` passes the reviewer or escalates after 3 failed rounds.

## Bound autonomy (public Anthropic harness-design principle)

- Maximum loop count: **3**. After 3 rounds with blocker > 0, escalate to the user with the remaining blockers — do not silently keep retrying.
- Each round writes its review report to `projects/<name>/history/round_<N>/review_report.md` so progress is auditable.
- The user can interrupt at any point; resume from the last successful round by re-running this command.

## Steps

Copy this progress checklist into your reply:

```
shortvideo-loop progress (project=<name>)
- [ ] Round 0: planner → input.json
- [ ] Round 1: generate → review → (blocker check)
- [ ] Round 2 (if needed): apply patches → generate → review
- [ ] Round 3 (if needed): apply patches → generate → review
- [ ] Final: report status
```

### Round 0 — Plan

If `projects/<name>/input.json` does not exist:
- Invoke `/shortvideo-planner <name>` (the planner skill)
- Confirm with the user that the draft is acceptable BEFORE proceeding

If it exists, skip this round and tell the user "Using existing input.json. Use /shortvideo-planner manually if you want to revise."

### Round N — Generate + Review (N = 1, 2, 3)

1. Run `/shortvideo-generator <name>` (the generator skill, all Stages 0-7)
2. Spawn the reviewer subagent via the **Agent tool**.
   - DO NOT use the Skill tool — the `shortvideo-reviewer` skill has
     `disable-model-invocation: true` and rejects programmatic Skill calls by
     design (E3: 生成者と評価者の物理的分離).
   - **Preferred**: `subagent_type="shortvideo-reviewer"`. This requires
     `.claude/agents/shortvideo-reviewer.md` to be visible to the host runtime,
     which in practice means **`claude` was launched from this repository's
     directory** (Claude Code reads project-level `.claude/agents/` from cwd).
     Confirmed Phase 4.D.0.b: a Personal-scope symlink at
     `~/.claude/agents/shortvideo-reviewer.md` does NOT make the agent
     discoverable when cwd is elsewhere.
   - **Fallback (if `Agent type 'shortvideo-reviewer' not found`)**:
     `subagent_type="general-purpose"` with this prompt body —
     "You are the shortvideo-reviewer subagent. Read the agent spec at
     `.claude/agents/shortvideo-reviewer.md` first, then execute the steps in
     `.claude/skills/shortvideo-reviewer/SKILL.md` for project `<name>`.
     Working directory: repo root. Required outputs:
     `projects/<name>/review_report.md` (Markdown with `blocker=N / warning=M
     / info=K` summary line + sections + `## Patches (JSON array)`) and
     `projects/<name>/patches.json` (JSON array of patches)."
     The fallback loses E3 strict purity (no `context: fork`) but keeps the
     loop runnable. Surface a warning in the user reply when fallback is used.
3. Read `projects/<name>/review_report.md` (the reviewer's summary)
4. Copy the report to `projects/<name>/history/round_<N>/review_report.md`

### Patch decision

- **blocker == 0** AND warning ≤ 3: proceed to **Human review gate** (next section). DO NOT declare "Phase complete" until the human gate passes.
- **blocker == 0** AND warning > 3: ask the user "warning が N 件残っています。このまま採用するか、patch を当てて再ループしますか？" — wait for explicit answer.
- **blocker > 0** AND round < 3: apply patches from `projects/<name>/patches.json` to `input.json`, then loop to next round.
- **blocker > 0** AND round == 3: escalate.

### Human review gate (Required final step — never skip)

Anthropic harness-design principle: *verifier が generator と同じ盲点を共有する*
(agent-essence.md V-2 / C-3 迎合性). The reviewer subagent is still a Claude
model; it can rubber-stamp the orchestrator's output without surfacing
problems a human would catch immediately (e.g. caption tone feels off,
illust feels disconnected from voice, narrative pacing is dead, etc.).
**Pass through this gate before reporting Phase / project completion.**

1. Open the output for human viewing:
   ```bash
   open projects/<name>/output.mp4
   ```
2. Present the user with a 3-line summary:
   - `output.mp4 を再生しました (duration=Ns)`
   - `Reviewer 評価: blocker=0 / warning=N`
   - `視聴して pass か fail を判定してください。fail の場合は理由 1-3 行で。`
3. Wait for explicit `pass` / `fail` reply (no auto-pass on silence).
4. Record the verdict to `projects/<name>/HUMAN_REVIEW.md`:
   ```markdown
   verdict: pass | fail
   reviewer: <user name or "project owner">
   timestamp: <ISO>
   notes: <user's fail reason or "OK">
   ```
5. If `fail`, **treat the user's notes as a new patches.json entry** and
   loop back to Round N+1 even if reviewer said blocker=0. The human verdict
   overrides the AI verdict. Bound autonomy (max 3 rounds) still applies —
   if 3 human-review rounds also fail, escalate.
6. Only after `verdict: pass` may you report completion.

This is the gate that turned Phase 4 from "AI 評価 100%" into actual
delivery. Skipping it is the same failure mode as Phase 4.B.3
over-claiming E3 purity without runtime verification.

### Applying patches

For each patch object in `patches.json`:

| patch_type | action |
|---|---|
| `replace_bg` | Set `scenario.segments[<segment>].bg_query = <new_query>`. Also clear `contact_sheet_passed` so Stage 3 re-runs. |
| `replace_illust` | Set `scenario.segments[<segment>].illust_query = <new_query>`. Delete cached `work/assets/illust_<sid>.png`. |
| `rewrite_caption` | Set `scenario.segments[<segment>].caption_main = <new_caption>`. |
| `adjust_sub_delay` | Set `scenario.segments[<segment>].sub_delay = <new_delay>`. |
| `trim_trailing_silence` | Set top-level `trim_trailing_silence_sec = <seconds>`. The generator's Stage 6 trims accordingly. |
| `set_field` | Set the field at `path` (dot notation) to `value`. |

Unknown patch types: leave a warning in the user message; do not modify input.json.

After applying patches, write the updated input.json. Then recompute segment hashes:

```bash
python3 scripts/segment_hash.py projects/<name>/input.json \
  --diff projects/<name>/history/round_<N-1>/segment_hashes.json \
  > projects/<name>/history/round_<N>/segment_hash_diff.json
```

The diff lists `changed` / `unchanged` / `removed` segment ids. For each segment in `unchanged`, skip Stage 1/2/4 (fetch + tts) and reuse `work/cache/<segment_hash>/` artifacts. For `changed` segments, re-run all stages. For `removed`, garbage-collect `work/cache/<hash>/` to free disk.

Save the new hashes to `projects/<name>/history/round_<N>/segment_hashes.json` for the next diff.

### Escalation (round 3 with blocker > 0)

Tell the user:

```
3 round してもblocker N 件残っています:
- <blocker 1 のサマリ>
- <blocker 2 のサマリ>
...
projects/<name>/history/ に各ラウンドのレポートを保存。次の判断:
  a. 残りの blocker を手で直す
  b. acceptance_criteria を緩める (e.g. duration_tolerance_sec を上げる)
  c. このプロジェクトをスキップ
```

Wait for the user's choice. Do not proceed.

## Convergence safeguards (Anthropic harness-design principle)

- If the same patch_type is applied to the same segment in two consecutive rounds without resolving the blocker, surface a warning and stop the loop early. This indicates the generator cannot address the feedback.
- If the reviewer's blocker count *increases* between rounds, halt immediately and ask the user — the patch is making things worse.
