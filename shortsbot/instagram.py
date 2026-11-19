"""Instagram Reels publishing from a public video URL (Instagram API with Instagram Login)."""
import json, os, time
import requests

API = "https://graph.instagram.com"
VER = os.environ.get("IG_API_VERSION", "v26.0")

def _token():
    return os.environ["IG_ACCESS_TOKEN"]

def _check(r):
    try: data = r.json()
    except ValueError: raise RuntimeError("Instagram API %s: %s" % (r.status_code, r.text[:300]))
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError("Instagram API error: %s" % json.dumps(data.get("error", data))[:600])
    return data

def refresh_token(log=print):
    """Refresh the long-lived token; returns the new token."""
    r = requests.get(API + "/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": _token()}, timeout=30)
    data = _check(r)
    days = int(data.get("expires_in", 0)) // 86400
    log("instagram: token refreshed, valid for %d more days" % days)
    return data["access_token"]

def me():
    r = requests.get("%s/%s/me" % (API, VER), params={"fields": "user_id,username,account_type", "access_token": _token()}, timeout=30)
    return _check(r)

def wait_for_url(url, log=print, timeout=300):
    """Wait until the URL is reachable."""
    t_end = time.time() + timeout
    while time.time() < t_end:
        try:
            r = requests.head(url, timeout=20, allow_redirects=True)
            if r.status_code == 200 and int(r.headers.get("Content-Length", "1")) > 0:
                log("instagram: video is live at %s" % url); return True
        except requests.RequestException:
            pass
        time.sleep(10)
    raise RuntimeError("video URL never became reachable: %s" % url)

def publish_reel(video_url, caption, cover_offset_ms=None, log=print, poll_seconds=600):
    """Create a REELS container from a public video URL, wait for processing, then publish."""
    user = me()
    uid = user["user_id"]
    log("instagram: publishing as @%s (%s)" % (user.get("username"), user.get("account_type")))
    params = {"media_type": "REELS", "video_url": video_url, "caption": caption[:2200],
              "share_to_feed": "true", "access_token": _token()}
    if cover_offset_ms is not None: params["thumb_offset"] = str(int(cover_offset_ms))
    cid = _check(requests.post("%s/%s/%s/media" % (API, VER, uid), data=params, timeout=60))["id"]
    log("instagram: container %s created; waiting for Instagram to process the video" % cid)
    t_end = time.time() + poll_seconds
    status = None
    while time.time() < t_end:
        s = _check(requests.get("%s/%s/%s" % (API, VER, cid), params={"fields": "status_code,status", "access_token": _token()}, timeout=30))
        status = s.get("status_code")
        if status == "FINISHED": break
        if status in ("ERROR", "EXPIRED"): raise RuntimeError("Instagram could not process the video: %s" % s)
        time.sleep(10)
    if status != "FINISHED": raise RuntimeError("Instagram processing timed out (last status %s)" % status)
    mid = _check(requests.post("%s/%s/%s/media_publish" % (API, VER, uid), data={"creation_id": cid, "access_token": _token()}, timeout=60))["id"]
    link = _check(requests.get("%s/%s/%s" % (API, VER, mid), params={"fields": "permalink", "access_token": _token()}, timeout=30)).get("permalink")
    log("instagram: published %s" % (link or mid))
    return mid, link

def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="shortsbot.instagram")
    sub = p.add_subparsers(dest="cmd", required=True)
    pub = sub.add_parser("publish"); pub.add_argument("--video-url", required=True); pub.add_argument("--package", required=True)
    sub.add_parser("refresh-token"); sub.add_parser("whoami")
    a = p.parse_args(argv)
    if a.cmd == "whoami": print(json.dumps(me(), indent=1))
    elif a.cmd == "refresh-token": print(refresh_token(log=lambda *x: None))
    else:
        caption = open(os.path.join(a.package, "caption.txt")).read().strip()
        cover = None
        try: cover = json.load(open(os.path.join(a.package, "result.json"))).get("cover_time")
        except Exception: pass
        wait_for_url(a.video_url)
        mid, link = publish_reel(a.video_url, caption, cover_offset_ms=None if cover is None else cover * 1000)
        with open(os.path.join(a.package, "instagram.json"), "w") as f:
            json.dump({"media_id": mid, "permalink": link}, f)

if __name__ == "__main__":
    main()
