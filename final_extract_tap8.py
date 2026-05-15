#!/usr/bin/env python3
"""Final extraction: get clean text for top 8 stories with proper titles."""
import re, json

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

def clean_line(line):
    s = line.strip()
    if re.match(r'=== PAGE \d+ ===', s): return None
    if re.match(r'^\d+$', s): return None
    if s in ('Hạt giống tâm hồn', 'hạtglống', 'hạtøfG', 'ạtplống', 'tâm hồn.',
             'Những câu chuyện cuộc sống', 'Những câu chuyện', 'Những câu chuyện cuộc sông',
             'Những câu chuyện cuộc sống'): return None
    # Skip garbled title lines with special chars only
    if re.match(r'^[`\'\"\^~°®Œ\`\#\.\,\;\:\!\?\(\)\[\]\{\}…\-\–\—\\\/\|\@\$\€\%\&\*\+\=<>_ \t\n\r]+$', s) and len(s) < 40: 
        return None
    if re.match(r'^[lL]?\d+[\s`dseK\^h~]+$', s): return None
    # Skip single special chars
    if s in ('`', 'H', 'C', 'Tà', 'Sñ', 'First News tổng hợp và thực hiện Œ®)'): return None
    return s

def extract_clean_text(start_line, end_line, skip_epigraph=True):
    """Extract clean text between line numbers (1-indexed)."""
    result = []
    in_epigraph = skip_epigraph
    epigraph_ended = False
    
    for i in range(start_line - 1, min(end_line, len(lines))):
        cl = clean_line(lines[i])
        if cl is None:
            continue
        
        # Skip epigraph region (quote + "- Famous Person")
        if in_epigraph and not epigraph_ended:
            if cl.startswith('- ') and any(
                re.match(r'^- [A-Z].+', cl) for _ in [1]
            ):
                # Check if next lines are story text
                # This is the end of epigraph
                epigraph_ended = True
                continue
            # Skip quote lines in epigraph
            if '"' in cl or '"' in cl or "'" in cl or len(cl.split()) <= 25:
                continue
            epigraph_ended = True
        
        if cl.startswith('- ') and re.match(r'^- [A-ZÀ-Ỵ][a-zA-Zà-ỹ]+(\s+[A-ZÀ-Ỵ][a-zA-Zà-ỹ]+){0,3}$', cl):
            continue  # skip author line
        if re.match(r'^Theo\s', cl):
            continue  # skip source line
        
        result.append(cl)
    
    return '\n'.join(result)

# Define top 8 stories with their line ranges and proper titles
top8_stories = [
    {
        'title': 'Hàn gắn một trái tim vỡ',
        'author': 'Thanh Phương',
        'source': 'Love Is Just Like A Broken Arm',
        'start_line': 665,  # PAGE 27
        'end_line': 824,    # ends at line 823-824
        'score': 8
    },
    {
        'title': 'Thiên thần can đảm',
        'author': 'Thanh Phương',
        'source': 'Angle Of Courage',
        'start_line': 2323,  # PAGE 83
        'end_line': 2532,   # ends at line 2531-2532
        'score': 8
    },
    {
        'title': 'Quà của Annie',
        'author': 'Thanh Phương',
        'source': 'Goodwill',
        'start_line': 258,  # PAGE 14 (after epigraph)
        'end_line': 491,    # ends at line 490-491
        'score': 7
    },
    {
        'title': 'Tuyên ngôn của Cái Tôi',
        'author': 'Nguyễn Đoàn',
        'source': 'My Declaration Of Self-Esteem',
        'start_line': 828,  # PAGE 32
        'end_line': 914,    # ends at line 913-914
        'score': 7
    },
    {
        'title': 'Vượt lên chính mình',
        'author': 'Lê Lai',
        'source': 'Internet',
        'start_line': 1197,  # PAGE 44
        'end_line': 1436,    # ends at line 1435-1436
        'score': 7
    },
    {
        'title': 'Đôi mắt của mẹ',
        'author': 'Nguyễn Ngân',
        'source': 'My Own Experience',
        'start_line': 2119,  # PAGE 76
        'end_line': 2313,    # ends at line 2312-2313
        'score': 7
    },
    {
        'title': 'Thiếu nữ cài hoa',
        'author': 'Thành Nhân',
        'source': 'Flower In Her Hair',
        'start_line': 1546,  # After "Đừng thay đổi thế giới" ends at 1544-1545
        'end_line': 1756,    # ends at line 1755-1756
        'score': 6
    },
    {
        'title': 'Sinh ra từ trái tim',
        'author': 'Thanh Phương',
        'source': 'From The Heart',
        'start_line': 2599,  # PAGE 92
        'end_line': 2894,    # ends at line 2893-2894
        'score': 6
    }
]

# Extract clean texts
results = []
for s in top8_stories:
    text = extract_clean_text(s['start_line'], s['end_line'])
    s['text'] = text
    s['char_count'] = len(text)
    s['word_count'] = len(text.split())
    print(f"\n=== {s['title']} ===")
    print(f"  Author: {s['author']} | Source: {s['source']} | Score: {s['score']}")
    print(f"  Chars: {s['char_count']} | Words: {s['word_count']}")
    print(f"  Lines: {s['start_line']}-{s['end_line']}")
    print(f"  First 100 chars: {text[:100]}...")
    print(f"  Last 100 chars: ...{text[-100:]}")

# Save for Gemini processing
with open('/tmp/tap8_top8_texts.json', 'w') as f:
    json.dump([{k: v for k, v in s.items()} for s in top8_stories], f, ensure_ascii=False, indent=2)

print("\n\n=== READY FOR GEMINI PROCESSING ===")
print(f"Total stories ready: {len(top8_stories)}")
