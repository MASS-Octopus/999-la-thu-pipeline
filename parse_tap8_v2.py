#!/usr/bin/env python3
"""Extract all story boundaries from Tập 8."""
import re

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

# Find all PAGE markers
page_boundaries = []
for i, line in enumerate(lines):
    m = re.match(r'=== PAGE (\d+) ===', line)
    if m:
        page_boundaries.append((i, int(m.group(1))))

# Find potential story endings: lines that are just author credits
# Pattern: "- Name" (short line, Vietnamese name) or "Theo ..."
# These appear near the END of stories
author_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        continue
    # Author credit pattern: "- Name" where Name is 2-4 words, Vietnamese or Western
    # Or "Theo ..." 
    # Or just a name by itself (no dash) that's the last line before next story
    
    # Lines that are ONLY an author name (short, preceded by story text)
    if re.match(r'^- [A-ZÀ-Ỵ][a-zà-ỹ]+(\s+[A-ZÀ-Ỵ][a-zà-ỹ]+){0,3}$', stripped):
        # But exclude dialogue lines (check if previous lines have dialogue context)
        author_lines.append((i, stripped, 'author'))
    elif re.match(r'^Theo\s', stripped) and len(stripped) < 60:
        author_lines.append((i, stripped, 'source'))
    elif re.match(r'^- [A-Za-zÀ-Ỵ][a-zà-ỹ]+$', stripped) and i > 200:
        # Single name, could be author or dialogue
        # Check if it's isolated (surrounded by blank lines or page markers)
        prev_empty = i > 0 and not lines[i-1].strip()
        next_empty = i < len(lines)-1 and not lines[i+1].strip()
        if prev_empty or next_empty:
            author_lines.append((i, stripped, 'author'))

print("Found potential author/source lines:")
for ln, txt, typ in author_lines:
    print(f"  Line {ln+1}: [{typ}] {txt}")

print(f"\nTotal potential endings: {len(author_lines)}")
