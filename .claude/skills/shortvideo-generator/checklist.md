# Generator Checklist

Copy this into your reply when starting Stage 0, tick as you progress.

```
shortvideo-generator: projects/<name>/
- [ ] Stage 0 lint exit 0
- [ ] Stage 1 bg videos fetched for all segments
- [ ] Stage 2 illusts fetched for all segments
- [ ] Stage 3 contact_sheet reviewed; contact_sheet_passed=true for all
- [ ] Stage 4 voice.mp3 generated, duration verified via ffprobe
- [ ] Stage 5 caption + bubble PNGs generated for all segments
- [ ] Stage 6 render_video.py exit 0, output.mp4 written
- [ ] Stage 7 ffprobe_quality.py exit 0 OR errors surfaced to user
```

If any box stays unticked after retry, escalate to the user with the specific stage and error message — do not silently proceed.
