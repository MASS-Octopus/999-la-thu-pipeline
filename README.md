# 999 Lá Thư — TikTok Video Pipeline

Tự động tạo video TikTok từ các lá thư trong sách "999 Lá Thư Gửi Cho Chính Mình".

## Flow

```
Thư JSON → AI (qwen3.5:cloud) phân tích vibe → sinh keywords
         → Pexels API tìm video portrait nhẹ nhàng
         → AI format text (emotional emphasis prompt)
         → ElevenLabs TTS (eleven_v3, giọng BdXlJle17DV6QV63lzql)
         → ffmpeg compose 1080×1920 TikTok
         → Upload CDN (cdn.lqduong.dev)
```

## Config

| Thành phần | Giá trị |
|---|---|
| AI Model | `qwen3.5:cloud` (localhost:11434) |
| TTS Model | `eleven_v3` |
| TTS Voice | `BdXlJle17DV6QV63lzql` |
| TTS Params | stability=0.25, similarity=0.5, style=0.4, speed=1.1 |
| Video | 1080×1920, H.264 CRF 20, AAC 128k |

## Usage

```bash
python3 pipeline.py <số_thư>
```

## Prerequisites

- Ollama local với `qwen3.5:cloud`
- ElevenLabs API key (set via `hermes config set tts.providers.elevenlabs.api_key`)
- Pexels API key (hardcoded)
- CDN publisher service running on `127.0.0.1:9876`
- `999-la-thu-gui-cho-chinh-minh.json` tại path trong script
