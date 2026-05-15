#!/usr/bin/env python3
"""
Final extraction: find proper story titles + select 8 best for Gemini transformation.
Uses section headers to identify titles.
"""
import re
import json
import subprocess
import sys

OCR_FILE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-10/full.txt"

with open(OCR_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all section starts: after "Theo dòng thời gian" or "Hạt giống tâm hồn", 
# the next 1-3 non-empty lines form the title
sections = []
in_start = True
i = 0
while i < len(lines):
    line = lines[i].strip()
    
    # Skip pages 1-10
    if line == "=== PAGE 11 ===":
        in_start = False
    
    if in_start:
        i += 1
        continue
    
    # Section markers
    if line in ("Theo dòng thời gian", "Hạt giống tâm hồn"):
        # Collect title lines (next 1-3 non-empty, non-number lines)
        title_lines = []
        j = i + 1
        while j < len(lines) and j < i + 5:
            nl = lines[j].strip()
            if nl and not re.match(r'^\d+$', nl) and nl not in ("Theo dòng thời gian", "Hạt giống tâm hồn"):
                # Stop if hitting an epigraph (quote with attribution)
                if nl.startswith('"') or nl.startswith('"') or nl.startswith('"'):
                    # Single quote line might be epigraph, check if next is "- Name"
                    if j+1 < len(lines) and lines[j+1].strip().startswith('-'):
                        break
                title_lines.append(nl)
                j += 1
            else:
                break
        
        if title_lines:
            title = ' '.join(title_lines)
            sections.append({
                'start_line': i + 1,
                'title': title,
                'text_start': j + 1  # where story text begins
            })
    
    i += 1

# Now extract story text between section starts
# Story ends at the author signature "- Author Name" before next section
stories_raw = []
for idx, sec in enumerate(sections):
    start = sec['text_start']
    # Find end: author signature before next section or EOF
    if idx + 1 < len(sections):
        end_line = sections[idx + 1]['start_line'] - 1
    else:
        end_line = len(lines)
    
    # Collect text, looking for author signature
    story_lines = []
    author = ""
    found_author = False
    
    for li in range(start - 1, min(end_line, len(lines))):
        l = lines[li].strip()
        
        # Skip page markers, headers
        if re.match(r'=== PAGE \d+ ===', l):
            continue
        if l in ("Theo dòng thời gian", "Hạt giống tâm hồn"):
            continue
        if re.match(r'^\d+$', l):
            continue
        
        # Check for author signature
        auth_match = re.match(r'^-\s+(.+)$', l)
        if auth_match and not found_author:
            # Verify it's likely a real author name (not dialogue)
            candidate = auth_match.group(1)
            # Skip dialogue (starts with lowercase or is clearly conversation)
            if (len(candidate) > 5 and 
                not candidate.startswith('"') and
                not re.match(r'^[a-zà-ỹ]', candidate) and
                not re.match(r'^(Nếu|Khi|Vì|Nhưng|Để|Chúng|Các|Hãy|Đừng|Mẹ|Con|Cha|Bố|Anh|Chị|Em|Tôi|Nó|Họ|Ông|Bà|Thôi|Không|Có|Sẽ|Đã)', candidate)):
                author = candidate
                found_author = True
                continue
        
        if not found_author:
            story_lines.append(l)
    
    story_text = '\n'.join(story_lines).strip()
    story_text = re.sub(r'\n{3,}', '\n\n', story_text)
    
    if len(story_text) > 300:
        stories_raw.append({
            'title': sec['title'],
            'text': story_text,
            'author': author,
            'char_count': len(story_text)
        })

print(f"Extracted {len(stories_raw)} stories with proper titles:\n")
for i, s in enumerate(stories_raw):
    print(f"{i+1}. [{s['title']}] by {s['author']} ({s['char_count']} chars)")

# Classification function
def classify(s):
    """Return (keep: bool, score: int, reason: str)"""
    full = (s['title'] + ' ' + s['text']).lower()
    fp_count = len(re.findall(r'\b(tôi|mình)\b', full))
    
    # Rejection keywords
    rejection_kw = [
        'bài học', 'đạo đức', 'chúng ta nên', 'chúng ta phải',
        'hãy luôn', 'ngụ ngôn', 'triết lý', 'bài giảng',
        'rút ra', 'kết luận', 'thông điệp', 'lời khuyên',
        'bạn hãy', 'bạn nên', 'chân lý', 'sống có đạo đức',
        'quyết định đúng đắn', 'lẽ phải', 'bài học quý',
    ]
    rej_score = sum(len(re.findall(kw, full)) for kw in rejection_kw)
    
    # Check last paragraph for moralizing
    paragraphs = s['text'].split('\n\n')
    last_para = paragraphs[-1][:300] if paragraphs else ''
    moral_end = bool(re.search(r'(bài học|chúng ta|bạn sẽ|hãy\s|phải\s|nên\s|bài học)', last_para.lower()))
    
    # Scoring
    if fp_count >= 10 and rej_score <= 2:
        return True, fp_count + 10, "Strong personal narrative"
    elif fp_count >= 5 and rej_score <= 1:
        return True, fp_count + 5, "Good personal elements"
    elif fp_count >= 3 and rej_score == 0:
        return True, fp_count + 2, "Has personal voice"
    elif rej_score >= 5:
        return False, -rej_score, f"Moralistic (rej={rej_score})"
    elif fp_count == 0 and rej_score >= 2:
        return False, -rej_score, "No personal voice, moralistic"
    elif fp_count == 0 and moral_end:
        return False, -1, "No personal voice, moral ending"
    elif fp_count < 2:
        return False, 0, "Insufficient personal voice"
    
    return True, fp_count, "OK"

print("\n" + "=" * 80)
print("CLASSIFICATION & RANKING:")
print("=" * 80)

ranked = []
for s in stories_raw:
    keep, score, reason = classify(s)
    fp = len(re.findall(r'\b(tôi|mình)\b', (s['title'] + ' ' + s['text']).lower()))
    ranked.append((s, keep, score, reason, fp))
    status = "✓" if keep else "✗"
    print(f"\n{status} [{s['title']}] by {s['author']}")
    print(f"  Chars: {s['char_count']}, fp={fp}, score={score}, reason: {reason}")
    preview = s['text'][:120].replace('\n', ' | ')
    print(f"  Preview: {preview}...")

# Sort by score desc
ranked.sort(key=lambda x: x[2], reverse=True)

# Select top 8 qualifying
top8 = [r for r in ranked if r[1]][:8]

print("\n" + "=" * 80)
print(f"TOP 8 SELECTED STORIES:")
print("=" * 80)
for i, (s, keep, score, reason, fp) in enumerate(top8):
    print(f"\n{i+1}. {s['title']}")
    print(f"   Author: {s['author']}")
    print(f"   Score: {score}, fp={fp}")
    print(f"   Text length: {s['char_count']} chars")

# Save selected stories
selected = [{'title': s['title'], 'text': s['text'], 'author': s['author']} 
            for s, _, _, _, _ in top8]

with open('/tmp/tap10_selected.json', 'w', encoding='utf-8') as f:
    json.dump(selected, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(selected)} stories to /tmp/tap10_selected.json")

# Output for Gemini processing
for i, s in enumerate(selected):
    print(f"\n{'='*60}")
    print(f"STORY {i+1}: {s['title']}")
    print(f"Author: {s['author']}")
    print(f"Text length: {len(s['text'])} chars")
    # Show first 500 chars
    print(f"--- BEGIN ---")
    print(s['text'][:500])
    print(f"--- END (truncated) ---")
