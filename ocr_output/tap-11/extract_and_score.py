#!/usr/bin/env python3
"""Extract full stories from tap-11, score, output JSON."""
import json, re

PATH = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/full.txt"
with open(PATH, "r") as f:
    lines = f.readlines()

# Manually defined story boundaries based on careful reading
# (start_line, end_line, title, author) 
# Start = first content line after section header
# End = last line before author credit
stories_raw = [
    (161, 477, "Bài học trong giây lát", "Michael J. Collins, M.D."),
    (498, 723, "Thông điệp từ vườn cây thích", "Edward Ziegler"),
    (739, 1185, "Đối thủ đáng gờm", "Derek Burnett"),
    (1199, 1440, "Liệu pháp tiếng cười", "Robert Schimmel"),
    (1462, 1736, "Lời khuyên của Gandhi", "Vijaya Lakshmi Pandit"),
    (1754, 1850, "Niềm hạnh phúc nhỏ nhoi", "Albert P. Hout"),
    (1863, 2385, "Từ bóng tối ra ánh sáng", "Christopher Carrier"),
    (2401, 2825, "Tác giả của trường ca Messiah", "David Berreby"),
    (2845, 3176, "Hai từ nên tránh và hai từ nên nhớ", "Arthur Gordon"),
    (3193, 3247, "Nghiên cứu của anh thật nhảm nhí", "Fran Lostys"),
    (3260, 3334, "Amy Tan và chồng", "Gary Sledge"),
    (3342, 3428, "Robert Ballard - Titanic", "Jamice Leqry"),
    (3441, 3639, "Bài học từ người Eskimo", "Gontran de Poncins"),
    (3651, 3718, "Nếu tôi được sống thêm lần nữa", "Erma Bombeck"),
    (3725, 4096, "Hành trình trên xe buýt", "Rachel Simon"),
    (4112, 4447, "Món quà quý giá nhất - Jack Benny", "Jack Benny"),
    (4468, 4679, "Sarah Mahoney", "Sarah Mahoney"),
    (4693, 5024, "Câu chuyện Giáng sinh - Dickens", "Thormas J. Burns"),
    (5036, 5324, "Nghệ thuật quản lý khách sạn - Ritz", "George Kenf"),
    (5336, 5387, "Câu chuyện ở sân bay", "Terry Paulson"),
]

# Score function from the skill
def score_story(text):
    s = text.lower()
    has_first = any(w in s for w in ['tôi ', 'mẹ tôi', 'cha tôi', 'con tôi', 'tôi đã', 'mình đã', 'chúng tôi'])
    has_emo = any(w in s for w in ['khóc', 'nước mắt', 'yêu', 'đau', 'buồn', 'nhớ', 'thương', 'mất', 'tạm biệt', 'tha thứ', 'biết ơn', 'cảm ơn', 'tự hào'])
    has_story = any(w in s for w in ['kể', 'hồi', 'ngày đó', 'năm ấy', 'một hôm', 'xảy ra', 'gặp'])
    is_phil = any(w in s for w in ['bạn nên', 'hãy luôn', 'đừng bao giờ', 'cuộc sống là', 'hạnh phúc là'])
    return has_first*2 + has_emo*2 + has_story*1 - is_phil*3

stories = []
for start, end, title, author in stories_raw:
    # Extract text between boundaries
    text = "".join(lines[start:end])
    score = score_story(text)
    stories.append({
        "title": title,
        "author": author,
        "start_line": start,
        "end_line": end,
        "text": text,
        "score": score,
        "length_chars": len(text)
    })

# Sort by score desc
stories.sort(key=lambda x: (-x["score"], -x["length_chars"]))

print("=== ALL STORIES SCORED ===\n")
for i, s in enumerate(stories):
    print(f"#{i+1} [score={s['score']}] {s['title']} ({s['author']}) - {s['length_chars']} chars")
    # Show first 120 chars of content
    preview = s["text"][:120].replace('\n', ' ').strip()
    print(f"    Preview: {preview}...\n")

# Output top 8 for Gemini
top8 = stories[:8]
print("\n=== TOP 8 FOR GEMINI ===\n")
for i, s in enumerate(top8):
    print(f"#{i+1} [score={s['score']}] {s['title']} by {s['author']} ({s['length_chars']} chars)")

# Save full data
out = {
    "tap": 11,
    "book": "Hạt Giống Tâm Hồn - Những Trải Nghiệm Cuộc Sống (Stephen Covey)",
    "total_stories": len(stories),
    "top8": [
        {"title": s["title"], "author": s["author"], "score": s["score"]}
        for s in top8
    ],
    "all_scored": [
        {"title": s["title"], "author": s["author"], "score": s["score"], "length_chars": s["length_chars"]}
        for s in stories
    ]
}

with open("/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/stories_scored.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("\nSaved stories_scored.json")
