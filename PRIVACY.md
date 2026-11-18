# shortsbot – Privacy Policy

_Last updated: November 18, 2026_

shortsbot is a personal, open-source tool used by its author to send draft videos to their own TikTok account.

**What it accesses.** When you authorise shortsbot with TikTok, it receives an access token and a refresh
token, and the scopes `user.info.basic` (basic profile info such as your open ID and display name) and
`video.upload` (upload drafts to your inbox).

**What it stores.** Only the refresh token, kept as an encrypted secret in the owner's own GitHub Actions
settings so scheduled runs can upload drafts. shortsbot does not store, sell or share your profile
information, videos or any other personal data, and it has no database or analytics.

**What it sends to TikTok.** The generated video file, uploaded to your own inbox as a draft.

**Other services.** Video scripts are written with the Anthropic Claude API; no TikTok user data is sent to it.

**Deleting your data.** Revoke access in TikTok (Settings and privacy → Security → Manage app permissions)
and delete the `TIKTOK_REFRESH_TOKEN` secret from the repository settings.

Contact: open an issue at https://github.com/jaewonjung297/shortsbot/issues
