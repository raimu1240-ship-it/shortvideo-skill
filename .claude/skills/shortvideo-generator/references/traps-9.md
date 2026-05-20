# Traps — 9 known failure modes

罠 9 件と自動検出・回避手段。`scripts/lint_recipe.py` がほぼ全てを pre-check する。

## Contents
- T1 PR バッジ・ブランド帯
- T2 Y 座標誤り
- T3 1 行字数超過
- T4 サブテロップ即時表示
- T5 whisper end 不正確
- T6 A/V drift
- T7 voice / caption 表記差
- T8 海外素材混入
- T9 CTA 文言重複

## T1: 勝手な PR バッジ / ブランド帯 / 商品カード追加

- 症状: Generator が "プロっぽさ" を出そうとして、acceptance_criteria.must_not_have を無視
- 検出: lint_recipe.py が `must_not_have` 項目を input.json に対して grep
- 回避: SKILL.md "What NOT to do" を毎ターン読み返す、reviewer が T02 (PR色文言) を blocker で出す

## T2: Y 座標誤り

- 症状: 1080x1920 用の Y=1280 を 720x1280 に流用 → letterbox からはみ出る
- 検出: lint_recipe.py が resolution と Y 座標を突き合わせ
- 回避: 座標は `overlay-positioning.md` のテーブル参照、自由値禁止

## T3: 1 行字数超過

- 症状: 8 字超え caption が改行されず画面外
- 検出: lint_recipe.py が `len > 8` warn / `len > 12` error
- 回避: planner で 2 行帯に分割

## T4: サブテロップ即時表示

- 症状: メインと同時に出ると視聴者が一読してスキップ
- 検出: lint_recipe.py が `sub_delay < 1.5` warn
- 回避: planner が 2.0-4.0 秒の delay を入れる、`enable='gte(t,N)'` で焼き込み

## T5: whisper segment.end が 1-2s 不正確

- 症状: 音声末尾の真値より早く / 遅く出る、A/V drift の元
- 検出: lint_recipe.py が `voice_duration_source != "ffprobe"` を error
- 回避: tts 後に `ffprobe -show_entries format=duration` を必ず実行して上書き

## T6: A/V drift (fastcut の小数秒累積)

- 症状: 11 セグ concat で 0.5-0.7s ズレる
- 検出: ffprobe_quality.py が audio_duration - video_duration を計算、>0.1 で error
- 回避: render_video.py が `setpts=ratio*PTS` で全体 rescale して voice 長に揃える

## T7: voice / caption 表記差 (アクセント不安定)

- 症状: voice 「こうじょう」(ひらがな) で頭高アクセント、caption 「工場」(漢字) で平板、視聴者違和感
- 検出: lint_recipe.py が voice_text と caption_main の漢字含有率を比較
- 回避: planner が voice_text も caption と同じ漢字優先で書く

## T8: 海外ストック素材混入

- 症状: Pexels 「park」検索で米国 playground、「street」で NY が紛れる
- 検出: contact_sheet.py で tile 化 → Vision Read で目視チェック (Claude が判定)
- 回避: bg_query に「japan」「tokyo」「kyoto」prefix、segment ごとに `contact_sheet_passed: true` を立ててから Stage 6

## T9: CTA 文言と overlay label の重複

- 症状: overlay 画像の中に「無料相談」と書いてあり、caption にも「無料相談」がある → くどい
- 検出: lint_recipe.py が `overlay_label` と `caption_main` の文字列重複を grep
- 回避: overlay は画像 only、caption は文字 only に責務分離
