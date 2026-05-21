# Review Report — sample-02-60s-round3

## Summary
blocker=0 / warning=3 / info=2

## Warning

### V01 borderline / P03 環境ミスマッチ (s10, t≈53s, frame f_95)
- 観測: f_95 (s10) の背景が「山岳の稜線 + 海が遠景に見える」屋久島/離島系の山頂風景。input.json の bg_query は round_3 patch で `japan park bench afternoon` に書き換え済みだが、Pexels から取得された bg_s10.mp4 は round_2 と同じ山岳素材 (P03 で指摘した動画) と推定される。
- 日本の山岳である可能性は高く `japanese_bg_only` への blocker 違反とまでは断定できないため warning に留める。ただし persona「働き方を見直して気付いた 32 歳男性」の締めとしては抽象度が高く、生活圏のビジュアル (公園・カフェ・住宅街) からは乖離している。
- fix 1: fetch_pexels_id.py 側で bg_query patch 後に asset cache を invalidate して再取得を強制する
- fix 2: bg_query を `tokyo park afternoon` / `japan suburb park` に変えて Pexels の検索結果集合を変える
- fix 3: bg_video_id を input.json に固定して再現性を確保する (round_2 fix 3 と同じ)
- patch: {"patch_type":"replace_bg","segment":"s10","new_query":"tokyo park bench afternoon"}

### V01 borderline / bg fallback 残存 (s6, t≈28-30s, frame f_50)
- 観測: f_50 (s6) の背景が依然として「ほぼ単色のダークブルー (空) + 下部に都市スカイラインのシルエット」。round_2 では s6 が完全な青単色フォールバックで blocker 扱いだったが、round_3 では下部にビル群が見えるところまで回復。bg_query は patch で `japan office desk afternoon` に変更されているはずだが、取得された bg_s6.mp4 は md5 で bg_s3.mp4 と一致 (`d3ca09…`)、つまり s3 と同じ素材を流用している。
- 日本の都市である痕跡 (スカイライン) はあるため blocker までは至らず、warning に留める。ただし「office desk afternoon」とは別物のスカイショットで、cache 流用または fetcher の重複返却が疑われる。
- fix 1: fetch_pexels_id.py に「同一プロジェクト内で同じ video_id を返さない」dedup フィルタを追加
- fix 2: s6 の bg_query をより固有な語に絞る (例: `tokyo office interior afternoon`)
- patch: {"patch_type":"replace_bg","segment":"s6","new_query":"tokyo office interior afternoon"}

### A01 loudnorm I=-25.34 LUFS (全体, t=0-56s)
- 観測: ffprobe_quality.json で `loudnorm_I=-25.34`、acceptance_criteria.loudnorm_lufs_range=[-25,-21] の下限を 0.34 LUFS 下回る。round_2 から数値が変わらず未対応。
- fix 1: ffmpeg loudnorm の二段パスで `i=-23` 固定で再エンコード
- fix 2: voice TTS の出力レベルを +2dB シフト
- patch: {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}

## Info

### V07 bg 重複は閾値以内 (10 seg, 8 unique bg)
- 観測: bg asset の md5 一致を確認すると 10 seg で 8 unique (s1=s5 同一、s3=s6 同一)。最大単一 bg=2/10=20%、warning 閾値 33% 未満で V07 PASS。ただし s1 と s5 は別 query (`japan train station morning` vs `japan commute walking morning`) なので、fetcher の cache キーが query 単位になっていない可能性がある。
- 対応: 上記 s6 と同じ dedup フィルタで吸収可能。今回は patch 不要。

### V09 illust grid PASS (round_2 V-NEW 完全解消)
- 観測: f_0 (s1) / f_15 (s2) / f_35 (s4) を含む 7 frame 全てで illust は単一人物表示。round_2 で blocker だった contact-sheet grid (4x3 表情シート、2x2 円グラフ+男性) は再現せず、Phase 4.D.1 の fetch_irasutoya_id.py grid filter + reviewer rubric V09 追加が機能している。
- illust md5 確認で 10/10 unique (V08 PASS)。s1=ニキビ顔少年, s2=ニキビ顔男性, s4=メガホン男性, s5=面談 2 人, s6=対面相談 2 人, s7=胸に手を当てる男性, s8=汗だくサラリーマン, s9=横顔歩く男性, s10=OK サイン男性。
- 対応: 不要 (V09 を round_3 で実機 PASS 確認、anchor として examples/ に保存検討)。

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s10","new_query":"tokyo park bench afternoon"},
  {"patch_type":"replace_bg","segment":"s6","new_query":"tokyo office interior afternoon"},
  {"patch_type":"set_field","path":"acceptance_criteria.loudnorm_target_i","value":-23.0}
]
```
