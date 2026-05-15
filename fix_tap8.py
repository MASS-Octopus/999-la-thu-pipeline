#!/usr/bin/env python3
"""Fix: remap story sources and ensure clean output for Tập 8."""
import re, json, os

# TOC from the OCR (page 160-161)
TOC = [
    "Câu chuyện về cuốn sách và giỏ đựng than",  # Lê Lai
    "Quà của Annie",                              # Thanh Phương
    "Điều này có giúp ích mẹ không?",             # Thanh Giang
    "Có một Johnny khác",                         # Hồng Nhung
    "Hàn gắn một trái tim vỡ",                    # Claude McDonald
    "Tuyên ngôn của cái Tôi",                     # Nguyễn Đoàn
    "Cái nút áo",                                 # Barbara Weidner / Thanh Giang
    "Hãy cho đi...",                              # Nguyên Thảo
    "Vượt lên chính mình",                        # Abraham Lincoln
    "Giá trị của 20 đô-la",                       # Bích Thủy
    "Những dấu chấm câu",                         # Lê Lai
    "Đừng thay đổi thế giới",                     # Thanh Giang
    "Thiếu nữ cài hoa",                           # Thành Nhân
    "Nếu có lòng",                                # Lan Nguyên
    "Ba người thầy vĩ đại",                       # Lê Lai
    "Bức chân dung",                              # (not in author list)
    "Nếu bạn vẫn có thể...",                      # Thanh Giang
    "Đôi mắt của mẹ",                             # Nguyễn Ngân
    "Thiên thần can đảm",                         # Thanh Phương
    "Những bài học từ trẻ thơ",                   # Lê Lai
    "Tình yêu diệu kỳ",                           # Thanh Phương
    "Sinh ra từ trái tim",                        # Bích Thủy
    "Tình yêu vô điều kiện",                      # (Albert Einstein)
    "Hãy nắm lấy bàn tay!",                       # Karl Marx
    "Phép màu của sự lắng nghe",                  # Mai Quốc Thế
    "Lời hứa",                                    # Bích Thủy
    "Cho và nhận",                                # Lord Byron
    "Lòng tin",                                   # Lan Nguyên
    "Cố gắng thêm chút nữa!",                     # Quỳnh Nga
    "Tiến về phía trước",                         # Jean Tharaud
    "Đừng bao giờ...",                            # Thanh Thủy
    "Sắc màu của cuộc sống",                      # Thanh Giang
    "Lời yêu thương",                             # William Penn / Thu Quỳnh
    "Sắc màu tình bạn",                           # Thanh Thảo
    "Lá thư cho đời sau",                         # Bích Thủy
    "Bàn tay cha",                                # Thanh Thủy
    "Thành công",                                 # (possibly Lan Nguyên)
    "Vai kịch cuối cùng",                         # Lan Nguyên
    "Món quà tạm biệt",                           # Thanh Giang
]

# Map content keywords to story names
# Based on reading the letter contents
LETTER_STORY_MAP = {
    0: "Tuyên ngôn của cái Tôi",       # Self-identity, freedom of choice
    1: "Cái nút áo",                    # Button story, mother sewing
    2: "Món quà tạm biệt",             # Dropping daughter at college, 150 miles
    3: "Thiên thần can đảm",           # Statue "Angel of Courage", Christmas
    4: "Tình yêu diệu kỳ",             # Mom with dementia, Ben playing Rummy
    5: "Thiên thần can đảm",           # DUPLICATE of story 3 - 75yo widow going to college
    6: "Lời yêu thương",               # Gloria passed away, regret for not speaking
    7: "Đôi mắt của mẹ",              # Blind mother touching/feeling
}

# Read existing output
with open('output/tap8_letters.json', 'r') as f:
    data = json.load(f)

# Fix nguon fields
fixed = []
seen_titles = set()
for i, item in enumerate(data):
    title = LETTER_STORY_MAP.get(i, "Unknown")
    
    # Skip duplicate stories (story 5 is same as story 3)
    if title in seen_titles:
        print(f"Skipping duplicate story: {title}")
        continue
    
    seen_titles.add(title)
    item["nguon"] = f"Hạt Giống Tâm Hồn - Tập 8 ({title})"
    fixed.append(item)

# If we have < 8, we need to generate more
print(f"Fixed {len(fixed)} unique letters (need 8)")

with open('output/tap8_letters.json', 'w', encoding='utf-8') as f:
    json.dump(fixed, f, ensure_ascii=False, indent=2)

print("Output fixed.")
for i, item in enumerate(fixed):
    print(f"  {i}: {item['nguon']} ({len(item['noi_dung'])} chars)")
