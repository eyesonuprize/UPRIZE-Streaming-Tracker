#!/usr/bin/env python3
"""Chạy mỗi giờ (GitHub Actions).

1. YouTube: lấy lượt xem hiện tại, ghi snapshot có giờ vào data/history.json.
2. Google Sheet (CSV): stream, người nghe hàng tháng, thứ hạng album và từng bài
   -> data/sheet.json. Bỏ qua phần nào chưa cấu hình link.
3. Bìa ca khúc: Spotify (oEmbed) và Apple/iTunes (Search API) -> data/covers.json.
   Chỉ tải những bìa còn thiếu.

Biến môi trường:
  YOUTUBE_API_KEY, SHEET_STREAM_CSV, SHEET_RANK_CSV, SHEET_TRACK_RANK_CSV
"""
import csv
import io
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKS = ROOT / "tracks.json"
HISTORY = ROOT / "data" / "history.json"
SHEET = ROOT / "data" / "sheet.json"
COVERS = ROOT / "data" / "covers.json"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
RANK_COLS = ["spotify_vn", "apple_music_vn", "itunes_vn"]
UA = "uprize-tracker/1.0"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def fetch_text(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def digits(s):
    """'31.220' -> 31220, '' -> None"""
    d = re.sub(r"\D", "", s or "")
    return int(d) if d else None


def youtube_views(ids, api_key):
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        qs = urllib.parse.urlencode({"part": "statistics", "id": ",".join(chunk), "key": api_key})
        data = http_json(f"https://www.googleapis.com/youtube/v3/videos?{qs}")
        for item in data.get("items", []):
            out[item["id"]] = int(item["statistics"].get("viewCount", 0))
    return out


def read_stream(text):
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip() for h in rows[0]]
    out = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        entry = {}
        for h, v in zip(head[1:], r[1:]):
            n = digits(v)
            if h and n is not None:
                entry[h] = n
        if entry:
            out[r[0].strip()] = entry
    return out


def read_ranks(text):
    """Nhận cột album (spotify_vn...) và cột từng bài (spotify_vn:thang...)."""
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip() for h in rows[0]]
    out = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        entry = {}
        for h, v in zip(head[1:], r[1:]):
            n = digits(v)
            if (h in RANK_COLS or ":" in h) and n is not None:
                entry[h] = n
        if entry:
            out[r[0].strip()] = entry
    return out


# ---------- bìa ca khúc ----------
def clean_title(title):
    return re.sub(r"\(.*?\)", "", title).strip()


def spotify_cover(url):
    qs = urllib.parse.urlencode({"url": url})
    return http_json(f"https://open.spotify.com/oembed?{qs}").get("thumbnail_url")


def apple_cover(term, entity):
    qs = urllib.parse.urlencode({"term": term, "entity": entity, "country": "VN", "limit": 10})
    for it in http_json(f"https://itunes.apple.com/search?{qs}").get("results", []):
        if "UPRIZE" in (it.get("artistName") or "").upper() and it.get("artworkUrl100"):
            return it["artworkUrl100"].replace("100x100bb", "600x600bb")
    return None


def safe(fn):
    try:
        return fn()
    except Exception as e:  # không để lỗi bìa làm hỏng cả lần chạy
        print("Lỗi lấy bìa:", e)
        return None


def update_covers(tracks):
    covers = load(COVERS, {})
    before = json.dumps(covers, sort_keys=True)
    for t in tracks:
        c = covers.setdefault(t["id"], {})
        if not c.get("spotify") and t.get("spotify_url"):
            c["spotify"] = safe(lambda: spotify_cover(t["spotify_url"]))
        if not c.get("apple"):
            c["apple"] = safe(lambda: apple_cover("UPRIZE " + clean_title(t["title"]), "song"))
    alb = covers.setdefault("album", {})
    if not alb.get("spotify") and covers.get("thang", {}).get("spotify"):
        alb["spotify"] = covers["thang"]["spotify"]
    if not alb.get("apple"):
        alb["apple"] = safe(lambda: apple_cover("UPRIZE THĂNG", "album"))
    if json.dumps(covers, sort_keys=True) != before:
        COVERS.write_text(json.dumps(covers, ensure_ascii=False, indent=1), encoding="utf-8")
        print("Đã cập nhật bìa")


def main():
    now = datetime.now(TZ)
    tracks = load(TRACKS, {"tracks": []})["tracks"]

    # 1. YouTube snapshot
    history = [h for h in load(HISTORY, []) if "yt" in h]  # bỏ bản ghi cũ dạng ngày
    key = os.environ.get("YOUTUBE_API_KEY", "")
    with_id = [t for t in tracks if t.get("youtube_id")]
    if with_id and key:
        views = youtube_views([t["youtube_id"] for t in with_id], key)
        yt = {t["id"]: views[t["youtube_id"]] for t in with_id if t["youtube_id"] in views}
        history.append({"ts": now.isoformat(timespec="minutes"), "date": now.strftime("%Y-%m-%d"), "yt": yt})
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"YouTube: {len(yt)} bài")
    else:
        print("Bỏ qua YouTube: thiếu YOUTUBE_API_KEY hoặc chưa có youtube_id")

    # 2. Google Sheet
    sheet = load(SHEET, {"stream": {}, "ranks": {}})
    s_url = os.environ.get("SHEET_STREAM_CSV", "")
    r_url = os.environ.get("SHEET_RANK_CSV", "")
    t_url = os.environ.get("SHEET_TRACK_RANK_CSV", "")
    if s_url:
        sheet["stream"] = read_stream(fetch_text(s_url))
        print(f"Stream: {len(sheet['stream'])} ngày")
    if r_url:
        sheet["ranks"] = read_ranks(fetch_text(r_url))
        print(f"Thứ hạng album: {len(sheet['ranks'])} ngày")
    if t_url:
        for d, entry in read_ranks(fetch_text(t_url)).items():
            sheet["ranks"].setdefault(d, {}).update(entry)
        print("Đã đọc thứ hạng từng bài")
    sheet["updated"] = now.isoformat(timespec="minutes")
    SHEET.write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")

    # 3. Bìa
    try:
        update_covers(tracks)
    except Exception as e:
        print("Lỗi bìa:", e)


if __name__ == "__main__":
    main()
