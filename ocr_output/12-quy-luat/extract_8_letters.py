#!/usr/bin/env python3
"""
Trích 8 đoạn từ 12 Quy Luật Cuộc Đời → Gemini → JSON array 8 thư.
Gọi Gemini qua Ollama localhost:11434, model gemini-3-flash-preview:cloud.
"""
import json, subprocess, sys, time, re

WORKSPACE = "/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/12-quy-luat"
OUTPUT = f"{WORKSPACE}/gemini_letters.json"

# Đọc full text
with open(f"{WORKSPACE}/full.txt", "r") as f:
    lines = f.readlines()

full_text = "".join(lines)
# Clean page markers
full_text = re.sub(r'=== PAGE \d+ ===\n?', '', full_text)

def extract_segment(start_line, end_line):
    """Extract lines, clean OCR artifacts."""
    text = "".join(lines[start_line:end_line])
    # Remove page markers
    text = re.sub(r'=== PAGE \d+ ===\n?', '', text)
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = " ".join(text.split())
    return text

# === 8 ĐOẠN CHỌN LỌC ===
# Mỗi tuple: (title, start_line, end_line, description)
passages = [
    ("Đứa trẻ bị bỏ đói và vợ tôi",
     5565, 5612,
     "Tôi từng chứng kiến một cậu bé bốn tuổi bị bỏ đói thường xuyên... vợ tôi kiên nhẫn cho cậu ăn... Hai mươi năm sau, hình ảnh đó vẫn khiến tôi rơi nước mắt."),

    ("Denis - gã chủ nhà say rượu và bài học về sự thật",
     9123, 9200,
     "Denis là một cựu thủ lĩnh băng mô-tô... 2h sáng gõ cửa bán lò vi sóng... Tôi nói thẳng sự thật với gã, và mối quan hệ trở nên mật thiết hơn."),

    ("Bệnh nhân hoang tưởng - kẻ phản diện đời thực",
     9100, 9121,
     "Bệnh nhân của tôi, một kẻ hoang tưởng... 'Ta sẽ là cơn ác mộng tồi tệ nhất của ngươi'... Tôi luôn nói sự thật với anh ta và điều đó khiến anh ta dịu lại."),

    ("Chris, Ed và những người bạn lạc lối",
     3909, 3980,
     "Tôi vẫn nhớ như in người bạn của Ed đang phê thuốc... Chris tự sát ở tuổi 30... Tại sao họ cứ liên tục chọn ở bên những người không tốt đẹp?"),

    ("Tôi bắt đầu viết trên Quora",
     658, 718,
     "Năm 2012, tôi bắt đầu viết bài cho Quora... Những lúc trốn việc, tôi tìm đến Quora... Danh sách quy luật tôi viết ra bất ngờ nhận được phản hồi vượt bậc."),

    ("Tôi cố viết sách và thất bại - bài học về sáng tạo",
     809, 822,
     "Tôi đã từng cố viết nên một phiên bản dễ hiểu hơn... Và tôi nhận ra rằng cả bản thân mình... chẳng có chút hồn nào cả. Tôi cho rằng do tôi đã phỏng theo bản thể cũ thay vì sáng tạo cái mới."),

    ("Ngôi nhà tranh Xô-viết và những cuộc trò chuyện trong bếp",
     376, 403,
     "Ngôi nhà được Tammy và chính anh chất đầy đồ đạc... tranh Lenin khắp tường... Chúng tôi trò chuyện trong căn bếp dưới tầng hầm... như đang sống trong một thế giới đã từng tồn tại."),

    ("Cha tôi và bài học từ chim hồng tước",
     1135, 1150,
     "Cha tôi nói về con chim hồng tước lấp đầy ủng hàng xóm bằng que củi... 'Nếu chúng ta lấy nó xuống, nó cũng sẽ lại lấp đầy thôi'... Hồng tước là loài chim nhỏ bé đáng yêu nhưng không biết khoan nhượng."),
]

print(f"Đã chọn {len(passages)} đoạn từ sách.\n")

results = []

