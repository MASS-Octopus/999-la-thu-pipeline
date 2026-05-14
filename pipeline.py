#!/usr/bin/env python3
"""
999 Lá Thư — TikTok Video Pipeline (v5)
- Bỏ AI keywords → 15 keyword nature cố định + tracking tránh trùng
- AI format TTS (emotional emphasis, prompt rút gọn để tránh timeout qwen3.5)
- ElevenLabs eleven_v3 + giọng BdXlJle17DV6QV63lzql
- Whisper word timestamps → .ass subtitle chạy theo giọng đọc
- ffmpeg compose 1080×1920 + burn-in subtitle → upload CDN
"""

import json, os, sys, subprocess, time, re
import urllib.request, urllib.parse

# === CONFIG ===
PEXELS_KEY = "Q3rh4s6N17TYVUhcACEk6kWhPN2UXXU5TX0isucbKnrF0KEw8RrfGOny"
ELEVENLABS_KEY = "a861a7a1c92c5fa8fef4c81a01d2b924a3745d824b902aa6a46b2da1de7e2140"
ELEVENLABS_VOICE = "BdXlJle17DV6QV63lzql"
ELEVENLABS_MODEL = "eleven_v3"
CDN_URL = "http://127.0.0.1:9876/publish"
LETTERS_JSON = "/Volumes/ServerData/Users/octopus/Downloads/sach-chua-lanh/999-la-thu-gui-cho-chinh-minh.json"
OLLAMA_MODEL = "qwen3.5:cloud"
OLLAMA_BASE = "http://localhost:11434"
STATE_FILE = os.path.expanduser("~/.hermes/state/pexels_used_videos.json")

PEXELS_QUERIES = [
    "nature peaceful landscape", "calm ocean waves beach",
    "gentle sunlight forest", "serene mountain lake",
    "soft flower bloom garden", "quiet river stream water",
    "warm sunset golden hour", "morning dew green leaves",
    "zen garden meditation", "autumn leaves falling breeze",
    "meadow grass wind soft", "lavender field purple calm",
    "clouds drifting blue sky", "waterfall mist tropical",
    "bamboo forest green peaceful",
]

# Prompt rút gọn — bỏ danh sách emphasis dài, giữ instruction chính
TTS_PROMPT_SHORT = """Convert this Vietnamese monologue into TTS-optimized text.
- Replace punctuation with pauses: ... short, line break medium, empty line long
- Split sentences into breath-sized chunks
- Add 1-2 emotional emphasis words (nhé, thôi, mà, đấy, đâu, cố lên, thôi thì) naturally
- Max 1 emphasis per 2 sentences. Tone: warm, hopeful.
- Plain text only, no explanation.

Input:
{text}

Output:"""


def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


# === STATE ===

def load_used_videos():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return []

def save_used_videos(ids):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(ids, f)


# === AI (Qwen 3.5 via Ollama local) ===

def call_qwen(prompt):
    payload = json.dumps({
        "model": OLLAMA_MODEL, "messages": [{"role": "user", "content": prompt}],
        "stream": False, "think": False, "options": {"temperature": 0.7},
    })
    tmpf = f"/tmp/_qwen_{os.getpid()}.json"
    with open(tmpf, "w") as f:
        f.write(payload)
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "60", "-d", f"@{tmpf}", f"{OLLAMA_BASE}/api/chat"],
            capture_output=True, text=True, timeout=65
        )
        if r.returncode != 0 or not r.stdout:
            print(f"    ⚠️ Qwen: rc={r.returncode}, {r.stderr[:80] if r.stderr else ''}")
            return ""
        return json.loads(r.stdout)["message"]["content"].strip()
    except Exception as e:
        print(f"    ⚠️ Qwen exception: {e}")
        return ""
    finally:
        os.unlink(tmpf)


def format_tts_text(raw_text):
    prompt = TTS_PROMPT_SHORT.replace("{text}", raw_text)
    result = call_qwen(prompt)
    return result if result else raw_text


# === PEXELS ===

def pexels_search(query, per_page=15):
    params = urllib.parse.urlencode({
        "query": query, "per_page": per_page, "orientation": "portrait", "size": "large",
    })
    out, _, rc = run(
        f'curl -s --max-time 15 -H "Authorization: {PEXELS_KEY}" '
        f'"https://api.pexels.com/videos/search?{params}"'
    )
    if rc != 0 or not out:
        return []
    try:
        return json.loads(out).get("videos", [])
    except:
        return []


