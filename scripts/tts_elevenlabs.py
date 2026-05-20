#!/usr/bin/env python3
"""ナレーション生成。ELEVENLABS_API_KEY が .env にあれば ElevenLabs、
無ければ macOS `say -v Otoya` にフォールバック。出力は mp3 (44.1kHz, mono)。

Usage: python3 tts_elevenlabs.py <text_file_or_inline> <output_mp3>
       python3 tts_elevenlabs.py --text "ナレーション本文" out.mp3
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# justification: ElevenLabs eleven_multilingual_v2 が日本語 Morioki voice を
# 安定して扱う。settings は v3 公式 doc の "neutral storytelling" 推奨値。
ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_STABILITY = 0.5
ELEVENLABS_SIMILARITY = 0.75


def load_env(env_path: Path) -> dict:
    """シンプルな .env パーサ。`key=value` のみ。"""
    out: dict = {}
    if not env_path.exists():
        return out
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def tts_say(text: str, out_path: Path) -> None:
    """macOS `say` で aiff → ffmpeg で mp3 化。"""
    aiff = out_path.with_suffix(".aiff")
    subprocess.run(
        ["say", "-v", "Otoya", "-r", "180", "-o", str(aiff), text],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "1",
         "-codec:a", "libmp3lame", "-b:a", "192k", str(out_path)],
        check=True, stderr=subprocess.DEVNULL,
    )
    aiff.unlink(missing_ok=True)


def tts_elevenlabs(text: str, out_path: Path, api_key: str, voice_id: str) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    body = json.dumps({
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": ELEVENLABS_STABILITY,
            "similarity_boost": ELEVENLABS_SIMILARITY,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out_path.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        # solve: ElevenLabs 失敗時は say にフォールバック、無音生成は避ける
        print(f"[tts] ElevenLabs HTTP {e.code}: {e.reason}, falling back to say",
              file=sys.stderr)
        tts_say(text, out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text_or_file", help="text content or path to .txt file")
    ap.add_argument("output_mp3")
    ap.add_argument("--text", action="store_true",
                    help="treat first arg as inline text instead of file path")
    ap.add_argument("--env", default=str(Path(__file__).parent.parent / ".env"))
    ap.add_argument("--force-say", action="store_true",
                    help="skip ElevenLabs even if API key is set")
    args = ap.parse_args()

    if args.text or not Path(args.text_or_file).exists():
        text = args.text_or_file
    else:
        text = Path(args.text_or_file).read_text(encoding="utf-8")

    out = Path(args.output_mp3)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = load_env(Path(args.env))
    api_key = env.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_API_KEY")
    voice_id = (env.get("ELEVENLABS_VOICE_ID")
                or os.environ.get("ELEVENLABS_VOICE_ID")
                or "8EkOjt4xTPGMclNlh1pk")

    if api_key and not args.force_say:
        print(f"[tts] using ElevenLabs voice {voice_id}", file=sys.stderr)
        tts_elevenlabs(text, out, api_key, voice_id)
    else:
        print("[tts] using macOS say -v Otoya (no API key)", file=sys.stderr)
        tts_say(text, out)

    size = out.stat().st_size
    print(json.dumps({"output": str(out), "size_bytes": size, "provider":
                      "elevenlabs" if (api_key and not args.force_say) else "say"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
