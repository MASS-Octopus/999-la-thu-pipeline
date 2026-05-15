#!/usr/bin/env python3
"""Trích và gọi Gemini cho Hiểu Về Trái Tim - Minh Niệm"""

import json, subprocess, sys, re

with open('full.txt', 'r') as f:
    lines = f.readlines()

# Chapter boundaries from scan
chapters = [
    ("Khổ đau", 237, 426),
    ("Hạnh phúc", 426, 639),
    ("Tình yêu", 639, 794),
    ("Tình thương", 794, 934),
    ("Tức giận", 934, 1116),
    ("Chịu đựng", 1116, 1261),
    ("Ghen tuông", 1261, 1423),
    ("Tha thứ", 1423, 1618),
    ("Sòng phẳng", 1618, 1766),
    ("Cô đơn", 1766, 1945),
    ("Hiến tặng", 1945, 2168),
    ("Trao thân", 2168, 2316),
    ("Tạ ơn", 2316, 2501),
    ("Nhàm chán", 2501, 2684),
    ("Kính trọng", 2684, 2869),
    ("Nghi ngờ", 2869, 3095),
    ("Lắng nghe", 3095, 3292),
    ("Phán xét", 3292, 3514),
    ("Ái ngữ", 3514, 3707),
    ("Thành kiến", 3707, 3854),
    ("Làm mới", 3854, 4064),
    ("Che đậy", 4064, 4298),
    ("Thành thật", 4298, 4504),
    ("Nguyên tắc", 4504, 4700),
    ("Tùy duyên", 4700, 4901),
    ("Tuyệt vọng", 4901, 5079),
    ("Niềm tin", 5079, 5296),
    ("Ý chí", 5296, 5486),
    ("Do dự", 5486, 5699),
    ("Thất bại", 5699, 5875),
    ("Thành công", 5875, 6019),
    ("Tham vọng", 6019, 6242),
    ("Biết đủ", 6242, 6470),
    ("Dựa dẫm", 6470, 6672),
    ("Nương tựa", 6672, 6865),
    ("Yếu đuối", 6865, 7099),
    ("Sám hối", 7099, 7322),
    ("Lười biếng", 7322, 99999),
]

def extract_chapter_text(start_line, end_line):
    """Extract text for a chapter between line boundaries (1-indexed)."""
    return ''.join(lines[start_line-1:end_line-1])

def clean_ocr(text):
    """Clean up OCR artifacts."""
    # Remove page markers
    text = re.sub(r'=== PAGE \d+ ===', '', text)
    # Remove obvious OCR noise lines
    text = re.sub(r'[ˆ°®‚„\u200b]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_best_segment(text, min_len=200, max_len=800):
    """Find the best segment with first-person voice for Gemini input."""
    # Split by double newlines
    paras = re.split(r'\n\s*\n', text)
    
    candidates = []
    for para in paras:
        clean = clean_ocr(para)
        if len(clean) < min_len or len(clean) > max_len:
            continue
        
        # Score
        fp_score = len(re.findall(r'\b(tôi|mình)\b', clean.lower())) * 2
        emo_score = len(re.findall(r'\b(khổ|đau|buồn|hạnh phúc|yêu|thương|nhớ|giận|ghen|cô đơn|sợ|khóc|nước mắt|tổn thương|tha thứ|tuyệt vọng|tin|mong|ước|chịu đựng)\b', clean.lower()))
        rej_score = -len(re.findall(r'\b(bạn nên|hãy luôn|đừng bao giờ|chúng ta nên|ta phải|ta cần phải)\b', clean.lower())) * 3
        
        score = fp_score + emo_score + rej_score
        if score >= 3:
            candidates.append((score, clean))
    
    candidates.sort(key=lambda x: -x[0])
    
    if not candidates:
        # Fallback: just take the largest chunk of text
        clean_all = clean_ocr(text)
        return clean_all[:min(max_len, len(clean_all))]
    
    # Return top 2 combined (or just top 1)
    if len(candidates) >= 2 and candidates[1][0] >= candidates[0][0] * 0.7:
        combined = candidates[0][1] + ' ' + candidates[1][1]
        return combined[:max_len]
    return candidates[0][1]

def call_gemini(chapter_name, passage):
    """Call Gemini to transform passage into a letter."""
    prompt = f"""Viết một lá thư tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. 
Không kể lại cốt truyện. Không bài học đạo đức. Giữ trọn vẹn tinh thần và giọng văn của tác giả gốc (Minh Niệm).
Chủ đề: {chapter_name}

Dựa vào đoạn văn sau của Minh Niệm:
'''
{passage}
'''

Trả về KẾT QUẢ DƯỚI DẠNG JSON:
{{"noi_dung": "lá thư..."}}"""

    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. Không kể lại cốt truyện. Không bài học đạo đức. Giữ trọn vẹn tinh thần và giọng văn của tác giả gốc (Minh Niệm). Trả về JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '90',
             'http://localhost:11434/api/chat',
             '-d', json.dumps(payload)],
            capture_output=True, text=True, timeout=95
        )
        
        resp = json.loads(result.stdout)
        content = resp.get('message', {}).get('content', '')
        
        # Try to extract JSON
        json_match = re.search(r'\{[^{}]*"noi_dung"[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        # Fallback: treat entire content as noi_dung
        content = content.strip()
        if content.startswith('```'):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        return {"noi_dung": content.strip()}
        
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return {"noi_dung": f"[Lỗi Gemini: {str(e)[:100]}]"}

# Process all chapters
results = []
total = len(chapters)

for idx, (name, start, end) in enumerate(chapters):
    print(f"[{idx+1}/{total}] {name} (lines {start}-{end})", file=sys.stderr)
    
    text = extract_chapter_text(start, end)
    passage = find_best_segment(text)
    
    print(f"  Passage: {len(passage)} chars", file=sys.stderr)
    
    letter = call_gemini(name, passage)
    noi_dung = letter.get('noi_dung', '')
    
    results.append({
        "so_thu": None,
        "noi_dung": noi_dung,
        "nguon": f"Hiểu Về Trái Tim - Minh Niệm ({name})"
    })
    
    print(f"  Letter: {len(noi_dung)} chars", file=sys.stderr)

# Output all results
output_path = 'gemini_all_letters.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone! Saved {len(results)} letters to {output_path}", file=sys.stderr)
print(json.dumps(results, ensure_ascii=False, indent=2))
