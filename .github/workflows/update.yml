#!/usr/bin/env python3
"""Chạy mỗi giờ (GitHub Actions).

1. YouTube: lấy lượt xem hiện tại của từng MV, ghi một snapshot có giờ vào data/history.json.
2. Google Sheet (đã publish dạng CSV): kéo số stream Spotify, người nghe hàng tháng
   và thứ hạng vào data/sheet.json. Bỏ qua nếu chưa cấu hình link.

Biến môi trường:
  YOUTUBE_API_KEY     API key YouTube Data API v3
  SHEET_STREAM_CSV    link CSV của tab Stream
  SHEET_RANK_CSV      link CSV của tab Thứ hạng
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
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
RANK_COLS = ["spotify_vn", "apple_music_vn", "itunes_vn"]


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def fetch_text(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def digits(s):
    """'31.220' -> 31220, '' -> None"""
    d = re.sub(r"\D", "", s or "")
    return int(d) if d else None


def youtube_views(ids, api_key):
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        qs = urllib.parse.urlencode({"part": "statistics", "id": ",".join(chunk), "key": api_key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/videos?{qs}", timeout=30) as resp:
            data = json.load(resp)
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
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip() for h in rows[0]]
    out = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        entry = {}
        for h, v in zip(head[1:], r[1:]):
            n = digits(v)
            if h in RANK_COLS and n is not None:
                entry[h] = n
        if entry:
            out[r[0].strip()] = entry
    return out


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
        print(f"YouTube: {len(yt)} bài, ghi snapshot {now:%Y-%m-%d %H:%M}")
    else:
        print("Bỏ qua YouTube: thiếu YOUTUBE_API_KEY hoặc chưa có youtube_id")

    # 2. Google Sheet
    sheet = load(SHEET, {"stream": {}, "ranks": {}})
    s_url = os.environ.get("SHEET_STREAM_CSV", "")
    r_url = os.environ.get("SHEET_RANK_CSV", "")
    if s_url:
        sheet["stream"] = read_stream(fetch_text(s_url))
        print(f"Stream: {len(sheet['stream'])} ngày")
    if r_url:
        sheet["ranks"] = read_ranks(fetch_text(r_url))
        print(f"Thứ hạng: {len(sheet['ranks'])} ngày")
    sheet["updated"] = now.isoformat(timespec="minutes")
    SHEET.write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
