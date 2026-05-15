# OneJAV Telegram Bot — Plan v2

**Goal:** Telegram bot `/get` → scrape OneJAV/new (tăng dần pages, tối đa 100 items) → gửi thumb + title + 2 button [Download/Reject] → click Download → xóa message → add torrent qBittorrent → cronjob 4h update status → max 5 concurrent download → post-download filter <1GB delete → copy ≥1GB vào Jellyfin media.

**Created:** 2026-05-15 20:00 | **Updated:** 2026-05-15 20:10  
**Status:** ✅ Approved — ready to build

---

## 🎯 Quyết định từ review

| # | Vấn đề | Quyết định |
|---|--------|------------|
| 1 | Cách chạy bot | **Process riêng** — launchd trên macOS, persistent |
| 2 | Magnet link | **Không cần** — chỉ .torrent file |
| 3 | Jellyfin scan | **Manual** — không auto-trigger |
| 4 | Scrape range | **Tăng dần pages** cho đến khi đủ 100 items, bỏ qua item đã check |
| 5 | Progress UI | **Xóa message** sau click; cronjob 4h update status torrents |
| 6 | Message format | **Chỉ title + thumb** (không size, date) |
| 7 | Concurrent DL | **Max 5 video** đang download cùng lúc |

---

## 🔄 Flow cập nhật

### Flow 1: `/get`

```
User: /get
  │
  ├─ 1. Scrape OneJAV/new, page 1 → 2 → 3 → ...
  │     Dừng khi: (a) đủ 100 items chưa seen, hoặc (b) hết pages
  │
  ├─ 2. Filter: bỏ code đã có trong seen_codes (rejected ∪ downloaded)
  │
  ├─ 3. Lấy item đầu tiên
  │
  ├─ 4. Download thumbnail → cache
  │
  └─ 5. Gửi Telegram:
        Photo: thumb
        Caption: "{code}"  (chỉ code, không title dài)
        Buttons: [⬇️ Download] [❌ Reject]
```

> **Note:** Anh nói "chỉ cần tên + thumb" → gửi code (FC2PPV...) + thumb. Không cần full title dài.

### Flow 2: Click [⬇️ Download]

```
Callback: download:{code}:{torrent_url}
  │
  ├─ 1. Kiểm tra: active downloads < 5? Nếu = 5 → alert "Đang down tối đa 5 video, thử lại sau"
  │
  ├─ 2. Download .torrent → /tmp/
  │
  ├─ 3. Gọi qBittorrent API: add torrent, savepath=/downloads/{code}/
  │
  ├─ 4. Ghi vào downloading.json: {code: {torrent_hash, start_ts, status: "downloading"}}
  │
  ├─ 5. XÓA message Telegram (không edit)
  │
  └─ 6. Gửi message mới: "⏳ {code} — đã thêm vào queue"
        → Message này sẽ được cronjob cập nhật sau
```

### Flow 3: Click [❌ Reject]

```
Callback: reject:{code}
  │
  ├─ 1. Ghi rejected.json
  │
  └─ 2. XÓA message Telegram
```

### Flow 4: Cronjob 4h — update download status

```
Mỗi 4 giờ:
  │
  ├─ 1. Đọc downloading.json → active torrents
  │
  ├─ 2. Gọi qBittorrent API: GET torrent info theo hash
  │
  ├─ 3. Với mỗi torrent:
  │     - "downloading" → update progress (% + speed) → edit message
  │     - "completed" / "pausedUP" → trigger post-download pipeline
  │     - "stalled" > 24h → alert user + remove
  │
  ├─ 4. Post-download pipeline (khi completed):
  │     - Duyệt /Volumes/.../VideoServerMedia/{code}/
  │     - Xóa file < 1GB
  │     - Copy file ≥ 1GB → .../media/
  │     - Xóa folder gốc {code}
  │     - Ghi downloaded.json, xóa khỏi downloading.json
  │     - Edit/send message: "✅ {code} — xong, copy vào media"
  │
  └─ 5. Nếu có slot trống (< 5 active) → gửi hint "Còn {N} slot, /get để thêm"
```

### Flow 5: `/status`

```
/status → liệt kê tất cả torrent đang download:
  {code} — {progress}% ({speed}) [{eta}]
  ...
  Active: {N}/5 slots
```

---

## 🏗 Kiến trúc

