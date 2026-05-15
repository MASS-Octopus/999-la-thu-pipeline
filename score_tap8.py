#!/usr/bin/env python3
"""Complete extraction, scoring, and ranking of Tập 8 stories."""
import re, json, subprocess, sys

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    raw_text = f.read()

# Remove page markers and header/footer cruft
cleaned = raw_text
cleaned = re.sub(r'=== PAGE \d+ ===\n', '\n', cleaned)
cleaned = re.sub(r'\nHạt giống tâm hồn\n', '\n', cleaned)
cleaned = re.sub(r'\nNhững câu chuyện cuộc sống\n', '\n', cleaned)
cleaned = re.sub(r'\nNhững câu chuyện cuộc sông\n', '\n', cleaned)
cleaned = re.sub(r'\n\d+\n', '\n', cleaned)  # standalone page numbers

# Find story boundaries: pattern is "- Name\nTheo Source" or just "- Name\nTheo Source"
# Split by these boundaries
story_ends = list(re.finditer(r'\n- ([A-ZÀ-Ỵ][a-zA-Zà-ỹ]+(?:\s+[A-ZÀ-Ỵ][a-zA-Zà-ỹ]+){0,3})\nTheo (.+?)(?:\n|$)', cleaned))

print(f"Found {len(story_ends)} story endings via regex")

# Extract stories
stories_raw = []
prev_end = 0

# Skip front matter - find first story start after intro
# Intro ends at page 10, story 1 starts around "Câu chuyện về\ncuốn sách và giỏ\nđựng than"
# Find this title
first_story_start = cleaned.find('Câu chuyện về')
if first_story_start < 0:
    first_story_start = 0

prev_end = first_story_start

for m in story_ends:
    author = m.group(1)
    source = m.group(2)
    end_pos = m.start()
    
    story_text = cleaned[prev_end:end_pos]
    
    # Clean up story text
    story_text = re.sub(r'\n{3,}', '\n\n', story_text)
    story_text = story_text.strip()
    
    if len(story_text) > 100:
        # Extract title from first few lines
        lines = story_text.split('\n')
        title_lines = []
        for l in lines[:6]:
            l = l.strip()
            if not l:
                break
            if len(l.split()) <= 12 and not l.startswith('- ') and not l.startswith('"'):
                title_lines.append(l)
            else:
                break
        title = ' '.join(title_lines) if title_lines else 'UNTITLED'
        
        stories_raw.append({
            'title': title,
            'text': story_text,
            'author': author,
            'source': source
        })
    
    prev_end = m.end()

print(f"Extracted {len(stories_raw)} stories")

# Score each story
def score_story(text):
    score = 0
    
    # Check for first person narrative (tôi, mình, tớ, tao, em, con - as narrator)
    first_person_markers = ['tôi ', ' tôi,', ' tôi.', ' tôi!', 'tôi đã', 'tôi không', 'tôi chỉ',
                           'mình ', ' mình,', ' mình.', ' mình!',
                           'của tôi', 'cho tôi', 'với tôi', 'và tôi', 'khi tôi']
    fp_count = sum(text.lower().count(m) for m in first_person_markers)
    if fp_count > 15:
        score += 4
    elif fp_count > 8:
        score += 3
    elif fp_count > 3:
        score += 2
    elif fp_count > 0:
        score += 1
    
    # Check for strong emotion words
    emotion_words = ['khóc', 'nước mắt', 'đau', 'xúc động', 'cảm động', 'nghẹn', 
                    'yêu thương', 'nhớ', 'cô đơn', 'tủi', 'hối hận', 'ân hận',
                    'hạnh phúc', 'vỡ òa', 'tim', 'lòng', 'nỗi', 'buồn', 'sợ',
                    'dũng cảm', 'can đảm', 'hy vọng', 'tuyệt vọng', 'tha thứ']
    em_count = sum(text.lower().count(w) for w in emotion_words)
    if em_count > 20:
        score += 3
    elif em_count > 12:
        score += 2
    elif em_count > 5:
        score += 1
    
    # Check for personal confession / tâm sự markers
    confession_markers = ['tôi đã từng', 'tôi chưa bao giờ', 'tôi nhận ra', 'tôi hiểu ra',
                         'tôi muốn nói', 'tôi thú nhận', 'tôi xin lỗi', 'tôi ân hận',
                         'giá như', 'ước gì', 'nếu có thể']
    conf_count = sum(text.lower().count(m) for m in confession_markers)
    if conf_count > 3:
        score += 2
    elif conf_count > 1:
        score += 1
    
    # Penalize self-help/didactic/ngụ ngôn patterns
    didactic_markers = ['bài học', 'chúng ta nên', 'chúng ta phải', 'bạn nên', 'bạn phải',
                       'hãy luôn', 'đừng bao giờ', 'phải biết', 'cần phải', 'muốn thành công',
                       'ngụ ngôn', 'bài học rút ra', 'từ đó tôi rút ra']
    did_count = sum(text.lower().count(m) for m in didactic_markers)
    score -= did_count * 1
    
    # Penalize third-person ngụ ngôn / fairy tale style
    third_person_story = text.count('có một') + text.count('ngày xưa') + text.count('ngày xửa')
    if third_person_story > 3:
        score -= 2
    
    # Bonus for stories with dialogue (more personal, narrative-driven)
    dialogue_count = text.count('\n- ') + text.count('\n— ') + text.count('\n– ')
    if dialogue_count > 10:
        score += 1
    
    # Bonus for longer, more developed stories (but not too long)
    text_len = len(text)
    if 800 < text_len < 8000:
        score += 2
    elif text_len > 8000:
        score += 0  # too long might be rambling
    
    return score

# Score all stories
for s in stories_raw:
    s['score'] = score_story(s['text'])
    # Count words
    s['word_count'] = len(s['text'].split())

# Sort by score
stories_raw.sort(key=lambda x: x['score'], reverse=True)

print("\n=== RANKED STORIES ===")
for i, s in enumerate(stories_raw):
    print(f"  {i+1}. Score={s['score']:2d} | [{s['title'][:50]}] ({s['word_count']} words) | {s['author']}")

# Select top 8
top8 = stories_raw[:8]
print(f"\n=== TOP 8 SELECTED ===")
for i, s in enumerate(top8):
    print(f"  {i+1}. Score={s['score']:2d} | [{s['title'][:60]}] | {s['author']} | {s['source']}")

# Save for processing
with open('/tmp/tap8_top8.json', 'w') as f:
    json.dump(top8, f, ensure_ascii=False, indent=2)

# Also save all ranked
with open('/tmp/tap8_all_ranked.json', 'w') as f:
    json.dump(stories_raw, f, ensure_ascii=False, indent=2)
