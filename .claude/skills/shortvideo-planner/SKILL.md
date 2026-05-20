---
name: shortvideo-planner
description: Converts a user's natural-language video brief into a validated input.json with acceptance_criteria. Use when the user requests a new short vertical video, asks to design a scenario, or starts a new project under projects/. Always run BEFORE shortvideo-generator. Outputs projects/<name>/input.json.
allowed-tools: Read, Write, Edit
argument-hint: [project-name]
---

# shortvideo-planner

Plan a short empathy-first vertical video and produce a frozen `input.json` that the generator and reviewer will both bind to.

## When this runs

- User says "新しい縦動画を作りたい" / "プランニングして" / "シナリオ書いて"
- A `projects/<name>/` directory does not yet have `input.json`
- Always **before** `/shortvideo-generator`

## Process

1. Ask the user (max 3 questions, batched):
   - 尺の目安 (秒): 10 / 15 / 30 / 45
   - 解像度: 720x1280 (軽量) or 1080x1920 (LP・提案用)
   - シナリオの一言 (誰が、何で悩んでいて、どうなったか)

2. Read [references/tone-guide-empathy.md](references/tone-guide-empathy.md) to confirm what counts as PR-tone and must never appear in captions.

3. Read [references/scenario-templates.md](references/scenario-templates.md) and pick the closest template (3-scene / 5-scene / 7-scene).

4. Draft `projects/<name>/input.json` with these top-level keys:
   - `project_name`, `duration_target_sec`, `resolution`, `fps` (default 24)
   - `persona` (age, gender, context)
   - `scenario.segments[]` — each with `id`, `duration_sec`, `bg_query`, `illust_query`, `voice_text`, `caption_main`, `caption_sub`, `sub_delay`, `bubble_text`
   - `acceptance_criteria` (sprint contract — see below)
   - `voice_provider: "auto"` (auto-switches to ElevenLabs if API key, else say)
   - `seed: 42` (for deterministic asset picking)

5. Echo the draft to the user, ask "この内容で確定して generator に流していい？"

6. On approval, save the file and exit. Do NOT call the generator yourself — that is the orchestrator's job.

## acceptance_criteria (sprint contract)

This block is the "done" definition that the reviewer will grade against. Always include:

```json
{
  "duration_target_sec": 30,
  "duration_tolerance_sec": 0.5,
  "resolution": "1080x1920",
  "fps": 24,
  "av_drift_max_sec": 0.1,
  "loudnorm_lufs_range": [-25, -21],
  "must_have": [
    "caption_main_per_segment",
    "irasutoya_per_segment",
    "japanese_bg_only"
  ],
  "must_not_have": [
    "pr_badge",
    "header_brand_bar",
    "footer_brand_bar",
    "logo_persistent_overlay",
    "product_card",
    "bgm",
    "direct_sales_caption"
  ]
}
```

If the user's brief implies any item in `must_not_have` (e.g. they want a "PR badge"), push back: the skill is purpose-built for the empathy-first format, and PR-style decorations belong to a different skill.

## Output

`projects/<name>/input.json` only. No other files. The generator will create `work/`, `output.mp4`, and `ffprobe_quality.json` later.

## Rules

- caption_main 1 行は最大 8 字目安、12 字超は禁止 (lint_recipe.py が拒否)
- voice_text と caption_main は漢字優先で揃える (ElevenLabs アクセント安定化)
- sub_delay は 2.0 〜 4.0 秒、0 は禁止 (視聴者がスキップする)
- 一人称・体験談・気付きトーン。ブランド名や商品名を caption に書かない
- 背景は日本ロケのみ。bg_query に "japan ..." を明示
