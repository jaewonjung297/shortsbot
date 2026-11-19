# shortsbot: project context

Handoff notes so Claude Code (or anyone) can pick up where the Claude chat left off. Keep this file current.

## What this is
Jaewon's pipeline for making vertical short videos (1080×1920, 30 fps) with **procedurally rendered** low-poly /
blocky 3D-style animation (pycairo, no generative video models), narration or captions, and synthesized audio.
Claude writes the scripts; plain Python renders everything. Runs locally or in GitHub Actions.

Repo: https://github.com/jaewonjung297/shortsbot (public). Secrets live only in GitHub Actions secrets and a
local, gitignored `.env` (see `.env.example`); GitHub secrets are write-only and can't be read back.

## Current direction (Nov 2026)
1. **Platform: TikTok first** (Instagram Reels code exists but is parked). TikTok Creator Rewards only pays for
   videos **over 1 minute**, so target 65–85 s.
2. **Format: narrated Reddit stories** (r/AmIOverreacting style) in an **imitation-Roblox look**: blocky,
   Roblox-style characters that are original designs (no Roblox assets, avatars, names or logos). The user
   pastes a post; Claude condenses it **in its own words** into a shot list; the characters act it out with big
   word-by-word captions (white, black outline, current word yellow) and a TTS narrator.
   **Modes** (`story.yml` input `mode`, `scripts/story --mode`): `reddit_story` (default), `in_this_town`
   (Claude writes 3-4 deadpan "In this town, everybody... Except me." bits from an optional premise; same renderer),
   and `what_if` (legacy "What if…?" pipeline, run via `tiktok.yml` as a reusable workflow; keep working, don't develop).
   **Every condensed video** (both modes) opens with "In this town, everyone goes HUSS HUSS." and has >= 3 more
   "HUSS HUSS"; Reddit stories are reframed as happening in that town (townspeople, town places, gossip; "town" in
   >= 6 lines). Enforced in `condense.format_errors`.
3. **Human in the loop:** videos go to the TikTok inbox as **drafts** (Upload mode); the user adds their own
   voice/edits and posts from the app. Don't build auto-publishing: platforms demonetize mass-produced,
   unattended AI content, and narrated Reddit stories with TTS are a named risk.
4. **Paste a story and watch the pipeline run:** `scripts/story` (uses `gh`) triggers the multi-job
   `story.yml` workflow (condense → narrate → render (matrix) → assemble → deliver) and shows live job status;
   the Actions page shows the pipeline graph. Works end to end on GitHub (run 44472305496).

## Layout
```
shortsbot/
  timeline.py, engine.py, render.py, audio.py   "What if" engine: spec -> timeline/channels -> frames + synth audio
  templates/{car,window,hill}.py                 low-poly POV scene templates for "What if"
  spec.py, writer.py                             "What if" spec schema/validator + Claude writer & vision critic
  pipeline.py, __main__.py                       CLI: run | tiktok | instagram | ideas | validate | sheet
  tiktok.py                                      TikTok package (caption, voiceover script, cover) + inbox upload
  instagram.py                                   Instagram Reels publish (parked)
  upload.py                                      YouTube upload (parked)
scripts/get_tiktok_token.py                      one-time OAuth (Desktop + PKCE, hex SHA256) -> refresh token
scripts/get_refresh_token.py                     YouTube OAuth helper
.github/workflows/                               tiktok.yml (drafts), daily.yml (YouTube, schedule off),
                                                 instagram-draft.yml / instagram-publish.yml
examples/                                        hand-written specs (blackout_car, blackout_tiktok, sun_window, sealevel_hill)
TERMS.md, PRIVACY.md                             linked from the TikTok developer app
```

### Reddit-story pipeline (merged to `main`, working end to end on GitHub, Nov 19 2026)
```
shortsbot/story/
  art.py        drawing kit: toy-like blocks, faces (happy/sad/angry/shocked/...), people, cat, white dog, rooms
  spec.py       story spec schema + validator (cast looks, scenes incl. 'phone' text-message scene, poses, fx)
  condense.py   Claude: pasted post -> spec (paraphrase, privacy, 300-360 words, 18-34 lines; narration speed 1.575) with repair loop
  narrate.py    Kokoro TTS (kokoro-onnx; model files auto-download from GitHub releases into ~/.cache/kokoro)
                -> narration.wav + timeline.json with estimated per-word timings
  render.py     spec + timeline -> frames; camera presets (wide/medium/push/closeup:<who>); captions; end card
  music.py      soft piano bed, cut swooshes, booms on dramatic lines, text pings, ducking under the voice
  __main__.py   stages: condense | narrate | render --part k --parts n | assemble | deliver | all | preview
examples/story_cat.json      hand-converted spec of the first test story (mom selling the cat), incl. a phone scene
.github/workflows/story.yml  jobs: condense -> narrate -> render (matrix) -> assemble -> deliver (TikTok inbox)
scripts/story                terminal CLI: paste a post (or --example story_cat), triggers story.yml via `gh`,
                             streams job status with `gh run watch`, downloads the video into out/story-<run id>/
```
Verified locally (macOS, Python 3.11 venv in `.venv`, brew ffmpeg): narrate -> preview -> all on `story_cat.json`
gives a 76.7 s 1080x1920 video at -14.3 LUFS in ~55 s with 6 render processes. Fixed: close-ups now frame head and
shoulders so the caption no longer covers the eyes.
Not yet verified: `condense` against the live Claude API (first run with a real pasted post).
Apt packages come from `.github/actions/system-packages` (cached .debs, fallback mirrors).
Narration: Kokoro at <= 1.15x (`TTS_SPEED`), then ffmpeg `atempo` up to the spec speed (default 1.575); Kokoro itself
swallows first words and slurs above ~1.3x. Caption groups are capped at 14 characters so text stays full size.
`in_this_town` tested locally (Nov 19 2026): valid spec after JSON repairs, 86 s narration, night/party exterior.
kokoro-onnx/onnxruntime may lack wheels for brand-new Pythons (3.15); use 3.11/3.12. Characters must stay
**original** (not Roblox's avatars/branding).

### 3D renderer (experimental, Nov 19 2026)
`.claude/skills/blocky-shorts` (third-party skill v1.2, MIT; reviewed: no network calls beyond npm/Remotion/Whisper
downloads) and its Remotion template copied to `blocky/` (+ `blocky/scripts`). `npm ci` done (npm skips esbuild's
postinstall; works anyway). Use `PYTHON=../.venv/bin/python` (faster-whisper 1.2, av 15). `tools/checks.sh` all ok;
`render.sh 1 BlockyTestSub 0-89` renders 3 s in ~35 s with CONC=3. Not yet connected to the story pipeline; local
GPU only.

## Status of external setup
- GitHub: `gh` logged in locally (`~/homebrew/bin/gh`). Secrets set: `ANTHROPIC_API_KEY` and the **Sandbox**
  `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN` (all three must come from the same app;
  mismatched key/secret gives `invalid_client`). The same values are in `.env`.
- TikTok: developer app "shortsbot" created; **Sandbox** configured (Login Kit + Content Posting API, scopes
  `user.info.basic` + `video.upload`, Desktop redirect `http://localhost:8723/callback/`, Direct Post off).
  Sandbox inbox uploads work without app review: story run 44472305496 (Nov 19 2026, `story_cat` example) delivered
  a 76.5 s draft with status `SEND_TO_USER_INBOX`.
- "What if" `tiktok-draft` run 44470883670 rendered via the live Claude API but failed at upload (secrets not set then).

## Conventions and gotchas
- Code comments: short and descriptive only; no rationale, design history or conversation notes.
- macOS: use the `.venv` (Python 3.11); Homebrew's `python3` is 3.15 and lacks onnxruntime wheels. Fonts: Inter (captions/HUD) and Caladea (serif); Actions installs `fonts-inter` and
  `fonts-crosextra-caladea`.
- Rendering: one encoded file per chunk/part, joined with the concat demuxer (`-c copy`), audio muxed with
  `-c:v copy`; write to a temp name and rename on success. ~0.03–0.1 s per frame on one core.
- Models: `SHORTSBOT_MODEL` (default `claude-sonnet-5-5`). Cost is roughly $0.10–0.20 per video on Sonnet.
- GitHub Actions: free on public repos; artifacts kept 7 days.
- Keep captions paraphrased; never reproduce Reddit posts verbatim; strip identifying details; keep sensitive
  material (abuse, self-harm, health) to one non-graphic line.
