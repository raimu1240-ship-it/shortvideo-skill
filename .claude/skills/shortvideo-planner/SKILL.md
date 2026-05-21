---
name: shortvideo-planner
description: Converts a user's natural-language video brief into a validated input.json with acceptance_criteria. Use when the user requests a new short vertical video, asks to design a scenario, or starts a new project under projects/. Always run BEFORE shortvideo-generator. Outputs projects/<name>/input.json.
disable-model-invocation: true
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

### duration_sec の決め方 (一律値禁止)

**絶対に `duration_sec=8.0` のような一律値を全 segment にコピーしない**。
test-001 で実発話 4-5s に対して duration_sec=8.0 を一律設定したため、
generator (render_video.py) が `apad=whole_dur=8` で末尾に 3-4s の無音 padding
を入れ、視聴体験が「途中で会話が止まる」状態になった (Round 3 fail)。

推定式 (Otoya 180wpm / Morioki 200wpm 換算):
- 日本語 voice_text を **モーラ数 (≒ かな文字数)** で数える
- macOS say (Otoya 180): `duration = mora_count / 8.5 + 0.4` (発話 + 0.4s 余韻)
- ElevenLabs Morioki: `duration = mora_count / 9.5 + 0.4`
- 漢字 1 字 ≒ 2 モーラと仮置き (「工場 (こうじょう)」= 4 モーラ)

planner 段では推定値で OK。generator Stage 4 が actual TTS 後に
`work/voices/durations.json` を吐くので、ズレが大きい場合は patch で
`set_field` 経由で補正される設計 (`A03` blocker: voice 長 vs duration_sec
差 > 0.3s)。

| voice_text 例 | モーラ数目安 | 推定 duration_sec (Otoya) |
|---|---|---|
| 「迷ってた頃の話」(8 モーラ) | 8 | 1.4s + 余韻 0.5 = **2.0s** |
| 「電車で考え事が止まらなくて」(15 モーラ) | 15 | 2.2s + 0.5 = **2.7s** |
| 「気付いたら、自然と変わってた」(15 モーラ) | 15 | 2.2s + 0.5 = **2.7s** |
| 「○○を試してから 3 ヶ月、毎朝スッキリ」(20 モーラ) | 20 | 2.8s + 0.5 = **3.3s** |

短尺 (5-7s/seg) を基本にしてテンポを保つ。長すぎる voice_text は分割する。

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
- voice_text と caption_main は文字集合 60% 以上 overlap させる (T06 検出回避)
- voice_text の自然な発話長 ≈ segment.duration_sec ±0.5s。voice が短いと
  末尾無音 padding (`apad=whole_dur=N`) が長くなり「会話が途中で止まる」現象、
  長いと caption 表示が voice より先に終わる。**duration_sec を一律値で揃えない**
  (上記「duration_sec の決め方」セクション参照)
- sub_delay は 2.0 〜 4.0 秒、0 は禁止 (視聴者がスキップする)
- 一人称・体験談・気付きトーン。ブランド名や商品名を caption に書かない
- 背景は日本ロケのみ。bg_query に "japan ..." を明示

## Asset query diversification (V07/V08 再発防止)

本番運用で同じ素材を多数 segment で使うと「手抜き感」が出るため、planner 段で
**最初から query を分散**させる。lint と reviewer が後段で検出するが、planner
で予防する方が修正コストが低い。

| segments 数 | 最低 unique bg_query | 最低 unique illust_query |
|---|---|---|
| 1-3 | 1 (制約緩) | 1 (制約緩) |
| 4-5 | 2 | 2 |
| 6-7 | 3 | 3 |
| 8-10 | 4 | 4 |
| 11+ | 5 | 5 |

**ハードルール (lint と整合)**:
- 同じ `bg_query` が segments の 50% 以上に出ない (`>=50%` で V07 blocker)
- 同じ `illust_query` が segments の 50% 以上に出ない (`>=50%` で V08 blocker)
- 33% 超でも warning が出るので、可能なら均等分散させる

**bg_query 候補集 (10 segments 用、例)**:
- "japan train station morning" / "tokyo subway commuter"
- "japan park bench autumn" / "kyoto temple path"
- "japan residential street evening" / "japan riverside walk"
- "japan office building exterior" / "japan cafe interior"

**illust_query 候補集 (共感型ペルソナ x 局面)**:
- 困り局面: "考える 男性 困った" / "悩む 男性 パソコン" / "迷う 男性 立ち止まる"
- 気付き局面: "穏やか 男性 笑顔" / "歩く 男性 リラックス" / "コーヒー 男性 朝"

詳細な分散例は [references/scenario-templates.md](references/scenario-templates.md)
の "Query 分散テンプレ" セクション参照。
