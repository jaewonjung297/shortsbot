"""Run once on your own computer to authorise the uploader for your YouTube channel.

    pip install google-auth-oauthlib
    python scripts/get_refresh_token.py path/to/client_secret.json

Sign in with the Google account that owns the channel. The script prints the three values to store
as GitHub secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import json, sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
info = json.load(open(path))
info = info.get("installed") or info.get("web")
print("\nYT_CLIENT_ID=" + info["client_id"])
print("YT_CLIENT_SECRET=" + info["client_secret"])
print("YT_REFRESH_TOKEN=" + creds.refresh_token)
