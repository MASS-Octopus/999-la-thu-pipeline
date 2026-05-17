#!/usr/bin/env python3
"""Trigger TTS video từ data letters.json — 2 bước: format text → user review → produce video."""

import json, os, sys, random, subprocess, re, hashlib, argparse

REPO = os.path.dirname(os.path.abspath(__file__))
LETTERS_FILE = os.path.join(REPO, "data", "letters.json")
STATE_FILE = os.path.expanduser("~/.hermes/state/tts_completed.json")
PIPELINE = os.path.join(REPO, "pipeline.py")
ENV_FILE = os.path.expanduser("~/.mass/.env")
CDN_URL = "http://127.0.0.1:9876/publish"

# Discord config
CHANNEL_ID = "1504495292219785267"  # #tts-video

def load_env():
    """Load bot token from .env"""
    token = ""
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("MASS_DISCORD_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return token

def content_hash(content):
    """SHA256 hash của nội dung — dùng để dedup bất kể so_thu thay đổi."""
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]

def load_completed():
    try:
        data = json.load(open(STATE_FILE))
        return set(str(x) for x in data)
    except:
        return set()

def save_completed(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(list(s), open(STATE_FILE, "w"))

def pick_random(letters, completed):
    """Chọn 1 thư ngẫu nhiên chưa từng chạy (dùng hash nội dung)."""
    available = [l for l in letters if content_hash(l.get("noi_dung", "")) not in completed]
    if not available:
        print("❌ Hết thư để chạy!")
        return None
    return random.choice(available)

def generate_hashtags(text):
    """Tạo hashtags từ nội dung."""
    tags = ["#tam_su", "#chualanh", "#docsach", "#lofi", "#healing", "#tuoitre"]
    keywords = ["tình yêu", "cuộc sống", "hạnh phúc", "nỗi buồn", "ước mơ", "hy vọng", 
                "cố lên", "tuổi trẻ", "gia đình", "bạn bè", "đau khổ", "ý nghĩa"]
    for kw in keywords:
        if kw in text.lower():
            tags.append(f"#{kw.replace(' ', '_')}")
    return " ".join(tags[:7])

def send_discord(token, message):
    """Gửi message vào channel qua REST API."""
    import urllib.request
    payload = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        data=payload,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (https://hermes-agent.nousresearch.com, 1.0)"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"❌ Discord send failed: {e}")
        return None

# ========== BƯỚC 1: Format text ==========

def step_format():
    letters = json.load(open(LETTERS_FILE))
    completed = load_completed()
    
    print(f"📋 {len(letters)} letters, {len(completed)} completed, {len(letters) - len(completed)} available")
    
    pick = pick_random(letters, completed)
    if not pick:
        return
    
    so_thu = pick["so_thu"]
    title = pick.get("title", f"Thư #{so_thu}")
    content = pick.get("noi_dung", pick.get("text", ""))
    source = pick.get("source", "")
    
    print(f"🎲 Chọn thư #{so_thu}: {title}")
    print(f"   Content: {content[:80]}...")
    
    # Chạy pipeline --format-only
    print(f"🔧 Formatting text (LLM)...")
    r = subprocess.run(
        ["python3", PIPELINE, str(so_thu), "--format-only"],
        capture_output=True, text=True, timeout=300, cwd=REPO
    )
    
    formatted = None
    for line in r.stdout.split("\n"):
        if line.startswith("FORMATTED_TEXT:"):
            formatted = line.split("FORMATTED_TEXT:", 1)[-1].strip()
            break
    
    if not formatted:
        print(f"❌ Format failed:\\n{r.stdout[-500:]}")
        return
    
    print(f"✅ Formatted ({len(formatted)} chars)")
    print(f"FORMATTED_TEXT:{formatted}")
    
    # Lưu pending preview (chờ user review TEXT)
    pending_file = os.path.expanduser("~/.hermes/state/tts_pending_preview.json")
    os.makedirs(os.path.dirname(pending_file), exist_ok=True)
    hashes = generate_hashtags(formatted)
    pending_data = {
        "so_thu": so_thu,
        "title": title,
        "source": source,
        "formatted_text": formatted,
        "hashtags": hashes
    }
    json.dump(pending_data, open(pending_file, "w"), ensure_ascii=False)
    
    print(f"\nPENDING_TEXT_REVIEW: {so_thu}")
    print(f"   → Gửi text cho Anh review, confirm rồi mới produce TTS+video")

# ========== BƯỚC 2: Produce video (sau khi user duyệt text) ==========

def step_produce():
    """Đọc pending preview, produce TTS+video, post Discord."""
    pending_file = os.path.expanduser("~/.hermes/state/tts_pending_preview.json")
    try:
        pending = json.load(open(pending_file))
    except:
        print("❌ Không có pending preview! Chạy --format trước.")
        return
    
    so_thu = pending["so_thu"]
    formatted_text = pending["formatted_text"]
    title = pending["title"]
    source = pending.get("source", "")
    hashtags = pending.get("hashtags", "")
    
    print(f"🎬 Produce video for thư #{so_thu}...")
    
    # Chạy pipeline --text (produce mode: TTS+video, không format lại)
    r = subprocess.run(
        ["python3", PIPELINE, str(so_thu), "--text", formatted_text],
        capture_output=True, text=True, timeout=300, cwd=REPO
    )
    
    cdn = None
    for line in r.stdout.split("\n"):
        if "CDN: https://" in line:
            cdn = line.split("CDN: ")[-1].strip()
            break
    if not cdn:
        for line in r.stdout.split("\n"):
            if "RESULT: https://" in line:
                cdn = line.split("RESULT: ")[-1].strip()
                break
    
    if not cdn:
        print(f"❌ Produce failed:\\n{r.stdout[-500:]}")
        return
    
    print(f"✅ CDN: {cdn}")
    
    # Gửi Discord
    token = load_env()
    if not token:
        print(f"❌ No Discord token\\nCDN: {cdn}")
        return
    
    # Gửi Discord: 1 message gọn (CDN + hashtags, không full text TTS)
    msg = f"🎬 **{title} — #{so_thu}**\n{cdn}\n\n{hashtags}"
    send_discord(token, msg)
    
    print(f"\n📤 Posted to #tts-video")
    
    # Mark completed
    letters = json.load(open(LETTERS_FILE))
    for l in letters:
        if l["so_thu"] == so_thu:
            h = content_hash(l.get("noi_dung", ""))
            completed = load_completed()
            completed.add(h)
            save_completed(completed)
            print(f"✅ Marked #{so_thu} as completed (hash: {h})")
            break
    
    # Xoá pending
    os.remove(pending_file)

# ========== MAIN ==========

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--produce", action="store_true", help="Produce TTS+video from pending preview (step 2)")
    args = ap.parse_args()
    
    if args.produce:
        step_produce()
    else:
        step_format()
