# Irasutoya Feed Howto

いらすとや の素材検索は内部検索が貧弱なため Blogger 標準の Atom feed (JSON 形式) を使う。WebFetch のみで完結、curl 不要。

## Contents
- Feed エンドポイント
- 個別記事から PNG URL 抽出
- 商用利用の前提
- query テクニック

## Feed エンドポイント

```
https://www.irasutoya.com/feeds/posts/default?q=<URLエンコード済みquery>&max-results=8&alt=json
```

- `q` は日本語 OK (URL エンコード必須)
- `max-results` 上限 25
- `alt=json` で JSON 応答

JSON の `feed.entry[].link[].href` に個別記事 URL が入る (rel=alternate)。

## 個別記事から PNG URL 抽出

各記事ページを WebFetch:

```
https://www.irasutoya.com/YYYY/MM/blog-post*.html
```

中の `<img>` タグから `blogger.googleusercontent.com/img/.../s800/<filename>.png` を抽出。s800 が標準サイズ、より大きいときは s1200, s1600 も可。

## 商用利用の前提

- 個人・商用とも無料、ただし 1 デザインで 21 点以上の素材使用は有料 → 1 動画あたり 1-3 点が安全
- ブランド系・成人向けには使用しない
- 「いらすとや」のクレジット表記は不要 (規約準拠)

## Query テクニック

- 表情指定: 「困った」「悩む」「考える」「驚いた」
- 職業指定: 「サラリーマン」「会社員」「主婦」
- 状況指定: 「パソコン」「会議」「電話」「散歩」
- 動詞より名詞ベースの方がヒット率が高い

例: `困った サラリーマン パソコン` → `kaisya_komaru_man.png` 等
