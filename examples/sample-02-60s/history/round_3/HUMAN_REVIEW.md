# Human review — sample-02-60s round_3

**Round**: 3
**Reviewer (AI)**: blocker=0 / warning=3 / info=2 (V09 PASS、A01 LUFS 微差 + s10 mountain bg + s6 cache 流用)
**Output**: `examples/sample-02-60s/history/round_3/output.mp4` (20.6 MB, 56.19s)

## Human verdict

**reviewer**: project owner
**timestamp**: 2026-05-21
**verdict**: **fail**
**notes**:
1. illust が grid 残存 (s5「ひらめく 男性」= 車運転 12 グリッド、s8「ため息 男性」= 5 表情 grid)。reviewer は V09 PASS と判断したが、実フレーム目視で明らかに複数キャラ grid PNG。V09 機能不全 = fetch_irasutoya_id.py の GRID_KEYWORDS 漏れ (「無気力」「車を運転」等) + reviewer Vision の rubber-stamp。
2. 背景動画が 2-3 秒で切り替わっていない。期待は「voice/caption 進行中でも 2-3 秒ごとに別 src に切り替わる (1 テロップ = 1 背景の制限なし)」、現実装は seg 境界でしか bg が変わらない (1 seg 内は同 src を fastcut しても同じ動画)。render_video.py の bg fastcut 設計がクロス segment になっていない。

→ Phase 4.F.bug として round_4 で対処。

---

## ユーザーへの依頼

`/shortvideo-loop` Phase 4.F human review gate に基づき、上記 output.mp4 を
視聴して下記 3 観点で判定してください。AI reviewer は通過していますが、
最終 gate は人間です:

1. **配信して恥ずかしくないか** — 海外風 bg / illust 不一致 / テロップ違和感
2. **視聴体験として成立しているか** — 60s 中盤に飽きないか、narrative がつながるか
3. **共感型トーン違反がないか** — PR 色 / 押し付け / ペルソナ崩壊

verdict=fail の場合: 理由を notes に書き、`/shortvideo-loop` で round_4 を回す
(その時 patches.json にユーザー指摘を 1 件追加)。

verdict=pass の場合: HUMAN_REVIEW.md に pass + timestamp を記録、Phase 4
は本当の意味で完走。
