#!/usr/bin/env python3
import re

with open('ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

page10_idx = next(i for i, l in enumerate(lines) 
                  if re.match(r'=== PAGE 10 ===', l.strip()))

KNOWN_AUTHORS = [
    'Lê Lai', 'Thanh Phương', 'Thanh Giang', 'Hồng Nhung',
    'Claude McDonald', 'Nguyễn Đoàn', 'Barbara Weidner',
    'Nguyên Thảo', 'Abraham Lincoln', 'Bích Thủy',
    'Thành Nhân', 'Lan Nguyên', 'Nguyễn Ngân',
    'Mai Quốc Thế', 'Lord Byron', 'Quỳnh Nga',
    'Jean Tharaud', 'Thanh Thủy', 'Thu Quỳnh',
    'Thanh Thảo', 'William Penn', 'Albert Einstein', 'Karl Marx'
]

author_positions = []
for i in range(page10_idx, len(lines)):
    line = lines[i].strip()
    if line.startswith('- '):
        name = line[2:].strip()
        for author in KNOWN_AUTHORS:
            if name == author or name.startswith(author + ' '):
                author_positions.append((i, author))
                break

print(f'Found {len(author_positions)} stories')
for idx, (pos, author) in enumerate(author_positions):
    start_pos = page10_idx + 1 if idx == 0 else author_positions[idx-1][0] + 1
    title_candidates = []
    for j in range(start_pos, min(start_pos+30, len(lines))):
        s = lines[j].strip()
        if (s and not s.startswith('===') and not s.startswith('Hạt giống')
            and 'Những câu chuyện' not in s
            and not s.startswith('-') and not s.startswith('"')
            and not re.match(r'\d+$', s) and len(s) > 3
            and not re.match(r'[\`\^\*#\+\(\)~@°\|]+', s)):
            garbled_ratio = sum(1 for c in s if c in '^®©™†‡§¶◊¥€£$¢@#~`\\°') / max(len(s),1)
            if garbled_ratio < 0.3:
                title_candidates.append(s)
    title = title_candidates[0][:60] if title_candidates else '???'
    
    raw_text = ''.join(lines[start_pos:pos])
    fp_count = len(re.findall(r'\b(tôi|mình)\b', raw_text.lower()))
    print(f'{idx:2d}: [{author:20s}] "{title}" (1st={fp_count}, chars={len(raw_text)})')