def pick_new_videos(videos, used_ids, max_n=3):
    valid = []
    for v in videos:
        if v["id"] in used_ids:
            continue
        h, w = v.get("height", 0), v.get("width", 0)
        if h >= 1080 and h > w:
            valid.append(v)
    valid.sort(key=lambda v: v.get("duration", 0), reverse=True)
    return valid[:max_n]


def get_best_file(video):
    best, best_px = None, 0
    for f in video.get("video_files", []):
        px = f.get("width", 0) * f.get("height", 0)
        if px > best_px:
            best_px = px
            best = f
    return best["link"] if best else None


def download_video(url, outpath):
    print(f"  ⬇ Downloading...")
    _, _, rc = run(f'curl -sL --max-time 60 -o "{outpath}" "{url}"', timeout=70)
    if rc != 0:
        return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB")
    return True


# === ELEVENLABS ===

def generate_tts(text, outpath):
    payload = json.dumps({
        "text": text, "model_id": ELEVENLABS_MODEL,
        "voice_settings": {"stability": 0.25, "similarity_boost": 0.5, "style": 0.4, "speed": 1.1, "use_speaker_boost": True},
    }).encode()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}?language_code=vi&output_format=mp3_44100_128"
    req = urllib.request.Request(url, data=payload)
    req.add_header("xi-api-key", ELEVENLABS_KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(outpath, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  ❌ TTS error: {e}")
        return False


# === WHISPER SUBTITLE ===

def create_subtitle(audio_path, out_ass, video_start_offset=0.5):
    """Dùng Whisper transcribe audio → tạo file .ass subtitle."""
    import whisper

    print(f"  🎧 Whisper transcribing (model=small)...")
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, word_timestamps=True, language="vi")

    # Gộp words thành câu dựa trên pauses > 0.5s
    segments = []
    current_words = []
    current_start = None

    for seg in result.get("segments", []):
        words = seg.get("words", [])
        if not words:
            continue

        seg_start = words[0]["start"] + video_start_offset
        seg_end = words[-1]["end"] + video_start_offset
        text = seg["text"].strip()

        if text:
            segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": text,
            })

    # Viết file .ass
    ass_header = """[Script Info]
Title: 999 Lá Thư
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Helvetica Neue,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,1.5,2,20,20,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(out_ass, "w") as f:
        f.write(ass_header)
        for seg in segments:
            start_ts = format_ass_time(seg["start"])
            end_ts = format_ass_time(seg["end"])
            text = seg["text"].replace("\n", "\\N")
            f.write(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}\n")

    print(f"  ✅ Subtitle: {len(segments)} lines → {out_ass}")
    return out_ass


def format_ass_time(seconds):
    """Convert seconds → ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# === VIDEO ===

def get_duration(filepath):
    out, _, _ = run(f'ffprobe -v error -show_entries format=duration -of json "{filepath}"')
    try:
        return float(json.loads(out)["format"]["duration"])
    except:
        return 0


def concat_videos(paths, outpath):
    if len(paths) == 1:
        run(f'cp "{paths[0]}" "{outpath}"')
        return True
    tf = outpath + ".concat.txt"
    with open(tf, "w") as f:
        for p in paths:
            f.write(f"file '{p}'\n")
    return run(f'ffmpeg -y -f concat -safe 0 -i "{tf}" -c copy "{outpath}"')[2] == 0


def compose_tiktok(video_path, audio_path, outpath, subtitle_ass=None, fade_sec=1.0):
    vid_dur = get_duration(video_path)
    aud_dur = get_duration(audio_path)
    print(f"  🎬 Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s")

    if vid_dur <= 0 or aud_dur <= 0:
        return False

    total_dur = aud_dur + fade_sec
    wv = video_path

    if vid_dur < total_dur:
        loops = int(total_dur / vid_dur) + 1
        print(f"  🔄 Looping {loops}x")
        tf = outpath + ".concat_loop.txt"
        with open(tf, "w") as f:
            for _ in range(loops):
                f.write(f"file '{video_path}'\n")
        wv = outpath + ".looped.mp4"
        run(f'ffmpeg -y -f concat -safe 0 -i "{tf}" -c copy "{wv}"')

    fade_start = total_dur - fade_sec

    # Video filter chain
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"fade=t=in:d=0.8,fade=t=out:d={fade_sec}:start_time={fade_start},"
        f"fps=30,format=yuv420p"
    )

    # Thêm subtitle filter nếu có
    if subtitle_ass and os.path.exists(subtitle_ass):
        vf += f",ass={subtitle_ass}"
        print(f"  📝 Subtitle burn-in: {subtitle_ass}")

    cmd = (
        f'ffmpeg -y -i "{wv}" -i "{audio_path}" '
        f'-filter_complex '
        f'"[0:v]{vf}[v];'
        f'[1:a]adelay=500|500[a]" '
        f'-map "[v]" -map "[a]" '
        f'-c:v libx264 -preset fast -crf 20 '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart '
        f'-t {total_dur} '
        f'-shortest '
        f'"{outpath}"'
    )
    _, err, rc = run(cmd, timeout=180)
    if rc != 0:
        print(f"  ❌ Compose: {err[:300]}")
        return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB, {total_dur:.1f}s")
    return True


