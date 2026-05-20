# Recipe — Empathy-First Vertical Video

## Contents
- Spec summary (resolution, fps, codec, audio)
- Stage 1-7 flow
- ffmpeg filter pattern fragments
- Known constraints (Homebrew ffmpeg 8.1 lacks drawtext)
- Determinism rules

## Spec summary

| Field | Value |
|---|---|
| Resolution | 720x1280 or 1080x1920 (9:16) |
| FPS | 24 (default) or 30 |
| Video codec | libx264, crf 23, preset medium, pix_fmt yuv420p |
| Audio | AAC 192k, 1 track (narration only, no BGM) |
| Duration | 10-60s typical |

## Stage flow

1. **lint** input.json (scripts/lint_recipe.py)
2. **fetch** bg videos (Pexels via WebFetch + urllib)
3. **fetch** irasutoya PNG inserts
4. **contact_sheet** Vision pass (overseas exclusion)
5. **narration** TTS (say or ElevenLabs auto)
6. **captions** PNG (Pillow, no drawtext)
7. **render** ffmpeg 1-pass (scripts/render_video.py)
8. **probe** ffmpeg/ffprobe quality (scripts/ffprobe_quality.py)

## ffmpeg fragments (for scripts only, do not hand-run)

- Resize landscape to 9:16 cropped: `scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}`
- Darkening for caption legibility: `color=c=black@0.35:s={w}x{h}:d={dur}`
- Caption overlay (Pillow PNG): `[v][cap]overlay=0:0`
- Voice mux with shortest end: `-map 0:v -map 1:a -shortest`

## Known constraints

- **Homebrew ffmpeg 8.1 has no drawtext / subtitles filter**: text must be pre-rendered to transparent PNGs via Pillow, then `overlay`-ed. The scripts/make_captions.py already handles this.
- **Mac fonts may not match WSL fonts**: `fc-match` cache is generated per-host on first run. Different hosts produce visually similar but byte-different captions; md5sum determinism therefore holds per-host, not cross-host.

## Determinism rules

- All randomness through `seed` in input.json (passed to Pillow / asset selection)
- ffmpeg flags fixed to `crf 23 / preset medium / pix_fmt yuv420p`
- Same input.json + same fonts cached → same md5sum of output.mp4
- Fonts are resolved once at Stage 5; the resolved path is persisted in `work/font_path.txt`

## When to re-run from which stage

| Change in input.json | Re-run from |
|---|---|
| voice_text only | Stage 4 (narration) |
| caption_main only | Stage 5 (captions) |
| bg_query | Stage 1 (fetch) |
| sub_delay / overlay layout | Stage 5 + Stage 6 |
| resolution / fps | Stage 1 (everything) |

Cache directories under `work/cache/<segment_hash>/` ensure unchanged segments skip re-fetch.
