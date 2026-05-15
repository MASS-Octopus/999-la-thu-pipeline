#!/usr/bin/env python3
"""Extract and classify stories from Tap 10 OCR output."""
import re
import json
import sys

OCR_FILE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-10/full.txt"

def parse_ocr(filepath, start_page=11):
    """Parse OCR file, return list of (title, story_text, author) tuples."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    for i, line in enumerate(lines, 1):
        entries.append((i, line.rstrip('\n')))
    
    stories = []
    current_story_lines = []
    current_title = ""
    in_story = False
    story_start_line = 0
    current_page = 1
    in_start_pages = True
    skip_count = 0
    
    for line_num, line in entries:
        # Track page
        m = re.match(r'^=== PAGE (\d+) ===$', line)
        if m:
            current_page = int(m.group(1))
            if current_page >= start_page:
                in_start_pages = False
            continue
        
        if in_start_pages:
            continue
        
        # Skip page numbers (standalone numbers)
        if re.match(r'^\d+$', line.strip()):
            continue
        # Skip section headers
        if re.match(r'^(Hạt giống tâm hồn|Theo dòng thời gian)$', line.strip(), re.IGNORECASE):
            # "Theo dòng thời gian" might indicate a new sub-section/title following
            continue
        
        # Detect author signature line: "- Author Name" (signals end of story)
        author_match = re.match(r'^-\s+([A-Za-zÀ-ỹ\s\.\,\']+?)$', line.strip())
        
        if author_match and in_story and len(current_story_lines) > 3:
            author = author_match.group(1).strip()
            story_text = '\n'.join(current_story_lines).strip()
            
            # Also collect the title from the first meaningful line
            # The title is often near the beginning of the story
            # Let's look back to find the title
            found_title = ""
            for tline in current_story_lines:
                tline = tline.strip()
                if tline and len(tline) > 3 and len(tline) < 80:
                    # Title should be a proper noun phrase
                    if not tline.startswith('-') and not re.match(r'^["""]', tline):
                        found_title = tline
                        # Remove title from story text
                        story_lines_filtered = [l for l in current_story_lines if l.strip() != found_title]
                        story_text = '\n'.join(story_lines_filtered).strip()
                        break
            
            stories.append({
                'title': found_title or current_title,
                'text': story_text,
                'author': author,
                'start_line': story_start_line,
                'end_line': line_num
            })
            current_story_lines = []
            current_title = ""
            in_story = False
            continue
        
        if not in_story:
            stripped = line.strip()
            if stripped and len(stripped) > 3 and not stripped.startswith('-'):
                # Check if it looks like a title (proper capitalization)
                # Skip quote lines
                if re.match(r'^["""]', stripped):
                    continue
                # Skip lines that are clearly dialogue or continuation
                if re.match(r'^\d', stripped) and len(stripped) < 5:
                    continue
                # Skip epigraphs / quote attributions
                if re.match(r'^[\(\[]\d+[\)\]]', stripped):
                    continue
                current_title = stripped
                current_story_lines = []
                in_story = True
                story_start_line = line_num
        else:
            if line.strip():
                current_story_lines.append(line.strip())
    
    # Remove stories where title = first line of text (duplicate)
    clean_stories = []
    for s in stories:
        if s['title'] and s['text'].startswith(s['title']):
            s['text'] = s['text'][len(s['title']):].strip()
        clean_stories.append(s)
    
    return clean_stories


