#!/usr/bin/env python3
"""Parse OCR for Tập 8, extract stories, filter, and produce Gemini-transformed letters."""
import re, json, subprocess, sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_FILE = os.path.join(SCRIPT_DIR, 'ocr_output/tap-8/full.txt')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'output/tap8_letters.json')

def clean_text(text):
    """Clean OCR noise but preserve meaning."""
    # Remove page markers
    text = re.sub(r'=== PAGE \d+ ===', '', text)
    # Remove header/footer patterns
    text = re.sub(r'Hạt giống tâm hồn\n+', '', text)
    text = re.sub(r'^Những câu chuyện cuộc sống\n+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Những câu chuyện\n+', '', text, flags=re.MULTILINE)
    # Remove page numbers (standalone 1-3 digit numbers on their own line)
    text = re.sub(r'^\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    # Fix common OCR errors
    text = text.replace('  ', ' ')
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def parse_stories():
    with open(OCR_FILE, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find PAGE 10 boundary
    page10_idx = None
    for i, line in enumerate(lines):
        if re.match(r'=== PAGE 10 ===', line.strip()):
            page10_idx = i
            break
    
    if page10_idx is None:
        print("ERROR: PAGE 10 not found!")
        return []
    
    # Known author names from the task description
    known_authors = ['Thanh Giang', 'Lê Lai', 'Thanh Phương', 'Thành Nhân', 
                     'Bích Thủy', 'Nguyên Thảo', 'Lan Nguyên', 'Thanh Thủy',
                     'Thanh Thảo', 'Thu Quỳnh', 'Quỳnh Nga', 'Mai Quốc Thế',
                     'Nguyễn Ngân', 'Claude McDonald', 'Barbara Weidner',
                     'Abraham Lincoln', 'Albert Einstein', 'Karl Marx',
                     'Lord Byron', 'Jean Tharaud', 'William Penn']
    
    # Find all story boundaries using author lines
    author_pattern = re.compile(r'^- (.+?)(?:\s*$|\s+Theo)')
    
    author_positions = []
    for i in range(page10_idx, len(lines)):
        line = lines[i].strip()
        m = author_pattern.match(line)
        if m:
            author = m.group(1).strip()
            # Skip preamble authors
            if author in ('First News', 'Eirst News', 'Lillian Hellman', 'Old Sanskit Text'):
                continue
            author_positions.append((i, author))
    
    print(f"Found {len(author_positions)} author markers after PAGE 10")
    for idx, (pos, author) in enumerate(author_positions):
        print(f"  {idx}: line {pos}, author={author}")
    
    # For each story: find its starting page marker boundary,
    # then collect text from start to author line
    stories = []
    for idx, (author_pos, author) in enumerate(author_positions):
        # Find the story start: go backwards to find the previous story end
        # A story starts after the previous story's author + any metadata pages
        story_start_pos = page10_idx
        if idx > 0:
            # Start after previous author line
            story_start_pos = author_positions[idx-1][0] + 1
        else:
            # First story: find the first page marker after PAGE 10
            for i in range(page10_idx, author_pos):
                if re.match(r'=== PAGE \d+ ===', lines[i].strip()):
                    story_start_pos = i
                    break
        
        # Collect raw text between story_start_pos and author_pos
        raw_lines = lines[story_start_pos:author_pos]
        raw_text = '\n'.join(raw_lines)
        
        # Try to extract title from first pages of story
        # The title page usually has the title on the first page
        title = None
        for i in range(story_start_pos, min(story_start_pos + 20, len(lines))):
            l = lines[i].strip()
            if (l and not l.startswith('===') and 
                not l.startswith('Hạt giống') and
                not 'Những câu chuyện' in l and
                not re.match(r'^\d{1,3}$', l) and
                not l.startswith('-') and
                not l.startswith('"') and
                not re.match(r'^[`\^\*#\+\(\)~@°]+', l) and
                len(l) > 3):
                # Skip clearly garbled OCR lines
                garbled_ratio = sum(1 for c in l if c in '`\\^°#®©℗™~†‡§¶◊¥€£$¢~*+@=<>|[]{}')
                if garbled_ratio > len(l) * 0.3:
                    continue
                title = l
                break
        
        if title is None:
            title = "Unknown"
        
        cleaned = clean_text(raw_text)
        
        # Determine type: first-person, parable, philosophical
        text_lower = cleaned.lower()
        has_first_person = bool(re.search(r'\b(tôi|mình|em)\b', text_lower))
        has_parable = bool(re.search(r'\b(ngụ ngôn|bài học|triết lý|đạo đức|bài học từ|câu chuyện về|chuyện ngụ ngôn|một hôm|ngày xưa)\b', text_lower))
        
        stories.append({
            'title': title,
            'author': author,
            'text': cleaned,
            'has_first_person': has_first_person,
            'is_parable': has_parable,
            'text_length': len(cleaned)
        })
    
    return stories

def filter_stories(stories):
    """Filter stories: prefer first-person, emotional, reject pure parables/philosophy."""
    # Score each story
    scored = []
    for s in stories:
        score = 0
        text = s['text'].lower()
        
        # Strong preference for first-person
        first_count = len(re.findall(r'\b(tôi|mình|em)\b', text))
        score += first_count * 3
        
        # Preference for emotional content words
        emotion_words = ['yêu', 'thương', 'nhớ', 'khóc', 'cười', 'nước mắt', 'hạnh phúc',
                         'đau', 'buồn', 'vui', 'xúc động', 'cảm động', 'nghẹn', 'tim',
                         'lòng', 'trái tim', 'tâm hồn', 'nỗi', 'chia tay', 'gặp', 'mong']
        for w in emotion_words:
            score += len(re.findall(r'\b' + w + r'\b', text))
        
        # Penalize pure parable/philosophy
        if s['is_parable']:
            score -= 10
        
        # Penalize stories that are ALL dialogue without personal voice
        if first_count == 0:
            score -= 5
        
        # Penalize stories with lots of quotes (likely philosophical)
        quote_count = text.count('"') + text.count('"') + text.count('"')
        if quote_count > 10:
            score -= 5
        
        scored.append((score, s))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    for score, s in scored:
        print(f"  Score {score:4d}: [{s['author']}] \"{s['title'][:60]}\" (1st:{s['has_first_person']}, parable:{s['is_parable']}, len:{s['text_length']})")
    
    # Take top 8
    return [s for _, s in scored[:8]]

def call_gemini(story_text, story_title):
    """Call Gemini via Ollama API to transform story into a letter."""
    system_prompt = (
        "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. "
        "Không kể lại cốt truyện. Không bài học đạo đức."
    )
    
    # Truncate story text if too long (keep ~3000 chars max)
    max_story_len = 3000
    if len(story_text) > max_story_len:
        story_text = story_text[:max_story_len] + "..."
    
    user_prompt = f"Dựa vào câu chuyện sau viết một lá thư tâm sự:\n\n{story_text}"
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    for attempt in range(2):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '90',
                 'http://localhost:11434/api/chat',
                 '-d', json.dumps(payload)],
                capture_output=True, text=True, timeout=95
            )
            
            if result.returncode == 0 and result.stdout.strip():
                resp = json.loads(result.stdout)
                content = resp.get('message', {}).get('content', '')
                if content and len(content) > 50:
                    return content.strip()
            
            print(f"  Attempt {attempt+1} failed: {result.stderr[:200] if result.stderr else 'empty response'}")
        except Exception as e:
            print(f"  Attempt {attempt+1} exception: {e}")
    
    return None

