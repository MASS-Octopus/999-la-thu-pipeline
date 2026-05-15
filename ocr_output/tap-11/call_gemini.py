#!/usr/bin/env python3
"""Call Gemini via Ollama to write letters for top 8 stories."""
import json, os, subprocess, sys

WORKSPACE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11"

# Load scored stories
with open(f"{WORKSPACE}/stories_scored.json", "r") as f:
    data = json.load(f)

# Top 8 stories (need the full text)
with open(f"{WORKSPACE}/full.txt", "r") as f:
    all_lines = f.readlines()

# Story boundaries from previous script
stories_raw = [
    (161, 477, "Bài học trong giây lát", "Michael J. Collins, M.D."),
    (498, 723, "Thông điệp từ vườn cây thích", "Edward Ziegler"),
    (739, 1185, "Đối thủ đáng gờm - Kyle Maynard", "Derek Burnett"),
    (1199, 1440, "Liệu pháp tiếng cười", "Robert Schimmel"),
    (1462, 1736, "Lời khuyên của Gandhi", "Vijaya Lakshmi Pandit"),
    (1754, 1850, "Niềm hạnh phúc nhỏ nhoi - Will Rogers", "Albert P. Hout"),
    (1863, 2385, "Từ bóng tối ra ánh sáng", "Christopher Carrier"),
    (2401, 2825, "Tác giả của trường ca Messiah", "David Berreby"),
    (2845, 3176, "Hai từ nên tránh và hai từ nên nhớ", "Arthur Gordon"),
    (3651, 3718, "Nếu tôi được sống thêm lần nữa", "Erma Bombeck"),
    (3725, 4096, "Hành trình trên xe buýt", "Rachel Simon"),
    (4112, 4447, "Món quà quý giá nhất - Jack Benny", "Jack Benny"),
    (4693, 5024, "Câu chuyện Giáng sinh - Dickens", "Thormas J. Burns"),
]

# Top 8 by score (from our output): Carrier, Maynard, Handel, Dickens, RachelSimon, ArthurGordon, Collins, JackBenny
# These are titles with highest scores & length 
top8_titles = [
    "Từ bóng tối ra ánh sáng",
    "Đối thủ đáng gờm - Kyle Maynard",
    "Tác giả của trường ca Messiah",
    "Câu chuyện Giáng sinh - Dickens",
    "Hành trình trên xe buýt",
    "Hai từ nên tránh và hai từ nên nhớ",
    "Bài học trong giây lát",
    "Món quà quý giá nhất - Jack Benny",
]

results = []

for s in stories_raw:
    start, end, title, author = s
    if title not in top8_titles:
        continue
    
    text = "".join(all_lines[start:end])
    
    # Create a summarization prompt
    # Extract key narrative elements
    summary = text[:3000]  # use first 3000 chars as context
    
    prompt = f"""Đây là một câu chuyện từ sách Hạt Giống Tâm Hồn tập "Những Trải Nghiệm Cuộc Sống" của Stephen Covey. Tên truyện: "{title}", tác giả gốc: {author}.

Nội dung truyện (OCR):
---
{summary}
---

Hãy chuyển hóa câu chuyện này thành một bức thư tâm sự 200-350 chữ, viết ở ngôi thứ nhất (tôi/mình), giọng thủ thỉ tâm tình như đang tâm sự với bạn thân. Phải ấm áp, cảm xúc, không giáo điều, không dạy đời. Giữ tinh thần câu chuyện gốc nhưng biến thành lời tâm sự cá nhân.

Trả về CHÍNH XÁC JSON này (không thêm gì khác):
{{"so_thu": null, "noi_dung": "...nội dung thư...", "nguon": "Hạt Giống Tâm Hồn - Tập 11: Những Trải Nghiệm Cuộc Sống ({title})"}}"""
    
    print(f"\n{'='*60}")
    print(f"Processing: {title}")
    print(f"Prompt length: {len(prompt)} chars")
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "Bạn là người viết thư tâm sự chuyên nghiệp. Luôn trả về JSON hợp lệ, nội dung thư 200-350 chữ tiếng Việt, giọng thủ thỉ ấm áp."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "options": {"temperature": 0.9}
    }
    
    try:
        cmd = [
            "curl", "-s", "--max-time", "90",
            "http://localhost:11434/api/chat",
            "-d", json.dumps(payload, ensure_ascii=False)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=95)
        
        if result.returncode == 0 and result.stdout:
            resp = json.loads(result.stdout)
            content = resp.get("message", {}).get("content", "")
            
            # Try to extract JSON from content
            json_match = None
            # Find JSON block
            import re
            m = re.search(r'\{[^{}]*"so_thu"[^{}]*\}', content, re.DOTALL)
            if m:
                try:
                    json_match = json.loads(m.group())
                except:
                    pass
            
            if not json_match:
                # Try entire content
                try:
                    json_match = json.loads(content)
                except:
                    pass
            
            if json_match:
                results.append(json_match)
                print(f"  ✓ Success: {len(json_match.get('noi_dung', ''))} chars")
            else:
                print(f"  ⚠ Could not parse JSON from response")
                print(f"  Raw: {content[:300]}...")
                # Save raw for debug
                results.append({
                    "so_thu": None,
                    "noi_dung": content[:500],
                    "nguon": f"Hạt Giống Tâm Hồn - Tập 11: Những Trải Nghiệm Cuộc Sống ({title})",
                    "_raw": True
                })
        else:
            print(f"  ✗ Error: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# Save results
output_path = f"{WORKSPACE}/gemini_letters.json"
with open(output_path, "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\n{'='*60}")
print(f"Total letters generated: {len(results)}")
print(f"Saved to: {output_path}")

# Print final JSON array
print("\n=== FINAL JSON ARRAY ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
