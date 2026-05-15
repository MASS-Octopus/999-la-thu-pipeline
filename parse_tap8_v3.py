#!/usr/bin/env python3
"""Extract stories from Tập 8 with proper boundary detection."""
import re, json

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

# Clean lines: remove page markers, header/footer artifacts
def clean_line(line):
    s = line.strip()
    if re.match(r'=== PAGE \d+ ===', s):
        return None
    if re.match(r'^\d+$', s):  # standalone page numbers
        return None
    # Remove "Hạt giống tâm hồn" and "Những câu chuyện cuộc sống" headers
    if s in ('Hạt giống tâm hồn', 'hạtglống', 'hạtøfG', 'ạtplống', 
             'Những câu chuyện cuộc sống', 'Những câu chuyện', 'Những câu chuyện cuộc sông'):
        return None
    # Remove garbled OCR artifacts
    if re.match(r'^[`\'\"\^~°®Œ\.\,\;\:\!\?\(\)\[\]\{\}…\-\–\—\\\/\|\@\#\$\%\&\*\+\=<>_]+$', s):
        return None
    if s in ('Sñ', 'First News tổng hợp và thực hiện Œ®)', 'H', 'l4 ` d se K^ ` h ~', 
             'y diệu tử những', 'đ -À . đi', 'lêu giản di...', '“ z ` e«. 2',
             '` 2 _.\\ °', '`', '® ^A *. + <<', 'C', 'Tà'):
        return None
    return s

# Build clean lines array
clean_lines = []
for i, line in enumerate(lines):
    cl = clean_line(line)
    clean_lines.append(cl)

# Find story endings: pattern "- Name" followed by "Theo ..." (within a few lines)
# These mark story boundaries. Also single "- Name" that's not an epigraph.
story_endings = []
i = 0
while i < len(clean_lines):
    cl = clean_lines[i]
    if cl and re.match(r'^- [A-ZÀ-Ỵ][a-zà-ỹ]+(\s+[A-ZÀ-Ỵ][a-zà-ỹ]+){0,3}$', cl):
        # Check if next non-empty line is "Theo ..."
        j = i + 1
        while j < len(clean_lines) and clean_lines[j] is not None and clean_lines[j] == '':
            j += 1
        if j < len(clean_lines) and clean_lines[j] and re.match(r'^Theo\s', clean_lines[j]):
            # This is a story ending: "- Author\n Theo Source"
            # Check it's not an epigraph (epigraphs are at story START, have quote before them)
            # Epigraphs: short quote + "- Famous Person", story hasn't started yet
            # Story endings: story text + "- Translator" + "Theo Original"
            # Heuristic: if the line is followed by empty line and then new title/story, it's ending
            story_endings.append((i, cl, clean_lines[j]))
            i = j + 1
            continue
        else:
            # Single "- Name" line - could be epigraph or ending
            # Check context: if followed by story text (not title), it's likely an epigraph
            # For now, mark as potential ending
            pass
    i += 1

# Also check for epigraphs: quote + "- Author" (no "Theo" following)
epigraphs = []
i = 0
while i < len(clean_lines):
    cl = clean_lines[i]
    # Epigraph: multi-line quote ending with "- Famous Person" (no Theo after)
    if cl and re.match(r'^- [A-ZÀ-Ỵ][a-zà-ỹ]+(\s+[A-ZÀ-Ỵ][a-zà-ỹ]+){0,4}$', cl):
        j = i + 1
        while j < len(clean_lines) and clean_lines[j] is not None and clean_lines[j] == '':
            j += 1
        # If next non-empty is NOT "Theo ...", and previous lines look like a quote
        is_theo = j < len(clean_lines) and clean_lines[j] and re.match(r'^Theo\s', clean_lines[j])
        if not is_theo and i > 0:
            # Check if there's quote text above
            prev_lines = []
            k = i - 1
            while k >= 0 and clean_lines[k] is not None and k > i - 6:
                if clean_lines[k]:
                    prev_lines.append(clean_lines[k])
                k -= 1
            if prev_lines:
                epigraphs.append((i, cl))
    i += 1

print(f"Story endings found: {len(story_endings)}")
for idx, (line_idx, author, source) in enumerate(story_endings):
    print(f"  Story {idx+1}: Line {line_idx+1} | {author} | {source}")

print(f"\nEpigraphs found: {len(epigraphs)}")
for line_idx, text in epigraphs:
    print(f"  Line {line_idx+1}: {text}")

# Save endings for further processing
with open('/tmp/tap8_endings.json', 'w') as f:
    json.dump([{'line_idx': le[0], 'author': le[1], 'source': le[2]} for le in story_endings], f, ensure_ascii=False)
