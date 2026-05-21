---
name: shortvideo-loop
description: Orchestrates the full plan→generate→review→fix loop for a shortvideo project. Drives shortvideo-planner, shortvideo-generator, and shortvideo-reviewer in sequence, merges JSON patches automatically, and retries until blocker=0 or 3 rounds reached. Use to fully automate one video end-to-end.
allowed-tools: Read, Write, Edit, Bash(python3 *), Bash(ffmpeg *), Bash(ffprobe *), Bash(mkdir *), WebFetch, Skill
argument-hint: [project-name]
---

# shortvideo-loop

End-to-end orchestrator for a single project. The user gives a project name; this command takes care of everything until `output.mp4` passes the reviewer or escalates after 3 failed rounds.

## 自動修正の上限

- 最大ループ数: **3**。3 ラウンド回しても blocker > 0 なら、残った blocker を提示してユーザーにエスカレーション。黙って延々と回し続けない
- 各ラウンドのレビュー結果は `projects/<name>/history/round_<N>/review_report.md` に保存される (後から見返せる)
- ユーザーは途中でいつでも中断 OK、再実行で前ラウンドから続行できる

## Steps

Copy this progress checklist into your reply:

```
shortvideo-loop progress (project=<name>)
- [ ] Round 0: planner → input.json
- [ ] Round 1: generate → review → (blocker check)
- [ ] Round 2 (if needed): apply patches → generate → review
- [ ] Round 3 (if needed): apply patches → generate → review
- [ ] Final: report status
```

### Round 0 — Plan (緑色 subagent: shortvideo-planner)

`projects/<name>/input.json` が無ければ:
- **Agent tool** で `subagent_type="shortvideo-planner"` を起動
  (transcript 上で緑色のラベルで表示される)
- 完成した input.json をユーザーに見せて確認 → OK が出てから次へ

既に input.json があれば、このラウンドはスキップして
「既存の input.json を使います。修正したい場合は /shortvideo-planner を手動で呼んでください」と伝える。

#### `Agent type 'shortvideo-planner' not found` が返った場合

これは Claude Code が **リポジトリ外の cwd で起動された**証拠 (project-level
`.claude/agents/` が見えていない)。

- **Skill tool で代替起動を試みない**。`/shortvideo-planner` skill は
  `disable-model-invocation: true` で programmatic 呼び出しを拒否するため、
  Skill tool 経由は確実に失敗する
- 代わりに以下のメッセージをユーザーに返して **stop**:

  ```
  ⚠ shortvideo-planner subagent が見つかりません。
    Claude Code がリポジトリ外で起動された可能性があります。

    対処:
      1. Ctrl+C で claude を終了
      2. cd ~/code/shortvideo-skill   (Mac/Linux)
         cd $env:USERPROFILE\code\shortvideo-skill   (Windows)
      3. claude
      4. /shortvideo-loop <name>

    それでも出る場合は install.sh を再実行してください:
      cd ~/code/shortvideo-skill && ./install.sh
  ```

- 上記メッセージを返したらループは中断する (勝手にフォールバック起動しない)

### Round N — Generate + Review (N = 1, 2, 3)

1. **Agent tool** で `subagent_type="shortvideo-generator"` を起動
   (transcript 上で青色のラベルで表示される) → 7 段階パイプライン実行
2. **Agent tool** で `subagent_type="shortvideo-reviewer"` を起動
   (transcript 上で紫色のラベルで表示される)
   - Skill ツールは使わない — `shortvideo-reviewer` skill は
     `disable-model-invocation: true` で programmatic な呼び出しを意図的に
     拒否している (生成者と評価者を別 context で物理的に分離するため)
   - 同様に generator も Agent tool 経由で起動する。planner / generator /
     reviewer の 3 つを subagent として呼ぶことで、TaskList / transcript で
     緑 / 青 / 紫の色分けでどのエージェントが動いているか視覚的に分かる
   - **推奨**: `subagent_type="shortvideo-reviewer"`。これは
     `.claude/agents/shortvideo-reviewer.md` がランタイムから見える状態が必要、
     具体的には **`claude` がこのリポジトリのディレクトリで起動されていること**
     (Claude Code は project-level `.claude/agents/` を cwd から読む)。
     実機検証で確認済み: `~/.claude/agents/shortvideo-reviewer.md` の
     Personal-scope symlink だけでは、cwd が別ディレクトリの時に reviewer
     を見つけられない
   - **`Agent type ... not found` が返った場合** (generator / reviewer どちらも同じ):
     これは Claude Code がリポジトリ外の cwd で起動された証拠。
     **Skill tool で代替起動を試みない** (skill は `disable-model-invocation: true` で拒否される)。
     代わりに Round 0 の「Agent not found」セクションと同じメッセージを返して **stop**。
     general-purpose subagent へのフォールバックは行わない (独立 context が崩れて
     判定が信頼できなくなるため)
