"""TikTok: build a posting package and (optionally) drop the video into your TikTok inbox as a draft.

Draft ("Upload") mode is deliberate: you open TikTok, add your voiceover, check the caption and post it
yourself. That keeps a human in the loop, which is what TikTok's originality rules for Creator Rewards
look for, and it works before your API client has passed TikTok's audit.
"""
import json, os, subprocess, time
import requests

API = "https://open.tiktokapis.com"

# ------------------------------------------------------------------ package
def write_package(spec, video_path, outdir):
    """caption.txt, voiceover_script.txt (timed lines to read) and cover.jpg next to the video."""
    from .timeline import Timeline
    tl = Timeline(spec)
    cap = spec.get("tiktok_caption") or spec["description"]
    with open(os.path.join(outdir, "caption.txt"), "w") as f:
        f.write(cap.strip() + "\n")
    lines = ["VOICEOVER SCRIPT - %s" % spec["premise"],
             "Read each line when its caption appears. Timings are seconds into the video.", ""]
    for a, b, text in tl.captions:
        lines.append("[%5.1f - %5.1f]  %s" % (a, min(b, tl.dur), text.replace("\n", " ")))
    lines += ["", "Stages: " + " -> ".join(s["label"] for s in tl.stages)]
    with open(os.path.join(outdir, "voiceover_script.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    # cover: a frame from the middle of the most dramatic (last) stage
    st = tl.stages[-1] if len(tl.stages) > 1 else tl.stages[0]
    t_cover = (st["at"] + min(st["end"], tl.final_at)) / 2
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % t_cover, "-i", video_path, "-frames:v", "1",
                    "-q:v", "3", os.path.join(outdir, "cover.jpg")], check=True)
    return {"caption": cap, "cover_time": t_cover}

# ------------------------------------------------------------------ auth
def access_token():
    """Exchange the stored refresh token for a fresh access token (TikTok rotates refresh tokens)."""
    r = requests.post(API + "/v2/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"]}, timeout=30)
    data = r.json()
    if "access_token" not in data: raise RuntimeError("TikTok token refresh failed: %s" % data)
    new_rt = data.get("refresh_token")
    if new_rt and new_rt != os.environ["TIKTOK_REFRESH_TOKEN"]:
        # Refresh tokens last ~1 year and may rotate. Surface the new one so a scheduler can store it.
        path = os.environ.get("TIKTOK_REFRESH_TOKEN_OUT")
        if path:
            with open(path, "w") as f: f.write(new_rt)
    return data["access_token"]

# ------------------------------------------------------------------ inbox upload
def send_to_inbox(video_path, log=print, poll_seconds=120):
    """Upload the video to the creator's TikTok inbox as a draft (Content Posting API, video.upload scope)."""
    tok = access_token()
    size = os.path.getsize(video_path)
    if size > 64 * 1024 * 1024:
        raise RuntimeError("video is over 64 MB; single-chunk upload not supported here")
    h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8"}
    body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}}
    r = requests.post(API + "/v2/post/publish/inbox/video/init/", headers=h, json=body, timeout=30).json()
    if r.get("error", {}).get("code") not in (None, "ok"): raise RuntimeError("TikTok init failed: %s" % r)
    publish_id, upload_url = r["data"]["publish_id"], r["data"]["upload_url"]
    with open(video_path, "rb") as f:
        put = requests.put(upload_url, data=f.read(), timeout=300, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": "bytes 0-%d/%d" % (size - 1, size)})
    if put.status_code not in (200, 201): raise RuntimeError("TikTok upload failed: %s %s" % (put.status_code, put.text[:300]))
    log("tiktok: uploaded, publish_id=%s; waiting for processing" % publish_id)
    status = None
    t_end = time.time() + poll_seconds
    while time.time() < t_end:
        s = requests.post(API + "/v2/post/publish/status/fetch/", headers=h, json={"publish_id": publish_id}, timeout=30).json()
        status = s.get("data", {}).get("status")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"): break
        if status == "FAILED": raise RuntimeError("TikTok processing failed: %s" % s)
        time.sleep(5)
    log("tiktok: status=%s. Open the TikTok app -> inbox notification to finish the post (within 24 h)." % status)
    return publish_id, status
