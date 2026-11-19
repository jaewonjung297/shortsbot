# shortsbot: narrated blocky-character videos for TikTok

Paste a Reddit post (r/AmIOverreacting, r/AITA and similar) and get a 65–85 s vertical video (1080×1920, 30 fps).
Blocky, Roblox-style characters act out the story. A TTS narrator reads it, with big word-by-word captions
(white with a black outline, the current word in yellow) and a soft music bed. The finished video goes to
your TikTok inbox as a draft, and you post it from the app.

Everything is drawn in code with pycairo, with no generative video models. The characters only imitate the
Roblox look: they are original designs and use no Roblox assets, avatars, names or logos.

```
post ──▶ condense ──▶ narrate ──▶ render (parallel parts) ──▶ assemble ──▶ deliver
         Claude        Kokoro TTS   pycairo + ffmpeg              music, mix,    TikTok inbox
         spec.json     narration    part_NN.mp4                   loudnorm       draft
                       timeline
```

| stage | what it does | output |
|---|---|---|
| condense | Claude rewrites the post in its own words as a shot list (18–34 lines, 300–360 words, read at 1.575× speed), changes identifying details, and retries until the spec validates | `spec.json` |
| narrate | Kokoro TTS reads each line; per-word timings are estimated for the captions | `narration.wav`, `timeline.json` |
| render | draws every frame (scenes, characters, camera, fx, captions, end card) in parallel parts | `part_NN.mp4` |
| assemble | joins the parts, adds piano bed, swooshes, booms and message pings, ducks the music under the voice, normalizes loudness to -14 LUFS | `short.mp4`, `caption.txt`, `script.txt`, `cover.jpg` |
| deliver | uploads to your TikTok inbox as a draft | `result.json` (publish id) |

## Modes

| mode | input | what you get |
|---|---|---|
| `reddit_story` (default) | a pasted Reddit post | the post retold in Claude's own words, 65–85 s |
| `in_this_town` | a premise, or nothing for fresh ideas | 3–4 deadpan "In this town, everybody… Except me." bits, 65–85 s |
| `what_if` | a premise, or nothing | the legacy low-poly "What if…?" video (see the end of this file) |

`reddit_story` and `in_this_town` share the same characters, scenes, narration and captions; only Claude's
prompt differs. `what_if` runs the separate legacy pipeline (`tiktok.yml`) from the same workflow.

Every `reddit_story` and `in_this_town` video opens with **"In this town, everyone goes HUSS HUSS."** and
uses "HUSS HUSS" at least 3 more times. Reddit stories are retold as if they happen in that town. Claude is
sent back to fix any script that breaks this (`OPENER`, `HUSS_MIN` and `format_errors` in
`shortsbot/story/condense.py`). Hand-written specs and `--from-run` specs are not checked.

## Run it

### From the terminal (GitHub Actions)

```bash
pbpaste | scripts/story                    # post from the clipboard
scripts/story post.txt                     # post from a file
scripts/story --example story_cat          # skip Claude, render examples/story_cat.json
scripts/story --mode in_this_town --premise "everyone parties except me"
scripts/story --mode in_this_town          # Claude invents the premises
scripts/story --mode what_if --premise "What if the Moon came twice as close?"
scripts/story --from-run <run id>          # re-render an earlier run's script without calling Claude
scripts/story --no-inbox --voice am_adam --notes "keep it light" post.txt
```

`scripts/story` starts the `story` workflow with `gh`, streams each job's status as it runs, and downloads
the result into `out/story-<run id>/`. The Actions page shows the same run as a pipeline graph:
condense → narrate → render (matrix) → assemble → deliver.

You can also start it from **Actions → story → Run workflow**: pick a **Format**, paste the post or premise into
the second box, and leave the developer fields empty. Or:

```bash
gh workflow run story.yml -f story="$(pbpaste)"
```

### Locally

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt kokoro-onnx soundfile
brew install ffmpeg cairo                  # Linux: apt install ffmpeg libcairo2-dev fonts-inter

