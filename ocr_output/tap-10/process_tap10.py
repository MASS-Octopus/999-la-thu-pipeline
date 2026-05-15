#!/usr/bin/env python3
"""
Hạt Giống Tâm Hồn Tập 10 — Extract, Score, Gemini Letter Generation
"""
import json, os, re, sys
import urllib.request, urllib.parse

FULL_PATH = os.path.join(os.path.dirname(__file__), "full.txt")
OLLAMA_URL = "http://localhost:11434/api/chat"
GEMINI_MODEL = "gemini-3-flash-preview:cloud"

# ===== STEP 1: PARSE STORIES =====

def parse_stories():
    """Parse full.txt into a list of (title, raw_text, author) tuples."""
    with open(FULL_PATH) as f:
        text = f.read()
    
    lines = text.split('\n')
    
    # Find story boundaries: "Theo dòng thời gian" markers + author credits
    theo_lines = []
    for i, line in enumerate(lines):
        if line.strip() == "Theo dòng thời gian":
            theo_lines.append(i)
    
    stories = []
    # Skip first "Theo dòng thời gian" on page 9 (it's the section header, story title is "Méẻ cá để đời")
    # Actually the first Theo dòng thời gian is at line 154, and "Méẻ cá để đời" is at line 156
    # Stories start between two Theo dòng thời gian markers
    # The pattern: PAGE NNN -> content -> Theo dòng thời gian -> story title -> story body -> author credit
    
    # Better approach: find story title lines (they appear right after Theo dòng... on next line or so)
    # and find author credits (lines that are just "- Author Name")
    
    # Let me extract all author lines first
    author_pattern = re.compile(r'^- [A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z.]+){1,3}$')
    author_candidates = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if author_pattern.match(stripped) and not stripped.startswith('- First') and not stripped.startswith('- Qprah') and not stripped.startswith('- Tục'):
            # Check it's not a quote attribution
            prev = lines[i-1].strip() if i > 0 else ""
            # Author credits typically end with just the name, no surrounding text
            author_candidates.append((i, stripped[2:].strip()))
    
    # Map authors to story ranges
    # Each story occupies a range between two Theo dòng thời gian markers
    story_ranges = []
    for i in range(len(theo_lines)):
        start = theo_lines[i]
        end = theo_lines[i+1] if i+1 < len(theo_lines) else len(lines)
        story_ranges.append((start, end))
    
    # For each range, find the title and author
    for r_start, r_end in story_ranges:
        # Find title: line or two after Theo dòng thời gian
        title = ""
        title_found = False
        for j in range(r_start+1, min(r_start+6, r_end)):
            line = lines[j].strip()
            if line and not line.startswith('Hạt giống') and not line.startswith('=== PAGE') and not line.startswith('Theo') and len(line) > 2:
                # Clean title
                clean = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s\.\,\!\?\-]+', '', line).strip()
                if clean and len(clean) > 2:
                    title = clean
                    title_found = True
                    break
        
        # Sometimes title spans 2 lines
        if title_found:
            for j in range(r_start+2, min(r_start+6, r_end)):
                line = lines[j].strip()
                if line and not line.startswith('Hạt giống') and not line.startswith('=== PAGE') and not line.startswith('Theo') and line != title:
                    clean = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s\.\,\!\?\-\/]+', '', line).strip()
                    if clean and len(clean) > 2 and clean not in title:
                        # Could be continuation of title
                        pass
        
        # Find author: last - Author in this range
        author = ""
        for aidx, aname in author_candidates:
            if r_start < aidx < r_end:
                author = aname
        
        if not title or not title_found:
            continue
        
        # Extract raw text: from after title/first non-header-lines to before trailing page nums
        text_start = r_start + 2
        # Skip header boilerplate
        for j in range(text_start, r_end):
            line = lines[j].strip()
            if line == "Hạt giống tâm hồn" or line.startswith("=== PAGE"):
                continue
            if line and len(line) > 10 and "Người liêm chính" not in line and not line.startswith('- ') and not line.startswith('Â'):
                text_start = j
                break
        
        text_end = r_end
        # Walk back to find last substantial line before author/footnotes
        for j in range(r_end-1, r_start, -1):
            if lines[j].strip().startswith('- '):
                text_end = j
                break
        
        # Collect raw text, strip page markers/quotes
        raw_lines = []
        quote_mode = False
        for j in range(text_start, text_end):
            line = lines[j]
            stripped = line.strip()
            if stripped.startswith("=== PAGE") or stripped == "Hạt giống tâm hồn":
                continue
            # Skip epigraph attribution lines (single author names at start)
            if author_pattern.match(stripped) and not quote_mode:
                # Check if it's at the very start of the story
                if len(raw_lines) < 10:
                    # likely an epigraph attribution, skip
                    continue
            # Skip footnote numbers
            if re.match(r'^\(\d+\)', stripped):
                continue
            # Remove leading quote indicators
            # Collect
            if stripped:
                raw_lines.append(stripped)
        
        raw_text = ' '.join(raw_lines)
        # Clean up OCR artifacts
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()
        
        if len(raw_text) > 100:
            stories.append({
                'title': title,
                'raw_text': raw_text,
                'author': author
            })
    
    return stories


# ===== STEP 2: SCORE STORIES =====

