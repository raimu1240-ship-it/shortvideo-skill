---
name: shortvideo-generator
description: Generates a short empathy-first vertical video (720x1280 or 1080x1920) from a validated input.json. Pipelines Japan-only landscape video bg + irasutoya inserts + empathy captions + auto-switched narration (say/ElevenLabs). Use AFTER shortvideo-planner has produced projects/<name>/input.json. Outputs output.mp4 + ffprobe_quality.json.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash(python3 *), Bash(ffmpeg *), Bash(ffprobe *), Bash(mkdir *), WebFetch
argument-hint: [project-name]
---

# shortvideo-generator

Take a finalized `projects/<name>/input.json` and produce `projects/<name>/output.mp4` plus `ffprobe_quality.json`.

Runs Stages 0-6 sequentially. Each stage has a single responsibility, machine-checks where possible, and writes intermediate artifacts under `projects/<name>/work/` so cache + resume work.

## When this runs

- AFTER `shortvideo-planner` has saved a frozen `input.json`
- Invoked manually (`disable-model-invocation: true`) — never automatic
- Project path = `projects/<name>/` (cwd 相対、つまり claude 起動ディレクトリ配下に作られる)

## 必須: repo root の resolve

すべての shell コマンドの前に、以下を実行して repo root を環境変数に保存する。
`scripts/` への参照は cwd 不問のため絶対パス化が必要 (`projects/` は cwd 配下で OK)。

```bash
SV_REPO=$(python3 -c "import os; print(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(os.path.expanduser('~/.claude/agents/shortvideo-planner.md'))))))")
```

これは `~/.claude/agents/shortvideo-planner.md` の symlink を辿って repo root
(`~/code/shortvideo-skill` 等) を取得する。install.sh で symlink が貼られている前提。

以降の `scripts/...` 呼び出しはすべて `$SV_REPO/scripts/...` で行う。

## Required references

Read each of these before the first run of a session — they encode constraints the scripts assume:

- [references/recipe-narration-vertical.md](references/recipe-narration-vertical.md) — Stage flow and ffmpeg patterns
- [references/traps-9.md](references/traps-9.md) — known failure modes the scripts auto-block
- [references/overlay-positioning.md](references/overlay-positioning.md) — Y-coordinate table by resolution
- [references/stock-sources.md](references/stock-sources.md) — Pexels / Mixkit / Pixabay / Coverr の使い分け表
- [references/pexels-curation.md](references/pexels-curation.md) — how to fetch Japan-only video bg via WebFetch + urllib
- [references/irasutoya-feed-howto.md](references/irasutoya-feed-howto.md) — Atom feed + image URL extraction

[schema.json](schema.json) is the JSON Schema for input.json.

## Stages

Copy this checklist into the working response and tick off as you go:

```
Stage Progress:
- [ ] Stage 0: lint input.json
- [ ] Stage 1: fetch bg videos (Pexels)
- [ ] Stage 2: fetch illusts (irasutoya)
- [ ] Stage 3: contact_sheet review (Vision pass for overseas exclusion)
- [ ] Stage 4: generate narration mp3
- [ ] Stage 5: generate caption + bubble PNGs
- [ ] Stage 6: render_video.py
- [ ] Stage 7: ffprobe_quality.py
```

### Stage 0 — validate input.json

```bash
python3 $SV_REPO/scripts/lint_recipe.py projects/$1/input.json
```

Exit 1 (error) → stop, ask user to fix. Exit 2 (warnings only) → proceed but surface warnings to user before continuing.

### Stage 1 — fetch background videos

For each segment, the planner has set `bg_query` like `"japan train station"`.

1. WebFetch `https://www.pexels.com/ja-jp/search/videos/<url-encoded query>/` → extract up to 5 video page IDs (format `/ja-jp/video/<id>/`)
2. WebFetch each video page → find direct mp4 URL (pattern `videos.pexels.com/video-files/<id>/*.mp4`)
3. Pick the first 1080x1920 (or any 9:16) candidate; if none, fall back to landscape (will be cropped later)
4. Download with `python3 $SV_REPO/scripts/fetch_pexels.py <url> projects/$1/work/assets/bg_<sid>.mp4 --cache projects/$1/work/cache/pexels`

**chunk rotation の素材プールは render_video.py が自動構築**: 全 segment の
`bg_<sid>.mp4` を集めて 1 つの `bg_pool` にまとめ、各 chunk で
`global_chunk_offset` を進めて cross-segment で別 src を pick する設計
(`scripts/render_video.py:246-257`)。segment ごとに別ファイルを持たせる
必要はない — **大事なのは planner が seg ごとに unique な `bg_query` を
書くこと** (V07 ルール: 同一 bg_query が 50% 超で blocker)。

### Stage 1.5 — stale cache 自動削除 (bg_pool / bg_query 切替検出)

input.json が前ラウンドから変更された場合、**前ラウンドの bg 素材と chunk が
残ったまま再生成すると古い動画が混入する** (test-001 Round 2→3 で発生)。
Stage 1 開始前に、各 segment の現在の `bg_pool` / `bg_query` と
`work/stages/scene_<sid>_chunk_*.mp4` / `work/assets/bg_<sid>*.mp4` を照合し、
**input.json で値が変わっている segment** は cache を削除:

