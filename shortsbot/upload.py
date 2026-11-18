"""YouTube Data API v3 resumable upload using a stored OAuth refresh token."""
import os, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def _youtube():
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"], scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def build_metadata(spec):
    desc = spec["description"].strip()
    if "#shorts" not in desc.lower(): desc += "\n\n#Shorts"
    tags = [t for t in spec.get("tags", []) if t][:15]
    return {
        "snippet": {"title": spec["title"][:100], "description": desc, "tags": tags,
                    "categoryId": os.environ.get("YT_CATEGORY_ID", "28"), "defaultLanguage": "en"},
        "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": False},
    }

def upload(video_path, spec, log=print, retries=5):
    yt = _youtube()
    body = build_metadata(spec)
    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    resp, attempt = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status: log("upload: %d%%" % int(status.progress() * 100))
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and attempt < retries:
                attempt += 1; time.sleep(2 ** attempt); continue
            raise
    vid = resp["id"]
    log("upload: done https://youtube.com/shorts/%s (privacy=%s)" % (vid, resp.get("status", {}).get("privacyStatus")))
    return vid, resp.get("status", {}).get("privacyStatus")
