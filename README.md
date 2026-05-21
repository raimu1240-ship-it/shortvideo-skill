# shortvideo-skill

短い一行のテーマから、共感型の縦動画 (720x1280 または 1080x1920) を自動生成する Claude Code 用スキルセット。

- 日本ロケのストック動画 (Pexels / Mixkit)
- いらすとや 差し込み
- 2 行字幕
- ナレーション (ElevenLabs API、無ければ OS 内蔵 TTS にフォールバック)

Anthropic 公式の [Agent Skills](https://code.claude.com/docs/en/skills) 仕様で構築。orchestrator が planner → generator → reviewer の順で動かし、最大 3 ラウンドの自動修正後、人間レビュー gate を経て完了する。

## 構成

| パス | 役割 |
|---|---|
| `.claude/skills/shortvideo-planner/` | ユーザーのお題から `input.json` (台本) を作成 |
| `.claude/skills/shortvideo-generator/` | 7 段階パイプライン: lint → fetch → curate → narrate → caption → render → probe |
| `.claude/skills/shortvideo-reviewer/` | 独立した reviewer (別 context で動かす) |
| `.claude/agents/shortvideo-planner.md` | 企画担当 subagent (緑色ラベル) |
| `.claude/agents/shortvideo-generator.md` | 生成担当 subagent (青色ラベル) |
| `.claude/agents/shortvideo-reviewer.md` | レビュー担当 subagent (紫色ラベル)、27 観点 + 人間レビュー gate |
| `.claude/commands/shortvideo-loop.md` | 最大 3 ラウンドの自動修正ループ |
| `scripts/` | Python ユーティリティ 8 種 (lint / fetch / render / probe / captions / tts / 他) |
| `evaluations/` | 動作評価シナリオ 3 種 (再現性 / 海外背景除外 / PR 色除外) |
| `examples/` | 動作確認済みサンプル (`sample-03-60s-pass/` は人間レビュー pass 済みの 60 秒見本) |

## 必要環境

- **OS**: macOS 14+ または Windows 10+
- **ffmpeg / ffprobe**
  - macOS: `brew install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` または公式バイナリを PATH に追加
- **Python 3.9+** + `Pillow`: `pip install Pillow`
- **日本語太字フォント**
  - macOS: Hiragino Sans W7 が標準搭載で OK
  - Windows: Yu Gothic UI Bold 等の OS 標準フォントで OK
  - リポジトリ同梱の `fonts/NotoSansCJKjp-Bold.otf` を優先使用
- **(任意) ElevenLabs API キー**: 高品質ナレーション用。無くても OS 内蔵 TTS にフォールバック
  - macOS: `say -v Otoya`
  - Windows: PowerShell の `System.Speech.Synthesizer`

## インストール

### macOS / Linux

```bash
git clone https://github.com/raimu1240-ship-it/shortvideo-skill.git ~/code/shortvideo-skill
cd ~/code/shortvideo-skill
./install.sh
cp .env.example .env    # ElevenLabs を使うなら ELEVENLABS_API_KEY を設定
```

`install.sh` は `~/.claude/skills/` `~/.claude/agents/` `~/.claude/commands/` 配下に symlink を作成する。`git pull` だけで反映される。

### Windows

**事前準備**: symlink 作成のため、以下のいずれかが必要です:

- **方法 A (推奨)**: 「開発者モード」を ON にする — Windows 10 1703 以降、設定 → プライバシーとセキュリティ → 開発者向け → 開発者モード を ON。一度設定すれば管理者権限なしで symlink が作れる
- **方法 B**: PowerShell を管理者として実行

その上で:

```powershell
git clone https://github.com/raimu1240-ship-it/shortvideo-skill.git $env:USERPROFILE\code\shortvideo-skill
cd $env:USERPROFILE\code\shortvideo-skill
.\install.ps1
copy .env.example .env
```

cmd.exe から起動する場合は `install.bat` をダブルクリック (中で PowerShell を呼ぶ)。

`install.ps1` は symlink 作成を試み、失敗した場合は自動的にファイルコピーに切り替えます。コピーで運用すると `git pull` 後に再度 `install.ps1` を実行する必要があります (symlink なら不要)。

### 必要コマンドが入っていない時

`install.sh` / `install.ps1` は最後に ffmpeg / ffprobe / python / Pillow / フォントの存在をチェックし、足りなければインストールコマンドを表示します。

## 使い方

**必ず、このリポジトリの中で `claude` を起動してください**。reviewer subagent が `.claude/agents/` を見つけるためです:

```bash
# macOS / Linux
cd ~/code/shortvideo-skill
claude
```

```powershell
# Windows
cd $env:USERPROFILE\code\shortvideo-skill
claude
```

Claude Code のセッションの中で:

```
/shortvideo-loop プロジェクト名
```

planner → generator → reviewer の順に自動実行。最大 3 ラウンドの自動修正後、人間レビュー gate が開きます。動画プレイヤーで `output.mp4` を見て `pass` か `fail` を返してください。`fail` なら理由を `patches.json` に追加してもう 1 ラウンド回ります。

完成した動画は `projects/プロジェクト名/output.mp4`。

個別にステップを動かしたい場合は `/shortvideo-planner` → `/shortvideo-generator` → reviewer skill を順に呼んでください。

### 3 エージェントの色分け

`/shortvideo-loop` は 3 つの subagent を順番に動かします。Claude Code の TaskList / transcript 上で**色分け表示**されるので、今どの段階を実行中か視覚的に分かります:

| エージェント | 色 | 役割 |
|---|---|---|
| `shortvideo-planner` | 🟢 緑 | お題から input.json (台本) を作る |
| `shortvideo-generator` | 🔵 青 | input.json から output.mp4 を生成 |
| `shortvideo-reviewer` | 🟣 紫 | 27 観点で grade、patch を出力 |

planner → generator → reviewer のチーム制で 1 本の動画ができる流れです。

### 別ディレクトリから claude を起動した場合

reviewer の subagent 認識は cwd 依存です。別ディレクトリから起動すると `Agent type 'shortvideo-reviewer' not found` が出るため、`/shortvideo-loop` は `subagent_type="general-purpose"` にフォールバックします。動作はしますが、reviewer の独立 context が崩れて判定が generator に引きずられやすくなります。基本は**リポ内で起動を推奨**。

### 人間レビュー gate (省略不可)

27 観点の自動 reviewer は Vision LLM で動いており、generator と同じ盲点を共有しやすいです (テンポが死んでいる、字幕が読めても意味が刺さらない、いらすとや のトーンが声と合わない、等)。**自動 reviewer の blocker=0 だけでは完成と呼びません**。

`/shortvideo-loop` は `output.mp4` をプレイヤーで開いて、人間の `pass` / `fail` を待ちます。判定は `projects/<name>/HUMAN_REVIEW.md` に記録されます。

### 背景動画ソース

デフォルトは Pexels (`scripts/fetch_pexels_id.py`)。0 件 hit / 海外混入が多い時は Mixkit にフォールバックできます。

| ソース | URL | 特徴 |
|---|---|---|
| Pexels | https://www.pexels.com/ja-jp/search/videos/japan/ | デフォルト、urllib + Cloudflare bypass headers |
| Mixkit | https://mixkit.co/free-stock-video/japan/ | 静的 HTML、ニッチ query (旅館・田舎) で hit しやすい |
| Pixabay / Coverr | (今後追加予定) | |

詳細とソース別 URL パターンは `.claude/skills/shortvideo-generator/references/stock-sources.md` を参照。

## 設計原則

- **BGM なし、PR バッジなし、ブランド帯なし** — 共感型フォーマットに特化、PR 用途は別スキル
- **日本ロケのみ** — Pexels 検索結果を Vision でコンタクトシート判定して海外混入を除外
- **決定論的レンダリング** — 同じ `input.json` + 同じフォント → 同じ `output.mp4` md5sum (同一ホスト内)
- **独立 reviewer** — 別 context で動かして、generator の推論経路を見せない
- **最大 3 ラウンドで打ち切り** — 自動修正は 3 回まで、それでも残るなら人間にエスカレーション

## ライセンス

MIT。`LICENSE` 参照。
