#!/usr/bin/env python3
"""
999 Lá Thư — TikTok Video Pipeline (v5-fix)
- Subtitle dùng PIL render text → ffmpeg overlay (không cần libass)
"""

import json, os, sys, subprocess, time
import urllib.request, urllib.parse

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
    "clouds drifting blue sky", "waterfall mist tropical", "bamboo forest green peaceful",
]

TTS_PROMPT_SHORT = """Convert this Vietnamese monologue into TTS-optimized text.
- Replace punctuation with pauses: ... short, line break medium, empty line long
- Split sentences into breath-sized chunks
- Add 1-2 emotional emphasis words (nhé, thôi, mà, đấy, đâu, cố lên, thôi thì) naturally
- Max 1 emphasis per 2 sentences. Tone: warm, hopeful.
- Plain text only, no explanation.

Input:
{text}

Output:"""

# Subtitle style
SUB_FONT = "/System/Library/Fonts/Helvetica.ttc"
SUB_SIZE = 44
SUB_COLOR = (255, 255, 255, 255)
SUB_OUTLINE = 2  # px


def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def load_used_videos():
    try: return json.load(open(STATE_FILE))
    except: return []

def save_used_videos(ids):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(ids, open(STATE_FILE, "w"))


def call_qwen(prompt):
    payload = json.dumps({"model": OLLAMA_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False, "options": {"temperature": 0.7}})
    tf = f"/tmp/_qwen_{os.getpid()}.json"
    with open(tf, "w") as f: f.write(payload)
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "60", "-d", f"@{tf}", f"{OLLAMA_BASE}/api/chat"], capture_output=True, text=True, timeout=65)
        if r.returncode != 0 or not r.stdout: return ""
        return json.loads(r.stdout)["message"]["content"].strip()
    except: return ""
    finally: os.unlink(tf)


def format_tts_text(raw_text):
    result = call_qwen(TTS_PROMPT_SHORT.replace("{text}", raw_text))
    return result if result else raw_text


def pexels_search(query, per_page=15):
    params = urllib.parse.urlencode({"query": query, "per_page": per_page, "orientation": "portrait", "size": "large"})
    out, _, rc = run(f'curl -s --max-time 15 -H "Authorization: {PEXELS_KEY}" "https://api.pexels.com/videos/search?{params}"')
    if rc != 0 or not out: return []
    try: return json.loads(out).get("videos", [])
    except: return []


def pick_new_videos(videos, used_ids, max_n=3):
    valid = [v for v in videos if v["id"] not in used_ids and v.get("height", 0) >= 1080 and v.get("height", 0) > v.get("width", 0)]
    valid.sort(key=lambda v: v.get("duration", 0), reverse=True)
    return valid[:max_n]


def get_best_file(video):
    return max(video.get("video_files", []), key=lambda f: f.get("width", 0) * f.get("height", 0))["link"]


def download_video(url, outpath):
    print(f"  ⬇ Downloading...")
    _, _, rc = run(f'curl -sL --max-time 60 -o "{outpath}" "{url}"', timeout=70)
    if rc != 0: return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB")
    return True


def generate_tts(text, outpath):
    payload = json.dumps({"text": text, "model_id": ELEVENLABS_MODEL, "voice_settings": {"stability": 0.25, "similarity_boost": 0.5, "style": 0.4, "speed": 1.1, "use_speaker_boost": True}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}?language_code=vi&output_format=mp3_44100_128", data=payload)
    req.add_header("xi-api-key", ELEVENLABS_KEY); req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(outpath, "wb") as f: f.write(resp.read())
        return True
    except Exception as e:
        print(f"  ❌ TTS error: {e}"); return False


# === WHISPER + PIL SUBTITLE ===

def get_whisper_segments(audio_path, video_start_offset=0.5):
    import whisper
    print(f"  🎧 Whisper transcribing (model=small)...")
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, word_timestamps=True, language="vi")
    segments = []
    for seg in result.get("segments", []):
        text = seg["text"].strip()
        if text:
            segments.append({
                "start": seg["start"] + video_start_offset,
                "end": seg["end"] + video_start_offset,
                "text": text,
            })
    print(f"  ✅ Whisper: {len(segments)} segments")
    return segments


