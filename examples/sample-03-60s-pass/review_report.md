# Review Report — sample-03-60s-pass

## Summary
blocker=0 / warning=1 / info=0

## Blocker

なし ✓ — 27 観点 (V01-V09 / T01-T06 / A01-A04 / P01-P03 / L01-L03 / Q01-Q05) + H01 全て pass。

## Warning

### A01 loudnorm I=-25.34 LUFS (全体, t=0-56s)
- 観測: ffprobe_quality.json で `loudnorm_I=-25.34`、acceptance_criteria.loudnorm_lufs_range=[-25,-21] の下限を 0.34 LUFS 下回る。聴感では「やや小さい」程度。
- fix: render_video.py に ffmpeg loudnorm 2-pass を組み込めば自動 -23 LUFS 固定にできる (Phase 5 候補)。
- 配信影響: 配信側の自動ノーマライズで他動画と微差が出る程度、配信不可レベルではない。

## Info

なし

## Patches (JSON array)

```json
[]
```

## このサンプルの位置付け

**reviewer few-shot calibration として「人間目視 pass 済みの 60s 例」**:

- bg = 10 seg / 8 unique src (max 重複 20%) → V07 pass
- illust = 10 seg / 10 unique 単キャラ PNG (grid なし、ため息サラリーマン / 迷う男性 / OK 男性 等) → V08/V09 pass
- caption = 全 seg ≤12 字、voice/caption overlap ≥ 60% → T01/T04/T06 pass
- bg cross-segment rotation で voice 進行中も 2-3 秒で切替 → 視聴維持率対策
- PNG `-loop 1` + chunk re-encode + cfr で overlay 暗転ゼロ → 滑らかな視聴体験

**HUMAN_REVIEW.md verdict: pass** (project owner / 2026-05-21)。Phase 4.F human gate を通過した実例。新規 project の reviewer はこの review_report.md を few-shot として読んでから 27+H rubric を適用すること。
