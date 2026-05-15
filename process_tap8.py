#!/usr/bin/env python3
"""Process Tập 8 Top 8 stories: extract text, call Gemini, generate letters."""
import re, json, subprocess, time

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

def clean_line(line):
    s = line.strip()
    if re.match(r'=== PAGE \d+ ===', s): return None
    if re.match(r'^\d+$', s): return None
    if s in ('Hạt giống tâm hồn', 'hạtglống', 'hạtøfG', 'ạtplống', 'tâm hồn.',
             'Những câu chuyện cuộc sống', 'Những câu chuyện', 'Những câu chuyện cuộc sông',
             'Những câu chuyện cuộc sống'): return None
    if re.match(r'^[`\'\"\^~°®Œ\`\#\.\,\;\:\!\?\(\)\[\]\{\}…\-\–\—\\\/\|\@\$\€\%\&\*\+\=<>_ \t\n\r]+$', s) and len(s) < 40: 
        return None
    if re.match(r'^[lL]?\d+[\s`dseK\^h~]+$', s): return None
    if s in ('`', 'H', 'C', 'Tà'): return None
    if re.match(r'^\d+[A-Z].*$', s) and len(s) < 15: return None  # like "12l", "2i"
    return s

def extract_text(start_line, end_line):
    """Extract clean story text between line numbers (1-indexed)."""
    result = []
    for i in range(start_line - 1, min(end_line, len(lines))):
        cl = clean_line(lines[i])
        if cl is None:
            continue
        # Skip author credit lines and "Theo ..." lines
        if re.match(r'^- [A-ZÀ-Ỵ][a-zA-Zà-ỹ\s]+$', cl):
            continue
        if re.match(r'^Theo\s', cl):
            continue
        # Skip epigraph quote lines with trailing " marker
        # Skip epigraph author lines that are NOT the story ending
        # Simple: just add everything that's not explicitly metadata
        result.append(cl)
    
    # Join and clean up
    text = '\n'.join(result)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix common OCR errors  
    text = text.replace('TL.', 'Tôi')
    text = text.replace('A«', 'Annie')
    text = text.replace('N. ', 'Nhân ')
    text = text.replace('M. ', 'Mary ')
    text = text.replace('C, ', 'Con gái, ')
    text = text.replace('Nx ', 'Như ')
    text = text.replace('Tà ', 'Tại ')
    text = text.replace('Ciạ ', 'Chợt ')
    text = text.replace('M... ', 'Mary ')
    return text.strip()

# Define top 8 stories with exact boundaries
top8 = [
    {
        'title': 'Hàn gắn một trái tim vỡ',
        'author': 'Thanh Phương',
        'source': 'Love Is Just Like A Broken Arm',
        'start_line': 672,   # "C, con gái năm tuổi..." (skip title+epigraph)
        'end_line': 822,     # ends before "- Thanh Phương"
        'score': 8
    },
    {
        'title': 'Thiên thần can đảm',
        'author': 'Thanh Phương',
        'source': 'Angle Of Courage',
        'start_line': 2332,  # "N. dịp Giáng sinh..."
        'end_line': 2530,    # ends before "- Thanh Phương"
        'score': 8
    },
    {
        'title': 'Quà của Annie',
        'author': 'Thanh Phương',
        'source': 'Goodwill',
        'start_line': 264,   # "A« đứng dựa vào tủ..."
        'end_line': 489,     # ends before "- Thanh Phương"
        'score': 7
    },
    {
        'title': 'Tuyên ngôn của Cái Tôi',
        'author': 'Nguyễn Đoàn',
        'source': 'My Declaration Of Self-Esteem',
        'start_line': 835,   # "TL. sẽ sẵn sàng..." (after epigraph)
        'end_line': 912,     # ends before "- Nguyễn Đoàn"
        'score': 7
    },
    {
        'title': 'Vượt lên chính mình',
        'author': 'Lê Lai',
        'source': 'Internet',
        'start_line': 1208,  # "M... Dowiling là chủ tịch..."
        'end_line': 1434,    # ends before "- Lê Lai"
        'score': 7
    },
    {
        'title': 'Đôi mắt của mẹ',
        'author': 'Nguyễn Ngân',
        'source': 'My Own Experience',
        'start_line': 2124,  # "TL. yêu nhất là đôi bàn tay mẹ..."
        'end_line': 2311,    # ends before "- Nguyễn Ngân"
        'score': 7
    },
    {
        'title': 'Thiếu nữ cài hoa',
        'author': 'Thành Nhân',
        'source': 'Flower In Her Hair',
        'start_line': 1546,  # "M. là một nhân viên đồ họa..." (after previous story)
        'end_line': 1754,    # ends before "- Thành Nhân"
        'score': 6
    },
    {
        'title': 'Sinh ra từ trái tim',
        'author': 'Thanh Phương',
        'source': 'From The Heart',
        'start_line': 2605,  # "M. tôi bị chứng bệnh..."
        'end_line': 2892,    # ends before "- Thanh Phương"
        'score': 6
    }
]

# Extract text and call Gemini for each story
results = []

for idx, story in enumerate(top8):
    print(f"\n{'='*60}")
    print(f"Processing story {idx+1}/8: {story['title']}")
    print(f"  Source: {story['source']} | Score: {story['score']}")
    
    # Extract text
    text = extract_text(story['start_line'], story['end_line'])
    print(f"  Extracted: {len(text)} chars, {len(text.split())} words")
    
    # Call Gemini
    system_prompt = "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. Không kể lại cốt truyện. Không bài học đạo đức."
    user_prompt = f"Dựa vào câu chuyện sau viết một lá thư tâm sự:\n\n{text}"
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    cmd = [
        'curl', '-s', '--max-time', '90',
        'http://localhost:11434/api/chat',
        '-d', json.dumps(payload, ensure_ascii=False)
    ]
    
    print(f"  Calling Gemini...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=95)
        response = json.loads(result.stdout)
        letter = response.get('message', {}).get('content', '')
        print(f"  Response: {len(letter)} chars")
        
        # Validate length
        if len(letter) < 200:
            print(f"  WARNING: Letter too short ({len(letter)} chars, need 200+)")
        elif len(letter) > 350:
            print(f"  WARNING: Letter too long ({len(letter)} chars, max 350)")
            letter = letter[:350]  # Truncate
        else:
            print(f"  ✓ Letter length OK ({len(letter)} chars)")
        
        results.append({
            'so_thu': None,
            'noi_dung': letter,
            'nguon': f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
        })
        
        print(f"  ✓ Done")
        
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout!")
        results.append({
            'so_thu': None,
            'noi_dung': f'[Lỗi: Timeout khi gọi Gemini cho "{story["title"]}"]',
            'nguon': f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
        })
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({
            'so_thu': None,
            'noi_dung': f'[Lỗi: {str(e)[:100]} cho "{story["title"]}"]',
            'nguon': f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
        })
    
    # Small delay between calls
    time.sleep(2)

# Output final JSON
print(f"\n{'='*60}")
print(f"FINAL RESULTS: {len(results)} letters")
print(f"{'='*60}")

output_path = '/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/output/tap8_letters.json'
with open(output_path, 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Saved to: {output_path}")
print(f"\nJSON output:")
print(json.dumps(results, ensure_ascii=False, indent=2))
