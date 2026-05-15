#!/usr/bin/env python3
"""
999 Lá Thư — TikTok Video Pipeline (v6)
- Format TTS thủ công (emotional emphasis rules)
- ElevenLabs with-timestamps → alignment chính xác tuyệt đối
- PIL render subtitle PNGs → ffmpeg overlay 1 lần
"""

import json, os, sys, subprocess, time, random
import urllib.request, urllib.parse

PEXELS_KEY = "Q3rh4s6N17TYVUhcACEk6kWhPN2UXXU5TX0isucbKnrF0KEw8RrfGOny"
ELEVENLABS_KEY = "a861a7a1c92c5fa8fef4c81a01d2b924a3745d824b902aa6a46b2da1de7e2140"
ELEVENLABS_VOICE = "BdXlJle17DV6QV63lzql"
ELEVENLABS_MODEL = "eleven_v3"
CDN_URL = "http://127.0.0.1:9876/publish"
LETTERS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "letters.json")
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
SUB_SIZE = 50  # +2px (48→50)
SUB_SIDE_PAD = 100
SUB_OUTLINE = 3
SUB_BG_ALPHA = 0  # bỏ overlay nền
FADE_MS = 0.2  # fade in/out 200ms
VIDEO_START_DELAY = 1.0  # text + audio bắt đầu sau 1s
VIDEO_END_PAD = 3.0  # video chạy thêm 3s sau giọng đọc


def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def load_used_videos():
    try:
        ids = json.load(open(STATE_FILE))
        if len(ids) > 100:
            print(f"  🔄 Auto-reset: {len(ids)} > 100 video IDs → clear")
            return []
        return ids
    except:
        return []

def save_used_videos(ids):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(ids, open(STATE_FILE, "w"))


# === FORMAT TTS (LLM via Ollama, manual fallback) ===

TTS_FORMAT_PROMPT = """CRITICAL RULE: Output VIETNAMESE ONLY. Never output Chinese, Hanzi, Kanji, CJK, or any non-Vietnamese script. If you output non-Vietnamese text, the system will reject your response.

You are a TTS emotional text formatter. Your job is to convert a short personal monologue into expressive, emotionally rich TTS-optimized text — written as if a close friend is speaking warmly to their best friend.

Rules:
- NO INTRO, NO EXPLANATION, NO META — start directly with the formatted text. Never output phrases like "Dưới đây là...", "Here is...", "Phiên bản..."
- Keep the original meaning and emotion 100%
- Write as a close friend speaking to their best friend — always use full natural sentences with subject and verb. Người nói xưng "tôi/mình", gọi người nghe là "bạn/cậu". Never drop the subject or verb. Avoid fragment phrases that sound like captions or slogans.
- Replace punctuation with natural pauses: use ... for short pause, line break for medium pause, empty line for long pause
- Remove markdown, symbols, parentheses, brackets, quotes
- Split long sentences into shorter breath-sized chunks
- Add emotional emphasis words naturally into the flow:
  - Softness/sadness: thật sự... mà... ấy... nhỉ... thôi... vậy đó... chứ sao... buồn lắm... khó lắm... nặng lòng lắm... biết làm sao giờ...
  - Warmth/comfort: nào... nhé... mà... đấy... thương lắm... hiểu mà... không sao đâu... có tôi đây... yên tâm đi... ổn thôi mà...
  - Sighing/reflection: ừ thì... biết là... thế mà... nghĩ lại thấy... cũng lạ nhỉ... mà thôi... kệ đi... thôi thì... rốt cuộc là... nhìn lại mới thấy...
  - Encouragement: cố lên... được mà... nhất định... tin tôi đi... làm được... không bỏ cuộc nhé... từng bước thôi... chậm mà chắc... ngày mai sẽ khác... còn nhiều lắm phía trước...
  - Longing/missing: nhớ lắm... xa rồi mà vẫn... sao quên được... cứ nghĩ mãi... in sâu trong lòng... dù đã lâu...
  - Tired/overwhelmed: mệt lắm rồi... kiệt sức rồi... cố mãi cũng... không còn sức... đến giới hạn rồi... buông ra thôi...
  - Acceptance/letting go: thôi thì... chấp nhận vậy... dù sao... cũng đã qua... bình thản lại thôi... không giữ nữa...
  - Hope/looking forward: biết đâu được... hy vọng mà... rồi sẽ ổn... còn ngày mai... chờ xem nhé... sẽ tới thôi...
- Do NOT overuse — max 1 emphasis word per 2 sentences
- Match the emotional tone of the input (sad, hopeful, tired, warm, nostalgic...)
- Keep the text concise but emotionally complete — capture the full emotional journey, don't truncate mid-feeling
- Output in Vietnamese ONLY. Never output Chinese characters, Hanzi, Kanji, or any CJK script.
- Output plain text only, no explanation

Input: {text}

Output: TTS-ready plain text, written as a warm friend speaking to their best friend, with natural emotional emphasis."""


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemini-3-flash-preview:cloud"  # model chính cho format text


