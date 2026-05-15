#!/usr/bin/env python3
"""Extract stories from Tap 10 using ONLY real author names as boundaries."""
import re
import json

OCR_FILE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-10/full.txt"

with open(OCR_FILE, 'r', encoding='utf-8') as f:
    full_text = f.read()

# Real author names from the book (verified from output):
# These are the actual story/article authors, not dialogue fragments
real_authors = [
    "James P. Lenfestey",
    "Helen Rezatto",  
    "Anne Goodrich",
    "Lynn Rosellini",
    "Dudley A. Henrique",
    "Mitchell Wilson",
    "William M. Hendryx",
    "Doris Cheney Whitehouse",
    "Sarah Ban Breathnach",
    "Richard Collier",
    "Janet Kinosian",
    "Jaroldeen Edwards",
    "Joe Paterno",
    "Peter Michelmore",
    "Leo Rosten",
    "Lee Maynard",
    "Reba McEntire",
    "Noah Gilson, M.D.",
]

# Also poetry/quote attributions (not real stories):
quotes = [
    "Emily Dickinson", "Freya Stark", "Martin Luther King", 
    "Arthur Ashe", "William Arthur Ward", "Abraham Lincoln",
    "Richard Moss", "George Lucas", "George Eliot",
    "Sydney J. Harris", "Jerry Ellis", "Marilyn Vos Savant",
    "Stephen Covey", "Abigail Van Buren",
    "Marfin Buxbaum",  # actually a real story
]

# Build a map of author name -> position in text
author_positions = []
for author in real_authors:
    # Find "- Author Name" at end of lines
    pattern = r'\n-\s+' + re.escape(author) + r'\s*\n'
    for m in re.finditer(pattern, full_text):
        author_positions.append((m.end(), author))

# Also check for OCR variants (e.g., RÑezatfto for Rezatto)
# Add known misspellings
ocr_variants = {
    "James P. Lenƒesfy": "James P. Lenfestey",
    "Helen RÑezatfto": "Helen Rezatto",
    "kynn RÑosellini": "Lynn Rosellini",
    "Dudley A. Henrique": "Dudley A. Henrique",
    "Mitchell Wïlson": "Mitchell Wilson",
    "WilHam M. Hendryx": "William M. Hendryx",
    "Doris Cheney Whiftehouse": "Doris Cheney Whitehouse",
    "Ñichard Collier": "Richard Collier",
    "Janet Kinosian": "Janet Kinosian",
    "Jaroldeen Edwards": "Jaroldeen Edwards",
    "Joe Puterno": "Joe Paterno",
    "Peter Michelmore": "Peter Michelmore",
    "Leo Rosten": "Leo Rosten",
    "Lee Maynard": "Lee Maynard",
    "Reba McEntire": "Reba McEntire",
    "Noah Gilson, M.D.": "Noah Gilson, M.D.",
    "Marfin Buxbaum": "Marfin Buxbaum",  # real story too
    "Sarah Ban Breathnach": "Sarah Ban Breathnach",
}

for ocr_name, real_name in ocr_variants.items():
    pattern = r'\n-\s+' + re.escape(ocr_name) + r'\s*\n'
    for m in re.finditer(pattern, full_text):
        author_positions.append((m.end(), real_name))

# Sort by position
author_positions.sort()

# Remove duplicates (same position)
seen = set()
unique = []
for pos, name in author_positions:
    if pos not in seen:
        seen.add(pos)
        unique.append((pos, name))
author_positions = unique

print(f"Found {len(author_positions)} real author signatures:")
for pos, name in author_positions:
    line_num = full_text[:pos].count('\n') + 1
    print(f"  Line {line_num}: {name}")

# Find page 11 start
page11 = re.search(r'=== PAGE 11 ===', full_text)
start_pos = page11.end() if page11 else 0

