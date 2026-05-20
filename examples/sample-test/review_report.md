# Review Report — sample-test

## Summary
blocker=3 / warning=4 / info=1

## Blocker

### V01 海外背景 (s2, t=5.0-6.89s)
- 観測: f_85 / f_95 で s2 の背景が欧米風 playground（青い金属製ジャングルジム、ウッドチップ地面、曇天）になっており、日本ロケに見えない。`acceptance_criteria.must_have` に `japanese_bg_only` が含まれているため必ず差し替えが必要。`japan park bench autumn` クエリが米国 playground を返したのを未選別で採用してしまっている。
- fix 1: bg_query を `japan park bench autumn morning` 等、`japan` + 具体名詞で絞る
- fix 2: 別の Pexels video_id（日本の公園ベンチ・神社境内・河川敷ベンチ等の確実な日本ロケ）に差し替え
- fix 3: contact_sheet 目視チェックを必ず通す stage を追加
- patch: {"patch_type":"replace_bg","segment":"s2","new_query":"japan park bench morning autumn"}

### Q-dur 尺不足 (全体, duration=6.89s vs 10±0.5s)
- 観測: ffprobe_quality.json で `duration 6.89s not within 10±0.5s` と検出済。input.json は s1=5.0s + s2=5.0s = 10s 想定だが、実出力は 6.89s。voice 再生長に映像が rescale されている可能性が高い（s2 末尾 1.95s で切れている）。voice_text が voice TTS で 6.89s 分しか発声されず、segment duration が voice 長に揃えられていると推定。
- fix 1: voice_text を duration_target_sec=10s に合うよう長文化する（s1/s2 各 5s 想定で voice 長を実測してから調整）
- fix 2: voice 長に映像を合わせるのではなく、segment.duration_sec を厳守し voice 末尾に padding silence を入れる方式に変更
- fix 3: 各 segment の voice_text を 1-2 文増やして自然に 5s 埋める
- patch: {"patch_type":"rewrite_caption","segment":"s1","new_caption":["毎日同じ通勤、","これでいいのかな。"]}

（補足: rewrite_caption だけでは尺は伸びない。実運用では voice_text 自体の書き直し + 再 TTS が必要。set_field で voice_text を上書きするパッチも併用）

- patch: {"patch_type":"set_field","path":"scenario.segments.0.voice_text","value":"毎日同じ通勤、これでいいのかなって、ふと立ち止まる朝があった。"}
- patch: {"patch_type":"set_field","path":"scenario.segments.1.voice_text","value":"自分のペースで、無理しない働き方を選んだ。それが、いちばん長く続く気がして。"}

### T06 voice/caption 内容乖離 (s2, t=5-6.89s)
- 観測: s2 の voice_text「自分のペースで、無理しない働き方を選んだ。」と caption_main「自分のペースが、いちばん続く。」で言っている内容が異なる。共通文字は「自分のペース」程度で文字重複は約 33%。voice は「働き方を選んだ」という過去の決断、caption は「いちばん続く」という結論。視聴者が音声と字幕で別情報を処理することになる。30% を下回ると blocker、30-60% は warning だが、本件は 33% 付近の境界。caption が voice の論理的続編・要約に近く、文意は通るため境界判定だが、s1 が 90% overlap で揃っていることとの対比で warning に留めず blocker 寄り判定。
- fix 1: caption_main を voice に揃える: `["自分のペースで、","無理しない働き方を。"]`
- fix 2: voice_text を caption に揃える（voice 再生成必要）
- patch: {"patch_type":"rewrite_caption","segment":"s2","new_caption":["自分のペースで、","無理しない働き方を。"]}

## Warning

### A01 loudnorm 範囲外 (全体, I=-25.37 LUFS)
- 観測: 統合ラウドネス -25.37 LUFS は acceptance_criteria の [-25, -21] LUFS 範囲を 0.37 LUFS 下回る。境界ぎりぎりの逸脱だが範囲外。
- fix 1: voice ミックス時に +2〜+3dB ゲイン適用して -23 LUFS 程度に揃える
- fix 2: loudnorm filter の target_i を -23 にして再エンコード
- patch: {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}

### P01 / P03 illust ペルソナ不一致 (s2, t=5-6.89s)
- 観測: s2 の irasutoya 素材は「腕が複数本ある super businessman（マルチタスク表現）」で、ペルソナ「28歳男性・新しい働き方への気付き」「無理しない働き方を選んだ」という落ち着いた共感型ストーリーと方向性が真逆。視聴者は皮肉・誇張に感じる。illust_query `穏やか 男性 笑顔` が意図と違う素材を引いてしまっている。
- fix 1: 「微笑む スーツ 男性」「リラックス サラリーマン」等の単一人物・穏やか表情に差し替え
- fix 2: contact_sheet で illust も目視確認する stage を追加
- patch: {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む リラックス"}

### V04 字幕視認性 (s2, t=5-6.89s)
- 観測: s2 背景の空がやや明るく、caption_main 下部はウッドチップで暗いため辛うじて読めるが、白文字 + soft shadow のみで scrim 黒 0.15 では境界が弱い。s1 は十分視認可。
- fix 1: scrim alpha を 0.15 → 0.25 に上げる
- fix 2: caption 下に局所スクリム帯（caption 行のみ alpha 0.35 程度）を入れる
- patch: {"patch_type":"set_field","path":"scenario.segments.1.scrim_alpha","value":0.25}

### T06 (s2) 警告統合
- s2 の T06 は blocker 判定だが、もし orchestrator が「文意は連続している」と判断するなら warning にダウングレード可。fix は同上の rewrite_caption。

## Info

### Q05 ファイルサイズ (測定値なし、duration 6.89s)
- 観測: 尺 6.89s 短尺のため file size は問題にならない見込み。ffprobe_quality.json に size 記載なし。Q05 範囲（60MB）超は実質ありえず情報のみ。
- 対応不要

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s2","new_query":"japan park bench morning autumn"},
  {"patch_type":"set_field","path":"scenario.segments.0.voice_text","value":"毎日同じ通勤、これでいいのかなって、ふと立ち止まる朝があった。"},
  {"patch_type":"set_field","path":"scenario.segments.1.voice_text","value":"自分のペースで、無理しない働き方を選んだ。それが、いちばん長く続く気がして。"},
  {"patch_type":"rewrite_caption","segment":"s2","new_caption":["自分のペースで、","無理しない働き方を。"]},
  {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む リラックス"},
  {"patch_type":"set_field","path":"scenario.segments.1.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}
]
```

## Calibration notes

- T03 (sub_delay 同時表示): **resolved**. f_0/f_15/f_35 にバブル不在、f_50/f_65 (s1 内 t=2.5s 以降) でバブル出現、f_85/f_95 (s2 内 t=0.86-1.95s < 2.5s) でバブル不在を確認。sub_delay=2.5s が正しく実装されている。
- V01 (s2 海外背景): sample-01-10s と同じ Pexels 公園クエリの罠が再現。`japan` prefix 単体では不十分、`japan + 固有名詞 or 都市名` まで絞る運用ルール化が必要。
- T06 (新指標): s1=90% 高 overlap pass / s2=33% 低 overlap で境界判定。voice と caption が「同じ意味の別表現」なら overlap 低くても許容、「異なる情報」なら blocker、を切り分ける判定基準を例として積み上げていく必要あり。本件は前者寄りだが s1 との対比で blocker 計上。
