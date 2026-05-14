#!/usr/bin/env python3
"""
Pexels + ElevenLabs TikTok Pipeline cho 999 Lá Thư — v3
- AI phân tích nội dung thư → sinh keyword tìm video Pexels
- Prompt TTS formatter → chuyển text thô thành TTS-optimized
- ElevenLabs eleven_v3 + giọng BdXlJle17DV6QV63lzql
- Chọn 1-5 video đúng vibe, cộng dồn đến khi đủ duration
- Compose 1080×1920 TikTok → upload CDN
"""

import json, os, sys, subprocess, time, tempfile
from pathlib import Path
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
OLLAMA_KEY = "91ff0f7615c84c1db48962a66f639192.m4E-eB92GqXXFVmBp1-gcalE"

TTS_PROMPT = """You are a TTS emotional text formatter. Your job is to convert a short personal monologue into expressive, emotionally rich TTS-optimized text.
Rules:

Keep the original meaning and emotion 100%
Replace punctuation with natural pauses: use ... for short pause, line break for medium pause, empty line for long pause
Remove markdown, symbols, parentheses, brackets
Split long sentences into shorter breath-sized chunks
Add emotional emphasis words naturally into the flow:

Softness/sadness: thật sự... mà... ấy... nhỉ... thôi... vậy đó... chứ sao... buồn lắm... khó lắm... nặng lòng lắm... biết làm sao giờ...
Warmth/comfort: nào... nhé... mà... đấy... thương lắm... hiểu mà... không sao đâu... có tôi đây... yên tâm đi... ổn thôi mà...
Sighing/reflection: ừ thì... biết là... thế mà... nghĩ lại thấy... cũng lạ nhỉ... mà thôi... kệ đi... thôi thì... rốt cuộc là... nhìn lại mới thấy...
Encouragement: cố lên... được mà... nhất định... tin tôi đi... làm được... không bỏ cuộc nhé... từng bước thôi... chậm mà chắc... ngày mai sẽ khác... còn nhiều lắm phía trước...
Longing/missing: nhớ lắm... xa rồi mà vẫn... sao quên được... cứ nghĩ mãi... in sâu trong lòng... dù đã lâu...
Tired/overwhelmed: mệt lắm rồi... kiệt sức rồi... cố mãi cũng... không còn sức... đến giới hạn rồi... buông ra thôi...
Acceptance/letting go: thôi thì... chấp nhận vậy... dù sao... cũng đã qua... bình thản lại thôi... không giữ nữa...
Hope/looking forward: biết đâu được... hy vọng mà... rồi sẽ ổn... còn ngày mai... chờ xem nhé... sẽ tới thôi...


Do NOT overuse — max 1 emphasis word per 2 sentences
Match the emotional tone of the input (sad, hopeful, tired, warm, nostalgic...)
Output plain text only, no explanation

Input:
{user_text}
Output:
TTS-ready plain text with natural emotional emphasis."""


def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


# === AI CALLS ===

def call_ollama(prompt, model=OLLAMA_MODEL):
    """Call Ollama local API via curl subprocess (list args, tránh shell escape issues)."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.7},
    })
    tmpf = f"/tmp/_ollama_payload_{os.getpid()}.json"
    with open(tmpf, "w") as f:
        f.write(payload)
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "120", "-d", f"@{tmpf}", f"{OLLAMA_BASE}/api/chat"],
            capture_output=True, text=True, timeout=130
        )
        if r.returncode != 0 or not r.stdout:
            print(f"  ⚠️ Ollama error: rc={r.returncode}, {r.stderr[:100]}")
            return ""
        return json.loads(r.stdout)["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️ Ollama error: {e}")
        return ""
    finally:
        os.unlink(tmpf)


def analyze_content_for_keywords(content):
    """Dùng AI phân tích nội dung thư → sinh 5 keyword tìm video nhẹ nhàng."""
    prompt = f"""Analyze this Vietnamese letter about self-healing/life wisdom. 
