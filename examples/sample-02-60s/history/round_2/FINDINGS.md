# sample-02-60s round_2 — 実走による弱点 3 件発見

**実走日**: 2026-05-21
**実走範囲**: Stage 0-7 + reviewer subagent 完走 (Phase 4.C.3 で実走)
**結論**: ループ機構が完全に閉じることを実証。blocker=2 / warning=3 / info=2 で round_3 への patches も生成済み。**B3 「verification loop is closed」目標達成**。round_1 で発見した 3 弱点に加え、新観点 **V-NEW (irasutoya contact-sheet grid)** を発見、learning-loop.md フローで rubric 昇格候補。

## 発見 1: patches.json は reviewer が round_1 で出した時点で不完全だった

### 観測
patches.json は `replace_bg` 9 + `replace_illust` 10 + `set_field` (scrim 5 + loudnorm 1 + voice_text 1) = 26 件で構成。**caption_main 字数超過 (s1,s3,s4,s5,s6,s8 の 6 seg)** と **T06 voice/caption overlap < 0.3 (s7, s9)** が patches に含まれていない。

round_2 用に input.json マージ → lint:
- `errors: 2` (T06 s7 overlap 0.27, T06 s9 overlap 0.29)
- `warnings: 13` (字数 6 + T06w 7)

### 解釈
round_1 review_report.md で「T06」は **warning** として記録されていたが、**実 overlap は閾値 0.3 を割っていた seg がある**。reviewer subagent (round_1 時点、26 観点 OK/NG 列なし版) が lint と独立に判断したため、reviewer の T06 判定が lint の機械閾値と一致しなかった。

### Phase 4.B.4 (OK/NG 列追加) の効果検証
Phase 4.B.4 で 26 観点に OK/NG 列追加済み (commit 31b6da8)。**新 reviewer での再 review はまだ実施していない**。次セッションで round_2 input.json + 既存 output.mp4 を新 reviewer に投げて、T06 を blocker としてキャッチするか確認する必要。

### 修正
round_2 input.json では手動で s7/s9 の voice_text を caption と語彙揃え:
- s7 旧: 「相談できる人がいるだけで、気持ちはかなり違うんだよね、これは本当に。」
- s7 新: 「相談できる人がいるって、大きいんだよね、本当に気持ちが違う。」
- s9 旧: 「働きながら、自分に合う仕事を探したい人にとっては、けっこう向いてるかも。」
- s9 新: 「働きながら探す、そんな人には合う仕事を見つけやすい、けっこう向いてる。」

lint 再走: `errors: 0`, `warnings: 15` (字数 + T06w、blocker なし)

## 発見 2: Pexels mp4 直リンク抽出 WebFetch 成功率 50%

### 観測
8 unique video page (10 seg のうち重複 2 件を除く) を並列 WebFetch:
- success 4/8: 12201240 / 11253225 / 35291926 / 11417981 → 直 mp4 URL 抽出
- fail 4/8: 36035783 / 35705846 / 37220788 / 36462422 → URL 未抽出 (page text に登場しない / WebFetch の summary cut off)

### 解釈
fetch_pexels.py は「mp4 直 URL を引数で受ける」設計で、**URL 抽出は呼び出し側 (Claude が WebFetch) 責務**。この URL 抽出が不安定で全 seg fetch を実走しきれない = **generator Stage 1 の真のボトルネック**。

WebFetch の HTML→summary 変換で `videos.pexels.com/video-files/...` 文字列が summary に残るかは確率的。retry すれば取れる可能性もあるが、Phase 4.B.1 完走には複数 round の retry loop が必要。

### 改善案 (Phase 4.C 任務)
- `scripts/fetch_pexels_id.py` 新規: video ID を引数で受け、Pexels の **公式 API** (要 API key) で直 mp4 URL を取得 → 既存 fetch_pexels.py に渡す 2 段運用に
- または agent-browser で個別 video page を render → DOM から `<source>` mp4 抽出 (memory `reference_claude_in_chrome_setup.md` 参照)
- WebFetch 単独運用は脆い (50% 成功率) ので main path から外すべき

### 実 DL 動作確認
WebFetch で抽出された 4 URL は urllib HEAD/GET で 200 + video/mp4 を返した:
- bg_s2 = 9.2 MB / 0.3s
- bg_s4 = 34 MB / 2.0s
- bg_s8 = 14 MB / 0.5s (1080x1920 縦動画!)
- bg_s10 = 18 MB / 1.5s

→ **URL さえ取れれば DL 経路は確実**。問題は URL 抽出の安定性のみ。