def clean_vni_errors(text):
    """Clean common VNI/Times OCR artifacts from Vietnamese text."""
    import re
    # Remove standalone z/zZ artifacts (OCR noise from page numbers)
    text = re.sub(r'\bz\s*zZ?\b', '', text)
    # Remove trailing artifacts like "z FÁ", "z zZ Bức thư thứ..."
    text = re.sub(r'\bz\s+\w+\s*$', '', text)
    # Fix common mixed-case errors: uppercase letter at end of lowercase word
    # "giaI" → "giai", "coI" → "coi", "saI" → "sai", "aI" → "ai"
    text = re.sub(r'\b([a-zà-ỹ]+)([A-Z])\b', lambda m: m.group(1) + m.group(2).lower(), text)
    # Fix "nỰC" → "nực", "CƯỜI" → "cười" (VNI all-caps diacritics)
    text = re.sub(r'Ự', 'ự', text).strip()
    # Clean multiple spaces
    text = re.sub(r'\s{3,}', ' ', text)
    return text.strip()


def _call_ollama_format(prompt):
    """Gọi Ollama API để format raw text → emotional TTS text."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2048, "think": False}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.load(resp).get("message", {}).get("content", "")
    except Exception as e:
        print(f"  ⚠️ Ollama format failed: {e}")
        return None


def _parse_formatted_text(text):
    """Parse LLM output thành list sentences. Tách theo dấu câu + line breaks.
    Tự động strip Chinese/Hanzi characters (code-switch safety net)."""
    import re
    # Clean markdown code fences
    text = re.sub(r'^\`\`\`[^\n]*\n', '', text)
    text = re.sub(r'\n\`\`\`\s*$', '', text)
    text = text.strip()
    
    # Safety net: strip Chinese/Hanzi/Kanji characters (qwen code-switch protection)
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+', '', text).strip()
    
    # Split by sentence-ending punctuation + line breaks
    # First split by explicit line breaks (LLM uses these for pauses)
    blocks = re.split(r'\n{2,}', text)  # empty line = long pause
    sentences = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Further split by single newlines
        sub = re.split(r'\n', block)
        sentences.extend(s.strip() for s in sub if s.strip())
    
    # Ensure each sentence ends with punctuation
    final = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Add period if missing
        if not s[-1] in '.!?…':
            s += '.'
        final.append(s)
    
    return final


def format_tts_ai(raw_text):
    """Dùng LLM format raw text → emotional TTS text + sentences.
    Fallback về manual nếu LLM fail."""
    prompt = TTS_FORMAT_PROMPT.replace("{text}", raw_text)
    result = _call_ollama_format(prompt)
    
    if result:
        sentences = _parse_formatted_text(result)
        if sentences:
            tts_text = " ".join(sentences)
            return tts_text, sentences
    
    print("  ⚠️ LLM format failed → fallback manual")
    return format_tts_manual(raw_text)


def format_tts_manual(raw_text):
    """Fallback: tự xử lý raw_text thành dạng TTS-friendly, không dùng LLM.
    Tách thành câu ngắn, thêm dấu ba chấm, chuẩn hóa xuống dòng."""
    import re
    # Safety net: strip Chinese/Hanzi/Kanji characters
    raw_text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+', '', raw_text).strip()
    text = raw_text.replace("\n", " ").strip()
    # Collapse multiple spaces
    text = " ".join(text.split())
    
    # Split by sentence-ending punctuation
    parts = re.split(r'(?<=[.!?])\s+', text)
    
    sentences = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Add trailing punctuation if missing
        if p[-1] not in '.!?…':
            p += '.'
        # Normalize: lowercase first letter (for TTS flow)
        if len(p) > 0 and p[0].isupper() and len(p) > 10:
            # Keep first letter uppercase for proper nouns
            pass
        sentences.append(p)
    
    tts_text = " ".join(sentences)
    return tts_text, sentences


# === PEXELS ===

def pexels_search(query, per_page=15):
    params = urllib.parse.urlencode({"query": query, "per_page": per_page, "orientation": "portrait", "size": "large"})
    out, _, rc = run(f'curl -s --max-time 15 -H "Authorization: {PEXELS_KEY}" "https://api.pexels.com/videos/search?{params}"')
    if rc != 0 or not out: return []
    try: return json.loads(out).get("videos", [])
    except: return []


def pick_new_videos(videos, used_ids, max_n=3):
    valid = [v for v in videos if v["id"] not in used_ids and v.get("height", 0) >= 1080 and v.get("height", 0) > v.get("width", 0)]
    # Sort by duration first, then pick từ top 70% để vừa dài vừa đa dạng
    valid.sort(key=lambda v: v.get("duration", 0), reverse=True)
    # Giới hạn pool để tránh chọn video quá ngắn, rồi shuffle để đa dạng
    pool = valid[:max(len(valid), max_n * 3)]
    random.shuffle(pool)
    return pool[:max_n]


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
    payload = json.dumps({"text": text, "model_id": ELEVENLABS_MODEL, "voice_settings": {"stability": 0.2, "similarity_boost": 0.7, "style": 0.9, "speed": 1.3, "use_speaker_boost": True}}).encode()
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


def alignment_to_segments(alignment, sentences):
    """Map ElevenLabs alignment words → sentence timing (sentences from format_tts_manual)."""
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

    def norm(s):
        import re
        s = re.sub(r'\.\.\.', ' ', s)
        s = re.sub(r'\.', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    # Prefix-match words → sentences
    segments = []
    wi = 0
    for sent in sentences:
        target = norm(sent)
        if not target: continue
        sent_words = []
        pos = 0
        while wi < len(words) and pos < len(target):
            w = words[wi]
            if target[pos:].startswith(w["text"]):
                sent_words.append(w)
                pos += len(w["text"])
                while pos < len(target) and target[pos] == " ":
                    pos += 1
                wi += 1
            else:
                wi += 1
        if sent_words:
            segments.append({"start": sent_words[0]["start"], "end": sent_words[-1]["end"],
                             "text": sent, "blank": False})
            if wi < len(words):
                gap_end = max(sent_words[-1]["end"] + 0.3, words[wi]["start"])
                segments.append({"start": sent_words[-1]["end"], "end": gap_end, "text": "", "blank": True})

    print(f"  ✅ {len(segments)} segments ({len(sentences)} câu + blanks)")
    return segments


def get_duration(fp):
    try: return float(json.loads(run(f'ffprobe -v error -show_entries format=duration -of json "{fp}"')[0])["format"]["duration"])
    except: return 0


def concat_videos(paths, outpath):
    """Concat nhiều video (video-only, Pexels stock thường không có audio)."""
    if len(paths) == 1:
        run(f'cp "{paths[0]}" "{outpath}"')
        return True
    
    # Build filter_complex: chỉ concat video (audio từ TTS thêm sau)
    inputs = " ".join(f'-i "{p}"' for p in paths)
    n = len(paths)
    
    v_parts = [f"[{i}:v]setpts=PTS-STARTPTS,fps=30,format=yuv420p[v{i}]" for i in range(n)]
    v_concat = "".join(f"[v{i}]" for i in range(n))
    filter_complex = f"{';'.join(v_parts)};{v_concat}concat=n={n}:v=1:a=0[vout]"
    
    return run(
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[vout]" '
        f'-c:v libx264 -preset ultrafast -crf 23 '
        f'-movflags +faststart "{outpath}"'
    )[2] == 0

# === HTML SUBTITLE RENDERER (Playwright) ===

def build_subtitle_html(css_extra=""):
    """HTML template cho subtitle: SN Pro SemiBold, fade in/out, không overlay nền."""
    import base64
    
    font_path = SUB_FONT
    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode()
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@font-face {{
    font-family: 'SNPro';
    src: url(data:font/ttf;base64,{font_b64}) format('truetype');
    font-weight: 600;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {1080}px; height: {1920}px;
    display: flex; align-items: center; justify-content: center;
    background: transparent;
    font-family: 'SNPro', sans-serif;
    font-weight: 600;
    font-size: {SUB_SIZE}px;
    color: #fff;
    text-align: center;
    line-height: 1.4;
    letter-spacing: -0.01em;
    overflow: hidden;
}}
.sub-container {{
    max-width: {1080 - 2 * SUB_SIDE_PAD}px;
    word-break: keep-all;
    white-space: pre-line;
    animation: fadeIn {FADE_MS}s ease-out;
}}
.sub-text {{
    text-shadow: 
        3px 3px 0 rgba(0,0,0,0.7),
        -3px 3px 0 rgba(0,0,0,0.7),
        3px -3px 0 rgba(0,0,0,0.7),
        -3px -3px 0 rgba(0,0,0,0.7),
        0 3px 0 rgba(0,0,0,0.7),
        0 -3px 0 rgba(0,0,0,0.7),
        3px 0 0 rgba(0,0,0,0.7),
        -3px 0 0 rgba(0,0,0,0.7);
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeOut {{
    from {{ opacity: 1; }}
    to {{ opacity: 0; }}
}}
.fading-out {{
    animation: fadeOut {FADE_MS}s ease-in forwards;
}}
{css_extra}
</style></head><body>
<div class="sub-container" id="sub-container">
    <div class="sub-text" id="subtitle-text"></div>
</div>
<script>
    window.setText = function(text) {{
        var el = document.getElementById('subtitle-text');
        var container = document.getElementById('sub-container');
        container.classList.remove('fading-out');
        el.textContent = text;
    }};
    window.startFadeOut = function() {{
        document.getElementById('sub-container').classList.add('fading-out');
    }};
</script>
</body></html>"""