def render_subtitle_overlay(segments, outdir, width=1080, height=1920):
    """Render mỗi segment thành 1 ảnh PNG transparent → trả về list (start, end, png_path)"""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype(SUB_FONT, SUB_SIZE)
    except:
        font = ImageFont.load_default()

    os.makedirs(outdir, exist_ok=True)
    overlays = []

    for i, seg in enumerate(segments):
        text = seg["text"]
        # Tạo ảnh full HD trong suốt
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Tính vị trí text: centered, gần đáy
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) / 2
        y = height - th - 120  # margin bottom 120px

        # Draw outline (shadow effect)
        for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            draw.text((x + dx * SUB_OUTLINE, y + dy * SUB_OUTLINE), text, font=font, fill=(0, 0, 0, 180))
        # Draw main text
        draw.text((x, y), text, font=font, fill=SUB_COLOR)

        png_path = f"{outdir}/sub_{i:03d}.png"
        img.save(png_path)
        overlays.append((seg["start"], seg["end"], png_path))

    print(f"  ✅ Rendered {len(overlays)} subtitle PNGs")
    return overlays


def compose_with_subtitle(video_path, audio_path, overlays, outpath, fade_sec=1.0):
    """Ghép video + audio + subtitle overlay dùng ffmpeg."""
    vid_dur = float(json.loads(run(f'ffprobe -v error -show_entries format=duration -of json "{video_path}"')[0])["format"]["duration"])
    aud_dur = float(json.loads(run(f'ffprobe -v error -show_entries format=duration -of json "{audio_path}"')[0])["format"]["duration"])
    print(f"  🎬 Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s")

    if vid_dur <= 0 or aud_dur <= 0: return False

    total_dur = aud_dur + fade_sec

    # Loop video
    if vid_dur < total_dur:
        loops = int(total_dur / vid_dur) + 1
        print(f"  🔄 Looping {loops}x")
        tf = outpath + ".concat_loop.txt"
        with open(tf, "w") as f:
            for _ in range(loops): f.write(f"file '{video_path}'\n")
        video_path = outpath + ".looped.mp4"
        run(f'ffmpeg -y -f concat -safe 0 -i "{tf}" -c copy "{video_path}"')

    # Build filter_complex với overlay cho từng subtitle
    video_inputs = f'-i "{video_path}" '
    overlay_inputs = ""
    for _, _, p in overlays:
        overlay_inputs += f'-i "{p}" '

    # Video scaling + fade
    fade_start = total_dur - fade_sec
    chains = []
    chains.append(f'[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fade=t=in:d=0.8,fade=t=out:d={fade_sec}:start_time={fade_start},fps=30,format=rgba,setpts=PTS-STARTPTS[v0]')

    # Overlay từng subtitle với enable=between(t, start, end)
    prev_label = "v0"
    for i, (start, end, _) in enumerate(overlays):
        input_idx = i + 1
        label = f"v{i+1}"
        chains.append(f'[{prev_label}][{input_idx}:v]overlay=0:0:enable=\\'between(t,{start},{end})\\':format=auto,setpts=PTS-STARTPTS[{label}]')
        prev_label = label

    # Format final
    chains.append(f'[{prev_label}]format=yuv420p[v]')
    chains.append(f'[1:a]adelay=500|500[a]')

    filter_complex = ";".join(chains)

    cmd = (
        f'ffmpeg -y {video_inputs} -i "{audio_path}" {overlay_inputs}'
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" -map "[a]" '
        f'-c:v libx264 -preset fast -crf 20 '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart '
        f'-t {total_dur} -shortest '
        f'"{outpath}"'
    )
    _, err, rc = run(cmd, timeout=180)
    if rc != 0:
        print(f"  ❌ Compose: {err[:400]}")
        return False
    print(f"  ✅ {os.path.getsize(outpath)/1_000_000:.1f} MB, {total_dur:.1f}s")
    return True


