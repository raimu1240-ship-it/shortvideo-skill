# shortvideo-skill

## 何ができるツール?

1 行のテーマから、共感型の縦動画 (720x1280 または 1080x1920) を 5〜10 分で自動生成する Claude Code 用ツール。Mac / Windows 両方で動く。

**例**:
- 入力: 「派遣で働いていた頃の気付き、30 代会社員向け」
- 出力: 60 秒の縦動画 (mp4)、日本ロケ背景 + いらすとや + 字幕 + ナレーション付き

## 得意なこと / 苦手なこと

### 得意

- **動画化** — 背景動画調達 (Pexels / Mixkit) / いらすとや差し込み / 字幕作成 / ナレーション生成 / レンダリングまで一気通貫
- **海外背景・PR 色 (薬機法/景表法違反) の自動検出と除外**
- **同じ素材の重複検出**、人間レビュー gate 必須

### 苦手 (= AI 任せでは限界)

- **本格的な台本作成** — このツールの planner は「ざっくり台本のたたき台」を出すだけ。バズる構成・心理導線・競合分析を反映した本格台本がほしい場合は、**自分でアカウント設計・伸びている投稿・競合分析の情報を planner に渡す必要がある**。デフォルトでは過去の蓄積を反映できないので、台本のクオリティは「叩き台レベル」。
- **横動画 / BGM 入り / PR バッジ等の「広告フォーマット」用途** — 共感型縦動画に特化、広告系は別スキル想定

要するに **「動画を組み立てる部分は強い、台本の中身そのものは別途整える前提」** のツールです。

## 5 分で動かす (Mac / Linux)

```bash
git clone https://github.com/raimu1240-ship-it/shortvideo-skill.git ~/code/shortvideo-skill
cd ~/code/shortvideo-skill
./install.sh
claude
# Claude Code のセッションが開いたら、続けてセッション内で:
#   /shortvideo-loop my-first-video
```

`my-first-video` は好きなプロジェクト名 (英数字とハイフン)。動画は `projects/my-first-video/output.mp4` に出力されます。

## 5 分で動かす (Windows)

**事前準備**: symlink 作成のため以下のどちらかが必要です:

- **方法 A (推奨)**: 「開発者モード」を ON にする — 設定 → プライバシーとセキュリティ → 開発者向け → 開発者モード ON
- **方法 B**: PowerShell を**管理者として実行**

その上で:

```powershell
git clone https://github.com/raimu1240-ship-it/shortvideo-skill.git $env:USERPROFILE\code\shortvideo-skill
cd $env:USERPROFILE\code\shortvideo-skill
.\install.ps1
claude
# Claude Code のセッションが開いたら、続けてセッション内で:
#   /shortvideo-loop my-first-video
```

cmd.exe を使う場合は `install.bat` をダブルクリック (中で PowerShell の install.ps1 が走る)。

`install.ps1` は symlink 作成を試み、失敗した場合は自動でファイルコピーに切り替えます (コピー運用時は `git pull` 後に再度 `install.ps1` を実行)。

## 必要環境

- **OS**: macOS 14+ または Windows 10+
- **ffmpeg / ffprobe**
  - Mac: `brew install ffmpeg`
  - Win: `winget install Gyan.FFmpeg`
- **Python 3.9+** + `Pillow`: `pip install Pillow`
- **日本語フォント**: リポ同梱の `NotoSansCJKjp-Regular.otf` を優先使用 (追加インストール不要)
- **(任意) ElevenLabs API キー**: 高品質ナレーション用。未設定なら OS 内蔵 TTS にフォールバック
  - Mac: `say -v Otoya`
  - Win: PowerShell の `System.Speech.Synthesizer`

`install.sh` / `install.ps1` は最後に依存チェックを実行し、不足があればインストールコマンドを表示します。

## 使い方の流れ

`/shortvideo-loop <プロジェクト名>` を打つと、3 つのエージェントがチーム制で動きます:

