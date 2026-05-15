#!/usr/bin/env python3
"""
Final correct extraction: use author signatures as boundaries (19 stories from v3),
assign correct titles, select 8 best for Gemini.
"""
import re
import json
import subprocess
import sys
import time

OCR_FILE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-10/full.txt"

with open(OCR_FILE, 'r', encoding='utf-8') as f:
    full_text = f.read()

# OCR variants mapped to real names, with correct story titles
# (verified from OCR file contents/table of contents)
story_map = [
    {"ocr_author": "James P. Lenƒesfy", "real_author": "James P. Lenfestey", 
     "title": "Mẻ cá để đời"},
    {"ocr_author": "Helen RÑezatfto", "real_author": "Helen Rezatto", 
     "title": "Cô bé trong trận bão tuyết"},
    {"ocr_author": "Anne Goodrich", "real_author": "Anne Goodrich", 
     "title": "Thiên đường trên mặt đất"},
    {"ocr_author": "kynn RÑosellini", "real_author": "Lynn Rosellini", 
     "title": "Mike, tôi và chiếc bánh"},
    {"ocr_author": "Dudley A. Henrique", "real_author": "Dudley A. Henrique", 
     "title": "Sự giúp đỡ của một người bạn"},
    {"ocr_author": "Mitchell Wïlson", "real_author": "Mitchell Wilson", 
     "title": "Và khoản tiền lớn đầu tiên trong đời"},
    {"ocr_author": "Marfin Buxbaum", "real_author": "Marfin Buxbaum", 
     "title": "Sức mạnh của một bức thư cảm ơn"},
    {"ocr_author": "WilHam M. Hendryx", "real_author": "William M. Hendryx", 
     "title": "Trên chiến tuyến"},
    {"ocr_author": "Doris Cheney Whiftehouse", "real_author": "Doris Cheney Whitehouse", 
     "title": "Gia tài của ông Ditto"},
    {"ocr_author": "Sarah Ban Breathnach", "real_author": "Sarah Ban Breathnach", 
     "title": "Tìm lại các giác quan"},
    {"ocr_author": "Ñichard Collier", "real_author": "Richard Collier", 
     "title": "Ước mơ vươn tới một ngôi sao"},
    {"ocr_author": "Janet Kinosian", "real_author": "Janet Kinosian", 
     "title": "Những chiếc xe miễn phí"},
    {"ocr_author": "Jaroldeen Edwards", "real_author": "Jaroldeen Edwards", 
     "title": "Vùng đất mặt trời dát vàng"},
    {"ocr_author": "Joe Puterno", "real_author": "Joe Paterno", 
     "title": "Người từ chối một triệu đô la"},
    {"ocr_author": "Peter Michelmore", "real_author": "Peter Michelmore", 
     "title": "Người thầy, người cha của nhà vô địch"},
    {"ocr_author": "Leo Rosten", "real_author": "Leo Rosten", 
     "title": "Một thiên tài trong lịch sử"},
    {"ocr_author": "Lee Maynard", "real_author": "Lee Maynard", 
     "title": "Kẻ chạy trốn"},
    {"ocr_author": "Reba McEntire", "real_author": "Reba McEntire", 
     "title": "Phong cách của riêng tôi"},
    {"ocr_author": "Noah Gilson, M.D.", "real_author": "Noah Gilson, M.D.", 
     "title": "Vấn đề chính là thời gian"},
]

# Find all author signature positions
author_positions = []
for sm in story_map:
    for ocr_name in [sm["ocr_author"], sm["real_author"]]:
        pattern = r'\n-\s+' + re.escape(ocr_name) + r'\s*\n'
        for m in re.finditer(pattern, full_text):
            author_positions.append((m.end(), sm))

# Sort and deduplicate
author_positions.sort()
seen = set()
unique = []
for pos, sm in author_positions:
    if pos not in seen:
        seen.add(pos)
        unique.append((pos, sm))
author_positions = unique

# Find page 11
page11 = re.search(r'=== PAGE 11 ===', full_text)
start_pos = page11.end() if page11 else 0

# Extract stories
stories = []
prev_pos = start_pos
for pos, sm in author_positions:
    story_text = full_text[prev_pos:pos].strip()
    
    if len(story_text) < 300:
        prev_pos = pos
        continue
    
    # Clean OCR
    story_text = re.sub(r'=== PAGE \d+ ===', '', story_text)
    story_text = re.sub(r'Hạt giống tâm hồn', '', story_text)
    story_text = re.sub(r'Theo dòng thời gian', '', story_text)
    story_text = re.sub(r'\n\d+\n', '\n', story_text)
    story_text = re.sub(r'\n{3,}', '\n\n', story_text)
    story_text = story_text.strip()
    
    # Remove the title line(s) from the body if they match
    title_parts = sm['title'].split()
    lines = story_text.split('\n')
    clean_lines = []
    title_found = False
    for i, l in enumerate(lines):
        ls = l.strip()
        if not title_found and ls and any(ls.startswith(tp[:3]) for tp in title_parts if len(tp) >= 3):
            title_found = True
            continue
        if title_found or i > 2:
            clean_lines.append(ls)
    
    body = '\n'.join(clean_lines).strip()
    if not body or len(body) < 200:
        body = story_text  # fallback
    
    stories.append({
        'title': sm['title'],
        'text': body,
        'author': sm['real_author'],
        'char_count': len(body)
    })
    
    prev_pos = pos

