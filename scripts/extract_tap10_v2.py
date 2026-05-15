#!/usr/bin/env python3
"""Re-extract stories from Tap 10 using author signatures as boundaries."""
import re
import json

OCR_FILE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-10/full.txt"

# Author signatures found in the text (line: author name)
# Stories end with "- Author Name" on its own line
# Between two signatures = one story (or poem/quote)

with open(OCR_FILE, 'r', encoding='utf-8') as f:
    full_text = f.read()

# Find all author signatures: "- Author Name" at end of line
# These mark story boundaries
sig_pattern = re.compile(r'^-\s+([A-Za-zÀ-ỹ\s\.\,\'\(\)]+?)$', re.MULTILINE)
signatures = [(m.start(), m.group(1).strip()) for m in sig_pattern.finditer(full_text)]

print(f"Found {len(signatures)} author signatures:")
for pos, name in signatures:
    # Find line number
    line_num = full_text[:pos].count('\n') + 1
    print(f"  Line {line_num}: '{name}'")

# Now extract stories: each story is text between consecutive signatures
# But also include text from page 11 start to first signature
# Skip pages 1-10 (page 11 starts after "=== PAGE 11 ===")

page11_match = re.search(r'=== PAGE 11 ===', full_text)
if page11_match:
    story_start_pos = page11_match.end()
else:
    story_start_pos = 0

stories = []
prev_pos = story_start_pos

# Find the actual first story title (it appears before the first signature)
# Look at text before first sig to find the title

for i, (sig_pos, sig_name) in enumerate(signatures):
    # Skip signatures that appear before page 11
    line_num = full_text[:sig_pos].count('\n') + 1
    if line_num < 230:  # page 11 is around line 229
        continue
    
    story_text = full_text[prev_pos:sig_pos].strip()
    
    # Skip if too short (less than 50 chars = likely a poem/quote fragment)
    if len(story_text) < 50:
        prev_pos = sig_pos + len(f"- {sig_name}\n")
        continue
    
    # Clean up: remove page markers
    story_text = re.sub(r'=== PAGE \d+ ===', '', story_text)
    story_text = re.sub(r'Hạt giống tâm hồn', '', story_text)
    story_text = re.sub(r'Theo dòng thời gian', '', story_text)
    
    # Remove standalone page numbers
    story_text = re.sub(r'\n\d+\n', '\n', story_text)
    
    # Collapse whitespace
    story_text = re.sub(r'\n{3,}', '\n\n', story_text)
    story_text = story_text.strip()
    
    # Try to find the story title (first non-empty, non-number line)
    lines = [l.strip() for l in story_text.split('\n') if l.strip()]
    title = ""
    text_body_lines = []
    
    # The title is usually the first meaningful line
    for l in lines:
        if not title and len(l) > 3 and not re.match(r'^\d+$', l) and not l.startswith('-'):
            title = l
        else:
            text_body_lines.append(l)
    
    # If no title found, use first line
    if not title and lines:
        title = lines[0]
        text_body_lines = lines[1:]
    
    story_body = '\n'.join(text_body_lines).strip()
    
    if len(story_body) > 100:  # Real stories have substantial text
        stories.append({
            'title': title,
            'text': story_body,
            'author': sig_name,
            'char_count': len(story_body)
        })
    
    prev_pos = sig_pos + len(f"- {sig_name}\n")

print(f"\nExtracted {len(stories)} substantial stories")

# Now classify each story
def classify_story(s):
    full = s['title'] + ' ' + s['text']
    
    # Count first-person
    fp = len(re.findall(r'\b(tôi|mình)\b', full.lower()))
    
    # Rejection markers
    rejection = [
        r'bài học', r'đạo đức', r'chúng ta nên', r'chúng ta phải',
        r'hãy luôn', r'ngụ ngôn', r'triết lý', r'bài giảng',
        r'rút ra', r'kết luận', r'thông điệp', r'lời khuyên',
        r'bạn hãy', r'bạn nên', r'đừng bao giờ', r'chân lý',
        r'chúng ta cần', r'chúng ta hãy', r'sống có đạo đức',
        r'quyết định đúng đắn', r'lẽ phải', r'bài học quý',
    ]
    
    rej_score = sum(len(re.findall(p, full.lower())) for p in rejection)
    
    if fp >= 3 and rej_score <= 3:
        return True, fp, rej_score
    elif fp >= 1 and rej_score <= 1:
        return True, fp, rej_score
    elif rej_score >= 5:
        return False, fp, rej_score
    elif fp == 0 and rej_score >= 2:
        return False, fp, rej_score
    
    return fp > 0, fp, rej_score

print("\n" + "=" * 80)
print("CLASSIFICATION:")
print("=" * 80)

qualifying = []
rejected = []

for i, s in enumerate(stories):
    keep, fp, rej = classify_story(s)
    status = "✓ KEEP" if keep else "✗ REJECT"
    print(f"\n{i+1}. [{status}] [{s['title']}] by {s['author']}")
    print(f"   Chars: {s['char_count']}, fp={fp}, rej={rej}")
    preview = s['text'][:150].replace('\n', ' | ')
    print(f"   Preview: {preview}...")
    
    if keep:
        qualifying.append(s)
    else:
        rejected.append(s)

print(f"\n{'='*80}")
print(f"QUALIFYING: {len(qualifying)} | REJECTED: {len(rejected)}")

# Save qualifying
with open('/tmp/tap10_qualifying.json', 'w', encoding='utf-8') as f:
    json.dump(qualifying, f, ensure_ascii=False, indent=2)

print("Saved to /tmp/tap10_qualifying.json")
