#!/usr/bin/env python3
"""
Extract and score passages from Hae Min's 'Bước Chậm Lại Giữa Thế Gian Vội Vã'
OCR text, then select top 10 from at least 5 chapters.
"""
import re, json, sys

def read_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def clean_text(text):
    """Remove OCR artifacts and metadata"""
    # Remove page markers
    text = re.sub(r'=== PAGE \d+ ===\n?', '', text)
    # Remove https://thuviensach.vn
    text = re.sub(r'https://thuviensach\.vn', '', text)
    # Remove separator lines like —w—, —*k—, etc.
    text = re.sub(r'—[wW\*kKQqOo]+—', '', text)
    text = re.sub(r'—ooOoo—', '', text)
    # Remove —*—
    text = re.sub(r'—\*—', '', text)
    # Remove —*k—
    text = re.sub(r'—\*k—', '', text)
    # Remove —*w—
    text = re.sub(r'—\*w—', '', text)
    # Remove lines that are just dashes or separators
    text = re.sub(r'\n—+—\n', '\n\n', text)
    text = re.sub(r'\n\s*—\*—\s*\n', '\n\n', text)
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix OCR artifacts like "Ctt.." and random single chars on lines
    text = re.sub(r'\nCtt\.\.\s*\n', '\n', text)
    return text.strip()

def identify_chapter(text):
    """Identify which chapter a passage belongs to"""
    # Look for chapter markers in the preceding context
    ch_patterns = {
        'Nghỉ ngơi': r'Chương 1\.?\s*.*Nghỉ ngơi',
        'Những mối quan hệ': r'Chương 2\.?\s*.*quan hệ|Chương 2\.?\s*.*Những mối',
        'Tương lai': r'Chương 3\.?\s*.*Tương lai',
        'Tình yêu': r'Chương 4\.?\s*.*(Tình yêu|yêu)',
        'Chữa lành': r'Chương 5\.?\s*.*(Chữa lành|chữa lành)',
        'Cuộc sống': r'Chương 6\.?\s*',
        'Hạnh phúc': r'Chương 7\.?\s*',
        'Kết': r'Chương 8\.?\s*|Kết\s*\n',
    }
    for ch_name, pattern in ch_patterns.items():
        if re.search(pattern, text):
            return ch_name
    return None

def split_passages(text):
    """Split text into passages, assign chapters"""
    # First find all chapter boundaries
    chapters = []
    ch_matches = list(re.finditer(r'Chương (\d+)\.?\s*(.*?)(?:\n|$)', text))
    
    if not ch_matches:
        return []
    
    for i, m in enumerate(ch_matches):
        start = m.start()
        end = ch_matches[i+1].start() if i+1 < len(ch_matches) else len(text)
        ch_num = m.group(1)
        ch_title = m.group(2).strip()
        chapters.append((ch_num, ch_title, start, end))
    
    # Also include intro section (before Chapter 1)
    if chapters and chapters[0][2] > 0:
        chapters.insert(0, ('0', 'Mở Đầu', 0, chapters[0][2]))
    
    # Now split each chapter into passages
    passages = []
    for ch_num, ch_title, start, end in chapters:
        ch_text = text[start:end]
        # Remove the chapter header itself
        ch_header = f'Chương {ch_num}. {ch_title}'
        ch_text = ch_text.replace(ch_header, '', 1)
        ch_text = ch_text.strip()
        
        # Split by double newlines
        paras = [p.strip() for p in re.split(r'\n\n+', ch_text) if p.strip()]
        
        for p in paras:
            # Clean up newlines within passage (join into single space)
            cleaned = re.sub(r'\n+', ' ', p).strip()
            # Remove repeated spaces
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            
            if len(cleaned) >= 50:
                passages.append({
                    'text': cleaned,
                    'chapter': f'Chương {ch_num}: {ch_title}',
                    'chapter_num': int(ch_num)
                })
    
    return passages