def score_story(story):
    """Score a story 0-100 based on emotional impact, first-person POV, narrative quality."""
    text = story['raw_text']
    score = 50  # baseline
    
    # First-person POV preference (context says ưu tiên ngôi thứ nhất)
    first_person_markers = ['tôi', 'mình', 'chúng tôi', 'em', 'cha tôi', 'mẹ tôi', 'con tôi']
    fp_count = sum(text.lower().count(m) for m in first_person_markers)
    if fp_count > 15:
        score += 15
    elif fp_count > 5:
        score += 8
    elif fp_count > 0:
        score += 3
    
    # Emotional content
    emotion_words = ['khóc', 'nước mắt', 'xúc động', 'cảm động', 'nghẹn', 'đau', 'buồn', 
                     'yêu thương', 'ấm áp', 'hạnh phúc', 'tuyệt vời', 'cảm ơn', 'biết ơn',
                     'hy sinh', 'chết', 'mất', 'nhớ', 'thương', 'run rẩy', 'sợ hãi',
                     'dũng cảm', 'can đảm', 'kiên trì', 'vượt qua', 'niềm tin',
                     'sững sờ', 'kinh ngạc', 'lặng người', 'thẫn thờ']
    emo_count = sum(text.lower().count(w) for w in emotion_words)
    if emo_count > 12:
        score += 15
    elif emo_count > 6:
        score += 10
    elif emo_count > 2:
        score += 5
    
    # Length bonus (substantial stories)
    length = len(text)
    if length > 3000:
        score += 10
    elif length > 1500:
        score += 7
    elif length > 800:
        score += 4
    
    # Dialogue/narrative quality (has conversations)
    dialogue_indicators = ['nói:', 'hỏi:', 'kêu lên', 'thốt lên', 'bảo:', 'hét']
    dia_count = sum(text.count(d) for d in dialogue_indicators)
    if dia_count > 5:
        score += 10
    elif dia_count > 2:
        score += 5
    
    # Child/parent relationship (powerful theme)
    family_words = ['cha', 'mẹ', 'con trai', 'con gái', 'bố', 'gia đình', 'con',
                    'vợ', 'chồng', 'ông', 'bà']
    fam_count = sum(text.lower().count(w) for w in family_words)
    if fam_count > 15:
        score += 10
    elif fam_count > 5:
        score += 5
    
    return min(score, 100)


# ===== STEP 3: CALL GEMINI =====

LETTER_PROMPT = """Bạn là người viết thư chuyên nghiệp cho series "999 Lá Thư" — những bức thư ngắn ấm áp gửi đến người đọc đang cần động viên.

NHIỆM VỤ: Đọc câu chuyện dưới đây, rút ra bài học sâu sắc nhất, rồi viết một lá thư ngắn (dưới 500 ký tự) bằng tiếng Việt. Lá thư phải:
- Viết ở ngôi thứ nhất, như một người bạn thân đang tâm sự
- Chứa ít nhất 1 câu trích dẫn hoặc hình ảnh từ chính câu chuyện gốc
- Kết thúc bằng lời nhắn nhủ ấm áp, tích cực
- Có cảm xúc chân thành, không sáo rỗng
- Dùng văn phong đời thường, gần gũi

CÂU CHUYỆN:
Tiêu đề: {title}
Tác giả: {author}
Nội dung: {text}

VIẾT LÁ THƯ (chỉ trả về nội dung thư, không giải thích gì thêm):"""


def call_gemini(prompt):
    """Call Gemini via Ollama."""
    payload = json.dumps({
        "model": GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 1024, "think": False}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "")
    except Exception as e:
        print(f"  ❌ Gemini error: {e}")
        return ""


# ===== MAIN =====

def main():
    print("=" * 60)
    print("HẠT GIỐNG TÂM HỒN TẬP 10 — PROCESSOR")
    print("=" * 60)
    
    # Step 1: Parse
    print("\n📖 Parsing stories from full.txt...")
    stories = parse_stories()
    print(f"   Found {len(stories)} stories")
    
    # Remove duplicate titles
    seen = set()
    unique = []
    for s in stories:
        key = s['title'][:30]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    stories = unique
    
    # Score
    print("\n📊 Scoring stories...")
    for s in stories:
        s['score'] = score_story(s)
        print(f"   [{s['score']:3d}] {s['title'][:50]:50s} | {s['author']}")
    
    # Sort by score
    stories.sort(key=lambda s: s['score'], reverse=True)
    
    # Top 8
    top8 = stories[:8]
    print(f"\n🏆 TOP 8 STORIES:")
    for i, s in enumerate(top8):
        print(f"   {i+1}. [{s['score']:3d}] {s['title'][:60]}")
    
    # Generate letters
    print(f"\n✉️  Calling Gemini for {len(top8)} letters...")
    results = []
    for i, s in enumerate(top8):
        print(f"   {i+1}/8: {s['title'][:40]}...")
        prompt = LETTER_PROMPT.format(
            title=s['title'],
            author=s.get('author', 'Khuyết danh'),
            text=s['raw_text'][:3000]  # Truncate for prompt
        )
        letter = call_gemini(prompt)
        
        # Clean letter
        letter = letter.strip()
        if letter.startswith('"') and letter.endswith('"'):
            letter = letter[1:-1]
        
        results.append({
            "so_thu_tap10": i + 1,
            "tieu_de_truyen": s['title'],
            "tac_gia_truyen": s.get('author', ''),
            "score": s['score'],
            "noi_dung_thu": letter or "[Gemini không trả về kết quả]"
        })
        print(f"      ✅ {len(letter)} chars")
    
    # Output JSON
    print("\n📋 FINAL JSON:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # Save
    out_path = os.path.join(os.path.dirname(__file__), "tap10_letters.json")
    with open(out_path, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Saved to {out_path}")
    
    return results

if __name__ == "__main__":
    main()
