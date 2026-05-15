#!/usr/bin/env python3
"""Parse tap-11 OCR, extract stories, score them, output candidates."""
import re, json

PATH = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/full.txt"
with open(PATH, "r") as f:
    lines = f.readlines()

# Author credits - end of stories
# Pattern: "^- Name Name" alone, or "^- Name Name, Suffix"
author_credits = []
for i, line in enumerate(lines):
    s = line.strip()
    # Must start with "- " and look like a name
    m = re.match(r'^- ([A-Z][a-zA-Záéíóúñ\.]+(?: [A-Z][a-zA-Záéíóúñ\.]+){1,3})(?:,.*)?$', s)
    if m:
        name = m.group(1)
        # Skip known non-story entries
        skip = {
            "First News", "Frank Tyger", "Henry Fielding", "Helen Keller",
            "William Arthur Ward", "WillHiam Feather", "William Penn",
            "Ralph Waldo Emerson", "Albert Einstein", "Robert Frost",
            "Margaret Thatcher", "Annie DiHard", "Sfephen Covey",
            "HẠT GIÓNG TÂM HÒN"
        }
        if name in skip or name.startswith("HẠT"):
            continue
        author_credits.append((i, name, s))

# Now match stories: find story start -> author credit
# Story starts are identified by section headers like:
# "Bài học trong giây lát", "Thông điệp từ vườn cây thích", etc.
# or by the first substantial paragraph after a page with "Những trải nghiệm cuộc sống"

# Define story boundaries manually based on reading the text structure
stories = []

# Story 1: Bài học trong giây lát (page 9-18) -> Michael J. Collins
# Story 2: Thông điệp từ vườn cây thích (page 19-26) -> Edward Ziegler
# Story 3: Đối thủ đáng gờm (page 27-40) -> Derek Burneft (Kyle Maynard story)
# Story 4: Liệu pháp tiếng cười (page 41-48) -> Robert Schimmel
# Story 5: ... (page 49-?) -> Rosalynn Carter
# Story 6: ... (page ?-?) -> Vijaya Lakshimmi Pandit (Gandhi story)
# Story 7: ... (page ?-?) -> Albert P. Hout (Will Rogers)
# Story 8: ... (page ?-?) -> Christopher Carrier (Hugh story)
# Story 9: ... (page ?-?) -> Anh Landers
# Story 10: ... (page ?-?) -> David Berreby (Amy Tan)
# Story 11: ... (page ?-?) -> Arthur Gordon
# Story 12: ... (page ?-?) -> Judah Folkman
# Story 13: ... (page ?-?) -> Fran Lostys
# Story 14: ... (page ?-?) -> Gary Sledge
# Story 15: ... (page ?-?) -> Jamice Leqry
# Story 16: ... (page ?-?) -> Errna Bombeck
# Story 17: ... (page ?-?) -> Jack Benny
# Story 18: ... (page ?-?) -> BonHie Friedman
# Story 19: ... (page ?-?) -> Sarah Mahoney
# Story 20: ... (page ?-?) -> George Kenf
# Story 21: ... (page ?-?) -> Terry Paulson

# Let me map author credits to page ranges more carefully
# Using the OCR text, the structure typically is:
# - Section header on a "Những trải nghiệm cuộc sống" page  
# - Content follows
# - Author credit at end

# Let me scan for section title patterns and match to nearest following author credit
section_headers = []
for i, line in enumerate(lines):
    s = line.strip()
    # Skip page markers, page numbers
    if not s or re.match(r'=== PAGE|^\d+$|^Hạt giống|^Những trải nghiệm', s):
        continue
    # Look for short all-caps or title-case lines that might be section titles
    # Usually 2-6 words, not a full sentence
    words = s.split()
    if len(words) < 2 or len(words) > 8:
        continue
    if s.endswith('.') or s.endswith('?'):
        continue
    # Skip if it starts with common sentence words
    common_starts = {'Tôi','Một','Khi','Nhưng','Và','Có','Sẽ','Vì','Sau','Trong',
                     'Đây','Đến','Rôi','Thế','Còn','Ông','Bà','Bác','Xin','Cậu',
                     'Cháu','Được','Là','Tất','Vậy','Tuy','Bây','Năm','Ngoài','Chỉ',
                     'Phải','Tên','Tại','Họ','Người','Giờ','Mời','Không','Trước',
                     'Thằng','Vợ','Cô','Anh','Chào','Cảm','Các','Chỗ','Quả','Rất',
                     'Cho','Mà','Vào','Đã','Công','Chúng','Đó','Nó','Em','Chính',
                     'Mắt','Đứa','Thay','Cái','Với','Lời','Mục','Từ','Dù','Cả','Điều'}
    if words[0] in common_starts:
        continue
    # Skip lines that clearly look like sentences or have OCR artifacts
    if any(c in s for c in ['\\', '/', '{', '^', '~']):
        continue
    if any(ch.isdigit() for ch in s):
        continue
    # Also skip lines with Vietnamese tone marks that look like garbled OCR
    section_headers.append((i, s))

