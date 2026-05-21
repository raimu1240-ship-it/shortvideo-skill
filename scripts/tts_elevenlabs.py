#!/usr/bin/env python3
"""ナレーション生成。ELEVENLABS_API_KEY が .env にあれば ElevenLabs、
無ければ OS 内蔵 TTS にフォールバック。出力は mp3 (44.1kHz, mono)。

OS 内蔵 TTS のフォールバック先:
  - macOS  : say -v Otoya
  - Windows: PowerShell の System.Speech.Synthesizer (Microsoft Haruka 等)
  - Linux  : 対応無し (ElevenLabs API キー必須)

Usage: python3 tts_elevenlabs.py <text_file_or_inline> <output_mp3>
       python3 tts_elevenlabs.py --text "ナレーション本文" out.mp3
"""
import argparse
import json
import os
import platform
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
    """OS 内蔵 TTS にフォールバック。

    macOS : `say -v Otoya` で aiff → ffmpeg で mp3 化
    Windows: PowerShell の System.Speech.Synthesizer で wav → ffmpeg で mp3 化
    Linux  : 対応無し (RuntimeError)
    """
    sys_name = platform.system()

    if sys_name == "Darwin":
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
        return

    if sys_name == "Windows":
        wav = out_path.with_suffix(".wav")
        # PowerShell の System.Speech.Synthesizer で wav 生成。
        # text は JSON エスケープして PowerShell の文字列リテラルに渡す
        # (改行・引用符が混じっても安全)。
        text_lit = json.dumps(text, ensure_ascii=False)
        wav_lit = str(wav).replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$s.SetOutputToWaveFile('{wav_lit}');"
            f"$s.Speak({text_lit});"
            "$s.Dispose()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav), "-ar", "44100", "-ac", "1",
             "-codec:a", "libmp3lame", "-b:a", "192k", str(out_path)],
            check=True, stderr=subprocess.DEVNULL,
        )
        wav.unlink(missing_ok=True)
        return

    raise RuntimeError(
        f"OS 内蔵 TTS は {sys_name} 非対応。.env に ELEVENLABS_API_KEY を設定してください。"
    )


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


def _ffprobe_dur(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def _resolve_tts(api_key: str | None, force_say: bool):
    """Returns (tts_fn(text, path), provider_label)."""
    if api_key and not force_say:
        voice_id = (os.environ.get("ELEVENLABS_VOICE_ID")
                    or "8EkOjt4xTPGMclNlh1pk")
        def _fn(text, path):
            tts_elevenlabs(text, path, api_key, voice_id)
        return _fn, "elevenlabs"
    return (lambda text, path: tts_say(text, path)), "say"


def main_per_segment(input_json: Path, out_dir: Path, env_path: Path,
                     force_say: bool) -> int:
    """input.json の各 segment.voice_text を別 mp3 にして出力、各 voice
    の実測 duration を <out_dir>/durations.json にまとめる。renderer が
    これを読んで segment.duration_sec を上書きする。"""
    data = json.loads(input_json.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    env = load_env(env_path)
    api_key = env.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_API_KEY")
    tts_fn, provider = _resolve_tts(api_key, force_say)
    print(f"[tts per-segment] provider={provider}", file=sys.stderr)

    durations: dict[str, float] = {}
    for seg in data.get("scenario", {}).get("segments", []):
        sid = seg["id"]
        text = seg.get("voice_text", "")
        if not text:
            print(f"[tts per-segment] skip {sid}: empty voice_text",
                  file=sys.stderr)
            continue
        out_mp3 = out_dir / f"voice_{sid}.mp3"
        tts_fn(text, out_mp3)
        durations[sid] = _ffprobe_dur(out_mp3)
        print(f"[tts per-segment] {sid}: {durations[sid]:.2f}s -> {out_mp3.name}",
              file=sys.stderr)

    dur_json = out_dir / "durations.json"
    dur_json.write_text(json.dumps(durations, ensure_ascii=False, indent=2))
    print(json.dumps({"durations_json": str(dur_json),
                      "segments": len(durations),
                      "total_sec": sum(durations.values()),
                      "provider": provider}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text_or_file", nargs="?",
                    help="text content or path to .txt file (single mode)")
    ap.add_argument("output_mp3", nargs="?",
                    help="output mp3 path (single mode)")
    ap.add_argument("--text", action="store_true",
                    help="treat first arg as inline text instead of file path")
    ap.add_argument("--env", default=str(Path(__file__).parent.parent / ".env"))
    ap.add_argument("--force-say", action="store_true",
                    help="skip ElevenLabs even if API key is set")
    # per-segment mode
    ap.add_argument("--per-segment", action="store_true",
                    help="read input.json and emit voice_<sid>.mp3 per segment")
    ap.add_argument("--input-json",
                    help="input.json path (required with --per-segment)")
    ap.add_argument("--out-dir",
                    help="output directory for voice_<sid>.mp3 + durations.json "
                         "(required with --per-segment)")
    args = ap.parse_args()

    if args.per_segment:
        if not args.input_json or not args.out_dir:
            print("[tts] --per-segment requires --input-json and --out-dir",
                  file=sys.stderr)
            return 1
        return main_per_segment(Path(args.input_json), Path(args.out_dir),
                                Path(args.env), args.force_say)

    # single-mode (legacy)
    if not args.text_or_file or not args.output_mp3:
        print("[tts] single mode needs text_or_file + output_mp3", file=sys.stderr)
        return 1
    if args.text or not Path(args.text_or_file).exists():
        text = args.text_or_file
    else:
        text = Path(args.text_or_file).read_text(encoding="utf-8")

    out = Path(args.output_mp3)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = load_env(Path(args.env))
    api_key = env.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_API_KEY")
    tts_fn, provider = _resolve_tts(api_key, args.force_say)
    print(f"[tts] using {provider}", file=sys.stderr)
    tts_fn(text, out)

    size = out.stat().st_size
    print(json.dumps({"output": str(out), "size_bytes": size,
                      "provider": provider}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