3. Read `projects/<name>/review_report.md` (the reviewer's summary)
4. Copy the report to `projects/<name>/history/round_<N>/review_report.md`

### Patch decision

- **blocker == 0** AND warning ≤ 3: 次の **人間レビュー gate** へ。人間 gate を通るまで「完了」と言わない。
- **blocker == 0** AND warning > 3: ask the user "warning が N 件残っています。このまま採用するか、patch を当てて再ループしますか？" — wait for explicit answer.
- **blocker > 0** AND round < 3: apply patches from `projects/<name>/patches.json` to `input.json`, then loop to next round.
- **blocker > 0** AND round == 3: escalate.

### 人間レビュー gate (省略不可、最後の必須ステップ)

reviewer subagent も結局は Claude の model なので、generator と同じ盲点
を共有する (字幕のトーンが微妙にズレている、illust と voice の温度感が
合ってない、ナレーションのテンポが死んでいる、等)。人間が見れば一発で
気付くことを AI が見落として「pass」を返す現象を防ぐため、最終 gate を
人間に持たせる。**この gate を通過するまで「完了」を宣言しない。**

1. Open the output for human viewing:
   ```bash
   open projects/<name>/output.mp4
   ```
2. Present the user with a 3-line summary:
   - `output.mp4 を再生しました (duration=Ns)`
   - `Reviewer 評価: blocker=0 / warning=N`
   - `視聴して pass か fail を判定してください。fail の場合は理由 1-3 行で。`
3. Wait for explicit `pass` / `fail` reply (no auto-pass on silence).
4. Record the verdict to `projects/<name>/HUMAN_REVIEW.md`:
   ```markdown
   verdict: pass | fail
   reviewer: <your name or handle>
   timestamp: <ISO>
   notes: <user's fail reason or "OK">
   ```
5. `fail` の場合、**ユーザーの notes を patches.json の新しい entry として扱い**、
   reviewer が blocker=0 と言っていても Round N+1 に戻る。人間の判定が
   AI の判定を上書きする。上限 (最大 3 ラウンド) は引き続き適用 —
   人間レビューで 3 ラウンド全部 fail ならエスカレーション
6. `verdict: pass` が出てはじめて完了報告できる

### Applying patches

For each patch object in `patches.json`:

| patch_type | action |
|---|---|
| `replace_bg` | Set `scenario.segments[<segment>].bg_query = <new_query>`. Also clear `contact_sheet_passed` so Stage 3 re-runs. |
| `replace_illust` | Set `scenario.segments[<segment>].illust_query = <new_query>`. Delete cached `work/assets/illust_<sid>.png`. |
| `rewrite_caption` | Set `scenario.segments[<segment>].caption_main = <new_caption>`. |
| `adjust_sub_delay` | Set `scenario.segments[<segment>].sub_delay = <new_delay>`. |
| `trim_trailing_silence` | Set top-level `trim_trailing_silence_sec = <seconds>`. The generator's Stage 6 trims accordingly. |
| `set_field` | Set the field at `path` (dot notation) to `value`. |

Unknown patch types: leave a warning in the user message; do not modify input.json.

After applying patches, write the updated input.json. Then recompute segment hashes:

```bash
python3 scripts/segment_hash.py projects/<name>/input.json \
  --diff projects/<name>/history/round_<N-1>/segment_hashes.json \
  > projects/<name>/history/round_<N>/segment_hash_diff.json
```

The diff lists `changed` / `unchanged` / `removed` segment ids. For each segment in `unchanged`, skip Stage 1/2/4 (fetch + tts) and reuse `work/cache/<segment_hash>/` artifacts. For `changed` segments, re-run all stages. For `removed`, garbage-collect `work/cache/<hash>/` to free disk.

Save the new hashes to `projects/<name>/history/round_<N>/segment_hashes.json` for the next diff.

### Escalation (round 3 with blocker > 0)

Tell the user:

```
3 round してもblocker N 件残っています:
- <blocker 1 のサマリ>
- <blocker 2 のサマリ>
...
projects/<name>/history/ に各ラウンドのレポートを保存。次の判断:
  a. 残りの blocker を手で直す
  b. acceptance_criteria を緩める (e.g. duration_tolerance_sec を上げる)
  c. このプロジェクトをスキップ
```

Wait for the user's choice. Do not proceed.

## 収束しないループの検出

- 同じ patch_type が同じ segment に 2 ラウンド連続で当てられて blocker
  が解消しない場合、warning を出してループを早期停止する (generator が
  フィードバックに対応できていない兆候)
- ラウンド間で reviewer の blocker 数が *増加* した場合、即停止して
  ユーザーに確認 — パッチが状況を悪化させている
