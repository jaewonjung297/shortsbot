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
2. **Format: switching from "What if…?" videos to narrated Reddit stories** (r/AmIOverreacting style). The user
   pastes a post; Claude condenses it **in its own words** into a shot list; blocky original characters act it
   out with big word-by-word captions (white, black outline, current word yellow) and a TTS narrator.
3. **Human in the loop:** videos go to the TikTok inbox as **drafts** (Upload mode); the user adds their own
   voice/edits and posts from the app. Don't build auto-publishing: platforms demonetize mass-produced,
   unattended AI content, and narrated Reddit stories with TTS are a named risk.
4. **Wanted next:** a nice way to paste a story and *watch the pipeline run*. The plan is a terminal command
   (`story` CLI using `gh`) that triggers a multi-job GitHub Actions workflow
   (condense → narrate → render (matrix) → assemble → deliver) and shows live job status, plus the normal
   Actions pipeline graph on GitHub.

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

### Reddit-story pipeline: branch `reddit-story-wip` (written, NOT yet tested end to end)
```
shortsbot/story/
  art.py        drawing kit: toy-like blocks, faces (happy/sad/angry/shocked/...), people, cat, white dog, rooms
  spec.py       story spec schema + validator (cast looks, scenes incl. 'phone' text-message scene, poses, fx)
  condense.py   Claude: pasted post -> spec (paraphrase, privacy, 185-240 words, 16-28 lines) with repair loop
  narrate.py    Kokoro TTS (kokoro-onnx; model files auto-download from GitHub releases into ~/.cache/kokoro)
                -> narration.wav + timeline.json with estimated per-word timings
  render.py     spec + timeline -> frames; camera presets (wide/medium/push/closeup:<who>); captions; end card
  music.py      soft piano bed, cut swooshes, booms on dramatic lines, text pings, ducking under the voice
  __main__.py   stages: condense | narrate | render --part k --parts n | assemble | all | preview
examples/story_cat.json   hand-converted spec of the first test story (mom selling the cat), incl. a phone scene
```
Next steps on that branch: run `python -m shortsbot.story narrate/preview/all --dir work` with
`examples/story_cat.json` copied to `work/spec.json`, fix rendering issues, then add `.github/workflows/story.yml`
(jobs: condense → narrate → render matrix → assemble → deliver to TikTok inbox via `tiktok.send_to_inbox`) and the
terminal CLI. Characters must stay **original** (not Roblox's avatars/branding).

## Status of external setup
- GitHub: repo pushed; secret `ANTHROPIC_API_KEY` added by the user.
- TikTok: developer app "shortsbot" created; **Sandbox** configured (Login Kit + Content Posting API, scopes
  `user.info.basic` + `video.upload`, Desktop redirect `http://localhost:8723/callback/`, Direct Post off).
  Still to do by the user: upload app icon, Apply changes, add own account as Target User, put the **sandbox**
  client key/secret in `.env`, run `python3 scripts/get_tiktok_token.py`, store `TIKTOK_CLIENT_KEY`,
  `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN` as GitHub secrets. Unverified: whether sandbox allows inbox
  uploads without app review; first real run will tell.
- Nothing has been run against the live Claude/TikTok/Instagram/YouTube APIs yet (only mocked).

## Conventions and gotchas
- macOS: use `python3`. Fonts: Inter (captions/HUD) and Caladea (serif); Actions installs `fonts-inter` and
  `fonts-crosextra-caladea`.
- Rendering: one encoded file per chunk/part, joined with the concat demuxer (`-c copy`), audio muxed with
  `-c:v copy`; write to a temp name and rename on success. ~0.03–0.1 s per frame on one core.
- Models: `SHORTSBOT_MODEL` (default `claude-sonnet-5-5`). Cost is roughly $0.10–0.20 per video on Sonnet.
- GitHub Actions: free on public repos; artifacts kept 7 days.
- Keep captions paraphrased; never reproduce Reddit posts verbatim; strip identifying details; keep sensitive
  material (abuse, self-harm, health) to one non-graphic line.
