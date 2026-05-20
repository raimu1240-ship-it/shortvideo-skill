# Review Report — sample-02-60s

## Summary
blocker=4 / warning=4 / info=2

## Blocker

### V01 海外背景 (s2/s4/s6/s8/s10, t≈6-12s, 18-24s, 30-36s, 42-48s, 54-59s)
- 観測: f_15 (s2 内), f_35 (s4 内), f_95 (s10 内) で同一の欧米風 playground（青い金属製ジャングルジム、ウッドチップ地面、曇天）が映る。s6/s8 も同じ `japan park afternoon` クエリで生成されているため同じ海外ロケ素材を fastcut で再利用している可能性が高い。`acceptance_criteria.must_have` に `japanese_bg_only` が含まれており、5 segment（50%）にわたって海外背景が確定で映るため致命的。fastcut で 2s チャンク化しても src 自体が overseas のため画変わりだけでは救済不可。
- fix 1: `japan park afternoon` を `japan park bench autumn` `japan kyoto temple path` `japan tokyo street afternoon` `japan office break` `japan riverside walk` 等、確実に日本ロケが返る具体名詞付きクエリ 5 種に分散
- fix 2: contact_sheet で各候補を目視チェックする stage を必ず通す
- fix 3: 既知の日本ロケ Pexels video_id に直接差し替える
- patch: {"patch_type":"replace_bg","segment":"s2","new_query":"japan kyoto temple path afternoon"}
- patch: {"patch_type":"replace_bg","segment":"s4","new_query":"japan riverside walk afternoon"}
- patch: {"patch_type":"replace_bg","segment":"s6","new_query":"japan office break afternoon"}
- patch: {"patch_type":"replace_bg","segment":"s8","new_query":"japan tokyo street afternoon"}
- patch: {"patch_type":"replace_bg","segment":"s10","new_query":"japan park bench autumn afternoon"}

### V07 bg_query 重複過多 (全体)
- 観測: `japan train station morning` が s1/s3/s5/s7/s9 の 5/10 = 50% で使用、`japan park afternoon` が s2/s4/s6/s8/s10 の 5/10 = 50% で使用。両方とも >50% blocker 閾値ちょうど（>33% warning 閾値超過）。fastcut で 1 segment 内に 3 チャンクの time offset 変化を入れても、視聴者は f_0/f_50/f_65/f_85 の比較で「同じ駅構内」と判別できる（天井ダクト・蛍光灯・案内サインが識別可能）。同様に f_15/f_35/f_95 で「同じ playground」と判別可能。fastcut の効果は局所的な目線移動どまりで、bucket レベルの単調さを解消できていない。
- fix 1: 2 種類しかない bg_query を、駅系 1 種 + 街系 / 通勤系 2 種 + 公園系 2 種 + 室内系 / 寺社 系 数種、合計 7〜8 種にばらす
- fix 2: 同一クエリは最大 2 segment（20%）までというルールを generator 側に組み込む
- fix 3: 同一 src video_id の最大再利用回数も 2 segment までに制限
- patch: V01 の patches で park 側 5 segment 分散済。駅系 5 segment も以下で分散:
- patch: {"patch_type":"replace_bg","segment":"s3","new_query":"japan office building morning"}
- patch: {"patch_type":"replace_bg","segment":"s5","new_query":"japan commute walking morning"}
- patch: {"patch_type":"replace_bg","segment":"s7","new_query":"japan cafe interior morning"}
- patch: {"patch_type":"replace_bg","segment":"s9","new_query":"japan crosswalk morning"}