def upload_cdn(filepath):
    out, _, _ = run(f'curl -s -X POST {CDN_URL} -F "file=@{filepath}"', timeout=120)
    if not out:
        return None
    try:
        return json.loads(out)["url"]
    except:
        return None


# === MAIN PIPELINE ===

def pipeline(so_thu, raw_content):
    print(f"\n{'='*60}")
    print(f"📝 Thư số {so_thu}")
    print(f"📄 {raw_content[:120]}...")
    print(f"{'='*60}")

    outdir = f"/tmp/thu_{so_thu}_pexels"
    os.makedirs(outdir, exist_ok=True)

    used_ids = load_used_videos()
    print(f"  📋 Used videos: {len(used_ids)} IDs tracked")

    # ── Step 1: Pexels search (keywords cố định, tránh trùng) ──
    all_videos = []
    for kw in PEXELS_QUERIES:
        print(f"  🔍 Pexels: '{kw}'")
        results = pexels_search(kw)
        new = pick_new_videos(results, used_ids, max_n=2)
        for v in new:
            all_videos.append(v)
            print(f"    + id={v['id']}, {v['duration']}s, {v['width']}×{v['height']}")
        time.sleep(0.3)
        if len(all_videos) >= 5:
            break

    if not all_videos:
        print("❌ Không tìm được video mới! Reset state file?")
        return None

    # ── Step 2: AI format TTS text (prompt ngắn) ──
    print(f"  ✍️ Formatting text for TTS (qwen3.5:cloud, short prompt)...")
    tts_text = format_tts_text(raw_content)
    print(f"  📝 Formatted ({len(tts_text)} chars): {tts_text[:120]}...")

    # ── Step 3: ElevenLabs TTS ──
    audio_path = f"{outdir}/tts.mp3"
    print(f"  🎙 ElevenLabs ({ELEVENLABS_MODEL}, {ELEVENLABS_VOICE})...")
    if not generate_tts(tts_text, audio_path):
        return None
    aud_dur = get_duration(audio_path)
    print(f"  ✅ TTS: {os.path.getsize(audio_path)/1000:.0f} KB, {aud_dur:.1f}s")

    # ── Step 4: Whisper subtitle ──
    subtitle_ass = f"{outdir}/subtitle.ass"
    create_subtitle(audio_path, subtitle_ass, video_start_offset=0.5)

    # ── Step 5: Download video đến khi đủ duration ──
    target_dur = aud_dur + 5.0
    downloaded, total_vid_dur = [], 0
    for v in all_videos:
        if total_vid_dur >= target_dur:
            break
        url = get_best_file(v)
        if not url:
            continue
        fpath = f"{outdir}/vid_{v['id']}.mp4"
        if download_video(url, fpath):
            downloaded.append(fpath)
            total_vid_dur += v.get("duration", 0)
        time.sleep(0.5)

    print(f"  📦 {len(downloaded)} videos, total {total_vid_dur:.1f}s (need > {target_dur:.1f}s)")

    # ── Step 6: Concat + compose (có subtitle burn-in) ──
    combined = f"{outdir}/combined.mp4"
    if not concat_videos(downloaded, combined):
        print("❌ Concat failed!")
        return None

    output_path = f"{outdir}/tiktok.mp4"
    if not compose_tiktok(combined, audio_path, output_path, subtitle_ass=subtitle_ass):
        return None

    # ── Step 7: Upload CDN ──
    print(f"  ☁️ Uploading CDN...")
    cdn_url = upload_cdn(output_path)
    if not cdn_url:
        return f"MEDIA:{output_path}"

    # ── Step 8: Save used video IDs ──
    for v in all_videos:
        if v["id"] not in used_ids:
            used_ids.append(v["id"])
    save_used_videos(used_ids)
    print(f"  💾 Saved {len(used_ids)} used IDs")

    print(f"\n✅ CDN: {cdn_url}")
    return cdn_url


if __name__ == "__main__":
    with open(LETTERS_JSON) as f:
        letters = json.load(f)

    so = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    matched = [l for l in letters if l["so_thu"] == so]

    for letter in matched:
        result = pipeline(letter["so_thu"], letter["noi_dung"])
        print(f"\n🔗 RESULT: {result}")
