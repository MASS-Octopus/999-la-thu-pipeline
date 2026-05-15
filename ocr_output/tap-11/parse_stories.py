#!/usr/bin/env python3
"""Parse tap-11 OCR and identify stories with heuristic scores."""
import re

with open("/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/full.txt", "r", encoding="utf-8") as f:
    text = f.read()

lines = text.split('\n')

# Find all page markers
page_starts = {}
for i, line in enumerate(lines):
    m = re.match(r'=== PAGE (\d+) ===', line)
    if m:
        page_starts[int(m.group(1))] = i

# Author credits: lines that look like "- Firstname Lastname" or "- Firstname Lastname, ..."
# at end of stories
author_credits = []
for i, line in enumerate(lines):
    line_stripped = line.strip()
    # Match pattern: "- Name Name" (simple author credits)
    m = re.match(r'^- ([A-Z][a-zA-Záéíóú]+(?: [A-Z][a-zA-Záéíóú]+){1,3})(?:,.*)?$', line_stripped)
    if m:
        name = m.group(1)
        # Skip known non-story lines
        if name in ('First News', 'Frank Tyger', 'Henry Fielding', 'Helen Keller', 
                     'William Arthur Ward', 'WillHiam Feather', 'William Penn',
                     'Ralph Waldo Emerson', 'Albert Einstein', 'Robert Frost',
                     'Margaret Thatcher', 'Annie DiHard', 'Sfephen Covey'):
            continue
        author_credits.append((i, name, line_stripped))

# Find section headers (story titles) - lines that are NOT page markers/headers
headers = []
for i, line in enumerate(lines):
    line_stripped = line.strip()
    # Skip page numbers, empty, etc
    if not line_stripped or re.match(r'=== PAGE', line_stripped):
        continue
    if line_stripped in ('Hạt giống tâm hồn', 'Những trải nghiệm cuộc sống'):
        continue
    if re.match(r'^\d+$', line_stripped):
        continue
    if len(line_stripped) < 5:
        continue
    
    # Look for short-ish lines that look like titles (not full sentences)
    words = line_stripped.split()
    if 2 <= len(words) <= 8 and not line_stripped.endswith('.') and not line_stripped.endswith(','):
        # Check if it might be a title
        if not re.match(r'^(Tôi|Một|Khi|Nhưng|Và|Có|Sẽ|Vì|Sau|Trong|Đây|Đến|Rôi|Thế|Còn|Ông|Bà|Bác|Xin|Cậu|Cháu|Được|Là|Tất|Vậy|Tuy|Bây|Năm|Ngoài|Chỉ|Phải|Tên|Tại|Họ|Người|Giờ|Mời|Không|Trước|Thằng|Vợ|Cô|Anh|Chào|Cảm|Các|Chỗ|Quả|Điều|Đôi|Rất|Cho|Mà|Vào|Đã|Công|Chúng|Mày|Đó|Nó|Em|Chính|Mắt|Đứa|Thay|Cái|Với|Lời|Mục|Thế|Còn|Từ)\b', line_stripped):
            headers.append((i, line_stripped))

# Now find stories: header -> author credit (page range)
print("=== AUTHOR CREDITS ===")
for idx, (line_no, name, raw) in enumerate(author_credits):
    # Find nearest preceding page boundary
    page = None
    for p, pline in sorted(page_starts.items()):
        if pline < line_no:
            page = p
    print(f"  [{idx}] Line {line_no} (page ~{page}): {raw}")

print(f"\nTotal author credits found: {len(author_credits)}")

# Print all section headers
print("\n=== POTENTIAL SECTION HEADERS ===")
for line_no, title in headers:
    # Find nearest page
    page = None
    for p, pline in sorted(page_starts.items()):
        if pline < line_no:
            page = p
    print(f"  Line {line_no} (page ~{page}): {title}")