| エージェント | 色 | 役割 |
|---|---|---|
| shortvideo-planner | 🟢 緑 | お題から台本 (input.json) を作る |
| shortvideo-generator | 🔵 青 | 台本から動画 (output.mp4) を生成 |
| shortvideo-reviewer | 🟣 紫 | 27 観点でチェックして修正 patch を出す |

最大 3 ラウンドで自動修正したあと、最後に**人間レビュー gate** が開きます (output.mp4 を動画プレイヤーで開いて、ユーザーが pass / fail を判定)。

個別に動かしたい場合は `/shortvideo-planner` や `/shortvideo-generator` を直接呼ぶこともできます。

### claude はどのディレクトリで起動しても OK

`install.sh` / `install.ps1` が `~/.claude/` 配下に symlink を貼るので、Claude Code はどのディレクトリで起動してもこの 3 エージェントを認識します。普段使っている作業ディレクトリで claude を起動してそのまま `/shortvideo-loop <名前>` を打ち込んでください。

**生成物は `claude を起動した cwd 配下の `projects/<名前>/`** に作られます。例えば `~/Documents/work/` で claude を起動 → `/shortvideo-loop test` → `~/Documents/work/projects/test/output.mp4` に動画が出ます。

## 背景動画ソース

デフォルトは Pexels。0 件 hit / 海外混入が多い時は Mixkit にフォールバック:

| ソース | URL |
|---|---|
| Pexels | https://www.pexels.com/ja-jp/search/videos/japan/ |
| Mixkit | https://mixkit.co/free-stock-video/japan/ |

詳細は `.claude/skills/shortvideo-generator/references/stock-sources.md`。

## トラブル時の対処

### `Agent type 'shortvideo-planner' not found` が出る

`~/.claude/agents/` に shortvideo-* の symlink が無い状態。install.sh を再実行してください:

```bash
cd ~/code/shortvideo-skill && ./install.sh   # Mac/Linux
# または: cd $env:USERPROFILE\code\shortvideo-skill && .\install.ps1   # Windows
```

その後 **Claude Code を一旦終了 (Ctrl+C) → `claude` で再起動**。Claude Code は起動時にエージェント一覧を読み込むため、install 直後の現セッションでは新エージェントが見えません。

### `Skill ... cannot be used with Skill tool due to disable-model-invocation` が出る

subagent が見つからず Skill tool にフォールバックして拒否された状態。原因は上と同じ (install.sh 未実行 or symlink 損失)。`./install.sh` 再実行 → claude 再起動で解消。

### agent symlink が無い

```bash
ls -la ~/.claude/agents/shortvideo-*
```

3 ファイル (planner / generator / reviewer) が出なければ install.sh の再実行が必要です:

```bash
cd ~/code/shortvideo-skill && ./install.sh
```

### 動画は出たが海外背景が混入する

reviewer が blocker を出して 3 ラウンドまで自動修正します。それでも残った場合は、**Claude Code に日本語で指示するだけ**で AI が `input.json` を直して再走させます:

> 「s3 の bg が海外っぽいので、日本の駅ホームに変えて」
> 「全体的に海外混入してるので、bg_query を全部見直して」

自分で `input.json` を直接編集する必要はありません。

### 台本がいまいち

このツールの planner はざっくり叩き台しか出しません。本格的にしたい場合は:

1. `/shortvideo-planner <name>` で叩き台を作る
2. 出来上がりを Claude Code に日本語で指示して修正:
   > 「s2 のキャッチコピーを『気付いたら変わってた』に変えて」
   > 「全体的にもっと共感寄りに、断定口調を減らして」
   > 「(別途用意した) アカウント設計と競合分析を貼るので、それを反映して台本書き直して」
3. `/shortvideo-loop <name>` で動画化

**「アカウント設計 / 競合分析 / 伸びている投稿の構成パターン」等は会話に貼り付ければ planner に反映されます**。お題だけ投げるよりはるかに精度が上がります。

## ライセンス

MIT。`LICENSE` 参照。