def score_passage(text):
    """Score a passage: first_person*3 + emotion*2 - lecture*3"""
    score = 0
    
    # First-person indicators (strong weight: ×3)
    first_person_words = [
        r'\btôi\b', r'\bmình\b', r'\bchúng tôi\b', r'\bchính tôi\b',
        r'\btôi đã\b', r'\btôi thấy\b', r'\btôi cảm\b', r'\btôi nghĩ\b',
        r'\btôi nhận ra\b', r'\btôi biết\b', r'\btôi muốn\b', r'\btôi chỉ\b',
        r'\bcủa tôi\b', r'\bcho tôi\b', r'\bvới tôi\b', r'\blòng tôi\b',
        r'\btrong tôi\b'
    ]
    fp_count = sum(len(re.findall(w, text, re.IGNORECASE)) for w in first_person_words)
    score += min(fp_count, 5) * 3  # Cap at 5 to prevent one passage dominating
    
    # Emotion words (medium weight: ×2)
    emotion_words = [
        r'\bmệt mỏi\b', r'\btổn thương\b', r'\bđau khổ\b', r'\byêu thương\b',
        r'\bthương\b', r'\bnước mắt\b', r'\bkhóc\b', r'\bcô đơn\b', r'\bcô quạnh\b',
        r'\bbuồn\b', r'\bđau đớn\b', r'\bvết thương\b', r'\bchữa lành\b', r'\ban ủi\b',
        r'\bhạnh phúc\b', r'\bvui vẻ\b', r'\bbình yên\b', r'\btrống trải\b',
        r'\bbất an\b', r'\blo lắng\b', r'\bkhổ sở\b', r'\bphiền não\b',
        r'\bxót xa\b', r'\bnhớ\b', r'\btha thứ\b', r'\bgiận\b', r'\bghét\b',
        r'\bkiệt sức\b', r'\btrầm cảm\b', r'\btuyệt vọng\b', r'\bsợ\b',
        r'\bđộng viên\b', r'\bấm áp\b', r'\btrân trọng\b', r'\bquý\b',
        r'\bxấu hổ\b', r'\bđáng thương\b', r'\bbị bỏ rơi\b', r'\bbị bỏ lại\b',
        r'\bthất bại\b', r'\bvấp ngã\b'
    ]
    em_count = sum(len(re.findall(w, text, re.IGNORECASE)) for w in emotion_words)
    score += min(em_count, 5) * 2  # Cap at 5
    
    # Lecture indicators (penalty: ×3) - only at START of passage
    lecture_words_start = [
        r'^[^.!?]*bạn nên\b', r'^[^.!?]*hãy\b', r'^[^.!?]*đừng\b',
        r'^[^.!?]*bạn hãy\b', r'^[^.!?]*bạn đừng\b'
    ]
    for w in lecture_words_start:
        if re.search(w, text, re.IGNORECASE):
            score -= 3
            break  # Only count once
    
    # Bonus: if the passage has both 'tôi' and emotion about suffering
    if re.search(r'\btôi\b', text, re.IGNORECASE) and re.search(r'\b(mệt mỏi|tổn thương|đau khổ|cô đơn|nước mắt|chữa lành|buồn)\b', text, re.IGNORECASE):
        score += 2
    
    # Bonus: confessional tone (tôi + kể/viết/nói/tâm sự/chia sẻ)
    if re.search(r'\btôi\b', text, re.IGNORECASE) and re.search(r'\b(kể|viết|tâm sự|chia sẻ|trò chuyện|thú thật)\b', text, re.IGNORECASE):
        score += 1
    
    # Penalty: too much imperative/lecturing overall
    lecture_count = len(re.findall(r'\b(hãy|đừng|phải|nên)\b', text, re.IGNORECASE))
    if lecture_count > 3:
        score -= 2
    
    # Penalty: too preachy/religious jargon heavy
    religious_count = len(re.findall(r'\b(Phật|Chúa|giác ngộ|tu hành|tôn giáo|kinh|cầu nguyện)\b', text, re.IGNORECASE))
    if religious_count > 2:
        score -= 1
    
    # Ensure minimum score
    score = max(score, -5)
    
    return score

def main():
    text = read_text('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/buoc-cham-lai/full.txt')
    text = clean_text(text)
    passages = split_passages(text)
    
    print(f"Total passages (>=50 chars): {len(passages)}")
    print(f"Chapters found: {set(p['chapter'] for p in passages)}")
    
    # Score all passages
    for p in passages:
        p['score'] = score_passage(p['text'])
    
    # Sort by score descending
    passages.sort(key=lambda x: x['score'], reverse=True)
    
    # Show top 30 for analysis
    print("\n=== TOP 30 PASSAGES (by score) ===")
    for i, p in enumerate(passages[:30]):
        print(f"\n--- Rank {i+1}, Score: {p['score']}, Chapter: {p['chapter']} ---")
        print(p['text'][:200] + "..." if len(p['text']) > 200 else p['text'])
    
    # Select top 10 from at least 5 different chapters
    selected = []
    used_chapters = set()
    
    for p in passages:
        if p['score'] < 4:
            continue
        if p['chapter_num'] == 0:  # Skip intro
            continue
        if len(selected) >= 10:
            break
        selected.append(p)
        used_chapters.add(p['chapter'])
    
    print(f"\n=== SELECTED ({len(selected)} passages from {len(used_chapters)} chapters) ===")
    print(f"Chapters used: {used_chapters}")
    
    for i, p in enumerate(selected):
        print(f"\n--- #{i+1}, Score: {p['score']}, Chapter: {p['chapter']} ---")
        print(p['text'])
    
    # Save as JSON
    output = [{
        'index': i+1,
        'score': p['score'],
        'chapter': p['chapter'],
        'text': p['text']
    } for i, p in enumerate(selected)]
    
    with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/data/selected_passages.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(output)} passages to selected_passages.json")

if __name__ == '__main__':
    main()
