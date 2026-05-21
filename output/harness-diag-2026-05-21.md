# Harness Diagnosis: shortvideo-skill

> 評価基準: [diagnosis-rubric](../../../claude-workspace/.claude/skills/review-harness/diagnosis-rubric.md)
> 診断日: 2026-05-21

## ハーネス構成サマリ

| 項目 | 現状 |
|------|------|
| CLAUDE.md | 未配置（README.md 120行が実質の入口、frontmatter なし） |
| Permissions | allow 0件 / deny 28件 (Edit×16, Bash×8, Write×1, ask×4) |
| Hooks | PostToolUse 1件（py_compile + lint_recipe.py auto-trigger）/ 他 0件 |
| Skills | 計3件（planner / generator / reviewer すべて `disable-model-invocation: true` のワークフロー型。手動 + `/shortvideo-loop` から駆動） |
| MCP | 未使用（CLI = ffmpeg / ffprobe / python3 で完結） |
| Memory | 未使用（プロジェクト単位の永続化は examples/ + projects/history/ + HUMAN_REVIEW.md に外部化） |
| Agents | カスタム1件（shortvideo-reviewer.md、`context: fork` 用） |
| Plugins | 未使用 |
| CI | GitHub Actions: lint, import-smoke, frontmatter validate, font check, install.sh syntax, output.mp4 playable, **trust-boundary sha256 監視**, **決定論 flag 監視** |
| Evals | 3件（replay / overseas-bg rejection / PR-tone rejection） |

## スコアサマリ

| カテゴリ | 指標 | スコア | 小計 |
|---------|------|--------|------|
| **A. 帯域効率** | A1 ✅ A2 — A3 ✅ A4 ✅ A5 ✅ | 8/8 | 100% |
| **B. 検証の堅牢性** | B1 ✅ B2 ✅ B3 ✅ B4 ✅ B5 ✅ | 10/10 | 100% |
| **C. 権限と信頼境界** | C1 ✅ C2 ✅ C3 ✅ C4 ✅ C5 — | 8/8 | 100% |
| **D. 知識と記憶** | D1 ✅ D2 ✅ D3 — D4 ✅ D5 ✅ | 8/8 | 100% |
| **E. 環境設計** | E1 ✅ E2 ✅ E3 ✅ E4 ✅ E5 ✅ | 10/10 | 100% |
| **総合** | | 44/44 | **100%** |

> 「—」（対象外）は分母から除外。A2 は MCP 未使用、C5 は外部 MCP 入力なし、D3 は Memory 機能未使用のため対象外。

### グレード

**S（90%+）** — ハーネス設計が成熟。微調整のフェーズ。

## 強み

3つだけ抜粋する。これは「強み」というよりこのハーネスの設計哲学そのもの。

### 1. 評価基準（ものさし）を二重に守っている（C1 + C3）

