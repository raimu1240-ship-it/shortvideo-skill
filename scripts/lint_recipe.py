#!/usr/bin/env python3
"""input.json の罠 9 件 + acceptance_criteria 違反を pre-check する。
Stage 0 で必ず通す mechanical gate。

Usage: python3 lint_recipe.py <input.json>
Exit: 0 = clean / 1 = error / 2 = warning only
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# justification: brand-name案件で観測した字数閾値。
# 8 字超え = 視認性低下 warn / 12 字超え = 1080x1920 で letterbox はみ出し error
CAPTION_WARN_CHARS = 8
CAPTION_ERROR_CHARS = 12

# justification: サブテロップ即時表示は視聴者が読み切ってスクロール → 公式罠 4
SUB_DELAY_MIN_SEC = 1.5

# PR 色 ng 文言パターン (caption に含まれていたら error)
PR_NG_KEYWORDS = [
    "PR｜", "PR|",   # PR バッジ風 prefix
    "ご検討ください", "お試しください", "ぜひ", "おすすめ", "詳しくはこちら",
    "資料請求", "今すぐ", "無料相談",
]

# japanese_bg_only を要求するときの NG ヒント
OVERSEAS_QUERY_HINTS = ["new york", "los angeles", "paris", "london", "berlin"]

# T06 voice-caption sync 閾値
# justification: 句読点・活用差で 100% は望めないが、文字集合 overlap 60% を
# 下回ると視聴者の耳と目で別物に聞こえる。30% 未満は明確な失敗。
VOICE_CAPTION_OVERLAP_WARN = 0.60
VOICE_CAPTION_OVERLAP_ERROR = 0.30
SYNC_IGNORE_CHARS = set("、。 ,.!?！？\n\r\t「」『』()（）")


def voice_caption_overlap(voice: str, caption: str) -> float:
    """文字集合 Jaccard で voice と caption の意味一致率を概算する。
    句読点等のノイズは除外。caption が voice の subset に近いほど 1.0。"""
    v = set(voice) - SYNC_IGNORE_CHARS
    c = set(caption) - SYNC_IGNORE_CHARS
    if not v or not c:
        return 0.0
    inter = v & c
    union = v | c
    return len(inter) / len(union)


def check(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    ac = data.get("acceptance_criteria", {})
    must_have = set(ac.get("must_have", []))
    must_not_have = set(ac.get("must_not_have", []))

    # 1. PR バッジ勝手追加 (must_not_have 違反)
    if "pr_badge" in must_not_have and data.get("pr_badge"):
        errors.append("[1] pr_badge present but must_not_have lists it")
    if "bgm" in must_not_have and data.get("bgm"):
        errors.append("[1b] bgm present but must_not_have lists it")
    if "logo_persistent_overlay" in must_not_have and data.get("logo_overlay"):
        errors.append("[1c] logo_overlay present but must_not_have lists it")

    # 2. Y 座標 (Y_TABLE 範囲外指定があれば error。今は schema 側で吸収するため skip)
    res = data.get("resolution")
    if res not in {"720x1280", "1080x1920"}:
        errors.append(f"[2] unsupported resolution {res}")

    # 3 / 5. caption 字数
    for seg in data.get("scenario", {}).get("segments", []):
        cap = seg.get("caption_main")
        lines = cap if isinstance(cap, list) else [cap] if cap else []
        for line in lines:
            n = len(line)
            if n > CAPTION_ERROR_CHARS:
                errors.append(f"[3] caption line too long ({n} chars) in {seg['id']}: {line!r}")
            elif n > CAPTION_WARN_CHARS:
                warns.append(f"[3w] caption line {n} chars (>8) in {seg['id']}: {line!r}")
            for kw in PR_NG_KEYWORDS:
                if kw in line:
                    errors.append(f"[T02] PR-tone keyword {kw!r} in {seg['id']} caption: {line!r}")

    # 4. sub_delay
    for seg in data.get("scenario", {}).get("segments", []):
        sd = seg.get("sub_delay")
        if seg.get("caption_sub") and (sd is None or sd < SUB_DELAY_MIN_SEC):
            warns.append(f"[4] sub_delay={sd} < {SUB_DELAY_MIN_SEC} in {seg['id']}")

    # 5. voice duration source = ffprobe required
    if data.get("voice_duration_source") and data["voice_duration_source"] != "ffprobe":
        errors.append("[5] voice_duration_source must be 'ffprobe', not whisper-end")

    # 7. voice text vs caption 表記差 (漢字優先 diff)
    for seg in data.get("scenario", {}).get("segments", []):
        v = seg.get("voice_text") or ""
        cs = seg.get("caption_main")
        c = "".join(cs) if isinstance(cs, list) else (cs or "")
        # 簡易: 一方にしかない漢字がもう一方にひらがなで存在しないか
        # ここでは ascii-only check で十分なエラー検出は別途
        if v and c:
            v_kana = sum(1 for ch in v if "぀" <= ch <= "ゟ")
            c_kanji = sum(1 for ch in c if "一" <= ch <= "鿿")
            v_kanji = sum(1 for ch in v if "一" <= ch <= "鿿")
            if c_kanji > 0 and v_kanji == 0 and v_kana > 4:
                warns.append(f"[7] voice all-kana but caption has kanji in {seg['id']} "
                             f"(accent risk)")

    # 8. japanese_bg_only に違反していないか query 文字列で簡易ヒント検出
    if "japanese_bg_only" in must_have:
        for seg in data.get("scenario", {}).get("segments", []):
            q = (seg.get("bg_query") or "").lower()
            for h in OVERSEAS_QUERY_HINTS:
                if h in q:
                    errors.append(f"[8] japanese_bg_only required but query hints overseas: "
                                  f"{seg['id']} -> {q!r}")
            # contact_sheet_passed フラグ
            if seg.get("contact_sheet_passed") is False:
                errors.append(f"[8b] contact_sheet not passed for {seg['id']} (overseas suspicion)")

    # 9. CTA 重複: overlay label と caption の文字列重複検出 (label が caption に含まれる)
    for seg in data.get("scenario", {}).get("segments", []):
        label = seg.get("overlay_label")
        cs = seg.get("caption_main")
        c = "".join(cs) if isinstance(cs, list) else (cs or "")
        if label and c and label in c:
            warns.append(f"[9] overlay label {label!r} duplicated in caption in {seg['id']}")

    # V09. illust_query が grid-likely query かどうかの先制 warn
    # justification: Phase 4.B.1 round_2 で「考える 男性」query が
    # 「グラフといろいろな表情の男性」grid PNG を返した実観測あり。
    # fetch_irasutoya_id.py の pick_best が grid を deprioritize するが、
    # query 自体が grid を誘発する語の場合は planner 段で書き換えるべき。
    V09_GRID_HINT_WORDS = ("いろいろ", "色々", "セット", "一覧", "種類", "5段階", "表情")
    for seg in data.get("scenario", {}).get("segments", []):
        iq = seg.get("illust_query", "") or ""
        if any(w in iq for w in V09_GRID_HINT_WORDS):
            warns.append(f"[V09w] illust_query {iq!r} in {seg['id']} contains a grid-hint "
                         f"word — irasutoya may return a multi-character contact sheet")

    # V07/V08. bg_query / illust_query 使い回しチェック
    # justification: 本番納品では同じ素材を複数 segment で使うと「手抜き感」
    # が出る。4 segments 以上で評価、同一素材が半数超なら error、3 分の 1 超なら warn。
    segs = data.get("scenario", {}).get("segments", [])
    if len(segs) >= 4:
        for field, vid in [("bg_query", "V07"), ("illust_query", "V08")]:
            counter = Counter(s.get(field, "") for s in segs if s.get(field))
            if not counter:
                continue
            top_val, top_count = counter.most_common(1)[0]
            ratio = top_count / len(segs)
            if ratio >= 0.50:
                errors.append(f"[{vid}] {field} {top_val!r} used in "
                              f"{top_count}/{len(segs)} segments ({ratio:.0%}) "
                              f"— same asset reused too much")
            elif ratio > 0.34:
                warns.append(f"[{vid}w] {field} {top_val!r} in "
                             f"{top_count}/{len(segs)} segments ({ratio:.0%}) "
                             f"— consider diversifying")

    # T06. voice-caption sync: voice_text と caption_main が意味的に揃っているか
    for seg in data.get("scenario", {}).get("segments", []):
        voice = seg.get("voice_text", "") or ""
        cs = seg.get("caption_main")
        cap = "".join(cs) if isinstance(cs, list) else (cs or "")
        if cap and not voice:
            errors.append(f"[T06] caption_main present but voice_text empty in {seg['id']} "
                          f"— viewer hears nothing while reading text")
            continue
        if voice and not cap:
            warns.append(f"[T06w] voice_text present but caption_main empty in {seg['id']} "
                         f"— spoken line has no on-screen anchor")
            continue
        if voice and cap:
            ratio = voice_caption_overlap(voice, cap)
            if ratio < VOICE_CAPTION_OVERLAP_ERROR:
                errors.append(f"[T06] voice/caption character overlap {ratio:.2f} "
                              f"< {VOICE_CAPTION_OVERLAP_ERROR} in {seg['id']} "
                              f"— voice and caption likely say different things")
            elif ratio < VOICE_CAPTION_OVERLAP_WARN:
                warns.append(f"[T06w] voice/caption overlap {ratio:.2f} "
                             f"< {VOICE_CAPTION_OVERLAP_WARN} in {seg['id']} "
                             f"— check if narration matches on-screen text")

    return errors, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--json", action="store_true",
                    help="output JSON report instead of human text")
    args = ap.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    errors, warns = check(data)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warns,
                          "input": args.input_json}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print(f"ERROR  {e}")
        for w in warns:
            print(f"WARN   {w}")
        if not errors and not warns:
            print("OK: lint clean")

    if errors:
        return 1
    if warns:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
