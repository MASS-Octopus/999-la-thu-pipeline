#!/usr/bin/env python3
"""Clean Tập 8 extraction: parse stories correctly, filter, call Gemini."""
import re, json, subprocess, os, sys

OCR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         'ocr_output/tap-8/full.txt')
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'output/tap8_letters.json')

# Known author markers from manual review
KNOWN_AUTHORS = [
    'Lê Lai', 'Thanh Phương', 'Thanh Giang', 'Hồng Nhung',
    'Claude McDonald', 'Nguyễn Đoàn', 'Barbara Weidner',
    'Nguyên Thảo', 'Abraham Lincoln', 'Bích Thủy',
    'Thành Nhân', 'Lan Nguyên', 'Nguyễn Ngân',
    'Mai Quốc Thế', 'Lord Byron', 'Quỳnh Nga',
    'Jean Tharaud', 'Thanh Thủy', 'Thu Quỳnh',
    'Thanh Thảo', 'William Penn', 'Albert Einstein', 'Karl Marx'
]

KNOWN_AUTHORS_SET = set(KNOWN_AUTHORS)

def clean_story_text(text):
    """Clean OCR noise from story text."""
    # Remove page markers
    text = re.sub(r'=== PAGE \d+ ===', '', text)
    # Remove headers
    text = re.sub(r'Hạt giống tâm hồn\n*', '', text)
    text = re.sub(r'^Những câu chuyện cuộc sống\n*', '', text, flags=re.MULTILINE)
    # Remove standalone page numbers
    text = re.sub(r'^\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def parse_stories():
    with open(OCR_FILE, 'r') as f:
        lines = f.readlines()
    
    # Find PAGE 10
    page10_idx = next(i for i, l in enumerate(lines) 
                      if re.match(r'=== PAGE 10 ===', l.strip()))
    
    # Collect all author positions (only exact matches to known names)
    author_positions = []
    for i in range(page10_idx, len(lines)):
        line = lines[i].strip()
        if line.startswith('- '):
            name = line[2:].strip()
            # Check if name matches a known author (exact or starts with)
            for author in KNOWN_AUTHORS:
                if name == author or name.startswith(author + ' '):
                    author_positions.append((i, author))
                    break
    
    print(f"Found {len(author_positions)} story boundaries")
    
    # Extract stories between author boundaries
    stories = []
    for idx, (end_pos, author) in enumerate(author_positions):
        # Story start: after previous author line (or after PAGE 10 for first)
        start_pos = page10_idx + 1 if idx == 0 else author_positions[idx-1][0] + 1
        
        # Extract text
        raw_text = ''.join(lines[start_pos:end_pos])
        cleaned = clean_story_text(raw_text)
        
        # Extract title from first meaningful lines of the story
        # The title page has the title on the first content page
        title_lines = []
        for l in lines[start_pos:min(start_pos+30, len(lines))]:
            s = l.strip()
            if (s and not s.startswith('===') and not s.startswith('Hạt giống')
                and 'Những câu chuyện' not in s
                and not s.startswith('-') and not s.startswith('"')
                and not re.match(r'^\d+$', s) and len(s) > 3
                and not re.match(r'^[`\^\*#+\(\)~@°\|]+', s)):
                # Skip garbled lines
                garbled = sum(1 for c in s if c in '^®©℗™†‡§¶◊¥€£$¢@#~`\\°')
                if garbled <= len(s) * 0.3:
                    title_lines.append(s)
        
        # Title is usually the first non-garbled meaningful line
        title = title_lines[0] if title_lines else f"Truyện {idx+1}"
        
        stories.append({
            'idx': idx,
            'title': title,
            'author': author,
            'text': cleaned,
            'text_length': len(cleaned)
        })
    
    return stories

def score_story(story):
    """Score story for selection: prefer first-person, emotional depth."""
    text = story['text'].lower()
    score = 0
    
    # First person count (tôi, mình, em as speaker)
    first_pronouns = len(re.findall(r'\b(tôi|mình)\b', text))
    score += first_pronouns * 5
    
    # Emotional words
    emotional = ['yêu', 'thương', 'nhớ', 'khóc', 'cười', 'nước mắt',
                 'hạnh phúc', 'đau', 'buồn', 'vui', 'xúc động', 'nghẹn',
                 'trái tim', 'tâm hồn', 'nỗi', 'chia tay', 'cảm ơn',
                 'biết ơn', 'ân hận', 'hối hận', 'bình yên', 'ấm áp']
    for w in emotional:
        score += len(re.findall(w, text))
    
    # Penalize pure philosophy / parables
    parable_signs = ['ngụ ngôn', 'bài học', 'triết lý', 'đạo đức',
                     'nhà vua', 'hoàng tử', 'công chúa', 'ngày xưa',
                     'thượng đế', 'chúa trời']
    for w in parable_signs:
        if w in text:
            score -= 5
    
    # Penalize stories that are 100% third-person narrative
    if first_pronouns == 0:
        score -= 10
    
    # Penalize very short stories (likely poems/quotes)
    if story['text_length'] < 500:
        score -= 15
    
    return score

def call_gemini(story_text):
    """Call Gemini to transform story into a personal letter."""
    # Truncate for API
    if len(story_text) > 3500:
        story_text = story_text[:3500]
    
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
                    return content.strip()
            print(f"  Attempt {attempt+1}: empty/error")
        except Exception as e:
            print(f"  Attempt {attempt+1}: {e}")
    
    return None

def main():
    print("=" * 60)
    print("TẬP 8: EXTRACTING STORIES")
    print("=" * 60)
    
    stories = parse_stories()
    print(f"Parsed {len(stories)} stories")
    
    # Score and sort
    scored = [(score_story(s), s) for s in stories]
    scored.sort(key=lambda x: x[0], reverse=True)
    
    print("\nTOP 15 by score:")
    for score, s in scored[:15]:
        print(f"  Score {score:4d}: [{s['author']:20s}] \"{s['title'][:50]}\" ({s['text_length']} chars)")
    
    # Take top 8
    top8 = [s for _, s in scored[:8]]
    
    print(f"\nTRANSFORMING {len(top8)} stories via Gemini...")
    results = []
    for i, story in enumerate(top8):
        print(f"\n--- Story {i+1}: [{story['author']}] \"{story['title'][:60]}\"")
        print(f"    Text: {story['text_length']} chars")
        
        letter = call_gemini(story['text'])
        
        if letter:
            results.append({
                "so_thu": None,
                "noi_dung": letter,
                "nguon": f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
            })
            print(f"    OK: {len(letter)} chars")
        else:
            print(f"    FAILED after retries")
            results.append({
                "so_thu": None,
                "noi_dung": f"[LỖI: Gemini không phản hồi] {story['text'][:300]}",
                "nguon": f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
            })
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {len(results)} letters written to {OUTPUT_FILE}")
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