def classify_story(story):
    """Return True if story has personal emotional elements."""
    text = story['text']
    title = story.get('title', '')
    full = title + ' ' + text
    
    # Count first-person pronouns
    first_person_count = len(re.findall(r'\b(tôi|mình|em|tớ|tao)\b', full.lower()))
    
    # Check for rejection markers (ngụ ngôn/triết lý/self-help)
    rejection_patterns = [
        r'bài học', r'đạo đức', r'luôn nhớ', r'chúng ta nên',
        r'phải biết', r'hãy luôn', r'người ta nói', r'cổ tích',
        r'ngụ ngôn', r'bài giảng', r'triết lý', r'suy ngẫm',
        r'chiêm nghiệm', r'rút ra', r'kết luận',
        r'thông điệp', r'ý nghĩa', r'lời khuyên',
        r'câu chuyện này', r'qua câu chuyện', r'từ đó',
        r'bạn hãy', r'bạn nên', r'đừng bao giờ',
        r'chân lý', r'sự thật là', r'điều quan trọng',
        r'mỗi người', r'tất cả chúng ta',
        r'cuộc sống là', r'cuộc đời là',
        r'chúng ta phải', r'chúng ta cần', r'chúng ta hãy',
        r'học được', r'bài học quý', r'lẽ phải',
        r'sống có đạo đức', r'quyết định đúng đắn',
    ]
    
    rejection_score = 0
    for pat in rejection_patterns:
        rejection_score += len(re.findall(pat, full.lower()))
    
    # Check for moral/call-to-action ending
    last_200 = full[-200:].lower() if len(full) > 200 else full.lower()
    moral_ending = bool(re.search(r'(bài học|chúng ta|bạn sẽ|bạn có thể|hãy|phải|nên|đừng)', last_200))
    
    # Decision logic
    if first_person_count >= 3 and rejection_score <= 3:
        return True
    elif first_person_count >= 1 and rejection_score <= 1:
        return True
    elif rejection_score >= 6:
        return False
    elif first_person_count == 0 and rejection_score >= 2:
        return False
    elif first_person_count == 0 and len(text) < 500 and moral_ending:
        return False
    
    return first_person_count > 0


def main():
    stories = parse_ocr(OCR_FILE, start_page=11)
    
    print(f"Total stories found: {len(stories)}")
    print("=" * 80)
    
    qualifying = []
    rejected = []
    
    for i, s in enumerate(stories):
        qualifies = classify_story(s)
        lines_count = len(s['text'].split('\n'))
        text_len = len(s['text'])
        first_person = len(re.findall(r'\b(tôi|mình)\b', (s.get('title','')+' '+s['text']).lower()))
        
        status = "KEEP" if qualifies else "REJECT"
        
        print(f"\n--- Story #{i+1} [{status}] ---")
        print(f"  Title: {s['title']}")
        print(f"  Author: {s['author']}")
        print(f"  Lines: {lines_count}, Chars: {text_len}")
        print(f"  First-person count: {first_person}")
        print(f"  Line range: {s['start_line']}-{s['end_line']}")
        
        preview = s['text'][:200].replace('\n', ' | ')
        print(f"  Preview: {preview}...")
        
        if qualifies:
            qualifying.append(s)
        else:
            rejected.append(s)
    
    print("\n" + "=" * 80)
    print(f"\nQUALIFYING: {len(qualifying)} stories")
    print(f"REJECTED: {len(rejected)} stories")
    
    print("\n--- QUALIFYING STORIES ---")
    for i, s in enumerate(qualifying):
        lines_count = len(s['text'].split('\n'))
        fp = len(re.findall(r'\b(tôi|mình)\b', (s.get('title','')+' '+s['text']).lower()))
        print(f"  {i+1}. [{s['title']}] by {s['author']} ({lines_count} lines, fp={fp})")
    
    print("\n--- REJECTED STORIES ---")
    for i, s in enumerate(rejected):
        lines_count = len(s['text'].split('\n'))
        fp = len(re.findall(r'\b(tôi|mình)\b', (s.get('title','')+' '+s['text']).lower()))
        print(f"  {i+1}. [{s['title']}] by {s['author']} ({lines_count} lines, fp={fp})")
    
    with open('/tmp/tap10_all.json', 'w', encoding='utf-8') as f:
        json.dump({'qualifying': qualifying, 'rejected': rejected}, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved all stories to /tmp/tap10_all.json")


if __name__ == '__main__':
    main()
