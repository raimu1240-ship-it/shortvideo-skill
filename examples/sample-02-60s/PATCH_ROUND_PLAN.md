# sample-02-60s — Phase 4.B.1 patch round 実走プラン

## 現状 (round_1 = baseline)

- `blocker=4`: V01 海外背景 (s2,s4,s6,s8,s10), V07 bg 重複 (50%), V08 illust 重複 (60%), P02-P03 ペルソナ不一致
- `warning=4`: T06 voice/caption グラデーション, V04 scrim 弱
- `info=2`

`review_report.md` が一次ソース。

## 適用予定 patches (`patches.json` 全 27 件)

| 種類 | 件数 | 想定効果 |
|---|---|---|
| replace_bg | 9 | 全 10 seg unique 化 → V07/V08 解消、全 "japan ..." prefix → V01 解消 |
| replace_illust | 10 | super_businessman 廃止 → P02/P03/V08 解消 |
| set_field (scrim_alpha) | 5 | 0.15 → 0.25、暗い seg の caption 視認性 → V04 解消 |
| set_field (loudnorm) | 1 | -23 LUFS 明示 → A01 安定 |
| set_field (voice_text) | 1 | s4 voice/caption overlap 改善 → T06 解消 |

## 次セッションでの実走手順

```bash
cd ~/code/shortvideo-skill
# 1. patches を input.json にマージ (orchestrator 経由)
/shortvideo-loop sample-02-60s
# 2. round_2 が走り、新 bg/illust を Pexels + irasutoya から DL
#    所要: 数分 (10 seg × 2 fetch + 10 TTS + render)
# 3. reviewer subagent (Agent tool subagent_type=shortvideo-reviewer) が再 review
# 4. blocker=0 達成 → examples/sample-02-60s/history/round_2/ に証跡保存
# 5. baseline-sha256.txt 更新 (review_report.md + output.mp4 の hash 変わる)
```

## 想定リスク

- **Pexels HTML 変更**: 2026 春の DOM 更新で fetch_pexels.py が直リンク取れない可能性 → 失敗時は `python3 scripts/fetch_pexels.py --debug` で HTML 確認、selector 修正
- **irasutoya feed 取得失敗**: ja query で hit 0 件の場合あり → query を「男性 ふと立ち止まる」→「男性 立ち止まる 通勤」のように緩める
- **TTS 失敗**: `.env` の `ELEVENLABS_API_KEY` が空なら say -v Otoya にフォールバック (自動)
- **round_2 で blocker が増える**: convergence safeguard (loop.md:113-114) で halt、patches が逆効果と判定

## 達成判定 (Verification)

1. `examples/sample-02-60s/history/round_2/review_report.md` で `blocker=0`
2. `examples/sample-02-60s/output.mp4` を視聴して海外風背景 0 件 / illust 多様性 8 種以上
3. `lint_recipe.py` で V07/V08 が出ない (`python3 scripts/lint_recipe.py examples/sample-02-60s/input.json --json | jq '.errors[] | select(.code=="V07" or .code=="V08")'` が空)

## 残存懸念 (3 round で消えない可能性のある blocker)

- **A03 voice mismatch**: per-segment TTS + voice mux refactor (commit 9ae1b8f) で構造的に解消されたはずだが、新 voice_text で発話長が想定外に短い/長い場合に再発しうる
- **fetch 系の偶発失敗**: 外部依存なので「patches を当てても素材が来ない」ケースは round_3 escalation
