#!/usr/bin/env python3
"""Lấy số liệu hôm nay và thêm vào data/history.json.

- YouTube: lấy tự động qua YouTube Data API v3 (biến môi trường YOUTUBE_API_KEY).
- Spotify / Apple Music: không có API công khai trả số stream, nên đọc từ
  data/manual.json (hoặc bạn tự nối nguồn khác vào hàm `fetch_streaming_totals`).
"""
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKS = ROOT / "tracks.json"
HISTORY = ROOT / "data" / "history.json"
MANUAL = ROOT / "data" / "manual.json"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def youtube_views(video_ids, api_key):
    """Trả về {video_id: views}. Gọi theo lô tối đa 50 video."""
    out = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        qs = urllib.parse.urlencode(
            {"part": "statistics", "id": ",".join(chunk), "key": api_key}
        )
        url = f"https://www.googleapis.com/youtube/v3/videos?{qs}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        for item in data.get("items", []):
            out[item["id"]] = int(item["statistics"].get("viewCount", 0))
    return out


def fetch_streaming_totals(track):
    """Móc nối nguồn Spotify / Apple Music ở đây nếu bạn có.
    Mặc định đọc từ data/manual.json."""
    manual = load_json(MANUAL, {})
    entry = manual.get(track["id"], {})
    return entry.get("spotify_streams"), entry.get("apple_plays")


def main():
    tracks = load_json(TRACKS, {"tracks": []})["tracks"]
    history = load_json(HISTORY, [])
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    yt_ids = [t["youtube_id"] for t in tracks if t.get("youtube_id")]
    yt = {}
    if yt_ids and api_key:
        yt = youtube_views(yt_ids, api_key)
    elif yt_ids:
        print("Thiếu YOUTUBE_API_KEY, bỏ qua YouTube.")

    snap = {"date": today, "tracks": {}}
    for t in tracks:
        spotify, apple = fetch_streaming_totals(t)
        snap["tracks"][t["id"]] = {
            "youtube_views": yt.get(t.get("youtube_id")),
            "spotify_streams": spotify,
            "apple_plays": apple,
        }

    history = [h for h in history if h["date"] != today] + [snap]
    history.sort(key=lambda h: h["date"])
    HISTORY.write_text(
        json.dumps(history, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Đã ghi snapshot {today} cho {len(tracks)} bài.")


if __name__ == "__main__":
    main()
