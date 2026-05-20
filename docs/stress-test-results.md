# Stress Test Results — Phase 3.A

公式 Anthropic harness-design 原則「Every component in a harness encodes an
assumption ... worth stress testing」に従い、planner / reviewer / loop の各
コンポーネントを 1 つずつ抜いた状態の品質を測定。それぞれの存在価値を数値と
質的観察で裏取りし、将来モデル進化で不要化したかの再評価ベースラインを残す。

測定対象: examples/ 配下の 3 calibration material
- sample-01-10s (10s, 2 seg, T06 一致型) — pass の手本
- sample-test (10s, 2 seg, T06 ズレ型) — fail 検出の手本
- sample-02-60s (60s, 10 seg, P02 連続 + T06 グラデーション + V07/V08 重複) — 長尺の手本

## Baseline (フル構成)

| sample | blocker | warning | info | rubric ver |
|---|---|---|---|---|
| sample-01-10s | 0 | 0 | 0 | v1 (T 5 件) |
| sample-test | 3 | 4 | 1 | v2 (T 6 件) |
| sample-02-60s | 4 | 4 | 2 | v3 (V 8 件 + T 6 件) |

フル構成 = planner 規約遵守 + lint mechanical gate + reviewer LLM gate + loop
の patch merge までフル稼働。examples/<name>/review_report.md が一次ソース。

## Ablation A — planner 抜き

planner skill を使わず、ユーザーが手書きで input.json を書いたケースをシミ
ュレート。問題: query 分散ルール / voice-caption overlap / 漢字優先などの
予防ルールが効かない。

**観察 (sample-02-60s のケースが該当)**:
sample-02-60s は当初 planner SKILL.md の query 分散ハードルール (commit
9c1cd31) が無かった時代に作られた input.json で、bg を 2 種類 × 5 seg、
illust を 2 種類 × 4-6 seg で配置していた。lint と reviewer が後段で V07
blocker (bg 50%) と V08 blocker (illust 60%) を出した。

**数値化**:
- planner ありの場合 → query 分散して同 V07/V08 が出ない設計 (sample-01-10s
  と sample-test は 2 seg のため V07/V08 評価範囲外、影響無)
- planner なしの場合 → sample-02-60s のように 10 seg で 2 種類重複 → V07
  blocker + V08 blocker + reviewer の指摘 26 patches

**結論**: planner は **長尺 (4 seg 超) で必須**。短尺 (1-3 seg) は手書きで
も成立。Phase 3 以降のモデル進化で「planner なしでも generator/reviewer が
分散を自動修正できる」状態になれば planner を再評価可能。

## Ablation B — reviewer 抜き

lint mechanical gate のみで判定するケース。LLM gate を抜いた状態。

**数値化** (sample-02-60s の lint 出力):
- lint errors: 4 件 (V07 / V08 / T06×2)
- lint warns: 13 件 (caption 字数 6 件 + T06w 7 件)

**reviewer フル稼働時の追加検出** (lint で出ない LLM 限定観点):
- V01 海外背景 (s2/s4/s6/s8/s10) ← Vision Read 必須
- P01/P02/P03 super_businessman ペルソナ不一致 ← 意味論判断
- V04 scrim 弱い (s5/s9) ← Vision 視認性判定

→ lint 単独だと **6 件相当の重要 blocker / warning を取りこぼす**。特に
V01 (海外素材) と P02 (illust 意味論ミスマッチ) は本番納品で致命。

**結論**: reviewer は **Vision LLM 観点 (V01/V04/P01/P02/P03) の検出に必須**。
mechanical 観点 (字数 / overlap / 解像度) は lint で取れるので二重判定にしな
い責務分離が正しい (公式記事「verifier は generator と同じ盲点を共有しない
よう別軸の criteria が必要」)。

## Ablation C — loop 抜き

`/shortvideo-loop` を使わず 1-shot 生成 (planner → generator → reviewer は
走るが、reviewer の patches.json を input.json に merge して再生成するルー
プが無い) ケース。

**観察**:
- sample-test と sample-02-60s は両方とも 1-shot で blocker 残存状態 → loop
  なら最大 3 round の patch merge で blocker 数を減らせる想定
- ただし「patches を当てれば本当に blocker が消えるか」は未実走 (loop が
  Skill tool 経由 reviewer 起動を block する仕様だった件は commit 81bca9b で
  Agent tool 切替済み、loop 機能自体は動く想定)

**数値化** (推論):
- 1-shot: blocker=3-4 (sample-test / sample-02-60s で実測)
- loop 3 round: 推定 blocker=0-2 (patches が当たれば V07/V08 は query 入れ替
  えで消える、V01 と P02 は素材差し替えで消える)

**結論**: loop は **patches.json が機械適用可能なケースで blocker 削減効果
大**。ただし素材調達が外部依存 (Pexels / irasutoya WebFetch) なので、loop
の patches を当てても素材取得失敗すれば blocker 残存する。

## まとめ — どのコンポーネントを抜けるか

| コンポーネント | 必須範囲 | 抜けるケース |
|---|---|---|
| planner | 4 seg 超の長尺 | 1-3 seg の短尺は手書き OK |
| lint | 全動画 | 抜けない (mechanical gate は最も安価で確実) |
| reviewer | 全動画 | 抜けない (Vision 必須観点を lint で取れない) |
| loop | blocker > 0 の動画 | blocker=0 で 1-shot 通過時は不要 |

**将来モデル進化で不要化を再評価する観点**:
- planner: モデルが「素材調達制約を理解して自動分散」できれば不要化
- lint: 機械的観点は変わらないので長期的に必須
- reviewer: モデルの Vision 能力が向上しても、独立判定の責務分離は維持
- loop: モデルが 1-shot で blocker=0 を出せるようになれば不要化

## ベースライン保存 (次回再測定の比較対象)

| 指標 | 値 | 出典 |
|---|---|---|
| sample-test blocker | 3 | examples/sample-test/review_report.md |
| sample-02-60s blocker | 4 | examples/sample-02-60s/review_report.md |
| sample-02-60s lint errors | 4 | local 実走 (commit 9ae1b8f 時点) |
| sample-02-60s lint warns | 13 | 同上 |
| CI run time | 37s | GitHub Actions run 26195124553 |

次回 stress test (例: Phase 4 で planner/reviewer モデル変更時) は、これらの
数値と比較して回帰 / 改善を測定する。
