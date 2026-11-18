# shortsbot: automatic "What if…?" YouTube Shorts

A scheduled pipeline that invents a "What if…?" premise, writes the script, renders a 1080×1920 low-poly
POV animation with a counter HUD, captions and sound, checks its own frames, and publishes the Short to
your channel. It runs on a schedule in GitHub Actions, with no server to look after.

```
            ┌──────────── Claude (writer) ────────────┐
history ──▶ │ premise + JSON spec (template, stages,  │ ──▶ validator ──┐
            │ captions, effects, title, tags)         │ ◀── errors ─────┘  (repairs until valid)
            └─────────────────────────────────────────┘
                              │
                     contact sheet render
                              │
            ┌──────────── Claude (critic, vision) ────┐
            │ approve, or return a revised spec       │  (up to 2 rounds)
            └─────────────────────────────────────────┘
                              │
     parallel frame render (pycairo) ─ procedural audio (numpy) ─ ffmpeg mux + loudnorm
                              │
                YouTube Data API upload ─▶ history.json committed back to the repo
```

## Instagram Reels (review, then publish)

Instagram's API can't save drafts: anything it uploads is posted publicly right away. So Reels are made in
two steps, and nothing goes public until you start the second one:

```
instagram-draft:   idea -> spec -> critic -> render -> package (video, caption, voiceover script, cover)
                   ...you watch it...
instagram-publish: host the mp4 on this repo's GitHub Pages -> Instagram fetches it -> Reel is published
```

**Ways to run it**
- **Make a draft:** **Actions → instagram-draft → Run workflow**, with an optional premise. The run summary
  shows the caption, the voiceover script and the exact publish command.
- **Publish it:** **Actions → instagram-publish → Run workflow** with the draft's run id, or run
  `gh workflow run instagram-publish.yml -f draft_run_id=<id>`.
- **Post it yourself instead:** download the draft (`short.mp4` + `caption.txt`) and post it from the
  Instagram app. Recording your own voiceover there is the best way to keep the account monetisable.

**Instagram setup (once)**
1. **Make the account professional.** In the Instagram app: Settings → Account type and tools → Switch to
   professional account (Business or Creator).
2. **Create a Meta app.** At developers.facebook.com → My Apps → Create app, pick the use case for managing
   content on Instagram, and choose **API setup with Instagram login**. Add your Instagram account
   (it gets a tester role; accept the invite in Instagram if asked). Then use **Generate access token** for
   that account. It needs the permissions `instagram_business_basic` and
   `instagram_business_content_publish`. You don't need App Review to post to your own account.
3. **Add the secret.** Store the token as the repo secret `IG_ACCESS_TOKEN`. It lasts 60 days.
   `instagram-publish` refreshes it on every run; to save the refreshed token automatically, also add a
   `GH_PAT` secret (a fine-grained token with *Secrets: read and write* on this repo). Otherwise,
   regenerate the token every ~50 days.
4. **Turn on GitHub Pages.** Settings → Pages → Source: **GitHub Actions**. This hosts each video
   temporarily so Instagram can fetch it; only the most recent video stays online.

Limits: Instagram allows up to 100 API-published posts per account per 24 hours, far more than you'll use.

## TikTok drafts (recommended workflow)

TikTok only pays Creator Rewards for videos **over one minute** and excludes fully automated content, so
the TikTok pipeline makes 72–85 s videos and stops before posting. You finish each post yourself.

```
idea (yours or Claude's) -> spec -> critic -> render -> package -> TikTok inbox draft -> YOU: voiceover, caption, post
```

**Ways to run it**
- GitHub: **Actions → tiktok-draft → Run workflow**, with an optional premise and template. This also works from the GitHub mobile app.
- CLI: `gh workflow run tiktok.yml -f premise="What if the Moon came twice as close?"`
- Locally: `python -m shortsbot ideas` lists fresh premises, then `python -m shortsbot tiktok --premise "..." --send-to-inbox`.

Each run produces `short.mp4`, `caption.txt`, `voiceover_script.txt` (timed lines to read), `cover.jpg` and
previews. The job summary shows the caption and script. With `--send-to-inbox`, the video also lands in
your TikTok app as a draft notification. Finish it within 24 hours: add your voiceover, check the caption, pick the cover, post.

**TikTok setup**
1. At developers.tiktok.com, create an app (Desktop) with **Login Kit** and the **Content Posting API**.
   Request the scope `video.upload` and add `http://localhost:8723/callback/` as a redirect URI. In
   Sandbox, add your account as a target user.
2. Run `python scripts/get_tiktok_token.py <client_key> <client_secret>`. Add `TIKTOK_CLIENT_KEY`,
   `TIKTOK_CLIENT_SECRET` and `TIKTOK_REFRESH_TOKEN` as repo secrets. The refresh token lasts about a year;
   re-run the script when it expires.