set -a; source .env; set +a                # ANTHROPIC_API_KEY, TikTok keys
.venv/bin/python -m shortsbot.story all --story post.txt --dir work
```

Individual stages, each reading and writing the work folder:

```bash
python -m shortsbot.story condense --story post.txt --dir work
python -m shortsbot.story narrate  --dir work
python -m shortsbot.story preview  --dir work            # contact sheet of every shot -> work/preview.png
python -m shortsbot.story render   --dir work --part 0 --parts 4
python -m shortsbot.story assemble --dir work
python -m shortsbot.story deliver  --dir work
```

To render a hand-written spec, copy it to `work/spec.json` and start at `narrate`.

Use Python 3.11 or 3.12; `kokoro-onnx` and `onnxruntime` may not have wheels for newer versions. Kokoro's
model files download to `~/.cache/kokoro` on first use.

## Setup

1. **GitHub CLI:** `gh auth login`.
2. **Repo secrets** (Settings → Secrets and variables → Actions). GitHub Actions doesn't read `.env`.
   - `ANTHROPIC_API_KEY`
   - `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`: only needed for `deliver`.
     Without them, run with `--no-inbox` and download the video instead.
3. **Local `.env`**: copy `.env.example` and fill in the same four values.
4. **TikTok app** at developers.tiktok.com: a Desktop app with Login Kit and the Content Posting API,
   scopes `user.info.basic` and `video.upload`, and redirect URI `http://localhost:8723/callback/`. In
   Sandbox, add your own account as a target user. Then get the refresh token (valid about a year):
   ```bash
   .venv/bin/python scripts/get_tiktok_token.py
   gh secret set TIKTOK_REFRESH_TOKEN
   ```
5. `story.yml` must be on the default branch (`main`) before GitHub lets you start it.

Optional repo variable: `SHORTSBOT_MODEL` (default `claude-sonnet-5-5`). Each video costs about
$0.10–0.20 in Claude usage. Actions minutes are free on public repos, and artifacts are kept for 7 days.

## Story spec

Claude writes the spec, and you can also write one by hand. The full schema is `SCHEMA` in
`shortsbot/story/spec.py`; `examples/story_cat.json` is a complete example.

- **cast**: 1–4 people, always including `me` (the narrator). Looks are `young_woman`, `young_man`,
  `older_woman` and `older_man`, plus a shirt and hair color.
- **pet**: `cat`, `dog` or none.
- **lines**: one narration line per shot. Each has a scene, characters with x position, emotion and pose,
  a camera and optional fx.

| | options |
|---|---|
| scenes | bedroom, bed, desk, living, kitchen, window, exterior, phone (text-message screen) |
| emotions | happy, neutral, smug, sad, worried, cold, tired, shocked, angry |
| poses | idle, hold_pet, cross, point, shrug, yell, facepalm, phone, lying (bed only) |
| camera | wide, medium, push, closeup:&lt;who&gt; |
| fx | hearts, sweat, tears, shake, punch, redflash, cold, desat, memory, dark, fluff, night, party |

## Content rules

- Narration is paraphrased; posts are never reproduced verbatim.
- Names, ages, places and other identifying details are changed.
- Sensitive material (abuse, self-harm, health) gets at most one plain, non-graphic line.
- Videos go to TikTok as drafts only. Add your own voice or edits and post from the app.

## Layout

```
shortsbot/story/
  condense.py   Claude: post or premise -> spec.json (one prompt per mode)
  spec.py       spec schema and validator
  narrate.py    Kokoro TTS -> narration.wav + timeline.json
  art.py        drawing kit: blocky characters, faces, pets, rooms
  render.py     frames: scenes, camera, fx, captions, end card
  music.py      music bed, sound effects, ducking
  __main__.py   stages: condense | narrate | render | assemble | deliver | all | preview
shortsbot/tiktok.py         TikTok inbox upload
scripts/story               terminal command: start story.yml and watch it
scripts/get_tiktok_token.py one-time TikTok OAuth
.github/workflows/story.yml condense -> narrate -> render (matrix) -> assemble -> deliver
examples/story_cat.json     example spec
TERMS.md, PRIVACY.md        linked from the TikTok developer app
```

## Legacy: "What if…?" videos

The earlier pipeline (`shortsbot/` top-level modules, `templates/`, `tiktok.yml`, `daily.yml`,
`instagram-*.yml`) is the `what_if` mode. It makes low-poly POV "What if…?" videos and can post to YouTube and Instagram Reels. It
still works but is no longer developed. See `python -m shortsbot --help`.
