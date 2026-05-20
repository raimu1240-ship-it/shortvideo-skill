# Review Report — sample-01-10s

This report is a **few-shot calibration example** for the `shortvideo-reviewer` agent. It mirrors the format the reviewer must emit and shows what severity level (blocker / warning / info) maps to which observation.

## Summary
blocker=1 / warning=2 / info=1

## Blocker

### V01 海外背景 (s2, t=7s)
- 観測: s2 の背景に欧米風 playground 遊具 (鉄製カラフル) と曇天の芝生エリアが映る。日本ロケに見えない。Pexels の "公園" 検索が米国 playground を返したものを未選別で採用してしまった。
- fix 1: bg_query を `japan park bench` に絞る (`japan` prefix + 都市名 or `bench` 等の名詞限定)
- fix 2: Pexels 個別ページ巡回時に contact_sheet で目視チェックする stage を必ず通す
- fix 3: 別 Pexels video_id (例 `34990547` 等の日本ロケ候補) に差し替え
- patch: {"patch_type":"replace_bg","segment":"s2","new_query":"japan kyoto temple path"}

## Warning

### P01 / P03 illust ペルソナ不一致 (s2, t=5-10s)
- 観測: s2 の irasutoya 素材 `super_businessman.png` は腕が複数本ある「マルチタスク」表現で、共感型ペルソナ (30歳・派遣業務での気付き) と方向性が一致しない。視聴者は皮肉や誇張に感じる可能性がある。
- fix 1: 「いろいろな表情のスーツを着た人 (悩む顔)」のような表情ベースの素材に差し替え
- fix 2: scene の責務 (締めの気付き) に合うのは「微笑む / 落ち着いた表情」の単一人物素材
- patch: {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む"}

### T03 sub_delay 未活用 (全シーン)
- 観測: caption_sub が input.json に定義されていない (sub caption 無し構成)。Phase 0 では許容範囲だが、補足情報を時間差で出す本来の演出効果が得られていない。
- fix 1: 各シーンに 1 行サブを追加 + `sub_delay: 2.5` を設定
- fix 2: Phase 1 で `sub_delay` を必須化するか検討
- patch: {"patch_type":"set_field","path":"scenario.segments.0.sub_delay","value":2.5}

## Info

### Q05 ファイルサイズ過小 (4.4MB, 10s)
- 観測: ファイルサイズが想定下限 (10s × 1Mbps ≒ 1.25MB) を大きく上回るが、Pillow stroke / 黒シャドー処理が動画コーデックに与える影響内。問題ではない。
- 対応不要

## Patches (JSON array)

```json
[
  {"patch_type":"replace_bg","segment":"s2","new_query":"japan kyoto temple path"},
  {"patch_type":"replace_illust","segment":"s2","new_query":"スーツ 男性 微笑む"},
  {"patch_type":"set_field","path":"scenario.segments.0.sub_delay","value":2.5}
]
```

## Calibration notes (for future reviewers)

- `V01` (overseas background) is **always blocker** when `must_have` includes `japanese_bg_only`. Even if the scene looks generic / nature-like, anything that could be misread as overseas (Western signage, foreign-style infrastructure, non-Japanese people) is blocker.
- Persona mismatch is **warning** when the illust is jarring but the message still reads, **blocker** only when gender / age is clearly wrong for the narrative voice.
- File size, codec choice, and other purely technical details are **info** unless they violate acceptance_criteria explicitly.
- This 10s example has no narration. Real production with narration must additionally check A01-A04.