# Find story ranges by matching headers to author credits
# Sort author credits by line number
author_credits.sort(key=lambda x: x[0])

print("=== SECTION HEADERS near story starts ===")
for h_line, title in section_headers:
    # Find nearest following author credit
    following_auth = None
    for a_line, name, raw in author_credits:
        if a_line > h_line:
            following_auth = (a_line, name)
            break
    if following_auth:
        gap = following_auth[0] - h_line
        if gap < 800:  # reasonable story length
            print(f"  Line {h_line}: '{title}' -> author: {following_auth[1]} (gap={gap} lines)")

# Now extract each story text between its header and author credit
print("\n\n=== STORY EXTRACTION ===")
story_data = []
for h_line, title in section_headers:
    # Find nearest following author credit
    best_auth = None
    best_gap = 99999
    for a_line, name, raw in author_credits:
        if a_line > h_line:
            gap = a_line - h_line
            if gap < best_gap and gap < 600:
                best_gap = gap
                best_auth = (a_line, name)
    
    if best_auth:
        # But also check there isn't another header between
        other_header_between = False
        for h2_line, _ in section_headers:
            if h2_line > h_line and h2_line < best_auth[0]:
                other_header_between = True
                break
        
        if not other_header_between:
            story_text = "".join(lines[h_line:best_auth[0]])
            story_data.append({
                "title": title,
                "author": best_auth[1],
                "start_line": h_line,
                "end_line": best_auth[0],
                "text": story_text,
                "length_chars": len(story_text)
            })

print(f"Found {len(story_data)} stories")

# Score function from the skill
def score_story(text):
    s = text.lower()
    has_first = any(w in s for w in ['tôi ', 'mẹ tôi', 'cha tôi', 'con tôi', 'tôi đã', 'mình đã', 'chúng tôi'])
    has_emo = any(w in s for w in ['khóc', 'nước mắt', 'yêu', 'đau', 'buồn', 'nhớ', 'thương', 'mất', 'tạm biệt', 'tha thứ', 'biết ơn', 'cảm ơn', 'tự hào'])
    has_story = any(w in s for w in ['kể', 'hồi', 'ngày đó', 'năm ấy', 'một hôm', 'xảy ra', 'gặp'])
    is_phil = any(w in s for w in ['bạn nên', 'hãy luôn', 'đừng bao giờ', 'cuộc sống là', 'hạnh phúc là'])
    return has_first*2 + has_emo*2 + has_story*1 - is_phil*3

print("\n=== SCORED STORIES ===")
for story in story_data:
    score = score_story(story["text"])
    story["score"] = score
    # Show excerpt
    excerpt = story["text"][:150].replace('\n', ' ').strip()
    print(f"  [{score}] {story['title']} ({story['author']}) - {story['length_chars']} chars")
    print(f"       {excerpt}...")
    print()

# Sort by score descending
story_data.sort(key=lambda x: x["score"], reverse=True)

print("\n=== TOP CANDIDATES ===")
for i, story in enumerate(story_data[:12]):
    print(f"  #{i+1} [score={story['score']}] {story['title']} by {story['author']} ({story['length_chars']} chars)")

# Output as JSON for next step
with open("/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/parsed_stories.json", "w") as f:
    json.dump(story_data, f, ensure_ascii=False, indent=2)

print("\nSaved parsed_stories.json")