3. Draft (inbox) mode doesn't need TikTok's audit, because you post from the app yourself. Direct posting would.

The YouTube workflow's daily schedule is now **off** by default. Run it manually when you've reviewed a video.

## Scene templates

| template | scene | good for |
|---|---|---|
| `car` | driver's POV at a red light on a city street | power/tech, traffic, street floods, snow, decay, quakes |
| `window` | 8th-floor apartment window over a river skyline | sun/moon/stars, storms, heat, river floods, city lights |
| `hill` | hilltop with a phone in hand, over a coastal town and sea | sea-level rise, sky and space, fires, quakes, nature returning |

Every template reacts to the same **effect channels**: `power, traffic, vegetation, decay, water, snow, rain,
smoke, red_sky, sun_scale, moon_scale, stars, shake, clouds, wind, heat` (plus an optional `daylight`). The
writer animates them stage by stage. The counter runs in either `time` mode (elapsed time accelerating
×10 every few seconds, with a real day/night cycle) or `number` mode (a quantity such as metres, °C or %).

## Setup (about 30 minutes, once)

1. **Make a private GitHub repo and push this folder to it.**
2. **Anthropic API key.** Create one at console.anthropic.com and add it as the repo secret `ANTHROPIC_API_KEY`
   (Settings → Secrets and variables → Actions).
3. **Google Cloud project for YouTube.**
   - Create a project at console.cloud.google.com and enable **YouTube Data API v3**.
   - Set up the OAuth consent screen (External) and add the channel's Google account as a test user.
   - Create an **OAuth client ID** of type *Desktop app* and download the JSON.
   - Set the consent screen's publishing status to **In production**. While an app is in *Testing*,
     Google expires its refresh tokens after 7 days and the daily job would start failing.
4. **Get a refresh token** on your own computer:
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_refresh_token.py client_secret.json
   ```
   Add the three printed values as repo secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
5. **Apply for the YouTube API compliance audit.** This is required for public auto-publishing. Videos
   uploaded through the API from an unaudited project created after 28 July 2020 are **locked to
   private**, whatever `privacyStatus` you send. Submit the *YouTube API Services Audit and Quota
   Extension* form for your project. Until it's approved, the pipeline still runs every day, but the
   uploads stay private.
6. Trigger **Actions → daily-short → Run workflow**, leaving *Upload* unticked for a dry run, and check the
   artifact. After that it runs on its own every day at 15:17 UTC. To change the schedule, edit the cron
   line in `.github/workflows/daily.yml`.

Optional repo **variables**: `YT_PRIVACY` (`public` / `unlisted` / `private`, default `public`) and
`SHORTSBOT_MODEL` (default `claude-sonnet-5-5`).

**Limits.** The default API quota is 10,000 units a day per project, and each upload uses a large share of
it, so plan on at most a handful of uploads a day. One a day is far below the limit.

## Local use

```bash
sudo apt install ffmpeg fonts-inter fonts-crosextra-caladea   # or brew install ffmpeg cairo + the fonts
pip install -r requirements.txt

python -m shortsbot validate examples/blackout_car.json
python -m shortsbot sheet examples/sun_window.json preview.png          # frames from every stage
python -m shortsbot run --spec examples/sealevel_hill.json --no-upload  # render a hand-written spec
ANTHROPIC_API_KEY=... python -m shortsbot run --no-upload               # full agent, no upload
```

Each run writes `out/<stamp>/` containing `short.mp4`, `spec.json`, the preview contact sheets and `result.json`.
A 60 s render takes about 85 s on 2 cores and about 45 s on a 4-core Actions runner.

## Writing specs by hand

The three files in `examples/` are complete specs. The full format, with comments, is `SCHEMA_DOC` in
`shortsbot/spec.py`. The validator enforces caption length, pacing (each stage at least 2.6 s on screen)
and channel ranges, and tells you which stage is too short.

## Adding a template

Copy `shortsbot/templates/car.py` and keep the module constants (`NAME`, `DESCRIPTION`, `FOCUS`, `HUD_Y`,
`CAPTION_Y`) and a `Scene(tl, seed)` class with `draw(ctx, env, t)`. Then add the name to `TEMPLATES` in
`spec.py` and `render.py`. The writer reads `DESCRIPTION`, so describe what the scene is good at.

## Staying monetisable

YouTube's Partner Program doesn't monetise "inauthentic" (mass-produced, repetitive) content, and the rule
applies to the whole channel. The pipeline already varies the premise, template, layout seed, time of
day and effects, and it never repeats a premise from `history.json`. To keep the channel on the right
side of that rule, add your own creative input: review the weekly output, add new templates, tune the
writer prompt in `shortsbot/writer.py`, and consider a voiceover.