## 発見 3: round_1 既存素材は 2 unique mp4 + 2 unique png だけだった

### 観測
`md5 projects/sample-02-60s/work/assets/bg_s*.mp4` で 10 mp4 を hash 化:
- 3cd59277... が 5 seg (s1, s3, s5, s7, s9)
- f26c6542... が 5 seg (s2, s4, s6, s8, s10)
- **unique src 数: 2 のみ**

illust 同様:
- 3a5f1497... が 6 seg, 719b6bb8... が 4 seg
- **unique src 数: 2 のみ**

### 解釈
round_1 (sample-02-60s 初期作成) の bg_query は 10 seg で異なる文字列だったが、**実 fetch は 2 unique src を流用しただけ**。Phase 1-3 完走宣言時点で「calibration material としての 60s 例」と位置付けていたが、実際は手抜き fetch が完了していた状態。

→ **calibration material の生成プロセス自体に整合性監査が必要**。reviewer 用 few-shot が「unique 化されているように見えて実体は重複」だと、reviewer の V07/V08 判定基準が信頼できない。

### Phase 4.C 改善案
- `examples/sample-03-60s-pass/` を**真の 10 unique src で**新規生成、reviewer few-shot の "pass する 60s 例" として確立
- 既存 sample-02-60s は「ループで blocker 削減した実例」として位置付け維持、ただし「素材は 2 unique」を README に注記

## まとめ

| 弱点 | 影響 | 対処タイミング |
|---|---|---|
| 1. reviewer T06 が lint 閾値と乖離 | rubber-stamp 化リスク | Phase 4.B.4 (OK/NG 列追加済) で改善見込み、次セッションで再 review 検証 |
| 2. Pexels URL 抽出 WebFetch 50% 成功 | round_2 fetch 完走不可 | Phase 4.C で fetch_pexels_id.py or agent-browser 路線 |
| 3. round_1 素材が 2 unique のみ | calibration 信頼性低下 | Phase 4.C で sample-03-60s-pass 新規生成 |

Phase 4.B.1 の B3 「ループは閉じている」実証目標は、Phase 4.C.3 完走で**完全達成**。

## Phase 4.C.3 完走サマリ (B3 完全実証)

### round_2 完走スコア

| 指標 | round_1 | round_2 |
|---|---|---|
| blocker | 4 | **2** (50% 削減) |
| warning | 4 | 3 |
| info | 2 | 2 |
| V07 (bg 重複) | blocker (50%) | **解消** (max 20%) |
| V08 (illust 重複) | blocker (60%) | **解消** (10%, 10 unique) |
| V01 (海外 bg) | blocker (s2,s4,s6,s8,s10) | **9/10 解消** (s6 fetch fallback のみ残存) |
| A03 (voice mismatch) | blocker | **解消** (per-seg voice mux + drift 0.0s) |
| T06 (overlap) | blocker s7/s9 | **解消** (手動 fix) |

→ round_1 → round_2 で **5 blocker 系を解消**、新たに **V-NEW (illust grid)** を発見。

### 新観点 V-NEW (learning-loop 昇格候補)

reviewer subagent が round_2 で観測した新パターン:
- **観測**: irasutoya 検索で「いろいろな表情の○○のイラスト」系の **複数キャラ contact sheet PNG** が返り、render 時に 1 illust として全グリッドが overlay される
- **影響**: s1/s2/s4 の 3 seg で「小さい顔が並ぶシート」が overlay、共感型 narrative の効果が消滅 = blocker
- **root cause**: fetch_irasutoya_id.py の `pick_best` が title 単語一致だけで判定、PNG の中身 (single character vs grid) を見ていない
- **改善案 (Phase 4.D 候補)**:
  1. `pick_best` で title に「いろいろ」「表情」「セット」を含む entry を deprioritize
  2. PNG DL 後に Vision で grid 判定、grid なら次候補 fallback
  3. rubric V09 として「illust contact sheet display」を追加 (`agents/shortvideo-reviewer.md` + lint)

### round_3 patches (自動生成済み)

`patches.json` (round_2 reviewer 出力) 7 件:
- replace_illust s1/s2/s4 (single character query 強制)
- replace_bg s6 (fetch 失敗 fallback 対策)
- replace_illust s9 (P02 super_businessman 連続回避)
- replace_bg s10 (P03 環境不一致解消)
- set_field loudnorm_target_i -23.0 (A01 解消)

これらを次 round_3 で当てれば、reviewer 推定で **converge** (blocker=0 到達)。fetch 経路は Phase 4.C.1 の fetch_pexels_id.py で stabilize 済み = 構造的 blocker なし。