def render_subtitle_html(sentences, segments, outpath, width=1080, height=1920):
    """Playwright render mỗi câu → PNG. Trả về dict {sentence_text: png_path}."""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    tmpdir = outpath + ".tmp"
    os.makedirs(tmpdir, exist_ok=True)

    html = build_subtitle_html()
    html_path = f"{tmpdir}/subtitle.html"
    with open(html_path, "w") as f:
        f.write(html)

    png_paths = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(500)

        for sent in sentences:
            page.evaluate(f"window.setText({json.dumps(sent)})")
            page.wait_for_timeout(int(FADE_MS * 1000) + 200)
            pp = f"{tmpdir}/sub_{sent[:20]}.png"
            page.screenshot(path=pp, omit_background=True)
            png_paths[sent] = pp

        browser.close()

    return png_paths


def build_tiktok(video_path, audio_path, sub_pngs, segments, outpath, fade_sec=1.0):
    """Overlay subtitle PNGs với absolute timing → không drift tuyệt đối."""
    aud_dur = get_duration(audio_path)
    vid_dur = get_duration(video_path)
    total_dur = VIDEO_START_DELAY + aud_dur + VIDEO_END_PAD
    delay_ms = int(VIDEO_START_DELAY * 1000)
    fade_start = total_dur - fade_sec
    
    # Loop video nếu cần (dùng -stream_loop -1 bên dưới)
    need_loop = vid_dur < total_dur
    if need_loop:
        print(f"  🔄 Video ngắn ({vid_dur:.1f}s < {total_dur:.1f}s) → sẽ stream_loop")
    
    print(f"  🎬 Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s, Target: {total_dur:.1f}s")
    
    # Build input list: video, audio, then all sub PNGs
    sub_png_list = []
    sub_overlays = []
    sub_idx = 0
    
    for seg in segments:
        if seg.get("blank") or not seg.get("text"):
            continue
        pp = sub_pngs.get(seg["text"])
        if not pp:
            continue
        t_start = seg["start"] + VIDEO_START_DELAY
        t_end = seg["end"] + VIDEO_START_DELAY
        sub_png_list.append(f'-i "{pp}"')
        
        png_input_idx = 2 + sub_idx  # 0=video, 1=audio, 2+=PNGs
        prev = "vbase" if not sub_overlays else f"vsub{sub_idx - 1}"
        cur = f"vsub{sub_idx}"
        sub_overlays.append(
            f"[{prev}][{png_input_idx}:v]overlay=0:0:"
            f"enable='between(t,{t_start:.3f},{t_end:.3f})':format=auto"
            f"[{cur}]"
        )
        sub_idx += 1
    
    last_v = f"vsub{len(sub_overlays) - 1}" if sub_overlays else "vbase"
    
    filter_lines = [
        f"[0:v]tonemap=hable:desat=0,"
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"fade=t=in:d=0.8,fade=t=out:d={fade_sec}:start_time={fade_start},"
        f"fps=30,format=rgba[vbase]",
        f"[1:a]adelay={delay_ms}|{delay_ms}[a]"
    ] + sub_overlays
    
    filter_complex = ";".join(filter_lines)
    
    video_input_flag = "-stream_loop -1 " if need_loop else ""
    
    cmd = (
        f'ffmpeg -y {video_input_flag}-i "{video_path}" -i "{audio_path}" '
        f'{" ".join(sub_png_list)} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[{last_v}]" -map "[a]" '
        f'-c:v libx264 -preset fast -crf 20 '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart '
        f'-t {total_dur} '
        f'"{outpath}"'
    )
    
    _, err, rc = run(cmd, timeout=300)
    if rc != 0:
        print(f"  ❌ Build: {err[:500]}")
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

    # 2. Clean font errors → Format TTS (LLM via Ollama, manual fallback)
    print(f"  ✍️ Formatting TTS text (LLM)...")
    cleaned = clean_vni_errors(raw_content)
    tts_text, sentences = format_tts_ai(cleaned)
    print(f"  📝 Formatted ({len(tts_text)} chars, {len(sentences)} câu): {tts_text[:150]}...")
    # In ra dòng đặc biệt để trigger.py capture
    print(f"FORMATTED_TEXT:{tts_text}")

    # 3. ElevenLabs with timestamps
    ap = f"{outdir}/tts.mp3"
    print(f"  🎙 ElevenLabs (with timestamps)...")
    ok, alignment = generate_tts_with_timestamps(tts_text, ap)
    if not ok: return
    aud_dur = get_duration(ap)
    print(f"  ✅ TTS: {os.path.getsize(ap)/1000:.0f} KB, {aud_dur:.1f}s")

    # 4. Alignment → segments (truyền sentences từ format)
    segments = alignment_to_segments(alignment, sentences)

    # 5. Render subtitle HTML → PNGs
    sub_pngs = render_subtitle_html(sentences, segments, f"{outdir}/subtitle")
    
    # 6. Download nhiều video → concat đến khi tổng duration > total_dur + buffer
    total_dur = VIDEO_START_DELAY + aud_dur + VIDEO_END_PAD
    buffer = 3.0  # thêm buffer để concat thoải mái
    target = total_dur + buffer
    
    # Sort video theo duration giảm dần
    all_videos.sort(key=lambda v: v.get("duration", 0), reverse=True)
    
    downloaded = []  # list of file paths
    total_downloaded = 0.0
    
    for v in all_videos:
        if total_downloaded >= target:
            break
        fp = f"{outdir}/vid_{v['id']}.mp4"
        if not download_video(get_best_file(v), fp):
            continue
        d = get_duration(fp)
        downloaded.append(fp)
        total_downloaded += d
        print(f"    📥 Downloaded id={v['id']}, {d:.1f}s (total: {total_downloaded:.1f}s / target: {target:.1f}s)")
    
    if not downloaded:
        return print("❌ Không download được video nào!")
    
    if len(downloaded) == 1 and total_downloaded < total_dur:
        # Fallback: 1 video duy nhất & ngắn hơn total_dur → stream_loop
        print(f"  🔄 Fallback: stream_loop (1 video {total_downloaded:.1f}s < {total_dur:.1f}s)")
        video_fp = downloaded[0]
    elif len(downloaded) > 1:
        # Concat tất cả video đã download (re-encode)
        print(f"  🔗 Concatenating {len(downloaded)} videos ({total_downloaded:.1f}s total)...")
        concat_fp = f"{outdir}/concat_bg.mp4"
        if not concat_videos(downloaded, concat_fp):
            # Fallback: dùng video dài nhất + stream_loop
            print(f"  ⚠️ Concat failed → fallback stream_loop")
            video_fp = downloaded[0]
        else:
            video_fp = concat_fp
    else:
        video_fp = downloaded[0]
    
    print(f"  🎬 Final video: {video_fp}, {get_duration(video_fp):.1f}s")
    
    # 7. Build TikTok: concat video + overlay subtitle absolute timing
    op = f"{outdir}/tiktok.mp4"
    if not build_tiktok(video_fp, ap, sub_pngs, segments, op): return

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