for i, (title, start, end, desc) in enumerate(passages):
    segment = extract_segment(start, end)
    print(f"\n{'='*60}")
    print(f"Đoạn {i+1}/8: {title}")
    print(f"  Lines {start}-{end}, {len(segment)} chars")
    print(f"  Mô tả: {desc[:120]}...")

    prompt = f"""Dựa vào đoạn chiêm nghiệm sau từ sách "12 Quy Luật Cuộc Đời" của Jordan B. Peterson, hãy viết một lá thư tâm sự.

Đoạn trích:
---
{segment}
---

Yêu cầu:
- Viết 200-350 chữ, giọng "tôi"/"mình", thủ thỉ như nói với bạn thân.
- Ấm áp, chân thành, giữ tinh thần thiền và giọng văn cá nhân của Jordan Peterson.
- KHÔNG bài học đạo đức, KHÔNG giảng giải, KHÔNG kể lại nội dung gốc.
- Là lời tâm sự cá nhân, từ trải nghiệm của chính người viết.

Trả VỀ CHÍNH XÁC JSON này (không thêm bất kỳ text nào khác):
{{"so_thu": null, "noi_dung": "...nội dung thư...", "nguon": "12 Quy Luật Cuộc Đời - Jordan B. Peterson"}}"""

    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "Bạn là người viết thư tâm sự chuyên nghiệp. Luôn trả về JSON hợp lệ, nội dung thư 200-350 chữ tiếng Việt. Giọng thủ thỉ ấm áp, cá nhân, không giáo điều."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "options": {"temperature": 0.85, "num_predict": 2048}
    }

    # Gọi Gemini qua Ollama
    success = False
    for attempt in range(2):
        try:
            cmd = [
                "curl", "-s", "--max-time", "120",
                "http://localhost:11434/api/chat",
                "-d", json.dumps(payload, ensure_ascii=False)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=125)

            if result.returncode == 0 and result.stdout:
                resp = json.loads(result.stdout)
                content = resp.get("message", {}).get("content", "")
                print(f"  Gemini response: {len(content)} chars")

                # Try to extract JSON
                json_match = None
                # Find JSON object
                m = re.search(r'\{[^{}]*"so_thu"[^{}]*\}', content, re.DOTALL)
                if m:
                    try:
                        json_match = json.loads(m.group())
                    except:
                        pass

                if not json_match:
                    # Try parsing entire content
                    try:
                        json_match = json.loads(content)
                    except:
                        pass

                if json_match:
                    noi_dung = json_match.get("noi_dung", "")
                    if len(noi_dung) < 100:
                        print(f"  ⚠ Nội dung quá ngắn ({len(noi_dung)} chars), thử lại...")
                        continue
                    results.append(json_match)
                    print(f"  ✓ Thành công: {len(noi_dung)} chars")
                    success = True
                    break
                else:
                    # Fallback: use raw content as letter
                    clean = content.strip()
                    if clean.startswith("```"):
                        clean = re.sub(r'```\w*\n?', '', clean)
                    if len(clean) > 60:
                        results.append({
                            "so_thu": None,
                            "noi_dung": clean[:500],
                            "nguon": "12 Quy Luật Cuộc Đời - Jordan B. Peterson"
                        })
                        print(f"  ⚠ Không parse được JSON, dùng raw ({len(clean)} chars)")
                        success = True
                        break
            else:
                print(f"  ✗ curl error: {result.stderr[:200]}")

        except Exception as e:
            print(f"  ✗ Exception (attempt {attempt+1}): {e}")

        if attempt == 0 and not success:
            print(f"  → Thử lại lần 2...")
            time.sleep(2)

    if not success:
        print(f"  ❌ THẤT BẠI hoàn toàn, dùng fallback text")
        results.append({
            "so_thu": None,
            "noi_dung": f"[Đoạn {i+1}: {title}] {desc[:300]}",
            "nguon": "12 Quy Luật Cuộc Đời - Jordan B. Peterson"
        })

    time.sleep(2)  # Rate limit giữa các request

# === SAVE ===
print(f"\n\n{'='*60}")
print(f"HOÀN THÀNH: {len(results)}/8 thư")
print(f"Lưu vào: {OUTPUT}")

with open(OUTPUT, "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n=== FINAL JSON ARRAY ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
