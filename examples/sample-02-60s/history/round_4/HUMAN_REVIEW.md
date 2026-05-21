# Human review — sample-02-60s round_4 (Phase 4.F closure)

**Round**: 4 (Phase 4.F bug-fix iterations: 3 attempts before pass)
**Reviewer (AI)**: ffprobe errors=0、warnings=1 (A01 LUFS のみ)
**Output**: `examples/sample-02-60s/history/round_4/output.mp4` (20.7 MB, 56.19s)

## Human verdict

**reviewer**: project owner
**timestamp**: 2026-05-21
**verdict**: **pass**
**notes**: bg 切り替わりで overlay が一瞬消える「暗転」が解消、s3 illust も grid から「分かれ道で迷う人」単キャラに改善、s5/s8 も単キャラ。配信レベル OK。

## round_3 → round_4 改善経緯 (3 bugs)

| bug | 検出経路 | 修正 |
|---|---|---|
| **bug1 V09 grid 漏れ** | round_3 human review で s3「5段階の困る表情」grid 残存 | GRID_KEYWORDS に「無気力」「を運転している」「シーン」「段階」「の表情」追加 + s3 を「迷う 男性」/ s5 「アイデア 男性」/ s8 「ため息 サラリーマン」へ query 変更 |
| **bug2 bg 単 src 固定** | round_3 human review で「voice/caption 中は bg が seg 境界でしか変わらない」と指摘 | render_video.py prepare_segment に `bg_pool` + `global_chunk_offset` 追加、各 chunk が pool から異 seg src を引く cross-segment rotation 実装 |
| **bug3 overlay 暗転** | round_4 v1/v2 で「bg 切り替わり瞬間に illust+caption 一瞬消える」と指摘 | (1) PNG input に `-loop 1 -t seg_dur` 追加 (PNG が 1 frame しか入らず残時間 bg のみ表示問題) + (2) chunk concat を `-c copy` → re-encode + cfr (chunk 境界の DTS 不連続による 1 frame 抜け) |

## なぜこれが Phase 4 で最も重要だったか

reviewer subagent (general-purpose fallback) は **3 bug 全て見逃した** (rubber-stamp):
- round_3 で V09 PASS と宣言 → 実は s3 grid 残存
- bg 単 src 問題は rubric にすら無かった
- overlay 暗転は frame 抽出 7 枚では境界 1 frame を catch しきれない

→ 「verifier が generator と同じ盲点を共有する」(agent-essence.md V-2) の典型実例。
人間目視 gate が機能して初めて 3 bug が surface した。Phase 4.F で
HUMAN_REVIEW.md を loop.md 必須 step に組み込んだのは正解だった。

## 残 warning (info レベル、配信可)

- A01 loudnorm I=-25.34 LUFS (acceptance -25 〜 -21 LUFS 下限を 0.34 下回り、配信側ノーマライズで他動画と僅か音量差出る可能性)

これは render_video.py に ffmpeg loudnorm 2-pass を組み込めば解消、Phase 5 候補。
