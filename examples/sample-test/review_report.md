# Review Report — sample-test

## Summary
blocker=3 / warning=4 / info=1

## Blocker

### V01 海外背景 (s2, t=5.8-6.5s)
- 観測: s2 全域 (f_85 / f_95) の背景が欧米風 playground — カラフルな鋼鉄製遊具・青と赤の手すり・ウッドチップ地面・曇天と樹木で、米国/欧州の公園に見える。日本の標識・看板・建物の特徴がゼロ。`acceptance_criteria.must_have: japanese_bg_only` に違反。
- fix 1: bg_query を `japan park bench autumn` から `tokyo park bench morning` または `japan kyoto temple path` のように都市名 + 名詞限定にする
- fix 2: Pexels の contact_sheet 段階で目視チェックを必須化、海外ロケが混入したら別 video_id に差し替え
- fix 3: 「公園」より「日本らしさが映る場所」(神社境内・河川敷・住宅街の歩道) を選ぶ
- patch: {"patch_type":"replace_bg","segment":"s2","new_query":"tokyo park bench morning"}

### Q-dur 尺不足 (全体, 6.89s vs 10±0.5s)
- 観測: ffprobe_quality.json の errors にも `[Q-dur] duration 6.89s not within 10±0.5s` として記録。voice 合計 6.89s に対し input.json の segments.duration_sec は 5.0 + 5.0 = 10.0s。voice_duration_source=ffprobe で voice 実測に揃えた結果、segment.duration_sec の指定が無視され目標尺を 3s 以上下回った。`acceptance_criteria.duration_tolerance_sec=0.5` の明確な失格。
- fix 1: voice_text を伸ばす (各 voice_text に間や追加フレーズを足し、TTS 後の実測で 10s に近づける)
- fix 2: voice_duration_source を `segment` に切替えて segment.duration_sec を真値とし、無音 padding で 10s に伸ばす
- fix 3: duration_target_sec を 7s に下げて acceptance_criteria を実態に合わせる (この案件の試験用途なら現実的)
- patch: {"patch_type":"set_field","path":"voice_duration_source","value":"segment"}

### P02 ペルソナ不一致 (illust s2, t=5.8-6.5s) — 重度
- 観測: s2 の irasutoya が「複数の腕でノートPC・電卓・書類・電話・鉛筆を同時に扱うスーパービジネスマン」表現。input.json.persona.context=「新しい働き方への気付き」、voice_text=「自分のペースで、無理しない働き方を選んだ」、caption=「自分のペースが、いちばん続く」というメッセージと真逆 (過剰マルチタスク = 無理な働き方の象徴)。視聴者には皮肉や矛盾として読まれる。illust_query=`穏やか 男性 笑顔` に対する素材選定ミス。
- fix 1: illust_query を「スーツ 男性 微笑む」に変更し、単一人物・穏やか表情の素材に差し替え
- fix 2: 「コーヒー 男性 リラックス」「公園 散歩 男性」等、コンテキスト一致の素材を選ぶ
- patch: {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む"}

## Warning

### T03 sub_delay 未反映 (s1 / s2, t=0s / t=5.8s)
- 観測: f_0 (t=0s) 時点で bubble「ふと立ち止まった」と main caption「毎日同じ通勤、これでいいのかな。」が同時に画面に存在。input.json は `sub_delay: 2.5` を両 segment に指定しているが、bubble が main と同タイミング (delay < 1.5s) で出ている。s2 も同じく f_85 (segment 開始直後) で bubble と main が同時表示。
- fix 1: bubble を `sub_delay` 秒後にフェードインさせるレンダラー実装を確認
- fix 2: bubble の delay を 2.5s 維持、もしくは 1.5s に短縮しつつ実装側で遅延を効かせる
- patch: {"patch_type":"adjust_sub_delay","segment":"s1","new_delay":2.5}

### A01 loudnorm 下限を僅かに下回る (-25.37 LUFS)
- 観測: integrated loudness I=-25.37、acceptance_criteria.loudnorm_lufs_range=[-25, -21] の下限を 0.37 LUFS 下回る。ffprobe_quality.json でも warning として既知。視聴的には小音量寄りだが致命ではない。
- fix 1: TTS 出力後の loudnorm 2-pass で target I=-23 (range 中央) に再正規化
- fix 2: rendered output に対し `ffmpeg -af loudnorm=I=-23:TP=-1.5:LRA=11` をかけ直す
- patch: {"patch_type":"set_field","path":"audio_post.loudnorm_target_I","value":-23}

### V02 irasutoya がフレーム内 caption に重なる (s1, t=0-5s)
- 観測: f_0/f_15/f_35/f_50/f_65 で salaryman illust の右腕・ノートPC部分が caption「毎日同じ通勤、」のベースラインに重なる。caption は illust の上に乗っているため可読性は保たれているが、illust の輪郭線が caption 周辺で視覚ノイズになっている。V02 (caption が動画領域に侵食) よりは Z-order 干渉に近いので warning。
- fix 1: illust の anchor 位置を中央やや上 (現状の中央下) に上げ、caption とのオーバーラップを減らす
- fix 2: caption の y 位置を下に 60px ずらす (letterbox 帯のすぐ上に着地)
- patch: {"patch_type":"set_field","path":"layout.caption_y_offset_px","value":60}

### P01 / P03 illust s2 のペルソナ不一致 (二次)
- 観測: P02 ですでに blocker として上げているが、加えて P01 (gender) は男性で input と一致 / P03 (環境) は「マルチタスク・オフィス系小物多数」で park bench context と不一致。P02 が解消されれば P01/P03 もまとめて解消する想定。
- fix: P02 と同じ patch で吸収
- patch: (P02 と重複のため省略)

## Info

### Q05 ファイル尺と loudnorm の関係
- 観測: 尺 6.89s で file size は妥当範囲。Q05 (60MB 超) には該当しない。Q01-Q04 (av_drift / fps / banding / pix_fmt) も全てクリア。
- 対応不要

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s2","new_query":"tokyo park bench morning"},
  {"patch_type":"set_field","path":"voice_duration_source","value":"segment"},
  {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む"},
  {"patch_type":"adjust_sub_delay","segment":"s1","new_delay":2.5},
  {"patch_type":"adjust_sub_delay","segment":"s2","new_delay":2.5},
  {"patch_type":"set_field","path":"audio_post.loudnorm_target_I","value":-23},
  {"patch_type":"set_field","path":"layout.caption_y_offset_px","value":60}
]
```
