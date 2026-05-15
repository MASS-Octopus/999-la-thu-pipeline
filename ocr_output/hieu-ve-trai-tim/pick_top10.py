#!/usr/bin/env python3
"""Pick top 10 best passages from 50 chapters -> call Gemini -> JSON array of 10 letters.
Relaxed criteria due to OCR noise. Normalizes OCR typos aggressively."""

import json, subprocess, sys, re

with open('full.txt', 'r') as f:
    raw = f.read()
lines = raw.split('\n')

chapters = [
    ("Khổ đau", 237, 426), ("Hạnh phúc", 426, 639), ("Tình yêu", 639, 794),
    ("Tình thương", 794, 934), ("Tức giận", 934, 1116), ("Chịu đựng", 1116, 1261),
    ("Ghen tuông", 1261, 1423), ("Tha thứ", 1423, 1618), ("Sòng phẳng", 1618, 1766),
    ("Cô đơn", 1766, 1945), ("Hiến tặng", 1945, 2168), ("Trao thân", 2168, 2316),
    ("Tạ ơn", 2316, 2501), ("Nhàm chán", 2501, 2684), ("Kính trọng", 2684, 2869),
    ("Nghi ngờ", 2869, 3095), ("Lắng nghe", 3095, 3292), ("Phán xét", 3292, 3514),
    ("Ái ngữ", 3514, 3707), ("Thành kiến", 3707, 3854), ("Làm mới", 3854, 4064),
    ("Che đậy", 4064, 4298), ("Thành thật", 4298, 4504), ("Nguyên tắc", 4504, 4700),
    ("Tùy duyên", 4700, 4901), ("Tuyệt vọng", 4901, 5079), ("Niềm tin", 5079, 5296),
    ("Ý chí", 5296, 5486), ("Do dự", 5486, 5699), ("Thất bại", 5699, 5875),
    ("Thành công", 5875, 6019), ("Tham vọng", 6019, 6242), ("Biết đủ", 6242, 6470),
    ("Dựa dẫm", 6470, 6672), ("Nương tựa", 6672, 6865), ("Yếu đuối", 6865, 7099),
    ("Sám hối", 7099, 7322), ("Lười biếng", 7322, 10392),
]

def normalize_vn(text):
    """Aggressively fix OCR typos in Vietnamese text while preserving case."""
    # Map common OCR corruptions
    mapping = [
        # 'u' for 'y' or 'v' or 'ý' (most common)
        ('uêu', 'yêu'), ('uếu', 'yếu'), ('uể', 'yể'), ('uê', 'yê'),
        ('uà', 'và'), ('uẫn', 'vẫn'), ('uội', 'vội'), ('uừa', 'vừa'),
        ('uề', 'về'), ('uới', 'với'), ('uào', 'vào'), ('uậy', 'vậy'),
        ('uốn', 'vốn'), ('uô', 'vô'), ('uất', 'vất'), ('uui', 'vui'),
        ('uui', 'vui'), ('uương', 'vương'),
        # 'u' for 'y' at word start
        ('uêu', 'yêu'), ('uếm', 'yếm'), ('uên', 'yên'),
        # 'khô' for 'khổ'
        ('khô ', 'khổ '), ('khô.', 'khổ.'), ('khô,', 'khổ,'),
        # 'ú'/'u' for 'ý'
        ('ú', 'ý'),
        # Mixed letters
        ('nôi', 'nỗi'), ('nồi', 'nỗi'),
        ('bâu', 'bây'), ('quuết', 'quyết'), ('sq', 'sa'),
        ('uí', 'ví'), ('chĩa', 'chia'), ('màu', 'màu'),
        ('UỚI', 'VỚI'), ('uẫn', 'vẫn'),
        # 'đ' issues
        ('đuợc', 'được'), ('đuỡng', 'đường'),
        # Misc
        ('dê', 'dễ'), ('chân thật', 'chân thật'),
    ]

    for old, new in mapping:
        text = text.replace(old, new)
    return text

