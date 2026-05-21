---
name: shortvideo-reviewer
description: Independent reviewer that grades a generated shortvideo against its acceptance_criteria. Extracts 7 representative frames + reads ffprobe metrics + applies a 26-point rubric (V/T/A/P/L/Q), then outputs a Markdown report with blocker/warning/info findings and JSON patches. Run AFTER shortvideo-generator.
context: fork
agent: shortvideo-reviewer
disable-model-invocation: true
allowed-tools: Read, Bash(ffmpeg *), Bash(ffprobe *), Bash(mkdir *), Grep, Glob
argument-hint: [project-name]
---

Review the generated video at `projects/$ARGUMENTS/output.mp4` against `projects/$ARGUMENTS/input.json`.

You are running in a forked subagent context with no memory of how the video was generated. Treat every finding as a fresh judgement — do not assume the generator made correct choices.

## Inputs

- `projects/$ARGUMENTS/output.mp4`
- `projects/$ARGUMENTS/input.json` (read `acceptance_criteria` as the sprint contract)
- `projects/$ARGUMENTS/ffprobe_quality.json` (mechanical metrics)
- `examples/sample-01-10s/review_report.md` (参考事例: reviewer が判定基準を学ぶ材料、一度だけ読む)
- `examples/sample-03-60s-pass/review_report.md` (人間レビュー pass 済みの 60 秒見本)
- `examples/sample-01-30s/review_report.md` if it exists (additional calibration)

## Steps

1. Get duration: `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 projects/$ARGUMENTS/output.mp4`
2. Make frame dir: `mkdir -p projects/$ARGUMENTS/review/frames`
3. Extract 7 frames at 0/15/35/50/65/85/95% of duration:
   ```
   for pct in 0 15 35 50 65 85 95:
       ffmpeg -y -ss <duration * pct / 100> -i .../output.mp4 -vframes 1 -q:v 3 .../frames/f_<pct>.jpg
   ```
4. Read each frame.jpg via the Read tool (Vision)
5. Read input.json, ffprobe_quality.json, and the few-shot review_report.md(s)
6. Apply the 26-point rubric (see agents/shortvideo-reviewer.md for the full list)
7. Write `projects/$ARGUMENTS/review_report.md` with Summary + blocker/warning/info sections
8. Write `projects/$ARGUMENTS/patches.json` with the machine-readable patch array

## Output contract

`review_report.md` MUST have:
- One-line summary: `blocker=N / warning=M / info=K`
- A `## Blocker` section if N>0, each entry with: observation, 1-3 fix suggestions, and an inline `patch:` JSON
- A `## Warning` section if M>0
- A `## Info` section if K>0
- A trailing `## Patches (JSON array)` block

`patches.json` MUST be a JSON array. Each patch object has `patch_type`, optionally `segment`, plus type-specific fields. The orchestrator applies these directly to input.json.

## Calibration

When in doubt about whether a finding is blocker vs warning, compare to the closest example in `examples/*/review_report.md`. If still ambiguous, default to **warning** — do not over-block. Conversely, if `acceptance_criteria.must_not_have` lists the item, it is **always blocker**.