# Extract stories between real author boundaries
stories = []
prev_pos = start_pos
for pos, author in author_positions:
    # Find the start of the story (go back to previous signature or page 11)
    story_text = full_text[prev_pos:pos].strip()
    
    if len(story_text) < 200:  # Skip very short fragments
        prev_pos = pos
        continue
    
    # Clean OCR artifacts
    story_text = re.sub(r'=== PAGE \d+ ===', '', story_text)
    story_text = re.sub(r'Hạt giống tâm hồn', '', story_text)
    story_text = re.sub(r'Theo dòng thời gian', '', story_text)
    story_text = re.sub(r'\n\d+\n', '\n', story_text)
    story_text = re.sub(r'\n{3,}', '\n\n', story_text)
    story_text = story_text.strip()
    
    # Find title (first meaningful line)
    lines = [l.strip() for l in story_text.split('\n') if l.strip()]
    title = ""
    body_lines = []
    found_title = False
    
    for l in lines:
        # Skip page numbers, obvious garbage
        if re.match(r'^\d+$', l) or len(l) <= 2:
            continue
        if not found_title and len(l) > 5 and len(l) < 100:
            title = l
            found_title = True
        else:
            body_lines.append(l)
    
    if not title and lines:
        title = lines[0]
        body_lines = lines[1:]
    
    body = '\n'.join(body_lines).strip()
    
    if len(body) > 200:
        stories.append({
            'title': title,
            'text': body,
            'author': author,
            'char_count': len(body)
        })
    
    prev_pos = pos

print(f"\nExtracted {len(stories)} real stories")

# Classify
def classify(s):
    full = s['title'] + ' ' + s['text']
    fp = len(re.findall(r'\b(tôi|mình)\b', full.lower()))
    
    rejection = [
        r'bài học', r'đạo đức', r'chúng ta nên', r'chúng ta phải',
        r'hãy luôn', r'ngụ ngôn', r'triết lý', r'bài giảng',
        r'rút ra', r'kết luận', r'thông điệp', r'lời khuyên',
        r'bạn hãy', r'bạn nên', r'chân lý',
        r'sống có đạo đức', r'quyết định đúng đắn', r'lẽ phải',
    ]
    rej = sum(len(re.findall(p, full.lower())) for p in rejection)
    
    # Check if last paragraphs are moralistic
    paragraphs = s['text'].split('\n\n')
    last_para = paragraphs[-1].lower() if paragraphs else ''
    moral_end = bool(re.search(r'(bài học|chúng ta|bạn sẽ|hãy|phải|nên)', last_para[:200]))
    
    if fp >= 5 and rej <= 3:
        return True, fp, rej
    elif fp >= 3 and rej <= 1:
        return True, fp, rej
    elif rej >= 5:
        return False, fp, rej
    elif fp == 0 and rej >= 2:
        return False, fp, rej
    elif fp == 0 and moral_end:
        return False, fp, rej
    
    return fp >= 2, fp, rej

print("\n" + "=" * 80)
qualifying = []
rejected = []

for i, s in enumerate(stories):
    keep, fp, rej = classify(s)
    status = "KEEP" if keep else "REJECT"
    print(f"\n{i+1}. [{status}] [{s['title']}] by {s['author']} ({s['char_count']} chars, fp={fp}, rej={rej})")
    preview = s['text'][:200].replace('\n', ' | ')
    print(f"   {preview}...")
    
    if keep:
        qualifying.append(s)
    else:
        rejected.append(s)

print(f"\n{'='*80}")
print(f"QUALIFYING: {len(qualifying)} | REJECTED: {len(rejected)}")

print("\n--- QUALIFYING ---")
for i, s in enumerate(qualifying):
    fp_count = len(re.findall(r'\b(tôi|mình)\b', (s['title']+' '+s['text']).lower()))
    print(f"  {i+1}. [{s['title']}] - {s['author']} ({s['char_count']} chars, fp={fp_count})")

with open('/tmp/tap10_final.json', 'w', encoding='utf-8') as f:
    json.dump({'qualifying': qualifying, 'rejected': rejected}, f, ensure_ascii=False, indent=2)

print("\nSaved to /tmp/tap10_final.json")