### V08 illust_query 重複過多 (全体)
- 観測: `穏やか 男性 笑顔` が s4/s5/s6/s7/s9/s10 の 6/10 = 60% で使用。>50% blocker 閾値超過。f_35/f_50/f_65/f_85/f_95 で同一 super_businessman.png（腕複数本のマルチタスク表現）が 6 segment 連続出現する。`考える 男性 困った` も s1/s2/s3/s8 の 4/10 = 40%（>33% warning 閾値超過）で、f_0/f_15 で同一 komaru 男性 PNG が連続。input.json notes に「P02 が super_businessman 側で 6 segment 連続で出る」を calibration として狙ったと記載があり、意図的構成だが rubric 上は明確に blocker。
- fix 1: illust_query を segment ごとに分散（「微笑む スーツ 男性」「リラックス サラリーマン」「考え事 男性」「気付き 男性」「ふと立ち止まる 男性」等）
- fix 2: 同一 PNG ファイルは最大 2 segment までという制約を generator に組み込む
- fix 3: irasutoya pool を事前に 8〜10 候補集めて segment 数だけ抽選する方式に切替
- patch: {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む リラックス"}
- patch: {"patch_type":"replace_illust","segment":"s5","new_query":"男性 気付き ひらめき"}
- patch: {"patch_type":"replace_illust","segment":"s6","new_query":"男性 話す 相談"}
- patch: {"patch_type":"replace_illust","segment":"s7","new_query":"男性 安心 落ち着き"}
- patch: {"patch_type":"replace_illust","segment":"s9","new_query":"男性 前向き 歩く"}
- patch: {"patch_type":"replace_illust","segment":"s10","new_query":"男性 納得 頷く"}

### P02/P03 illust ペルソナ過剰演出 (s4-s7, s9, s10)
- 観測: f_35/f_50/f_65/f_85/f_95 で super_businessman.png（腕 6 本、書類・電卓・鞄を多数持ったマルチタスク誇張表現）が「穏やかな気付き」局面 6 segment で連続使用される。voice_text は「生活リズムが整う」「相談できる人がいる」「働きながら自分に合う仕事を探したい人」等の落ち着いた共感型なのに、illust は明確に皮肉・誇張側に振れており方向性が真逆。視聴者は本気の共感ではなくネタとして受け取る。`illust_query` 自体が `穏やか 男性 笑顔` でこの素材を引いてしまっている事実は、検索辞書の歪みも示唆。P02（age/age-range 不一致）ではないが、P03（環境/責務 incongruent）が 6 segment 連続で blocker 寄り判定。
- fix 1: V08 patches で illust 自体を分散
- fix 2: contact_sheet で illust 候補を必ず目視確認
- fix 3: irasutoya pool に「穏やか系男性」素材を最低 6 候補事前用意
- patch: V08 と同じ replace_illust patches で対応

## Warning

### A01 loudnorm 範囲外 (全体, I=-25.4 LUFS)
- 観測: ffprobe_quality.json で I=-25.4 LUFS、acceptance_criteria の [-25, -21] LUFS 範囲を 0.4 LUFS 下回る。LRA=1.4 と非常に圧縮されている。
- fix 1: voice ミックス時に +2〜+3dB ゲイン適用
- fix 2: loudnorm filter の target_i を -23 にして再エンコード
- patch: {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}

### V04 字幕視認性 (s2/s4/s6/s8/s10, park 系全 segment)
- 観測: f_35/f_95 で曇天 playground 背景は中明度のため caption_main 下部は読めるが、白文字 + soft shadow のみで境界が弱い。f_15 (s2) も同様。s1/s3/s5/s7/s9 の station 背景（人混みで暗い）では十分視認可能だが、park 側 5 segment で警戒値。
- fix 1: park 系 segment に局所スクリム帯（caption 行のみ alpha 0.30 程度）追加
- fix 2: 全体 scrim alpha を 0.15 → 0.22 に上げる
- patch: {"patch_type":"set_field","path":"scenario.segments.1.scrim_alpha","value":0.25}
- patch: {"patch_type":"set_field","path":"scenario.segments.3.scrim_alpha","value":0.25}
- patch: {"patch_type":"set_field","path":"scenario.segments.5.scrim_alpha","value":0.25}
- patch: {"patch_type":"set_field","path":"scenario.segments.7.scrim_alpha","value":0.25}
- patch: {"patch_type":"set_field","path":"scenario.segments.9.scrim_alpha","value":0.25}

### V08w illust_query 二次重複 (考える 男性 困った, 4/10)
- 観測: `考える 男性 困った` が s1/s2/s3/s8 の 4/10 = 40% で >33% warning 閾値超過。f_0/f_15 で同一 komaru 男性 PNG。V08 blocker のセット項目として warning 計上。
- fix 1: V08 patches でも s1/s2/s3/s8 を個別 illust に分散すべき
- patch: {"patch_type":"replace_illust","segment":"s1","new_query":"男性 ふと立ち止まる 通勤"}
- patch: {"patch_type":"replace_illust","segment":"s2","new_query":"男性 考え事 歩く"}
- patch: {"patch_type":"replace_illust","segment":"s3","new_query":"男性 戸惑い 周囲の声"}
- patch: {"patch_type":"replace_illust","segment":"s8","new_query":"男性 正直 ため息"}

### T04 voice/caption 表記揺れ (s5)
- 観測: s5 voice `未経験から始められる` vs caption `未経験から始める`（活用形だけずれ、accent 影響軽微）。重大ではないが整える価値あり。
- fix 1: voice 側を caption 表記に寄せる
- patch: {"patch_type":"set_field","path":"scenario.segments.4.voice_text","value":"未経験から始める仕事も、意外と多いんだよね、調べてみると本当に。"}

## Info

### T03 sub_delay 動作確認 (resolved)
- 観測: 全 segment で sub_delay=2.5 設定。frame 抽出（t=0, 8.9, 20.7, 29.6, 38.5, 50.3, 56.3）から、bubble は s2 (f_15, t=8.9s, segment 内 t≈2.9s) で出現、s4 (f_35, t=20.7s, segment 内 t≈2.7s) で出現等、各 segment 内で 2.5s 以降の出現を確認。main caption と同時表示の violation 無し。
- 対応不要

### Q05 ファイルサイズ (測定値なし)
- 観測: 59.25s 長で 720x1280 / H264 / AAC の通常エンコード。size 記載は ffprobe_quality.json に無いが Q05 範囲（60MB）超は実用上ありえない。
- 対応不要

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s2","new_query":"japan kyoto temple path afternoon"},
  {"patch_type":"replace_bg","segment":"s3","new_query":"japan office building morning"},
  {"patch_type":"replace_bg","segment":"s4","new_query":"japan riverside walk afternoon"},
  {"patch_type":"replace_bg","segment":"s5","new_query":"japan commute walking morning"},
  {"patch_type":"replace_bg","segment":"s6","new_query":"japan office break afternoon"},
  {"patch_type":"replace_bg","segment":"s7","new_query":"japan cafe interior morning"},
  {"patch_type":"replace_bg","segment":"s8","new_query":"japan tokyo street afternoon"},
  {"patch_type":"replace_bg","segment":"s9","new_query":"japan crosswalk morning"},
  {"patch_type":"replace_bg","segment":"s10","new_query":"japan park bench autumn afternoon"},
  {"patch_type":"replace_illust","segment":"s1","new_query":"男性 ふと立ち止まる 通勤"},
  {"patch_type":"replace_illust","segment":"s2","new_query":"男性 考え事 歩く"},
  {"patch_type":"replace_illust","segment":"s3","new_query":"男性 戸惑い 周囲の声"},
  {"patch_type":"replace_illust","segment":"s4","new_query":"スーツ 男性 微笑む リラックス"},
  {"patch_type":"replace_illust","segment":"s5","new_query":"男性 気付き ひらめき"},
  {"patch_type":"replace_illust","segment":"s6","new_query":"男性 話す 相談"},
  {"patch_type":"replace_illust","segment":"s7","new_query":"男性 安心 落ち着き"},
  {"patch_type":"replace_illust","segment":"s8","new_query":"男性 正直 ため息"},
  {"patch_type":"replace_illust","segment":"s9","new_query":"男性 前向き 歩く"},
  {"patch_type":"replace_illust","segment":"s10","new_query":"男性 納得 頷く"},
  {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0},
  {"patch_type":"set_field","path":"scenario.segments.1.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.3.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.5.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.7.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.9.scrim_alpha","value":0.25},
  {"patch_type":"set_field","path":"scenario.segments.4.voice_text","value":"未経験から始める仕事も、意外と多いんだよね、調べてみると本当に。"}
]
```

## Calibration notes

- V07/V08 が新指標として初発火。bg fastcut（segment 内で同一 src の異なる time offset を 3 チャンク）は局所的な目線変化を作るが、bucket レベルの単調さ（50% / 60% の重複）は frame 抽出比較で簡単に検出可能で、視聴者の「同じ場所感」「同じ人物感」を解消できない。fastcut は補助、根本対策は query 分散
- V01 (s2/s4/s6/s8/s10 海外背景): `japan park afternoon` 系クエリは Pexels で米国 playground を返しやすいパターンが sample-test/sample-01-10s から継続再現。`japan` prefix 単体では不十分という運用知見が 3 サンプル連続で確定
- P02/P03 (super_businessman 6 segment 連続): input.json notes に意図的配置と記載があるが rubric 上は明確に過剰演出。illust pool 自体を多様化する設計変更が必要
- T03 sub_delay=2.5s は今回も正常動作、resolved 継続
