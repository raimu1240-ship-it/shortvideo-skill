# Stock Footage Sources — 日本風景 bg 調達先

bg_query で Pexels が hit しない / 海外混入率が高い / 同じ素材を 2 段
重複させたくない場合に、以下の代替ソースを試す。全て商用利用 OK の
フリー素材ソース。著作権表示は acceptance_criteria.must_have に含めて
いないが、社員配布前に各サイトの最新利用規約を確認すること。

## ソース一覧 (優先順)

| 優先 | サイト | URL | API key | 縦動画 (9:16) | 日本ロケ素材数 | fetch script |
|---|---|---|---|---|---|---|
| 1 | **Pexels** | https://www.pexels.com/ja-jp/search/videos/japan/ | 不要 (HTML + WebFetch) | 中程度 (~10-20%) | 多い | `scripts/fetch_pexels_id.py` |
| 2 | **Mixkit** | https://mixkit.co/free-stock-video/japan/ | 不要 | 少ない (~5%) | 中程度 | `scripts/fetch_mixkit_id.py` |
| 3 | Pixabay | https://pixabay.com/ja/videos/search/japan/ | あり/不要両対応 | 中程度 | 中程度 | (未実装) |
| 4 | Coverr | https://coverr.co/s?q=japan | 不要 | 少ない | 少ない | (未実装) |

## Pexels 詳細

`references/pexels-curation.md` 参照。

- 検索 URL: `https://www.pexels.com/ja-jp/search/videos/<query>/`
- 直 mp4 URL pattern: `https://videos.pexels.com/video-files/<id>/<file>_<W>_<H>_<fps>fps.mp4`
- 抽出: `python3 scripts/fetch_pexels_id.py <video_id_1> <video_id_2> ... --json-list`
  - 内部で Cloudflare bypass headers + URL filter (`videos.pexels.com/video-files/<page_id>/...`) で 9:16 縦動画優先抽出
  - 動作確認済み: 8/8 成功

## Mixkit 詳細

Mixkit は **HTML 静的に直リンク埋め込み**なので urllib + 正規表現で抽出
容易 (Pexels の Cloudflare BOT 対策と違って気軽)。

- 検索 URL: `https://mixkit.co/free-stock-video/japan/`
- 個別動画ページ URL pattern: `https://mixkit.co/free-stock-video/<slug>-<id>/`
- 直 mp4 URL pattern: `https://assets.mixkit.co/videos/preview/<id>/<id>-1080-preview.mp4`
  (1080-preview = 1080p preview、4k-preview = 4K 版もあり)
- Pexels 補完用途: Pexels で hit しない niche query (例: 「japan
  countryside autumn」「japan ryokan interior」) で Mixkit のほうが質の高い
  日本ロケが取れることがある

fetch_mixkit_id.py 実装:
1. 検索ページ HTML → 個別 video page URL リスト (slug-id pattern)
2. 個別 page HTML → 直 mp4 URL (`assets.mixkit.co/videos/<id>/<id>-<height>.mp4`)
3. 720p を best として返す (Mixkit asset の通常 max)

仕様:
- query は space → hyphen 連結 (例: "tokyo street" → "tokyo-street")
- Mixkit ライブラリに該当カテゴリが無い query は 0 件で返る (例: "japan ryokan")
- video page の `<id>` 一致で関連動画 URL を除外

## 使い分け運用

- **デフォルト**: Pexels (`fetch_pexels_id.py` で安定 8/8 抽出済み)
- **Pexels で 0 件 hit** or **海外混入率が高い**: Mixkit を試す
- **niche / 高品質**: Pixabay / Coverr / Videvo を WebFetch で手動探索

## V09 グリッド検出観点との関連

V09 (irasutoya grid contact-sheet) と同じ「fetch 段の query 設計と
実 fetch 結果のズレ」が bg 側にも存在。Pexels で hit しない時に
Mixkit / Pixabay を順に試して fallback する責務は orchestrator
(`/shortvideo-loop`) に持たせる方が clean。fetch_pexels_id.py が
0 件返したら fetch_mixkit_id.py を試す chain は今後実装予定。
