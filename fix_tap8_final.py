#!/usr/bin/env python3
"""Map existing letters to correct story names, add missing 8th story."""
import re, json, subprocess, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_FILE = os.path.join(SCRIPT_DIR, 'ocr_output/tap-8/full.txt')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'output/tap8_letters.json')

# Read existing letters
with open(OUTPUT_FILE, 'r') as f:
    existing = json.load(f)

print(f"Loaded {len(existing)} existing letters")

# Identify each letter's story by content analysis
# 0: Self-identity, freedom, choices → "Tuyên ngôn của cái Tôi" (Nguyễn Đoàn)
# 1: Button, 4am, mother sewing → "Cái nút áo" (Thanh Giang)
# 2: Daughter to college, 150 miles, dad's handshake → "Món quà tạm biệt" (Thanh Giang)
# 3: Angel statue, shy child, husband's war scars → "Thiên thần can đảm" (Thanh Phương)
# 4: Mother dementia, Ben playing Rummy → "Tình yêu diệu kỳ" (Thanh Phương)
# 5: 75-year-old college, husband's goodbye → DUPLICATE of "Thiên thần can đảm"
# 6: Gloria died, regret not speaking → "Lời yêu thương" (Thu Quỳnh)
# 7: Blind mother, touching/feeling → "Đôi mắt của mẹ" (Nguyễn Ngân)

story_map = {
    0: "Tuyên ngôn của cái Tôi",
    1: "Cái nút áo",
    2: "Món quà tạm biệt",
    3: "Thiên thần can đảm",
    4: "Tình yêu diệu kỳ",
    6: "Lời yêu thương",
    7: "Đôi mắt của mẹ",
}
# Letter 5 is duplicate of letter 3 — remove it

fixed = []
for i, item in enumerate(existing):
    if i == 5:  # Skip duplicate
        continue
    title = story_map.get(i, f"Truyện {i+1}")
    item["nguon"] = f"Hạt Giống Tâm Hồn - Tập 8 ({title})"
    fixed.append(item)

print(f"Kept {len(fixed)} unique letters, need 1 more")

# Now extract the "Thiếu nữ cài hoa" story (Thành Nhân) — high emotional score
# Find it in the OCR
def extract_story_by_author(target_author):
    with open(OCR_FILE, 'r') as f:
        lines = f.readlines()
    
    page10_idx = next(i for i, l in enumerate(lines) 
                      if re.match(r'=== PAGE 10 ===', l.strip()))
    
    KNOWN_AUTHORS = [
        'Lê Lai', 'Thanh Phương', 'Thanh Giang', 'Hồng Nhung',
        'Claude McDonald', 'Nguyễn Đoàn', 'Barbara Weidner',
        'Nguyên Thảo', 'Abraham Lincoln', 'Bích Thủy',
        'Thành Nhân', 'Lan Nguyên', 'Nguyễn Ngân',
        'Mai Quốc Thế', 'Lord Byron', 'Quỳnh Nga',
        'Jean Tharaud', 'Thanh Thủy', 'Thu Quỳnh',
        'Thanh Thảo', 'William Penn', 'Albert Einstein', 'Karl Marx'
    ]
    
    author_positions = []
    for i in range(page10_idx, len(lines)):
        line = lines[i].strip()
        if line.startswith('- '):
            name = line[2:].strip()
            for author in KNOWN_AUTHORS:
                if name == author or name.startswith(author + ' '):
                    author_positions.append((i, author))
                    break
    
    for idx, (pos, author) in enumerate(author_positions):
        if author == target_author:
            start_pos = page10_idx + 1 if idx == 0 else author_positions[idx-1][0] + 1
            raw_text = ''.join(lines[start_pos:pos])
            # Clean
            text = re.sub(r'=== PAGE \d+ ===', '', raw_text)
            text = re.sub(r'Hạt giống tâm hồn\n*', '', text)
            text = re.sub(r'^Những câu chuyện cuộc sống\n*', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\d{1,3}\s*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return text.strip()
    return None

# Get "Thiếu nữ cài hoa" by Thành Nhân
story_text = extract_story_by_author('Thành Nhân')
if story_text:
    print(f"Extracted 'Thiếu nữ cài hoa': {len(story_text)} chars")
    if len(story_text) > 3500:
        story_text = story_text[:3500]
    
    print("Calling Gemini...")
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": (
                "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. "
                "Không kể lại cốt truyện. Không bài học đạo đức."
            )},
            {"role": "user", "content": f"Dựa vào câu chuyện sau viết một lá thư tâm sự:\n\n{story_text}"}
        ]
    }
    
    for attempt in range(2):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '90',
                 'http://localhost:11434/api/chat',
                 '-d', json.dumps(payload, ensure_ascii=False)],
                capture_output=True, text=True, timeout=95
            )
            if result.returncode == 0:
                resp = json.loads(result.stdout)
                content = resp.get('message', {}).get('content', '')
                if content and len(content) > 80:
                    fixed.append({
                        "so_thu": None,
                        "noi_dung": content.strip(),
                        "nguon": "Hạt Giống Tâm Hồn - Tập 8 (Thiếu nữ cài hoa)"
                    })
                    print(f"  SUCCESS: {len(content)} chars")
                    break
            print(f"  Attempt {attempt+1}: failed")
        except Exception as e:
            print(f"  Attempt {attempt+1}: {e}")

print(f"\nTotal: {len(fixed)} letters")
for i, item in enumerate(fixed):
    print(f"  {i}: {item['nguon']} ({len(item['noi_dung'])} chars)")

# Save
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(fixed, f, ensure_ascii=False, indent=2)

print(f"\nSaved to {OUTPUT_FILE}")
print("\n" + json.dumps(fixed, ensure_ascii=False, indent=2))