def main():
    print("=" * 60)
    print("PARSING STORIES FROM TẬP 8 OCR")
    print("=" * 60)
    
    stories = parse_stories()
    print(f"\nFound {len(stories)} raw stories")
    
    print("\nFILTERING & SCORING:")
    top8 = filter_stories(stories)
    print(f"\nSelected {len(top8)} stories for transformation")
    
    results = []
    for idx, story in enumerate(top8):
        print(f"\n{'='*60}")
        print(f"STORY {idx+1}: {story['title'][:60]}")
        print(f"  Author: {story['author']}")
        print(f"  Text length: {story['text_length']} chars")
        
        print("  Calling Gemini...")
        letter = call_gemini(story['text'], story['title'])
        
        if letter:
            results.append({
                "so_thu": None,
                "noi_dung": letter,
                "nguon": f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
            })
            print(f"  SUCCESS: Got {len(letter)} chars letter")
        else:
            print(f"  FAILED after retries")
            # Try fallback: use story text as-is
            results.append({
                "so_thu": None,
                "noi_dung": f"[LỖI: Không thể chuyển hóa] {story['text'][:500]}",
                "nguon": f"Hạt Giống Tâm Hồn - Tập 8 ({story['title']})"
            })
    
    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"OUTPUT WRITTEN TO: {OUTPUT_FILE}")
    print(f"Total letters: {len(results)}")
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
