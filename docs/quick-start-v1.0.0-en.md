# Cutting Edge v2 — Quick start (5 minutes)

1. **Launch** the app. Wait for the green dot in the status bar (local core connected).
2. **Import clips** — drag 10 clips onto the Media panel (MP4/MOV/MKV, H.264 or HEVC).
3. **Pick the reference** — click the ★ on the reference video's card. A 15–45 s edit with
   clean cuts works best.
4. **Check compatibility** — the wizard warns you if the footage is too short or the aspect
   ratio differs; a red *block* means "add more clips".
5. **Build the EDL** — the wizard extracts the editing DNA (cut lengths, shot mix, camera
   motion, colour, beat grid) and lays your peak moments on that rhythm.
6. **Post-production** — enable *Instant replay*, *Auto captions*, *Loudness match*, pick a
   platform preset (TikTok 9:16 is the default), then **Build preview**.
7. **Render final** — NVENC H.264 when a GPU is present, openh264 otherwise. The file lands
   next to your project (`Exports/`).

## Keyboard

| Key | Action |
|---|---|
| `Space` | play / pause |
| `S` | split at playhead |
| `M` | bookmark |
| `Del` | delete selection |
| `Ctrl+Z` / `Ctrl+Shift+Z` | undo / redo |
| `+` / `-` | zoom timeline |
| `Ctrl+K` | command palette |

## Honest limits of v1.0.0

- Style Match is a **rule-based** recreation of the reference, not a frame-by-frame copy:
  expect 85–95 % stylistic similarity, not a pixel match.
- Captions come from faster-whisper `base`; unusual accents need a manual pass.
- Integration and performance figures for your GPU are measured on **your** machine — see
  `docs/TEST-PLAN.md` for the exact commands.