Generate 5 English search keywords for finding peaceful, calming, gentle stock videos on Pexels.
The videos should match the EMOTIONAL VIBE of the text (not literal objects).
Keywords should be descriptive and specific for stock video search.
Return ONLY the 5 keywords, one per line, no numbering, no explanation.

Letter content:
{content}

Keywords:"""

    result = call_ollama(prompt)
    keywords = [k.strip() for k in result.split("\n") if k.strip()]
    return keywords[:5]


def format_tts_text(raw_text):
    """Dùng prompt TTS formatter để chuyển text thô → TTS-optimized."""
    prompt = TTS_PROMPT.replace("{user_text}", raw_text)
    result = call_ollama(prompt, model=OLLAMA_MODEL)
    return result if result else raw_text


# === PEXELS ===

def pexels_search(query, per_page=10):
    """Search Pexels videos API qua curl."""
    params = urllib.parse.urlencode({
        "query": query, "per_page": per_page,
        "orientation": "portrait", "size": "large",
    })
    cmd = (
        f'curl -s --max-time 15 '
        f'-H "Authorization: {PEXELS_KEY}" '
        f'"https://api.pexels.com/videos/search?{params}"'
    )
    out, err, rc = run(cmd)
    if rc != 0 or not out:
        return []
    try:
        return json.loads(out).get("videos", [])
    except:
        return []


def pick_best_videos(videos, max_count=5):
    """Lọc video portrait ≥1080p, sắp xếp theo duration, chọn tối đa max_count."""
    valid = []
    for v in videos:
        w, h = v.get("width", 0), v.get("height", 0)
        dur = v.get("duration", 0)
        if h >= 1080 and h > w:  # portrait
            valid.append(v)
    # Sort by duration descending (prefer longer clips for better immersion)
    valid.sort(key=lambda v: v.get("duration", 0), reverse=True)
    return valid[:max_count]


def get_best_file(video):
    """Lấy file video chất lượng cao nhất."""
    files = video.get("video_files", [])
    best, best_px = None, 0
    for f in files:
        px = f.get("width", 0) * f.get("height", 0)
        if px > best_px:
            best_px = px
            best = f
    return best["link"] if best else None


def download_video(url, outpath):
    """Tải video từ Pexels CDN."""
    print(f"  ⬇ Downloading...")
    cmd = f'curl -sL --max-time 60 -o "{outpath}" "{url}"'
    _, _, rc = run(cmd, timeout=70)
    if rc != 0:
        return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB")
    return True


# === ELEVENLABS ===

def generate_tts(text, outpath):
    """Gọi ElevenLabs API tạo TTS."""
    payload = json.dumps({
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.25,
            "similarity_boost": 0.5,
            "style": 0.4,
            "speed": 1.1,
            "use_speaker_boost": True,
        },
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


# === VIDEO ===

def get_duration(filepath):
    out, _, _ = run(f'ffprobe -v error -show_entries format=duration -of json "{filepath}"')
    try:
        return float(json.loads(out)["format"]["duration"])
    except:
        return 0


def concat_videos(video_paths, outpath):
    """Nối nhiều video thành 1."""
    if len(video_paths) == 1:
        # Copy luôn
        run(f'cp "{video_paths[0]}" "{outpath}"')
        return True
    concat_txt = outpath + ".concat.txt"
    with open(concat_txt, "w") as f:
        for p in video_paths:
            f.write(f"file '{p}'\n")
    cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_txt}" -c copy "{outpath}"'
    _, err, rc = run(cmd)
    return rc == 0


def compose_tiktok(video_path, audio_path, outpath, fade_sec=1.0):
    """Ghép video + audio → TikTok 1080×1920."""
    vid_dur = get_duration(video_path)
    aud_dur = get_duration(audio_path)
    print(f"  🎬 Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s")

    if vid_dur <= 0 or aud_dur <= 0:
        return False

    total_dur = aud_dur + fade_sec

    # Loop video if needed
    working_video = video_path
    if vid_dur < total_dur:
        loops = int(total_dur / vid_dur) + 1
        print(f"  🔄 Looping {loops}x")
        concat_txt = outpath + ".concat_loop.txt"
        with open(concat_txt, "w") as f:
            for _ in range(loops):
                f.write(f"file '{video_path}'\n")
        looped = outpath + ".looped.mp4"
        run(f'ffmpeg -y -f concat -safe 0 -i "{concat_txt}" -c copy "{looped}"')
        working_video = looped

    fade_start = total_dur - fade_sec
    cmd = (
        f'ffmpeg -y -i "{working_video}" -i "{audio_path}" '
        f'-filter_complex '
        f'"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
        f'fade=t=in:d=0.8,fade=t=out:d={fade_sec}:start_time={fade_start},'
        f'fps=30,format=yuv420p[v];'
        f'[1:a]adelay=500|500[a]" '
        f'-map "[v]" -map "[a]" '
        f'-c:v libx264 -preset fast -crf 20 '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart '
        f'-t {total_dur} '
        f'-shortest '
        f'"{outpath}"'
    )
    _, err, rc = run(cmd, timeout=120)
    if rc != 0:
        print(f"  ❌ Compose: {err[:300]}")
        return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB, {total_dur:.1f}s")
    return True


def upload_cdn(filepath):
    cmd = f'curl -s -X POST {CDN_URL} -F "file=@{filepath}"'
    out, err, rc = run(cmd, timeout=120)
    if rc != 0 or not out:
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

    # ── Step 1: AI phân tích → sinh keywords ──
    print(f"  🤖 AI analyzing content for video keywords...")
    keywords = analyze_content_for_keywords(raw_content)
    print(f"  📋 Keywords: {keywords}")

    # ── Step 2: Pexels search → collect videos đến khi đủ duration ──
    all_videos = []
    seen_ids = set()
    for kw in keywords:
        print(f"  🔍 Pexels: '{kw}'")
        results = pexels_search(kw, per_page=10)
        best = pick_best_videos(results, max_count=3)
        for v in best:
            if v["id"] not in seen_ids:
                seen_ids.add(v["id"])
                all_videos.append(v)
                print(f"    + id={v['id']}, {v['duration']}s, {v['width']}×{v['height']}")
        time.sleep(0.3)
        if len(all_videos) >= 5:
            break

    if not all_videos:
        print("❌ Không tìm được video!")
        return None

    # ── Step 3: Preprocess text bằng TTS formatter prompt ──
    print(f"  ✍️ Formatting text for TTS...")
    tts_text = format_tts_text(raw_content)
    print(f"  📝 Formatted ({len(tts_text)} chars): {tts_text[:120]}...")

    # ── Step 4: ElevenLabs TTS ──
    audio_path = f"{outdir}/tts.mp3"
    print(f"  🎙 ElevenLabs ({ELEVENLABS_MODEL}, {ELEVENLABS_VOICE})...")
    if not generate_tts(tts_text, audio_path):
        return None
    aud_dur = get_duration(audio_path)
    print(f"  ✅ TTS: {os.path.getsize(audio_path)/1000:.0f} KB, {aud_dur:.1f}s")

    # ── Step 5: Chọn video cộng dồn đến khi tổng duration > audio duration + buffer ──
    target_dur = aud_dur + 5.0  # cần hơn audio 5s buffer
    downloaded = []
    total_vid_dur = 0
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

    # ── Step 6: Nối video → compose TikTok ──
    combined_video = f"{outdir}/combined.mp4"
    if not concat_videos(downloaded, combined_video):
        print("❌ Concat failed!")
        return None

    output_path = f"{outdir}/tiktok.mp4"
    if not compose_tiktok(combined_video, audio_path, output_path):
        return None

    # ── Step 7: Upload CDN ──
    print(f"  ☁️ Uploading CDN...")
    cdn_url = upload_cdn(output_path)
    if not cdn_url:
        return f"MEDIA:{output_path}"

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