print(f"Extracted {len(stories)} stories with correct titles\n")

# Classification
def classify(s):
    full = (s['title'] + ' ' + s['text']).lower()
    fp = len(re.findall(r'\b(tôi|mình)\b', full))
    
    rejection = [
        'bài học', 'đạo đức', 'chúng ta nên', 'chúng ta phải',
        'hãy luôn', 'ngụ ngôn', 'triết lý', 'bài giảng',
        'rút ra', 'kết luận', 'thông điệp', 'lời khuyên',
        'bạn hãy', 'bạn nên', 'chân lý', 'sống có đạo đức',
        'quyết định đúng đắn', 'lẽ phải',
    ]
    rej = sum(len(re.findall(p, full)) for p in rejection)
    
    # Quality score: personal voice + emotional depth - moralizing
    score = fp * 2 - rej * 3
    if fp >= 10: score += 10
    if fp >= 30: score += 15
    if fp >= 70: score += 20
    if rej >= 5: score -= 30
    
    keep = fp >= 3 and rej <= 3
    # Special cases
    if s['title'] == "Mẻ cá để đời":
        keep = False  # Too moralistic
    if s['title'] == "Sức mạnh của một bức thư cảm ơn":
        keep = False  # Too short/light
    if s['title'] == "Một thiên tài trong lịch sử":
        keep = False  # Biography, not personal
    
    return keep, score, fp, rej

print("=" * 80)
ranked = []
for i, s in enumerate(stories):
    keep, score, fp, rej = classify(s)
    status = "✓" if keep else "✗"
    ranked.append((s, keep, score, fp, rej))
    print(f"{i+1}. [{status}] {s['title']} ({s['author']}) - chars={s['char_count']}, fp={fp}, rej={rej}, score={score}")

# Sort by score
ranked.sort(key=lambda x: x[2], reverse=True)

# Select top 8 qualifying
top8 = [(s, score, fp) for s, keep, score, fp, rej in ranked if keep][:8]

print(f"\n{'='*80}")
print(f"TOP 8 SELECTED (of {sum(1 for _,k,_,_,_ in ranked if k)} qualifying):")
print("=" * 80)

for i, (s, score, fp) in enumerate(top8):
    print(f"{i+1}. {s['title']} by {s['author']} (score={score}, fp={fp}, {s['char_count']} chars)")

# Now call Gemini for each story
print(f"\n{'='*80}")
print("CALLING GEMINI FOR TRANSFORMATION...")
print("=" * 80)

results = []
system_prompt = "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. Không kể lại cốt truyện. Không bài học đạo đức."

for i, (s, score, fp) in enumerate(top8):
    user_prompt = f"Dựa vào câu chuyện sau viết một lá thư tâm sự:\n\n{s['text']}"
    
    print(f"\n--- Story {i+1}/{len(top8)}: {s['title']} ---")
    print(f"Text length: {len(s['text'])} chars")
    sys.stdout.flush()
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "90",
             "http://localhost:11434/api/chat",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=95
        )
        
        if result.returncode == 0 and result.stdout.strip():
            resp = json.loads(result.stdout)
            content = resp.get("message", {}).get("content", "")
            print(f"Got response: {len(content)} chars")
            print(f"Preview: {content[:150]}...")
            
            results.append({
                "so_thu": None,
                "noi_dung": content.strip(),
                "nguon": f"Hạt Giống Tâm Hồn - Tập 10 ({s['title']})"
            })
        else:
            print(f"Error: {result.stderr[:200]}")
            results.append({
                "so_thu": None,
                "noi_dung": f"[Lỗi gọi Gemini: {result.stderr[:100]}]",
                "nguon": f"Hạt Giống Tâm Hồn - Tập 10 ({s['title']})"
            })
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        results.append({
            "so_thu": None,
            "noi_dung": "[Lỗi: Timeout gọi Gemini]",
            "nguon": f"Hạt Giống Tâm Hồn - Tập 10 ({s['title']})"
        })
    except Exception as e:
        print(f"Exception: {e}")
        results.append({
            "so_thu": None,
            "noi_dung": f"[Lỗi: {str(e)[:100]}]",
            "nguon": f"Hạt Giống Tâm Hồn - Tập 10 ({s['title']})"
        })
    
    # Small delay between calls
    time.sleep(1)

# Save final JSON
output_path = "/tmp/tap10_final_output.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*80}")
print(f"FINAL JSON ARRAY ({len(results)} items):")
print(json.dumps(results, ensure_ascii=False, indent=2))
print(f"\nSaved to {output_path}")