`.claude/settings.json` の deny に、評価そのものを担う7ファイル（lint_recipe.py / ffprobe_quality.py / render_video.py / make_captions.py / segment_hash.py / fetch_pexels_id.py / fetch_irasutoya_id.py）と、レビュアー仕様一式（agents/**, skills/**/SKILL.md, references/**, commands/**）が並んでいる。

さらに `.github/workflows/scripts/check_sha256.py` が trust-boundary ファイルの SHA256 を CI で監視している（baseline-sha256.txt との照合）。手元で deny を回避できたとしても、PR が CI で落ちる二重 gate。`settings.json` 自身も deny に入っているので、エージェントが自分のルールを書き換える経路も塞がれている。settings.json 冒頭の `_comment` に「evaluators must be protected from the evaluated」と原則を明示しているのが意図の証拠。

### 2. 生成と評価の物理分離が runtime まで verify されている（E3）

`shortvideo-reviewer` skill は `context: fork` + `agent: shortvideo-reviewer` で別コンテキスト起動。さらに README と `/shortvideo-loop` の中に「Phase 4.D.0.b で project-level `.claude/agents/` 配置が必須と実証済み」「Personal-scope symlink だけでは Agent type not found になる」と runtime 検証の経緯が記録されている。

それでも fork が成立しなくなった時のために `general-purpose` agent fallback が用意され、「E3 strict purity を失う」と明示してユーザーに警告を出す設計。**「分離してます」と宣言するだけで終わらせず、runtime で確認し、壊れた時の劣化パスまで設計してある**のが S 級の証拠。

### 3. 「AI 評価で完了」を構造的に拒否する Human gate（B2 / E5 / C-3 迎合性対策）

26点ルーブリックの上に H01 (`HUMAN_REVIEW.md verdict=pass` 必須) を blocker として置いている。reviewer が blocker=0 を出しても H01 が pass になるまで `/shortvideo-loop` は完了宣言できない。`fail` 判定はユーザーの理由文がそのまま新 round の patches.json になり、`max 3 rounds` のループに再投入される（人間判定も無限ループしない bound autonomy）。

reviewer も生成者と同じ Claude モデルで盲点を共有することを agent-essence V-2 / C-3 として明示し、その構造的対処として人間 gate を入れた経緯を `agents/shortvideo-reviewer.md` H01 行と `/shortvideo-loop` の Human review gate セクションに二重記載している。

## 検出されたアンチパターン

なし。❌と⚠️は 0 件。

すべての対象指標が ✅ で着地している。指摘するなら「強化余地」だが、それは「アンチパターン」ではない（後述）。

## 次のステップ — 中期的な改善

S 級ハーネスに対する diff なので「直すべき問題」ではなく「次の余白」。

### 1. CLAUDE.md を1枚だけ置く（任意、A1/D5 補強）

現状 README.md が入口を兼ねているが、Claude Code がセッション起動時に自動 import するのは CLAUDE.md。README は GitHub 読者向け、CLAUDE.md は AI 向けに分離すると、Claude が「Launch from repo root」「Human gate を絶対飛ばすな」「max 3 rounds」を起動直後に把握できる。10〜20行の薄いもので十分。

```markdown
# CLAUDE.md（案、20行以内）

## このリポジトリは何か
shortvideo-skill — empathy-first 縦動画生成スキル（planner → generator → reviewer の3段＋orchestrator）

## 起動時の必須事項
- このディレクトリから `claude` 起動（`.claude/agents/shortvideo-reviewer.md` の discoverability に必要）
- `/shortvideo-loop <project-name>` が唯一のエントリポイント、Round 0 を必ず通す

## 信頼境界
- `.claude/settings.json` の deny は触らない（評価基準とパイプラインの保護）
- `examples/sample-03-60s-pass/` は frozen baseline、編集しない

## Human gate（絶対）
reviewer blocker=0 でも `HUMAN_REVIEW.md verdict=pass` まで完了宣言しない。
詳細: `.claude/commands/shortvideo-loop.md` → Human review gate
```

### 2. 決定論の md5 ベースライン化（B4 一段強化）

`check_determinism_flags.py` は flag が緩んでいないかをソース静的解析で検出している。さらに一歩進めて、frozen asset を `examples/sample-03-60s-pass/work/cache/` に commit して `output.mp4 md5` を baseline 化できれば、render パイプライン全体の決定論を CI で機械保証できる。素材ファイルサイズの commit コストとのトレードオフ判断。

### 3. Learning loop の昇格痕跡を CI でも assert（B5 / E4 補強）

`references/learning-loop.md` に「T06 / V07 / V08 が観察→昇格された」と記録があるが、「rubric / lint / examples の3点セット」が揃っているかを CI で機械確認すると、次の昇格時に片肺になりにくい。

## Quick Wins — 今日できる改善

S 級では Quick Wins が真に「なくてもいい」レベル。あえて挙げるなら **1番の CLAUDE.md** だけ（5〜10分）。それ以外は現状で十分機能している。

## 総評

このハーネスは Claude Code のエージェント設計で参照される基準作と言っていい完成度。**指標 25 中、適用可能 22 がすべて ✅、対象外 3 を除いて満点**。診断ルーブリックは「アンチパターンの不在」だけでなく「対処の構造化」を問う設計だが、その全項目で構造化を確認できた。特に Phase 4.D.0.b（agent discoverability の runtime 検証）と Phase 4.F（Human gate 追加）の経緯が README / settings.json / SKILL.md / agents / commands の **5箇所に分散して残っている**ことが、ハーネス設計が単発の判断ではなく学習プロセスとして回っていることを示している。

検出限界の明記: この診断は静的解析が主で、(a) 実際に `/shortvideo-loop` を回したときの reviewer の指摘精度、(b) Human gate が長期運用で本当に守られているか、(c) patches.json の収束性、までは確認していない。`evaluations/*.json` の 3 シナリオを定期実行する E2E 検証は次の余白として残る。

S 級。微調整フェーズ。
