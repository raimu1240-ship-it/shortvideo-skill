# Review Report — sample-02-60s

## Summary
blocker=1 / warning=10 / info=3

## Blocker

### V01 海外背景 (s2/s4/s6/s8/s10, t≈6-12s / 18-24s / 30-36s / 42-48s / 54-59.25s)
- 観測: `bg_query: japan park afternoon` を採用した 5 segments (s2, s4, s6, s8, s10) すべてで、青と赤の鉄製ジャングルジム遊具・ウッドチップ地面・曇天という欧米風 playground 背景が映る。f_15 (s2, t≈8.9s)、f_35 (s4, t≈20.7s)、f_95 (s10, t≈56.3s) で同一の海外ロケ素材が連続使用されており、日本ロケに見えない。`acceptance_criteria.must_have` に `japanese_bg_only` が明記されているため必ず差し替える必要がある。1 video の半分 (5/10 segments、約 30s) が海外背景という重度の侵害。sample-01-10s / sample-test と同じ `japan park` クエリの罠が再現。
- fix 1: bg_query を `japan park bench autumn` `japan kyoto temple path` 等、`japan` + 固有名詞/都市名で絞る
- fix 2: park afternoon の Pexels video_id を contact_sheet 目視で確実な日本ロケ (鳥居・神社・河川敷・桜並木等) に差し替え
- fix 3: s2/s4/s6/s8/s10 で背景を分けて単調さも回避
- patch: {"patch_type":"replace_bg","segment":"s2","new_query":"japan park bench autumn"}
- patch: {"patch_type":"replace_bg","segment":"s4","new_query":"japan shrine path morning"}
- patch: {"patch_type":"replace_bg","segment":"s6","new_query":"japan riverside autumn"}
- patch: {"patch_type":"replace_bg","segment":"s8","new_query":"japan park sakura"}
- patch: {"patch_type":"replace_bg","segment":"s10","new_query":"japan kyoto temple path"}

## Warning

### A01 loudnorm 範囲外 (全体, I=-25.4 LUFS)
- 観測: ffprobe_quality.json の integrated loudness -25.4 LUFS が acceptance_criteria の [-25, -21] LUFS 範囲を 0.4 LUFS 下回る。LRA=1.4 と非常にコンプ気味だが、目標下限を割っている。
- fix 1: TTS mix 段で +2〜+3dB ゲイン適用し -23 LUFS 程度に揃える
- fix 2: loudnorm filter の target_i を -23 にして再エンコード
- patch: {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}

### P02 illust 属性ミスマッチ (s4, s5, s6, s7, s9, s10 = 6 segments)
- 観測: s4-s7 / s9 / s10 の illust は「腕が複数本ある super_businessman (マルチタスク仕事人)」素材。persona context「働き方を見直して気付いたこと」「穏やかに気付きを語る 32 歳男性」という落ち着いた共感型ナラティブと真逆。視聴者は皮肉・誇張・「むしろ忙しそう」と感じる。illust_query `穏やか 男性 笑顔` が super_businessman を引き当てており、クエリ→素材マップが意図と乖離している。6 segments 連続で同一素材なため疲労感も発生。input.json notes で「P02 が super_businessman 側で 6 segment 連続で出る」 calibration として明記済の意図的検出。
  - s4 t≈20.7s (f_35): 「生活も整う」← 4 腕で書類とタブレットを同時操作するキャラ
  - s5 t≈29.6s (f_50): 「未経験から始める」← 同上
  - s6: 「悩んだ時に抱え込まなくていい」← マルチタスクで完全に逆メッセージ
  - s7 t≈38.5s (f_65): 「相談できる人がいるって大きい」← 同上
  - s9 t≈50.4s (f_85): 「働きながら探す」← 多忙人物が「探す余裕」を語る皮肉
  - s10 t≈56.3s (f_95): 「ありだと思う」← 結論を激務人物が語る違和感