```bash
python3 $SV_REPO/scripts/segment_hash.py projects/$1/input.json \
  --diff projects/$1/history/round_<N-1>/segment_hashes.json \
  > projects/$1/history/round_<N>/segment_hash_diff.json
# changed/removed segment id ごとに以下を実行
for sid in $(jq -r '.changed[], .removed[]' projects/$1/history/round_<N>/segment_hash_diff.json); do
  rm -f projects/$1/work/assets/bg_${sid}*.mp4 \
        projects/$1/work/assets/illust_${sid}.png \
        projects/$1/work/stages/scene_${sid}_*.mp4 \
        projects/$1/work/voices/voice_${sid}*.mp3 \
        projects/$1/work/captions/cap_main_${sid}.png \
        projects/$1/work/captions/bubble_${sid}.png
done
```

unchanged segment は cache 再利用 OK (高速化)。

### Stage 2 — fetch irasutoya inserts

For each segment with `illust_query`:

1. WebFetch `https://www.irasutoya.com/feeds/posts/default?q=<query>&max-results=6&alt=json` → list article URLs
2. WebFetch one article page → extract `s800` PNG URL on `blogger.googleusercontent.com`
3. Download with `python3 $SV_REPO/scripts/fetch_irasutoya.py <url> projects/$1/work/assets/illust_<sid>.png --cache projects/$1/work/cache/irasutoya`

### Stage 3 — contact_sheet review (Vision pass)

```bash
python3 $SV_REPO/scripts/contact_sheet.py --videos projects/$1/work/assets/bg_*.mp4 --out projects/$1/work/contact_sheet.jpg
```

Read the contact sheet via the Read tool and judge visually: does every frame look like Japan? If any cell looks like overseas (playground / signage / pedestrians), set `contact_sheet_passed: false` for that segment in `input.json` and **return to Stage 1** with a different `bg_query` (e.g. add "tokyo" or "kyoto" qualifier).

Only proceed when every segment has `contact_sheet_passed: true`.

### Stage 4 — narration (per-segment)

```bash
python3 $SV_REPO/scripts/tts_elevenlabs.py --per-segment \
  --input-json projects/$1/input.json \
  --out-dir projects/$1/work/voices
```

Each segment's `voice_text` is rendered to a separate `voice_<sid>.mp3` under
`work/voices/`, and `work/voices/durations.json` records the actual ffprobe
duration per segment. Stage 6 (render) reads `durations.json` and overrides
each `segment.duration_sec` with the measured voice length, so the rendered
video duration ≒ voice duration (no `-shortest` truncation, no trailing silence).

If `ELEVENLABS_API_KEY` is in `.env`, ElevenLabs Morioki is used; otherwise
macOS `say -v Otoya`.

Legacy single-mode (`python3 $SV_REPO/scripts/tts_elevenlabs.py --text "..." voice.mp3`)
is still supported for backwards compat — render falls back to legacy when
`durations.json` is absent.

### Stage 5 — captions + bubbles

```bash
python3 $SV_REPO/scripts/make_captions.py projects/$1/input.json projects/$1/work/captions
```

Writes `cap_main_<sid>.png` and `bubble_<sid>.png` per segment. Resolution-aware Y coordinates from `overlay-positioning.md` are baked into the script.

### Stage 6 — render (bg は約 2.5 秒ごと chunk rotation)

```bash
python3 $SV_REPO/scripts/render_video.py projects/$1/input.json projects/$1/work projects/$1/output.mp4
```

Deterministic ffmpeg pipeline: per-segment bg trim → scene overlay (scrim + illust + bubble + caption) → concat → voice mux. Uses `crf 23`, `pix_fmt yuv420p`, `preset medium`, fixed fps from input.json.

**背景動画の chunk rotation (実装済仕様、変更禁止)**: `prepare_segment()`
(`scripts/render_video.py:51-128`) が 1 segment を `FASTCUT_CHUNK_SEC=2.5s`
目安で chunk 分割し、各 chunk を `scene_<sid>chunk<N>.mp4` として書き出して
concat する。視聴者が「同じ動画が長時間流れている」と感じないための仕様。

- chunk 数: `max(2, round(duration_sec / 2.5))` = 最低 2 chunks/seg
- 各 chunk の src: 全 seg `bg_*.mp4` を集めた pool から
  `global_chunk_offset` rotation で cross-segment pick (segment 境界を越えて
  別 src を順次使う設計)
- **pool バリエーションが落ちる = 全 chunk が同じ src の offset 違いで終わる**
  ため、planner で seg ごとに unique な `bg_query` を書くことが死活的に重要
  (V07 = 同一 bg_query >50% で blocker)

reviewer rubric V10 が「unique src 数 == 1 の segment があれば blocker」で
機械検出する (= bg_query 重複の極端ケースを後段でも catch)。

### Stage 7 — quality probe

```bash
python3 $SV_REPO/scripts/ffprobe_quality.py projects/$1/output.mp4 projects/$1/input.json --out projects/$1/ffprobe_quality.json
```

Exit 0 (pass) → done, report path to user. Exit 1 (acceptance failed) → surface specific errors, the orchestrator will trigger the reviewer.

## What NOT to do

- Do NOT skip Stage 0 or Stage 3 — they are the two cheapest gates that catch the most failures
- Do NOT add ffmpeg flags beyond what `render_video.py` uses (deterministic output depends on flag stability)
- Do NOT mix BGM (acceptance_criteria.must_not_have includes `bgm`)
- Do NOT add brand bars / PR badges / persistent logos (must_not_have)
- Do NOT modify the input.json mid-pipeline; if a stage fails, surface and ask the user

## Output

- `projects/<name>/output.mp4`
- `projects/<name>/ffprobe_quality.json`
- `projects/<name>/work/` (intermediate, can be deleted to free space; cache/ inside is reusable)
