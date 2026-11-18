"""Run once on your computer to authorise shortsbot to put drafts in your TikTok inbox.

1. developers.tiktok.com -> Manage apps -> create an app (platform: Desktop), add the products
   "Login Kit" and "Content Posting API", request the scope `video.upload`, and add
   http://localhost:8723/callback/ as a redirect URI.
2. Put TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in a .env file at the repo root (it's gitignored), then
   python scripts/get_tiktok_token.py
   (or pass them as arguments: python scripts/get_tiktok_token.py <client_key> <client_secret>)
3. Log in with the TikTok account that will post. Store the printed values as GitHub secrets:
   TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN.

Note: while the app is in Sandbox, add your TikTok account as a target user in the developer portal.
"""
import hashlib, http.server, os, secrets, sys, threading, urllib.parse, webbrowser
import requests

def load_dotenv(path=".env"):
    try:
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass

load_dotenv()
if len(sys.argv) >= 3:
    KEY, SECRET = sys.argv[1], sys.argv[2]
else:
    KEY, SECRET = os.environ.get("TIKTOK_CLIENT_KEY"), os.environ.get("TIKTOK_CLIENT_SECRET")
    if not KEY or not SECRET:
        sys.exit("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET (in .env or your shell), or pass them as arguments.")
PORT = 8723
REDIRECT = "http://localhost:%d/callback/" % PORT
verifier = secrets.token_urlsafe(64)[:64]
challenge = hashlib.sha256(verifier.encode()).hexdigest()   # TikTok desktop PKCE uses a hex-encoded SHA256
state = secrets.token_urlsafe(16)
got = {}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        got.update({k: v[0] for k, v in q.items()})
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Done - you can close this tab and go back to the terminal.")
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("localhost", PORT), H)
threading.Thread(target=srv.handle_request, daemon=True).start()
url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": KEY, "response_type": "code", "scope": "user.info.basic,video.upload", "redirect_uri": REDIRECT,
    "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})
print("Opening:", url)
webbrowser.open(url)
while "code" not in got and "error" not in got:
    srv.timeout = 1
    import time; time.sleep(0.5)
if got.get("state") != state or "code" not in got:
    sys.exit("Authorisation failed: %s" % got)
r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                  data={"client_key": KEY, "client_secret": SECRET, "code": got["code"], "grant_type": "authorization_code",
                        "redirect_uri": REDIRECT, "code_verifier": verifier}).json()
if "refresh_token" not in r: sys.exit("Token exchange failed: %s" % r)
print("\nTIKTOK_REFRESH_TOKEN=" + r["refresh_token"])
print("(refresh token valid for about %d days)" % (int(r.get("refresh_expires_in", 0)) // 86400))
