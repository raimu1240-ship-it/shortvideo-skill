# Review Report — sample-02-60s-round2

## Summary
blocker=2 / warning=3 / info=2

## Blocker

### V-NEW (illust contact-sheet grid rendered instead of single character) (s1 t=0s, s2 t=8s, s4 t=20s)
- 観測: f_0 (s1) で 2x2 グリッドの「円グラフ + 男性キャラ」が画面中央に出ている。f_15 (s2) と f_35 (s4) では 4x3 グリッドの「いろいろな表情のスーツ男性」素材がそのまま貼られている。input.json 上は各 seg に単一の illust_query を指定しているが、レンダラが contact_sheet (irasutoya の検索結果一覧 PNG) を crop せずに貼っている挙動。s1 の "男性 ふと立ち止まる 通勤"、s2 の "男性 考え事 歩く"、s4 の "スーツ 男性 微笑む リラックス" それぞれで意図したキャラ単体に絞れていない。
- 視聴体験: 「複数の小さい顔が並ぶシート」が前面に出るので、共感型 narrative としての効果がほぼ消える。round_1 → round_2 で illust query は具体化されたが、fetcher/cropper 側のバグが残っていると推定。
- fix 1: irasutoya fetch step で contact sheet を 1 キャラに crop する処理を追加 (例: 上位 1 件の `s400` または `400.png` を選択して、複数キャラ収録の `_list.png` は除外)
- fix 2: illust_query を「単一人物が明確に確定する語」に書き換え (例: s1 を `スーツ 男性 困った顔 立ち止まる` のように 1 表情を強制)
- fix 3: round_3 で seg ごとに contact_sheet_passed=true の判定基準に「面数=1」を含める
- patch: {"patch_type":"replace_illust","segment":"s1","new_query":"スーツ 男性 困った 立ち止まる"}
- patch: {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 悩む 一人"}
- patch: {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む 一人"}

### V01 / Q-missing-bg (s6 背景 Pexels 動画が抜けて青空単色) (s6, t=28s)
- 観測: f_50 (s6, t=28s) で背景がほぼ単色のブルーグラデーション、下部にビル群の輪郭がうっすら見えるだけ。input.json の bg_query は "japan office break afternoon" だが、render 上は Pexels 動画が落ちず黒/青のフォールバックに見える。must_have の `japanese_bg_only` を満たしているかが目視で判断できない状態。
- なぜ blocker: 背景動画が無い = "japan" であることを担保する画情報がゼロ = `japanese_bg_only` 失敗リスク。round_1 の learning で背景日本ロケを強化した文脈で、s6 だけ抜けるのは acceptance criteria 違反扱い。
- fix 1: s6 の bg_query を Pexels で確実にヒットする語に置換 (`japan office building afternoon` / `tokyo office desk` 等)
- fix 2: fetch_pexels_id.py 側で 0 件ヒット時に再クエリ or fallback を強制する
- fix 3: round_3 で seg ごとに `bg_video_id` を input.json に固定化し、再現性を上げる
- patch: {"patch_type":"replace_bg","segment":"s6","new_query":"japan office desk afternoon"}

## Warning

### A01 loudnorm I=-25.34 LUFS (全体, t=0-56s)
- 観測: ffprobe_quality.json で `loudnorm_I=-25.34`、acceptance_criteria.loudnorm_lufs_range=[-25,-21] の下限を 0.34 LUFS 下回る。聴感では「やや小さい」程度だが、配信側の自動ノーマライズで他動画と音量差が出る可能性。
- fix 1: ffmpeg loudnorm の二段パスで `i=-23` 固定で再エンコード
- fix 2: voice TTS の出力レベルを +2dB シフト
- patch: {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}

### P02 / V08 illust 重複疑い (s7 t=37s, s9 t=48s, s10 t=53s で super_businessman 系が連続)
- 観測: f_65 (s7) / f_85 (s9) / f_95 (s10) で「青い服の男性 1 人立ち / OK ポーズ / 汗だくサラリーマン」と super_businessman 派生が後半に固まる。input.json の notes でも「super_businessman を s4,s5,s6,s7,s9,s10 = 6 seg に意図的に分配」と書かれており、設計どおりだが視聴体験としては「同じ人物が何度も出る」印象を生む。
- fix 1: s9 / s10 のどちらかを別 query (例: 「男性 海 リラックス」「男性 夜景 散歩」) に振って後半の visual variety を確保
- fix 2: persona の age=32, gender=male は維持しつつ、表情のバリエーション (微笑/真顔/考え) を強制
- patch: {"patch_type":"replace_illust","segment":"s9","new_query":"男性 歩く 横顔 落ち着き"}

### P03 環境ミスマッチ疑い (s10 t=53s)
- 観測: f_95 (s10) の背景が「山岳の稜線 + 海が遠景に見える」構図で、input.json の bg_query "japan park bench autumn afternoon" と乖離。「公園のベンチ」訴求が刺さらず、屋久島/離島系の山頂風景になっている。persona "働き方を見直して気付いたこと" の締めとしては抽象度が高すぎる。
- fix 1: bg_query を `japan park bench autumn` (短く絞る) または `tokyo park afternoon` に変更
- fix 2: 最後の seg は「日常に戻る」絵づくりを優先 → カフェ窓辺、住宅街、駅前など生活圏のビジュアル
- patch: {"patch_type":"replace_bg","segment":"s10","new_query":"japan park bench afternoon"}

## Info

### Duration 56.19s (target 60s, tolerance ±4s)
- 観測: 動画長 56.19s、acceptance_criteria.duration_target_sec=60、tolerance 4.0s → 範囲内 (差 3.81s)。境界ぎりぎり (4.0s tolerance に対して 3.81s 使用) なので、round_3 で voice_text が伸びるとアウトになる余地あり。
- 対応: voice TTS の話速を +3% 程度上げるか、seg10 末尾に 0.2-0.5s buffer を追加して 58s 前後に揃えると安全。
- patch: 不要 (現状は spec 内)

### 観察事項 (新カテゴリ候補): irasutoya contact-sheet そのまま貼り付け
- 観測: 上記 V-NEW で挙げた「グリッド型 irasutoya がそのまま画面に出る」現象は、現 rubric の V06 (upscale) / V08 (illust query 重複) では完全には捕捉できない。"single character mandate" の新カテゴリとして昇格候補。
- 昇格条件: 別 sample (sample-03 以降) で 1 件以上同パターンが再現したら `V09` として rubric 追加 (learning-loop.md の手順に従う)
- 対応: 今回は V-NEW 名義で blocker 計上、observation を info に残す

## Patches (JSON array)

```json
[
  {"patch_type":"replace_illust","segment":"s1","new_query":"スーツ 男性 困った 立ち止まる"},
  {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 悩む 一人"},
  {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む 一人"},
  {"patch_type":"replace_bg","segment":"s6","new_query":"japan office desk afternoon"},
  {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0},
  {"patch_type":"replace_illust","segment":"s9","new_query":"男性 歩く 横顔 落ち着き"},
  {"patch_type":"replace_bg","segment":"s10","new_query":"japan park bench afternoon"}
]
```