def clean_ocr(text):
    text = re.sub(r'=== PAGE \d+ ===', '', text)
    text = re.sub(r'[ˆ°®‚„\u200b]', '', text)
    text = normalize_vn(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Emotion keywords - expanded
EMO_WORDS = re.compile(
    r'\b(khóc|yêu|thương|đau|buồn|nhớ|cô đơn|hạnh phúc|tha thứ|tổn thương|ghen|tuyệt vọng'
    r'|giận|sợ|tin|mong|ước|chịu đựng|hy vọng|mất mát|chia lìa|bỏ rơi|nâng niu'
    r'|ấm áp|bình yên|an ủi|vỗ về|thổn thức|ngậm ngùi|xót xa|nước mắt'
    r'|khổ đau|chịu khổ|thương đau|nỗi buồn|niềm vui|cô độc|trống vắng)\b',
    re.IGNORECASE
)

all_candidates = []

for ch_name, start, end in chapters:
    text = '\n'.join(lines[start-1:end-1])
    paras = re.split(r'\n\s*\n', text)

    for para in paras:
        clean = clean_ocr(para)
        char_count = len(clean)

        # Relaxed: 80-500 chars
        if char_count < 80 or char_count > 500:
            continue

        # Count 'tôi'/'mình' - relaxed: >=1
        fp_count = len(re.findall(r'\b(tôi|mình)\b', clean.lower()))

        # Count 'ta' (also first-person in Vietnamese spiritual prose)
        ta_count = len(re.findall(r'\bta\b', clean.lower()))

        if fp_count + ta_count < 2:
            continue

        # Count emotion words - relaxed: >=1
        emo_count = len(EMO_WORDS.findall(clean.lower()))
        if emo_count < 1:
            continue

        # Score
        score = fp_count * 4 + emo_count * 3 + ta_count * 2 + min(char_count // 40, 6)

        # Penalty for lecture tone
        lecture = len(re.findall(
            r'\b(bạn nên|hãy luôn|đừng bao giờ|chúng ta nên|ta phải|ta cần phải|phải biết|hãy nhớ)\b',
            clean.lower()
        ))
        score -= lecture * 3

        # Bonus for rhetorical questions
        questions = clean.count('?')
        score += questions * 2

        # Bonus for emotional quotes/poetry
        quotes = clean.count('"') // 2
        score += quotes

        all_candidates.append((score, clean, ch_name))

all_candidates.sort(key=lambda x: -x[0])

# Pick top 10 from DISTINCT chapters
seen_chapters = set()
top10 = []
for score, passage, ch_name in all_candidates:
    if ch_name not in seen_chapters:
        seen_chapters.add(ch_name)
        top10.append((score, passage, ch_name))
    if len(top10) >= 10:
        break

print(f"Found {len(all_candidates)} total candidates across {len(set(c for _,_,c in all_candidates))} chapters", file=sys.stderr)
if len(top10) < 10:
    print(f"WARNING: Only {len(top10)} distinct chapters with candidates!", file=sys.stderr)

# Print top selections
for i, (score, passage, ch_name) in enumerate(top10):
    print(f"  [{i+1}] {ch_name}: score={score}, chars={len(passage)}",
          file=sys.stderr)

def call_gemini(chapter_name, passage):
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
            {"role": "user", "content": prompt}
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
        json_match = re.search(r'\{[^{}]*"noi_dung"[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        content = content.strip()
        if content.startswith('```'):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        return {"noi_dung": content.strip()}
    except Exception as e:
        print(f"  ERROR [{chapter_name}]: {e}", file=sys.stderr)
        return {"noi_dung": f"[Lỗi Gemini: {str(e)[:100]}]"}

# Call Gemini
results = []
for i, (score, passage, ch_name) in enumerate(top10):
    print(f"\n[{i+1}/10] Calling Gemini for '{ch_name}'...", file=sys.stderr)
    print(f"  Passage ({len(passage)} chars): {passage[:150]}...", file=sys.stderr)

    letter = call_gemini(ch_name, passage)
    noi_dung = letter.get('noi_dung', '')
    results.append({
        "so_thu": None,
        "noi_dung": noi_dung,
        "nguon": f"Hiểu Về Trái Tim - Minh Niệm ({ch_name})"
    })
    print(f"  -> Letter: {len(noi_dung)} chars", file=sys.stderr)

output_path = 'top10_letters.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone! Saved to {output_path}", file=sys.stderr)
# Final JSON output to stdout
print(json.dumps(results, ensure_ascii=False, indent=2))
