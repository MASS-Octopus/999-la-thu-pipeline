#!/usr/bin/env python3
"""Extract clean text for each top story to individual files."""
import re

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

def clean_line(line):
    s = line.strip()
    if re.match(r'=== PAGE \d+ ===', s): return None
    if re.match(r'^\d+$', s): return None
    if s in ('Hạt giống tâm hồn', 'hạtglống', 'hạtøfG', 'ạtplống', 'tâm hồn.',
             'Những câu chuyện cuộc sống', 'Những câu chuyện', 'Những câu chuyện cuộc sông'): 
        return None
    if re.match(r'^[`\'\"\^~°®Œ\`\#\.\,\;\:\!\?\(\)\[\]\{\}…\-\–\—\\\/\|\@\$\€\%\&\*\+\=<>_ \t\n\r]+$', s) and len(s) < 40: 
        return None
    if re.match(r'^[lL]?\d+[\s`dseK\^h~]+$', s): return None
    if s in ('`', 'H', 'C', 'Tà'): return None
    return s

def extract_text(start_line, end_line):
    result = []
    for i in range(start_line - 1, min(end_line, len(lines))):
        cl = clean_line(lines[i])
        if cl is None:
            continue
        if re.match(r'^- [A-ZÀ-Ỵ][a-zA-Zà-ỹ\s]+$', cl):
            continue
        if re.match(r'^Theo\s', cl):
            continue
        result.append(cl)
    text = '\n'.join(result)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix OCR
    text = text.replace('TL.', 'Tôi')
    text = text.replace('A«', 'Annie')
    text = text.replace('N. ', 'Nhân ')
    text = text.replace('M. ', 'Mary ')
    text = text.replace('C, ', 'Con gái, ')
    text = text.replace('Nx ', 'Như ')
    text = text.replace('Tà ', 'Tại ')
    text = text.replace('Ciạ ', 'Chợt ')
    text = text.replace('M... ', 'Mary ')
    return text.strip()

top8 = [
    {'title': 'Hàn gắn một trái tim vỡ', 'start': 672, 'end': 822},
    {'title': 'Thiên thần can đảm', 'start': 2332, 'end': 2530},
    {'title': 'Quà của Annie', 'start': 264, 'end': 489},
    {'title': 'Tuyên ngôn của Cái Tôi', 'start': 835, 'end': 912},
    {'title': 'Vượt lên chính mình', 'start': 1208, 'end': 1434},
    {'title': 'Đôi mắt của mẹ', 'start': 2124, 'end': 2311},
    {'title': 'Thiếu nữ cài hoa', 'start': 1546, 'end': 1754},
    {'title': 'Sinh ra từ trái tim', 'start': 2605, 'end': 2892},
]

import os
out_dir = '/tmp/tap8_stories'
os.makedirs(out_dir, exist_ok=True)

for i, s in enumerate(top8):
    text = extract_text(s['start'], s['end'])
    filename = f"{out_dir}/story_{i+1:02d}.txt"
    with open(filename, 'w') as f:
        f.write(text)
    print(f"Story {i+1}: {s['title']} -> {len(text)} chars ({len(text.split())} words) -> {filename}")