def get_duration(filepath):
    try: return float(json.loads(run(f'ffprobe -v error -show_entries format=duration -of json "{filepath}"')[0])["format"]["duration"])
    except: return 0


def concat_videos(paths, outpath):
    if len(paths) == 1:
        run(f'cp "{paths[0]}" "{outpath}"'); return True
    tf = outpath + ".concat.txt"
    with open(tf, "w") as f:
        for p in paths: f.write(f"file '{p}'\n")
    return run(f'ffmpeg -y -f concat -safe 0 -i "{tf}" -c copy "{outpath}"')[2] == 0


def upload_cdn(fp):
    out, _, _ = run(f'curl -s -X POST {CDN_URL} -F "file=@{fp}"', timeout=120)
    if not out: return None
    try: return json.loads(out)["url"]
    except: return None


# === MAIN ===

def pipeline(so_thu, raw_content):
    print(f"\n{'='*60}\n📝 Thư số {so_thu}\n📄 {raw_content[:120]}...\n{'='*60}")
    outdir = f"/tmp/thu_{so_thu}_pexels"
    os.makedirs(outdir, exist_ok=True)
    used_ids = load_used_videos()
    print(f"  📋 Used videos: {len(used_ids)} IDs tracked")

    # 1. Pexels
    all_videos = []
    for kw in PEXELS_QUERIES:
        print(f"  🔍 Pexels: '{kw}'")
        for v in pick_new_videos(pexels_search(kw), used_ids, max_n=2):
            all_videos.append(v)
            print(f"    + id={v['id']}, {v['duration']}s, {v['width']}×{v['height']}")
        time.sleep(0.3)
        if len(all_videos) >= 5: break
    if not all_videos: return print("❌ Không tìm được video!")

    # 2. AI Format TTS
    print(f"  ✍️ Formatting text for TTS...")
    tts_text = format_tts_text(raw_content)
    print(f"  📝 Formatted ({len(tts_text)} chars): {tts_text[:120]}...")

    # 3. ElevenLabs
    ap = f"{outdir}/tts.mp3"
    print(f"  🎙 ElevenLabs...")
    if not generate_tts(tts_text, ap): return
    aud_dur = get_duration(ap)
    print(f"  ✅ TTS: {os.path.getsize(ap)/1000:.0f} KB, {aud_dur:.1f}s")

    # 4. Whisper → segments
    segments = get_whisper_segments(ap, video_start_offset=0.5)

    # 5. Render subtitle PNGs
    sub_dir = f"{outdir}/subtitles"
    overlays = render_subtitle_overlay(segments, sub_dir)

    # 6. Download videos
    target = aud_dur + 5.0; dl, tdur = [], 0
    for v in all_videos:
        if tdur >= target: break
        fp = f"{outdir}/vid_{v['id']}.mp4"
        if download_video(get_best_file(v), fp):
            dl.append(fp); tdur += v.get("duration", 0)
        time.sleep(0.5)
    print(f"  📦 {len(dl)} videos, total {tdur:.1f}s (need > {target:.1f}s)")

    # 7. Concat
    comb = f"{outdir}/combined.mp4"
    if not concat_videos(dl, comb): return print("❌ Concat failed!")

    # 8. Compose with subtitle overlay
    op = f"{outdir}/tiktok.mp4"
    if not compose_with_subtitle(comb, ap, overlays, op): return

    # 9. CDN
    print(f"  ☁️ Uploading CDN...")
    cdn = upload_cdn(op)
    if not cdn: return print(f"MEDIA:{op}")

    # 10. Save used IDs
    for v in all_videos:
        if v["id"] not in used_ids: used_ids.append(v["id"])
    save_used_videos(used_ids)
    print(f"  💾 Saved {len(used_ids)} used IDs\n✅ CDN: {cdn}")
    return cdn


if __name__ == "__main__":
    letters = json.load(open(LETTERS_JSON))
    so = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for l in [l for l in letters if l["so_thu"] == so]:
        r = pipeline(l["so_thu"], l["noi_dung"])
        print(f"\n🔗 RESULT: {r}")
