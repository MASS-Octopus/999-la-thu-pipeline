#!/usr/bin/env python3
"""
999 Lá Thư — TikTok Video Pipeline (v6)
- Format TTS thủ công (emotional emphasis rules)
- ElevenLabs with-timestamps → alignment chính xác tuyệt đối
- PIL render subtitle PNGs → ffmpeg overlay 1 lần
"""

import json, os, sys, subprocess, time
import urllib.request, urllib.parse

PEXELS_KEY = "Q3rh4s6N17TYVUhcACEk6kWhPN2UXXU5TX0isucbKnrF0KEw8RrfGOny"
ELEVENLABS_KEY = "a861a7a1c92c5fa8fef4c81a01d2b924a3745d824b902aa6a46b2da1de7e2140"
ELEVENLABS_VOICE = "BdXlJle17DV6QV63lzql"
ELEVENLABS_MODEL = "eleven_v3"
CDN_URL = "http://127.0.0.1:9876/publish"
LETTERS_JSON = "/Volumes/ServerData/Users/octopus/Downloads/sach-chua-lanh/999-la-thu-gui-cho-chinh-minh.json"
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
# Subtitle style
SUB_FONT = "/tmp/snpro-fonts/SNPro-Semibold-VI.ttf"  # SN Pro SemiBold, vietnamese subset
SUB_SIZE = 48  # +2px
SUB_SIDE_PAD = 100
SUB_OUTLINE = 3
SUB_BG_ALPHA = 50  # overlay nền mờ (giảm để hòa video)
SUB_BG_PAD = 16  # padding overlay quanh text
SUB_BG_BLUR = 12  # Gaussian blur radius cho overlay (0 = không blur)


def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def load_used_videos():
    try: return json.load(open(STATE_FILE))
    except: return []

def save_used_videos(ids):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(ids, open(STATE_FILE, "w"))


# === FORMAT TTS (thủ công theo rules emotional emphasis) ===

def format_tts_manual(raw_text):
    """Thêm ... pause, line breaks, emotional emphasis words cho TTS."""
    # Thư số 1: hopeful/warm tone → dùng nhé, thôi, mà, đấy, đâu, cố lên
    text = raw_text.replace("\n", " ").strip()
    
    sentences = [
        "Kể từ hôm nay... mỗi ngày hãy cười lên nhé",
        "",
        "trên đời này... trừ việc sinh tử ra... còn lại đều là chuyện nhỏ thôi",
        "",
        "cho dù gặp phải chuyện buồn gì đi chăng nữa... cũng đừng tự làm khó mình mà",
        "cho dù xảy ra chuyện rắc rối đến thế nào... cũng chẳng cần phải đau lòng đâu",
        "",
        "Hôm nay là ngày bạn còn trẻ nhất đấy... so với những ngày tháng nỗ lực về sau",
        "Bởi vì có ngày mai... hôm nay mãi mãi chỉ là vạch kẻ xuất phát cho hành trình ấy... cố lên nhé",
    ]
    return "\n".join(sentences)


# === PEXELS ===

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


# === ELEVENLABS (with-timestamps) ===

def generate_tts_with_timestamps(text, outpath):
    """Gọi ElevenLabs TTS với alignment timestamps. Trả về (bool, alignment_dict)."""
    payload = json.dumps({"text": text, "model_id": ELEVENLABS_MODEL, "voice_settings": {"stability": 0.25, "similarity_boost": 0.5, "style": 0.4, "speed": 1.1, "use_speaker_boost": True}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}/with-timestamps?language_code=vi&output_format=mp3_44100_128", data=payload)
    req.add_header("xi-api-key", ELEVENLABS_KEY); req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
            import base64
            audio_bytes = base64.b64decode(data["audio_base64"])
            with open(outpath, "wb") as f: f.write(audio_bytes)
        return True, data.get("alignment")
    except Exception as e:
        print(f"  ❌ TTS error: {e}"); return False, None


def alignment_to_segments(alignment, tts_text):
    """Chia segments theo từng câu (phân cách bởi \\n\\n trong TTS text)."""
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]

    # Build words từ alignment
    words = []
    word_chars = []
    word_start = None
    word_end = None

    for i, ch in enumerate(chars):
        if ch in " \n.":
            if word_chars:
                words.append({"start": word_start, "end": word_end, "text": "".join(word_chars)})
                word_chars = []; word_start = None; word_end = None
        else:
            if word_start is None: word_start = starts[i]
            word_chars.append(ch); word_end = ends[i]

    if word_chars:
        words.append({"start": word_start, "end": word_end, "text": "".join(word_chars)})

    # Fix alignment errors + skip dur=0 words
    skip = set()
    for i in range(len(words) - 1):
        w, nxt = words[i], words[i + 1]
        if w["end"] > nxt["start"] + 0.05:
            w["end"] = nxt["start"] - 0.001
        if abs(nxt["end"] - nxt["start"]) < 0.001:
            skip.add(i + 1)
    words = [w for j, w in enumerate(words) if j not in skip]

    # Split TTS text thành các câu (phân cách bởi \\n\\n)
    raw_sentences = [s.strip() for s in tts_text.split("\n\n") if s.strip()]
    # Chuẩn hóa text câu (bỏ ... và khoảng trắng thừa) để match với words
    def norm(s):
        import re
        return re.sub(r'\s+', ' ', s.replace("...", " ")).strip()

    sentences = [{"raw": s, "norm": norm(s)} for s in raw_sentences]

    # Match words vào từng câu
    segments = []
    wi = 0
    for sent in sentences:
        # Tìm các words khớp với câu này
        sent_words = []
        remaining = sent["norm"]
        while wi < len(words) and remaining:
            w = words[wi]
            # So khớp prefix
            if remaining.startswith(w["text"]):
                sent_words.append(w)
                remaining = remaining[len(w["text"]):].lstrip()
                wi += 1
            else:
                # Có thể alignment bỏ sót 1 từ, thử skip 1 word
                wi += 1
                break

        if sent_words:
            segments.append({
                "start": sent_words[0]["start"],
                "end": sent_words[-1]["end"],
                "text": sent["raw"],
                "blank": False
            })
            # Chèn blank nếu có gap đến câu sau
            if wi < len(words):
                gap = words[wi]["start"] - sent_words[-1]["end"]
                if gap > 0.3:
                    segments.append({"start": sent_words[-1]["end"], "end": words[wi]["start"],
                                     "text": "", "blank": True})

    print(f"  ✅ {len(segments)} segments ({len(raw_sentences)} câu + blanks)")
    return segments


