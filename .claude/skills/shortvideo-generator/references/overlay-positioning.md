# Overlay Positioning

解像度別の Y 座標テーブル。`scripts/make_captions.py` が自動参照。手書き input.json でカスタム値を入れることは原則禁止。

## Contents
- 720x1280
- 1080x1920
- illust の中央配置 Y
- bubble の Y (illust の下、cap_main の上)

## 720x1280

| 要素 | Y top | サイズ | フォント |
|---|---|---|---|
| illust 中央寄せ | 480 | 幅 400px | (画像、フォント無関係) |
| bubble | 820 中心 | 高さ 60-80px | bold 28-32px |
| cap_main | 1010 開始 | line height 70px | bold 52px |
| cap_sub | 1170 開始 | line height 58px | bold 44px |

letterbox 上下黒帯: 0-120 / 1180-1280

## 1080x1920

| 要素 | Y top | サイズ | フォント |
|---|---|---|---|
| illust 中央寄せ | 700 | 幅 600px | (画像) |
| bubble | 1180 中心 | 高さ 80-110px | bold 40-48px |
| cap_main | 1430 開始 | line height 105px | bold 78px |
| cap_sub | 1660 開始 | line height 88px | bold 66px |

letterbox 上下黒帯: 0-180 / 1740-1920

## illust の中央配置

- 横位置は `(W - illust_width) // 2` で常に水平中央
- 縦位置は上記表の "illust 中央寄せ" Y を top に設定
- illust 自体の伸縮は `target_w` を指定して `Image.LANCZOS` で resize

## bubble の Y

bubble の `y_center` は `cap_main の y_top - 120` (720x1280) / `cap_main の y_top - 250` (1080x1920) を目安に、illust 下端とぶつからない位置に配置。

## カスタム値が許される例外

なし。Phase 3 で新解像度 (1080x1350 など) を追加するときに、このファイルの表に追記する形で対応する。フリースタイルでの Y 指定は lint_recipe.py [2] error で弾く。
