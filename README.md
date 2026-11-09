# UPRIZE Tracker

Website tĩnh theo dõi số liệu hằng ngày của UPRIZE:

- **YouTube**: lượt xem MV, lấy tự động qua YouTube Data API v3.
- **Spotify / Apple Music**: không có API công khai cho số stream, nên số tổng được nhập vào `data/manual.json` (hoặc bạn nối nguồn khác vào `fetch_streaming_totals` trong `scripts/update.py`).

## Cấu trúc

```
index.html              giao diện dashboard
tracks.json             danh sách bài hát + ID/link từng nền tảng
data/history.json       lịch sử snapshot mỗi ngày (script tự ghi)
data/manual.json        số tổng Spotify / Apple Music nhập tay
scripts/update.py       lấy số liệu và ghi snapshot hôm nay
.github/workflows/      tự chạy mỗi ngày lúc 00:05 giờ Việt Nam
```

## Cách dùng

1. Mở `tracks.json`, thêm từng bài hát: `id` (viết thường, không dấu), `title`, và `youtube_id`
   (phần sau `v=` trong link YouTube).
2. Lấy YouTube API key (Google Cloud Console → bật YouTube Data API v3 → tạo API key).
3. Chạy thử trên máy:
   ```
   YOUTUBE_API_KEY=xxxx python scripts/update.py
   python -m http.server 8000
   ```
   rồi mở http://localhost:8000. Phải mở qua máy chủ, mở file trực tiếp sẽ không tải được dữ liệu.
4. Đưa lên GitHub, thêm secret `YOUTUBE_API_KEY` (Settings → Secrets and variables → Actions),
   bật GitHub Pages cho nhánh chính. Workflow sẽ tự cập nhật mỗi ngày.

Lượt tăng mỗi ngày được tính bằng chênh lệch giữa hai snapshot liên tiếp, nên biểu đồ cần ít nhất 2 ngày dữ liệu.
