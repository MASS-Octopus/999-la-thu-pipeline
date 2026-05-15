#!/usr/bin/env python3
"""Parse Hạt Giống Tâm Hồn Tập 8 - extract stories with boundaries."""
import re

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

# Find all PAGE markers
page_boundaries = []
for i, line in enumerate(lines):
    m = re.match(r'=== PAGE (\d+) ===', line)
    if m:
        page_boundaries.append((i, int(m.group(1))))

print(f"Total pages: {len(page_boundaries)}")
print(f"Page boundaries (line_idx, page_num):")
for p in page_boundaries[:15]:
    print(f"  line={p[0]}, page={p[1]}")
print("...")
for p in page_boundaries[-5:]:
    print(f"  line={p[0]}, page={p[1]}")

# Pages 1-10 are front matter (title, copyright, intro), stories start at page 11
# Find title-like lines (all-caps or capitalized multi-word phrases that aren't dialogue)
# Look for lines that are "cleaned text" short lines between page markers that could be titles

# First, let's look at content around pages 11-30 to understand structure
for start_idx, pg in page_boundaries:
    if 11 <= pg <= 30:
        end_idx = page_boundaries[page_boundaries.index((start_idx, pg)) + 1][0] if page_boundaries.index((start_idx, pg)) + 1 < len(page_boundaries) else len(lines)
        print(f"\n--- PAGE {pg} (lines {start_idx}-{end_idx-1}) ---")
        for i in range(start_idx, min(start_idx+12, end_idx)):
            stripped = lines[i].strip()
            if stripped and not re.match(r'=== PAGE', stripped):
                print(f"  {i}: {stripped}")
