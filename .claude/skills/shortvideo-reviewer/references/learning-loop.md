# Learning Loop — 新指摘パターンを 26 観点に昇格するプロセス

Reviewer が動画を見て「これは現行 rubric に該当しないが視聴者には致命的」と
判断した観察事項を、再現可能な観点として rubric に組み込むための手順。

観察を観点化することで、reviewer の盲点を継続的に縮めるためのフロー。

## 何を昇格対象とするか

以下のいずれかに該当する観察を昇格候補とする:

1. **再現性**: 同じ root cause が 2 件以上の sample で検出できる
2. **致命性**: 視聴者の理解 / 信頼を直接損なう (PR 色・誤情報・薬機法等)
3. **機械化可能性**: lint または ffprobe または vision read で再現検出できる
4. **既存観点に該当しない**: V01-V08 / T01-T06 / A01-A04 / P01-P03 / L01-L03
   / Q01-Q05 の 26 観点のどれにも収まらない新カテゴリ

3 件全部満たさなくても (1) + (4) があれば次の sample 出現で再判定する。

## 昇格プロセス (5 ステップ)

### Step 1 — 観察を生記録

reviewer subagent が出力する `review_report.md` の `## Info` セクションに
「**観察事項 (新カテゴリ候補)**」として記録。形式:

```markdown
### [obs-N] 短い名前 (segment, timestamp)
- 観測: 何が映っていたか / 何が問題か
- 想定 root cause: なぜ起きたか
- 現行 rubric では検出できない理由: V01 ではないが似てる、等
- 機械化案: lint / ffprobe / vision のどれで取れそうか
```

### Step 2 — 2 件目以降を待つ

1 件だけの観察は「単発の特殊事例」かもしれない。最低 2 件、できれば 3 件の
別 sample で同じ root cause を観測できたら昇格候補にする。

(早期に観点化すると「ハンコ押し」化のリスクがある = 大量の観点が並んで
reviewer がほぼ全部「pass」を返す状態に陥る。観点数が増えると一つ一つの
判定が雑になりやすいので、十分な再現性を確認してから昇格させる。)

### Step 3 — 観点 ID と分類を決める

V/T/A/P/L/Q のどのカテゴリに入るか + 既存最大 ID + 1 で採番。例:
- 視覚系新観点 → V09
- 音声系 → A05
- 法規系 → L04

カテゴリが既存 6 種類のどれにも入らないなら、新カテゴリ文字を作る (S =
Sound effects / I = Interactive 等)。最近 2 年でカテゴリ追加実績あり (T06 で
Text を 5 → 6 件に拡張、V07/V08 で Visual を 6 → 8 件に拡張)。

### Step 4 — rubric + lint への組み込み

3 ファイルを更新:

1. `agents/shortvideo-reviewer.md` — rubric 表に新観点 1 行追加 (ID / 判定基準
   / blocker or warning)
2. `scripts/lint_recipe.py` — 機械化可能なら 1 関数追加 (閾値定数 + check 本体)
3. `.claude/skills/shortvideo-planner/SKILL.md` (or `references/`) — 該当する
   予防ルールがあれば追記 (例: V07/V08 → planner の「query 分散」ハードルール)

### Step 5 — calibration material を 1 件追加

`examples/sample-<N>/` を 1 件作って、新観点が **発火するサンプル** と
**しないサンプル** をペアで残す:

- 発火例: input.json に違反パターンを意図的に埋め込み → reviewer が新観点で
  blocker / warning を返すことを確認 → review_report.md に該当行を残す
- pass 例: 既存の sample-01-10s / sample-02-60s で該当しないことを確認 (重複
  検出だけなら新 sample 不要、ペアは既存利用 OK)

### Step 6 — CI への組み込み (optional)

`.github/workflows/test.yml` の `check_lint.py` 経路で新観点が JSON 出力に
正しく現れるか自動 assert (現状の CI は「lint が JSON 出力 shape を保つ」だけ
を assert、観点別の出現有無まではチェックしていない)。重要観点なら個別 assert
を追加してもよい。

## 過去の昇格事例

| 観点 | 発見契機 | 昇格 commit | 機械化 |
|---|---|---|---|
| T06 voice-caption sync | sample-test で voice 6.89s vs caption 同時表示でズレ観測 | 98f9501 | lint Jaccard |
| V07 bg_query 重複 | sample-02-60s で同じ bg 5/10 = 50% 占有を観測 | 1a70450 | lint Counter |
| V08 illust_query 重複 | sample-02-60s で super_businessman 6/10 = 60% を観測 | 1a70450 | lint Counter |

これらは「単発の sample で気付き → 別 sample でも同じ問題が再現することを
確認 → rubric + lint に昇格」の流れで導入された。

## 昇格しない判断

すべての観察を観点にすると rubric が肥大化して reviewer の判断が散漫になる。
以下は「観察に留めて rubric には入れない」判断の例:

- **1 件だけの特殊事例** — 同じ案件特有の問題で、横展開する見込みがない
- **既存観点で吸収可能** — V04 (scrim 弱い) は新観点ではなく「V04 を多 segment
  にまたがる累積問題」として扱うほうが筋
- **撮影 / 編集の主観領域** — 「テンポ感が悪い」「明るさが暗い」のような
  数値化困難で個人差が大きい観察は、reviewer の自由記述に留める

判断に迷ったら、observation を `## Info` に残したまま、3 件目の出現を待つ。

## 関連

- `.claude/agents/shortvideo-reviewer.md` — 26 観点 rubric 本体
- `scripts/lint_recipe.py` — mechanical check 実装
- `.claude/skills/shortvideo-planner/SKILL.md` — 予防ルール
- `references/traps-9.md` — 罠 9 件 + 自動回避コード (lint 実装と対応)
