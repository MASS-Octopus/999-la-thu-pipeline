#!/usr/bin/env python3
"""Trigger TTS video từ data letters.json — chọn ngẫu nhiên, chạy pipeline, gửi Discord."""

import json, os, sys, random, subprocess, re

REPO = os.path.dirname(os.path.abspath(__file__))
LETTERS_FILE = os.path.join(REPO, "data", "letters.json")
STATE_FILE = os.path.expanduser("~/.hermes/state/tts_completed.json")
PIPELINE = os.path.join(REPO, "pipeline.py")
ENV_FILE = os.path.expanduser("~/.mass/.env")

# Discord config
CHANNEL_ID = "1504495292219785267"  # #tts-video
CDN_URL = "http://127.0.0.1:9876/publish"

def load_env():
    """Load bot token from .env"""
    token = ""
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("MASS_DISCORD_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return token

def load_completed():
    try:
        return set(json.load(open(STATE_FILE)))
    except:
        return set()

def save_completed(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(list(s), open(STATE_FILE, "w"))

def pick_random(letters, completed):
    """Chọn 1 thư ngẫu nhiên chưa từng chạy."""
    available = [l for l in letters if l["so_thu"] not in completed]
    if not available:
        print("❌ Hết thư để chạy!")
        return None
    return random.choice(available)

def run_pipeline(so_thu):
    """Chạy pipeline.py và trả về (CDN link, formatted_text)."""
    print(f"🚀 Running pipeline for thư #{so_thu}...")
    r = subprocess.run(
        ["python3", PIPELINE, str(so_thu)],
        capture_output=True, text=True, timeout=300, cwd=REPO
    )
    stdout = r.stdout
    # Extract formatted text
    formatted = None
    for line in stdout.split("\n"):
        if line.startswith("FORMATTED_TEXT:"):
            formatted = line.split("FORMATTED_TEXT:", 1)[-1].strip()
            break
    # Extract CDN link
    cdn = None
    for line in stdout.split("\n"):
        if "CDN: https://" in line:
            cdn = line.split("CDN: ")[-1].strip()
            break
    if not cdn:
        for line in stdout.split("\n"):
            if "RESULT: https://" in line:
                cdn = line.split("RESULT: ")[-1].strip()
                break
    if not cdn:
        print(f"❌ Pipeline output:\n{stdout[-500:]}")
    return cdn, formatted

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

def generate_hashtags(text):
    """Tạo hashtags từ nội dung."""
    tags = ["#tam_su", "#chualanh", "#docsach", "#lofi", "#healing", "#tuoitre"]
    # Thêm tag theo key words
    keywords = ["tình yêu", "cuộc sống", "hạnh phúc", "nỗi buồn", "ước mơ", "hy vọng", 
                "cố lên", "tuổi trẻ", "gia đình", "bạn bè", "đau khổ", "ý nghĩa"]
    for kw in keywords:
        if kw in text.lower():
            tags.append(f"#{kw.replace(' ', '_')}")
    return " ".join(tags[:7])  # Max 7 hashtags

def main():
    letters = json.load(open(LETTERS_FILE))
    completed = load_completed()
    
    print(f"📋 {len(letters)} letters, {len(completed)} completed, {len(letters) - len(completed)} available")
    
    # Chọn ngẫu nhiên
    pick = pick_random(letters, completed)
    if not pick:
        return
    
    so_thu = pick["so_thu"]
    title = pick.get("title", f"Thư #{so_thu}")
    content = pick.get("noi_dung", pick.get("text", ""))
    source = pick.get("source", "")
    
    print(f"🎲 Chọn thư #{so_thu}: {title}")
    print(f"   Content: {content[:80]}...")
    
    # Chạy pipeline
    cdn, formatted = run_pipeline(so_thu)
    if not cdn:
        # Fallback: tìm file output
        outdir = f"/tmp/thu_{so_thu}_pexels"
        tiktok_mp4 = f"{outdir}/tiktok.mp4"
        if os.path.exists(tiktok_mp4):
            print(f"  📂 File local: {tiktok_mp4}")
            return
        print(f"  ❌ Pipeline failed for #{so_thu}")
        return
    
    print(f"\n✅ CDN: {cdn}")
    
    # Gửi Discord (3 messages)
    token = load_env()
    if not token:
        print("❌ No Discord token")
        print(f"CDN: {cdn}")
        print(f"Content: {(formatted or content)[:200]}...")
        return
    
    # Dùng formatted text (tiếng Việt thuần) nếu có
    display_text = formatted if formatted else content
    
    # Message A: CDN link only
    msg_a = f"🎬 **Video mới — #{so_thu}**\n\n🔗 {cdn}"
    send_discord(token, msg_a)
    
    # Message B: Full formatted text (copy cho mô tả TikTok)
    hashtags = generate_hashtags(display_text)
    msg_b = f"📝 **{title}**\n*{source}*\n\n{display_text}\n\n{hashtags}"
    send_discord(token, msg_b)
    
    # Message C: Confirm prompt
    msg_c = f"✅ Thư `#{so_thu}` đã tạo xong. Reply `ok` để xác nhận & remove khỏi pool, hoặc `skip` để giữ lại."
    send_discord(token, msg_c)
    
    # Lưu pending state (chưa remove)
    pending_file = os.path.expanduser("~/.hermes/state/tts_pending.json")
    os.makedirs(os.path.dirname(pending_file), exist_ok=True)
    json.dump({"so_thu": so_thu, "cdn": cdn, "title": title}, open(pending_file, "w"), ensure_ascii=False)
    
    print(f"\n📤 Sent to #tts-video channel (pending confirm)")
    print(f"   → Reply 'ok #{so_thu}' để confirm & remove")

if __name__ == "__main__":
    main()
