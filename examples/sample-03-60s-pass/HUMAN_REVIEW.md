# Human review — sample-03-60s-pass (frozen)

**Round**: final (最終ラウンド、人間レビューで pass 判定)
**Reviewer (AI)**: blocker=0 / warning=1 (A01 LUFS のみ) / info=0
**Output**: `examples/sample-03-60s-pass/output.mp4` (20.7 MB, 56.19s)

## Human verdict

**reviewer**: project owner
**timestamp**: 2026-05-21
**verdict**: **pass**
**notes**: bg 切り替わりで overlay が一瞬消える「暗転」が解消、s3 illust も grid から「分かれ道で迷う人」単キャラに改善、s5/s8 も単キャラ。配信レベル OK。

## このファイルの位置付け

**判定基準の参考事例 (frozen)** として `examples/sample-03-60s-pass/` を構成する 1 ファイル。reviewer subagent が新規 project を grade する際の参考事例として、「人間目視 pass 済みの 60 秒見本 = HUMAN_REVIEW.md verdict: pass を持つ動画はこういう品質」を学ぶために読む。

H01 (`HUMAN_REVIEW.md exists with verdict: pass`) は人間目視を通っていない動画には付与されない hard gate。このファイルがあるサンプルは「人間が見て配信 OK と判定した動画」の手本として扱う。