def get_duration(fp):
    try: return float(json.loads(run(f'ffprobe -v error -show_entries format=duration -of json "{fp}"')[0])["format"]["duration"])
    except: return 0


def concat_videos(paths, outpath):
    if len(paths) == 1: run(f'cp "{paths[0]}" "{outpath}"'); return True
    tf = outpath + ".concat.txt"
    with open(tf, "w") as f:
        for p in paths: f.write(f"file '{p}'\n")
    return run(f'ffmpeg -y -f concat -safe 0 -i "{tf}" -c copy "{outpath}"')[2] == 0

def render_subtitle_video(segments, outpath, width=1080, height=1920):
    """Tạo video trong suốt với subtitle xuất hiện/tắt theo thời gian."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    try:
        font = ImageFont.truetype(SUB_FONT, SUB_SIZE)
    except:
        font = ImageFont.load_default()

    tmpdir = outpath + ".tmp"
    os.makedirs(tmpdir, exist_ok=True)
    png_paths = []

    text_width = width - 2 * SUB_SIDE_PAD  # 880px cho nội dung

    for i, seg in enumerate(segments):
        if seg.get("blank"):
            # Blank segment → transparent PNG
            pp = f"{tmpdir}/sub_blank_{i:03d}.png"
            Image.new("RGBA", (width, height), (0, 0, 0, 0)).save(pp)
            png_paths.append(pp)
            continue

        lines = wrap_text(seg["text"], font, text_width)

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
        line_widths = [draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0] for line in lines]
        total_h = sum(line_heights) + (len(lines) - 1) * 8
        max_lw = max(line_widths)

        y = (height - total_h) / 2

        # Overlay: vẽ trên layer riêng → blur → paste vào ảnh chính
        if SUB_BG_BLUR > 0:
            bg_x1 = int((width - max_lw) / 2 - SUB_BG_PAD)
            bg_y1 = int(y - SUB_BG_PAD)
            bg_x2 = int((width + max_lw) / 2 + SUB_BG_PAD)
            bg_y2 = int(y + total_h + SUB_BG_PAD)
            bg_w = bg_x2 - bg_x1
            bg_h = bg_y2 - bg_y1

            # Vẽ overlay lên layer nhỏ (chỉ vùng cần)
            bg_layer = Image.new("RGBA", (bg_w + SUB_BG_BLUR * 4, bg_h + SUB_BG_BLUR * 4), (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            bg_draw.rounded_rectangle(
                [SUB_BG_BLUR * 2, SUB_BG_BLUR * 2, bg_w + SUB_BG_BLUR * 2, bg_h + SUB_BG_BLUR * 2],
                radius=20, fill=(0, 0, 0, SUB_BG_ALPHA)
            )
            bg_layer = bg_layer.filter(ImageFilter.GaussianBlur(SUB_BG_BLUR))
            img.paste(bg_layer, (bg_x1 - SUB_BG_BLUR * 2, bg_y1 - SUB_BG_BLUR * 2), bg_layer)
        else:
            bg_x1 = (width - max_lw) / 2 - SUB_BG_PAD
            bg_y1 = y - SUB_BG_PAD
            bg_x2 = (width + max_lw) / 2 + SUB_BG_PAD
            bg_y2 = y + total_h + SUB_BG_PAD
            draw.rounded_rectangle([bg_x1, bg_y1, bg_x2, bg_y2], radius=20, fill=(0, 0, 0, SUB_BG_ALPHA))

        # Vẽ text
        cur_y = y
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            x = (width - lw) / 2

            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                draw.text((x + dx * SUB_OUTLINE, cur_y + dy * SUB_OUTLINE), line, font=font, fill=(0, 0, 0, 180))
            draw.text((x, cur_y), line, font=font, fill=(255, 255, 255, 255))
            cur_y += lh + 8

        pp = f"{tmpdir}/sub_{i:03d}.png"
        img.save(pp)
        png_paths.append(pp)

    # Tạo 1 blank transparent frame (dùng cho gap giữa các từ)
    blank_png = f"{tmpdir}/_blank.png"
    Image.new("RGBA", (width, height), (0, 0, 0, 0)).save(blank_png)

    # Tạo video từ PNGs, chèn blank frame cho gap giữa các segment
    concat_file = outpath + ".sub_concat.txt"
    last_end = 0.0
    with open(concat_file, "w") as f:
        for i, (seg, pp) in enumerate(zip(segments, png_paths)):
            gap = seg["start"] - last_end
            if gap > 0.001:
                f.write(f"file '{blank_png}'\n")
                f.write(f"duration {gap:.3f}\n")
            dur = seg["end"] - seg["start"]
            if dur < 0.001:
                dur = 0.001
            f.write(f"file '{pp}'\n")
            f.write(f"duration {dur:.3f}\n")
            last_end = seg["start"] + dur

    cmd = (
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-vf "fps=30,format=rgba" '
        f'-c:v qtrle '
        f'"{outpath}"'
    )
    _, err, rc = run(cmd, timeout=60)
    if rc != 0:
        print(f"  ❌ Sub video: {err[:300]}")
        return None

    print(f"  ✅ Subtitle video: {os.path.getsize(outpath)/1_000_000:.1f} MB")
    return outpath


def wrap_text(text, font, max_width):
    """Wrap text thành nhiều dòng, giới hạn theo max_width pixel."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip() if current_line else word
        # Dùng textbbox thay textlength (PIL mới)
        try:
            bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except:
            # Fallback: dùng font.getlength hoặc textlength cũ
            try:
                w = font.getlength(test)
            except:
                w = len(test) * (font.size * 0.6)  # rough estimate

        if w <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


