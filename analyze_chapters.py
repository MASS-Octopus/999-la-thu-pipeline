#!/usr/bin/env python3
"""Extract chapters from Yeu Nhung Dieu Khong Hoan Hao OCR and map boundaries."""
import re

path = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/yeu-khong-hoan-hao/full.txt"
with open(path, 'r') as f:
    content = f.read()

# TOC order
toc_chapters = [
    "ĐỪNG SỐNG QUÁ HIỀN LÀNH",
    "CHỈ CẦN BẠN TỒN TẠI LÀ ĐÃ ĐỦ RỒI",
    "ĐIỀU NHỎ BÉ TÔI NHẬN RA KHI Ở THIỀN PHÒNG",
    "CÁCH GIẢI QUYẾT CẢM XÚC PHẬT LÒNG",
    "CÁI ÔM ẤM ÁP NHƯ ÁNH NẮNG MẶT TRỜI",
    "LẮNG NGHE LÀ MỘT BIỂU HIỆN CỦA TÌNH YÊU THƯƠNG",
    "GỬI NHỮNG BẠN TRẺ TÔI YÊU MẾN",
    "KHI LẦN ĐẦU TIÊN THẤT BẠI TRONG ĐỜI",
    "CON YÊU MẸ RẤT RẤT NHIỀU",
    "HIỂU VỀ CHA",
    "KHI GẶP NGƯỜI KHÓ CÓ THỂ THA THỨ",
    "THƯA SƯ THẦY, LÒNG CON QUÁ U SẦU",
    "HIỆN TẠI LUÔN THỨC TỈNH CHÍNH LÀ QUÊ HƯƠNG CỦA TÂM HỒN",
    "BẠN THẬT GIỐNG ĐỨC PHẬT",
    "HÃY CHO PHÉP BẢN THÂN MÌNH ĐAU KHỔ",
]

# Find all page markers
pages = {}
for m in re.finditer(r'=== PAGE (\d+) ===', content):
    page_num = int(m.group(1))
    pages[page_num] = m.start()

# Search for chapter titles in body (after page 7, after line 192)
body_start = pages.get(7, 0) + content[pages[7]:].find('\n', 0) + len('=== PAGE 7 ===\n')

# Find each chapter in body by looking for title patterns
chapter_starts = []
for i, title in enumerate(toc_chapters):
    # Search for the title or close variant
    # Normalize title for searching: remove accents partially
    pattern = re.escape(title[:15])  # first 15 chars
    matches = list(re.finditer(pattern, content))
    # Filter matches after TOC (page 6)
    toc_end = pages.get(7, 0)
    body_matches = [m for m in matches if m.start() > toc_end]
    if body_matches:
        start_pos = body_matches[0].start()
        # Find which page this is in
        page_num = None
        for pn in sorted(pages.keys()):
            if pages[pn] <= start_pos:
                page_num = pn
        char_count = len(content[start_pos:])
        chapter_starts.append((i+1, title, page_num, start_pos, char_count))
    else:
        # Try fuzzy search
        words = title.split()[:3]
        for w in words:
            m2 = re.search(re.escape(w[:4]), content[toc_end:], re.IGNORECASE)
            if m2:
                start_pos = toc_end + m2.start()
                page_num = None
                for pn in sorted(pages.keys()):
                    if pages[pn] <= start_pos:
                        page_num = pn
                char_count = len(content[start_pos:])
                chapter_starts.append((i+1, title, page_num, start_pos, char_count, "FUZZY"))
                break

print("CHAPTER MAP:")
print("=" * 80)
for ch in chapter_starts:
    if len(ch) == 5:
        idx, title, page, pos, chars = ch
        note = ""
    else:
        idx, title, page, pos, chars, note = ch
    # Show first 80 chars of content
    snippet = content[pos:pos+80].replace('\n', ' | ')
    print(f"#{idx}: {title}")
    print(f"   Page {page}, pos {pos}, ~{chars} chars {note}")
    print(f"   Start: {snippet}")
    print()

# Now identify the 8 most personal chapters
# Criteria: nhiều "tôi"/"mình", trải nghiệm cá nhân
print("\n\nPERSONAL CONTENT ANALYSIS:")
print("=" * 80)
for ch in chapter_starts:
    if len(ch) == 5:
        idx, title, page, pos, chars = ch
    else:
        idx, title, page, pos, chars, note = ch
    # Get chapter text (next 4000 chars or to next chapter)
    chap_text = content[pos:pos+4000]
    t_count = chap_text.lower().count('tôi ') + chap_text.lower().count('tôi,') + chap_text.lower().count('tôi.') + chap_text.lower().count('tôi\n')
    m_count = chap_text.lower().count('mình ') + chap_text.lower().count('mình,') + chap_text.lower().count('mình.')
    personal_count = t_count + m_count
    print(f"#{idx}: {title} -> 'tôi':{t_count} 'mình':{m_count} personal:{personal_count}")