```
┌─────────────┐
│  launchd    │  persistent, auto-restart
│  macOS      │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│  onejav-bot (Python asyncio)                │
│                                             │
│  ┌──────────┐  ┌───────────┐  ┌─────────┐ │
│  │ Telegram │  │ Scraper   │  │ qBit    │ │
│  │ Handlers │  │ (OneJAV)  │  │ Client  │ │
│  └──────────┘  └───────────┘  └─────────┘ │
│       │              │              │       │
│  ┌────▼──────────────▼──────────────▼────┐ │
│  │         State Manager                 │ │
│  │  rejected.json / downloaded.json      │ │
│  │  downloading.json                     │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  Cron scheduler (4h)                  │ │
│  │  - Poll download status               │ │
│  │  - Post-download filter + copy        │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
       │
       ├──→ qBittorrent API (:9091) — add/poll torrents
       ├──→ OneJAV.com — scrape listing
       └──→ Filesystem — filter/copy files
```

---

## 📁 Files

```
~/.hermes/services/onejav-bot/
├── main.py              # Bot entry + launchd plist generator
├── bot.py               # Telegram handlers (/get, /status, callbacks)
├── scraper.py           # OneJAV scraper: pagination, parse items
├── qbit_client.py       # qBittorrent API: auth, add, status, pause
├── state.py             # JSON state manager
├── post_download.py     # Filter <1GB, copy ≥1GB to media
├── scheduler.py         # Built-in cron 4h: poll status + post-download
├── config.py            # Env vars: TELEGRAM_TOKEN, QBIT_URL/PASS, paths
├── requirements.txt
└── data/
    ├── rejected.json     # {"code": {"ts": "...", "reason": "reject"}}
    ├── downloaded.json   # {"code": {"ts": "...", "path": "/media/..."}}
    ├── downloading.json  # {"code": {"hash": "...", "ts": "...", "msg_id": 123}}
    └── cache/            # Thumbnails (7-day TTL)
```

---

## 🔧 Prerequisites cần giải quyết

### 1. qBittorrent password 🔴
- `admin:adminadmin` → bị đổi, API trả về "Fails."
- **Fix:** Đọc config từ Docker volume để lấy password hash, hoặc reset:
  ```bash
  DOCKER_HOST=unix:///... docker exec qbittorrent cat /config/qBittorrent/qBittorrent.conf
  ```
- Hoặc set temporary bypass: `WebUI\AuthSubnetWhitelist=127.0.0.1/32,192.168.0.0/16`

### 2. Telegram Bot Token 🟡
- Tạo qua @BotFather → lưu vào `.env`

### 3. OneJAV HTML parsing
- Items: mỗi item có heading `<h5>` chứa code, ảnh thumb từ fc2.com, download link
- URL pattern: `/torrent/{code}/download/{id}/onejav.com_{code}.torrent`

---

## 📋 Build order

| # | Step | File | Prio |
|---|------|------|------|
| 1 | Fix qBittorrent auth | `qbit_client.py` prep | 🔴 |
| 2 | Scaffold project + venv + deps | `main.py`, `config.py`, `requirements.txt` | 🔴 |
| 3 | State manager | `state.py` | 🟡 |
| 4 | OneJAV scraper (paginate, parse) | `scraper.py` | 🟡 |
| 5 | qBittorrent client (auth, add, poll) | `qbit_client.py` | 🟡 |
| 6 | Telegram bot handlers (/get, /status, callbacks) | `bot.py` | 🟡 |
| 7 | Post-download filter + copy | `post_download.py` | 🟡 |
| 8 | Cron scheduler (4h loop) | `scheduler.py` | 🟡 |
| 9 | launchd plist generator | `main.py` | 🟢 |
| 10 | Integration test full flow | all | 🟡 |

---

## ⚠️ Constraints & Guards

- **Max concurrent downloads:** 5 — check `len(downloading.json)` trước khi add torrent
- **Page scrape limit:** 100 unseen items, scrape tuần tự page 1, 2, 3...
- **File size filter:** 1 GB = 1,073,741,824 bytes — delete anything smaller
- **Copy strategy:** Copy (không move) file ≥1GB → media/, rồi xoá folder gốc. Lý do: qBittorrent đang seed từ folder gốc, move sẽ break seed.
- **Download timeout:** 24h — stall >24h → alert + xóa torrent
- **Thumb cache:** Xóa sau 7 ngày
- **Telegram message:** Sau click button → delete message ngay, gửi status message mới

---

## 🔄 State transitions

```
[unseen] ──/get──→ [sent to user]
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
       [rejected]            [downloading]
       rejected.json         downloading.json
                                 │
                          ┌──────┴──────┐
                          ▼              ▼
                    [completed]      [stalled >24h]
                    downloaded.json   alert + remove
                    copy to media
```

---

Sẵn sàng build khi Anh confirm. Em sẽ bắt đầu với fix qBittorrent auth trước.