def compose_tiktok(video_path, audio_path, sub_video, outpath, fade_sec=1.0):
    vid_dur = get_duration(video_path)
    aud_dur = get_duration(audio_path)
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

    fade_start = total_dur - fade_sec

    cmd = (
        f'ffmpeg -y -i "{video_path}" -i "{audio_path}" -i "{sub_video}" '
        f'-filter_complex '
        f'"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
        f'fade=t=in:d=0.8,fade=t=out:d={fade_sec}:start_time={fade_start},'
        f'fps=30,format=rgba[vbase];'
        f'[vbase][2:v]overlay=0:0:format=auto,format=yuv420p[v];'
        f'[1:a]anull[a]" '
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

    # 2. Format TTS (thủ công)
    print(f"  ✍️ Formatting TTS text...")
    tts_text = format_tts_manual(raw_content)
    print(f"  📝 Formatted ({len(tts_text)} chars): {tts_text[:120]}...")

    # 3. ElevenLabs with timestamps
    ap = f"{outdir}/tts.mp3"
    print(f"  🎙 ElevenLabs (with timestamps)...")
    ok, alignment = generate_tts_with_timestamps(tts_text, ap)
    if not ok: return
    aud_dur = get_duration(ap)
    print(f"  ✅ TTS: {os.path.getsize(ap)/1000:.0f} KB, {aud_dur:.1f}s")

    # 4. Alignment → segments (theo từng câu)
    segments = alignment_to_segments(alignment, tts_text)

    # 5. Render subtitle video
    sub_video = f"{outdir}/subtitle.mov"
    if not render_subtitle_video(segments, sub_video): return

    # 6. Download videos
    target = aud_dur + 5.0; dl, tdur = [], 0
    for v in all_videos:
        if tdur >= target: break
        fp = f"{outdir}/vid_{v['id']}.mp4"
        if download_video(get_best_file(v), fp):
            dl.append(fp); tdur += v.get("duration", 0)
        time.sleep(0.5)
    print(f"  📦 {len(dl)} videos, total {tdur:.1f}s (need > {target:.1f}s)")

    # 7. Concat → compose with subtitle
    comb = f"{outdir}/combined.mp4"
    if not concat_videos(dl, comb): return print("❌ Concat failed!")
    op = f"{outdir}/tiktok.mp4"
    if not compose_tiktok(comb, ap, sub_video, op): return

    # 8. CDN
    print(f"  ☁️ Uploading CDN...")
    cdn = upload_cdn(op)
    if not cdn: return print(f"MEDIA:{op}")

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
