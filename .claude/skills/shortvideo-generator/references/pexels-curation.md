# Pexels Curation — Japan-only 背景動画調達

Pexels には API key 経由と HTML 経由の 2 通り。本スキルは **API key 不要の HTML 経由** に統一する (Claude の WebFetch + Python urllib で完結)。

## Contents
- 検索クエリの組み立て
- mp4 直リンクの抽出
- 海外混入の典型パターン
- Vision pass で弾く

## 検索クエリの組み立て

- 必ず prefix に `japan` をつける (`"japan"` 単独でも有効、英語のみ受け付ける)
- 都市名を足すと混入率が下がる: `japan tokyo`, `japan kyoto`, `japan osaka`
- 「park」「station」「street」など generic 名詞は海外混入率が高い、`japan + 都市 + 名詞` が安全
- 季節タグも効果あり: `japan autumn`, `japan winter morning`

検索 URL のテンプレ: `https://www.pexels.com/ja-jp/search/videos/<URLエンコード済みquery>/`

## mp4 直リンクの抽出

1. 検索結果ページを WebFetch → 動画 ID リスト取得 (パス `/ja-jp/video/<id>/`)
2. 各動画ページを WebFetch → 直リンクは `videos.pexels.com/video-files/<id>/<filename>_<W>_<H>_<fps>fps.mp4` 形式
3. 9:16 縦動画 (例 `1080_1920_30fps.mp4`) を優先、無ければ横長を後段で crop

## 海外混入の典型パターン (代表 NG)

- 米国 playground (カラフルな鉄製遊具)、欧州街並 (石畳・看板)
- 動物園・観光地的な過剰演出
- 外国人 / 欧米的服装の歩行者
- 海外運動会・スタジアム

## Vision pass で弾く

`scripts/contact_sheet.py` で 4xN tile を作り、Claude が Read で目視チェック → segment ごとに `contact_sheet_passed: true/false` を input.json に書き戻す。false が 1 つでも残っていたら Stage 6 へ進めない (lint で error)。