- fix 1: illust_query を「微笑む スーツ 男性 一人」「リラックス サラリーマン 落ち着いた」に変更し super_businessman を回避
- fix 2: 6 segments で 2-3 種類のイラストにバラして単調さも解消
- fix 3: 「気付き局面」の責務に合うのは「単一人物・落ち着いた表情・道具なし」素材
- patch: {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む リラックス"}
- patch: {"patch_type":"replace_illust","segment":"s5","new_query":"スーツ 男性 気付く 落ち着く"}
- patch: {"patch_type":"replace_illust","segment":"s6","new_query":"スーツ 男性 安心 一人"}
- patch: {"patch_type":"replace_illust","segment":"s7","new_query":"スーツ 男性 話す 穏やか"}
- patch: {"patch_type":"replace_illust","segment":"s9","new_query":"スーツ 男性 前向き 落ち着く"}
- patch: {"patch_type":"replace_illust","segment":"s10","new_query":"スーツ 男性 微笑む 確信"}

### T06 voice/caption overlap 低下 (s3, s5, s6, s7, s8 — 5 segments warn)

voice_text が ~6s 尺に合わせて拡張され、caption_main が 12 字×2 行に圧縮されたため filler 起因の overlap 低下が発生。30% 以上のため blocker 該当ゼロ、5 segments が warning。

per-segment table (10 segments):

| seg | voice_text 要点 | caption | overlap 体感 | 判定 |
|---|---|---|---|---|
| s1 | 自分に合う仕事って、本当にあるのかな、って正直ずっと思ってた | 自分に合う仕事って、/あるのかな | ~75% | info (pass) |
| s2 | でも今のやり方、案外続いているなって、気付いたのはつい最近のこと | でも今のやり方、/案外続いてる | ~70% | info (pass) |
| s3 | 正社員じゃないと不安、って言われることも、まあ、あるんだけどさ | 正社員じゃないと、/って声もある | ~50% | warn |
| s4 | 時間が決まってると、生活リズムは作りやすいし、整ってくるんだよね | 時間が決まってると、/生活も整う | ~70% | info (pass) |
| s5 | 未経験から始められる仕事も、意外と多いんだよね、調べてみると本当に | 未経験から始める、/選択肢も意外と | ~45% | warn |
| s6 | 人間関係で悩んだ時に、職場だけで抱え込まなくていいって、思えるようになった | 悩んだ時に、/抱え込まなくていい | ~55% | warn |
| s7 | 相談できる人がいるだけで、気持ちはかなり違うんだよね、これは本当に | 相談できる人が、/いるって大きい | ~50% | warn |
| s8 | もちろん、全部が楽なわけじゃないけどね、そこは正直に言っておく | もちろん、/全部が楽じゃない | ~55% | warn |
| s9 | 働きながら、自分に合う仕事を探したい人にとっては、けっこう向いてるかも | 働きながら探す、/そんな人には | ~65% | info (pass) |
| s10 | こういう働き方も、選択肢の一つとしてありだと思うんだよな、今は | こういう働き方、/ありだと思う | ~70% | info (pass) |

- 全 segments で重複 30% 以上 → blocker 該当ゼロ
- 5 segments warn (s3/s5/s6/s7/s8)、5 segments info pass (s1/s2/s4/s9/s10)
- fix 1: filler を caption に取り込んで音声と文字の不一致体感を下げる
- fix 2: voice_text を caption に近付けて filler 圧縮 (TTS 再生成必要、尺 6s 維持のため speed 微調整)
- fix 3: T06 評価ロジックを「filler 除外後 content-word overlap」に変更する運用案
- patch: {"patch_type":"rewrite_caption","segment":"s3","new_caption":["正社員じゃないと、","って声もあるけど。"]}
- patch: {"patch_type":"rewrite_caption","segment":"s5","new_caption":["未経験から始める、","調べると意外と多い。"]}
- patch: {"patch_type":"rewrite_caption","segment":"s7","new_caption":["相談できる人で、","気持ちはかなり違う。"]}
- patch: {"patch_type":"rewrite_caption","segment":"s8","new_caption":["全部が楽じゃない、","そこは正直に。"]}

### V04 字幕視認性 (s5, s9, t≈29.6s / 50.4s)
- 観測: s5/s9 の駅構内背景は天井ライトと白い柱で上半分が明るく、下半分は群衆で暗く中コントラスト。scrim alpha 0.15 は機能しているが、白文字 + soft shadow との境界が微妙。f_50 / f_85 で読める範囲だが、視認性余裕は小さい。
- fix 1: scrim alpha を 0.15 → 0.25 に上げる (該当 segments のみ)
- fix 2: caption 下に局所スクリム帯 (caption 行のみ alpha 0.35) を追加
- patch: {"patch_type":"set_field","path":"scenario.segments.4.scrim_alpha","value":0.25}
- patch: {"patch_type":"set_field","path":"scenario.segments.8.scrim_alpha","value":0.25}

### V03 illust 横位置オフセット (s2, s4, s10, 軽微)
- 観測: f_15 / f_35 / f_95 で illust 重心がやや左寄り (中央 360px に対し x≈310-330px、約 4-7% 左ズレ)。閾値 5% 境界上のため warning。super_businessman は伸ばした腕含めるとさらに左寄りに見えるが、本体ボディ位置で計測すれば閾値内に収まる可能性も。
- fix 1: renderer の illust 配置 x オフセットを 0 に再校正
- fix 2: super_businessman のように張り出しのある PNG は重心ではなく可視幅で中心計算
- patch: {"patch_type":"set_field","path":"render.illust_x_offset","value":0}

## Info

### T03 sub_delay=2.5s 実装確認 (全 segments) — RESOLVED
- 観測: 各 segment 内で bubble の出現タイミングを確認。f_0 (s1 t=0s) bubble 不在、f_15 (s2 t≈2.9s) bubble「気付けば半年」出現、f_35 (s4 t≈2.7s) bubble「予定が立つ安心」出現、f_50 (s5 t≈5.6s) bubble「始めて気付いた」出現、f_65 (s7 t≈2.5s) bubble「それだけで違う」出現、f_85 (s9 t≈2.4s) bubble 不在 (2.5s 直前)、f_95 (s10 t≈2.3s) bubble 不在 (2.5s 直前)。bubble は 2.5s 後にのみ出現しており、sub_delay=2.5s が正しく機能している。
- 対応不要

### V05 / Q01 / Q02 / Q04 / A03 — pass
- 解像度 720x1280 ✓、fps 30/1 ✓、pix_fmt yuv420p ✓、av_drift 0.0s ✓、duration 59.25s (target 60±2.0s) ✓、audio_duration = video_duration ✓。

### Q05 ファイルサイズ
- 観測: 59.25s の本動画で 60MB 上限は実質ありえない。ffprobe_quality.json に size 未記載だが、yuv420p / h264 / 720x1280 / 30fps であれば 10-25MB 想定で警告閾値外。
- 対応不要

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s2","new_query":"japan park bench autumn"},
  {"patch_type":"replace_bg","segment":"s4","new_query":"japan shrine path morning"},
  {"patch_type":"replace_bg","segment":"s6","new_query":"japan riverside autumn"},
  {"patch_type":"replace_bg","segment":"s8","new_query":"japan park sakura"},
  {"patch_type":"replace_bg","segment":"s10","new_query":"japan kyoto temple path"},
  {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む リラックス"},
  {"patch_type":"replace_illust","segment":"s5","new_query":"スーツ 男性 気付く 落ち着く"},
  {"patch_type":"replace_illust","segment":"s6","new_query":"スーツ 男性 安心 一人"},
  {"patch_type":"replace_illust","segment":"s7","new_query":"スーツ 男性 話す 穏やか"},
  {"patch_type":"replace_illust","segment":"s9","new_query":"スーツ 男性 前向き 落ち着く"},
  {"patch_type":"replace_illust","segment":"s10","new_query":"スーツ 男性 微笑む 確信"},
  {"patch_type":"rewrite_caption","segment":"s3","new_caption":["正社員じゃないと、","って声もあるけど。"]},
  {"patch_type":"rewrite_caption","segment":"s5","new_caption":["未経験から始める、","調べると意外と多い。"]},
  {"patch_type":"rewrite_caption","segment":"s7","new_caption":["相談できる人で、","気持ちはかなり違う。"]},
  {"patch_type":"rewrite_caption","segment":"s8","new_caption":["全部が楽じゃない、","そこは正直に。"]},
  {"patch_type":"set_field","path":"scenario.segments.4.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.8.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}
]
```

## Calibration notes

- T03 sub_delay=2.5s: **resolved**. 7 frames で期待通り bubble 表示/非表示が切り替わっている。f_85/f_95 が t≈2.4s/2.3s で bubble 不在、f_15/f_35/f_50/f_65 が t≥2.5s で bubble 出現を確認。
- V01: `japan park afternoon` という generic クエリが Pexels で同一の米国 playground を 5 segments 連続で引き当てる罠が再現 (sample-01-10s / sample-test に続き 3 回目)。`japan + 都市名/固有名詞` 必須ルールを bg_query 生成段階に組み込むべき時期。
- P02 calibration: super_businessman 6 segments 連続出現を計画通り検出。input.json notes 通りの意図的セット。`illust_query=穏やか 男性 笑顔` で super_businessman が引かれる素材検索ロジックの不具合、または irasutoya cache 偏重が原因と推定。
- T06: voice 6s 拡張型 narrative では filler ("まあ" "って" "んだよね" "これは本当に" "そこは正直に") が overlap を下げる構造的問題が露呈。sample-02-13s が voice=caption 同期で全 segment pass だったのに対し、本サンプルは 5/10 warn。filler 除外評価への切替が今後の課題。
