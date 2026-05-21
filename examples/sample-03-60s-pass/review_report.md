# Review Report — sample-03-60s-pass

## Summary
blocker=0 / warning=0 / info=0

## Blocker

なし ✓ — 27 観点 (V01-V09 / T01-T06 / A01-A04 / P01-P03 / L01-L03 / Q01-Q05) + H01 全て pass。

## Warning

なし ✓ — render_video.py に ffmpeg loudnorm filter (`-af loudnorm=I=-23:LRA=11:tp=-1.5`) を組み込み、A01 (loudnorm 範囲外) が完全解消。ffprobe で loudnorm_I=-22.99 (target -23 ぴったり)、人間目視で音量も自然と確認 (verdict=pass)。

## Info

なし

## Patches (JSON array)

```json
[]
```

## このサンプルの位置付け

**reviewer 用の参考事例 (人間目視 pass 済みの 60 秒見本)**:

- bg = 10 seg / 8 unique src (max 重複 20%) → V07 pass
- illust = 10 seg / 10 unique 単キャラ PNG (grid なし、ため息サラリーマン / 迷う男性 / OK 男性 等) → V08/V09 pass
- caption = 全 seg ≤12 字、voice/caption overlap ≥ 60% → T01/T04/T06 pass
- bg cross-segment rotation で voice 進行中も 2-3 秒で切替 → 視聴維持率対策
- PNG `-loop 1` + chunk re-encode + cfr で overlay 暗転ゼロ → 滑らかな視聴体験

**HUMAN_REVIEW.md verdict: pass** (project owner / 2026-05-21)。人間レビュー gate を通過した実例。新規 project の reviewer はこの review_report.md を参考事例として読んでから 27+H rubric を適用すること。
