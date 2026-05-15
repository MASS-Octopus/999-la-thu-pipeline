#!/usr/bin/env python3
"""
Trích xuất 8 đoạn hay nhất từ Good Luck, gọi Gemini chuyển hóa thành thư tâm sự,
xuất JSON array 8 thư.
"""

import subprocess
import json
import time
import re

# 8 đoạn được chọn thủ công từ nội dung sách (đã đọc toàn bộ)
PASSAGES = [
    # Đoạn 1: Cuộc gặp gỡ cảm động sau 50 năm - lời thoại đầu tiên
    """Khi đưa ánh mắt nhìn sang phía người đối diện, cả hai chợt thấy có điều gì dường như quen lắm, gợi nên từ rất xa xăm nhưng cũng thật gần gũi.
- Anh là Max phải không? - Ông già lên tiếng hỏi.
- Còn anh có phải là Jim không? - Max nhìn thật lâu và hỏi nhỏ với giọng ngạc nhiên khôn xiết.
- Ôi! Bao nhiêu năm đã trôi qua! - Ông lão tên Jim thốt lên.
- Không thể nào như thế được! Thật không thể tin nổi! - Max nghẹn lời.
Họ đứng dậy ôm chằm lấy nhau.
- Tôi đã nhận ra ngay đôi mắt xanh của cậu, Jim ạ - Max xúc động.
- Còn tôi thì lại không thể nào lầm vào đâu được cái nhìn thẳng thắn và chân thành của cậu... từ cách đây năm mươi năm vẫn không thay đổi chút nào. Tôi vẫn nhớ cậu, dù ngần ấy thời gian đã qua... - Jim nói giọng run run.""",

    # Đoạn 2: Jim kể về chuỗi thất bại - sự tổn thương và mất mát
    """Jim thở dài:
- Cuộc đời tôi là một chuỗi dài những thất bại liên tiếp.
- Tôi đã có tất cả, có những gì mà mình hằng mong muốn và cũng đã mất tất cả. Quả là may mắn không bao giờ ở bên tôi.
- Tôi không còn biết phải làm gì nữa. Tất cả những người đã từng sát cánh bên tôi thời hoàng kim giờ đều ngoảnh mặt lại. Ngay cả vợ tôi cũng bỏ tôi mà đi. Cuộc đời tôi xuống dốc đến độ đã có lúc tôi biết cơn đói là như thế nào. Quả thật cuộc đời đã không mang lại cho tôi nhiều may mắn, mà kết cục lại bất hạnh thế này đây.""",

    # Đoạn 3: Max phân biệt may mắn tình cờ và may mắn thật sự
    """Max trầm ngâm một hồi lâu rồi mới cất tiếng trả lời:
- Gia đình cậu đã may mắn khi bất ngờ được thừa hưởng một gia tài lớn. Nhưng sự may mắn đó lại không tùy thuộc vào chúng ta, đó là lý do tại sao nó không kéo dài lâu được. Ngược lại sự may mắn thật sự là do chính cậu tạo ra, nó phụ thuộc vào cậu. Đó mới chính là sự may mắn thật sự.
- Chín mươi phần trăm những người từng trúng vé số đã phá sản hay trở về tình cảnh như trước đây trong vòng chưa đầy mười năm kể từ ngày họ trúng số. Ngược lại, sự may mắn thật sự có thể đến với ta nếu ta thật lòng mong nó đến. Chính vì vậy mà ta gọi nó là sự may mắn tốt lành, là điều mà ai trong chúng ta cũng đều mong ước.""",

    # Đoạn 4: Sid tạo ra điều khác biệt - bước đầu của thành công
    """Sid đã làm được một điều hết sức quan trọng: đó là chàng đã tạo ra một điều khác biệt, điều mà chưa ai từng làm cho khu rừng này. Nếu từ trước đến giờ chưa hề có một cây bốn lá nào mọc ở đây, nếu chưa ai từng tìm ra được nó, thì đó chính là vì tất cả những người đó đã luôn lặp lại những điều cũ kỹ, những điều mà những người trước đó đã từng làm. Là một hiệp sĩ thực thụ, Sid biết mình cần tạo ra một điều khác biệt, và đó chính là bước đi đầu tiên để dẫn đến thành công.
- Trong quá khứ chưa từng có một cây bốn lá nào mọc ở khu rừng này thì đâu có nghĩa là trong tương lai nó sẽ không thể mọc lên được đâu. Giờ thì điều kiện đất đai đã khác rồi.""",

    # Đoạn 5: Bài học về sẻ chia - lời ông nội
    """Sid nhớ lại lời dặn của người ông quá cố: Cuộc sống sẽ mang lại cho cháu những gì cháu đã cho đi. Những vấn đề của người khác thường lại là một giải pháp cho chính cháu. Nếu cháu sẵn lòng sẻ chia, cháu sẽ nhận được nhiều hơn thế nữa.
Và điều này chính xác vừa xảy ra với Sid: chàng đã chấp nhận quên đi chuyện lấy nước để khỏi đánh thức những bông hoa ly và ngay khi chàng tìm cách chia sẻ những nỗi khổ của Bà chúa hồ thì chàng lại tìm được cách giải quyết được việc của chính mình.
Kỳ lạ thay, bây giờ Sid ít cảm thấy lo lắng hơn về việc liệu mảnh đất mình chọn có đúng là nơi Cây Bốn Lá thần kỳ sẽ mọc hay không. Chàng chỉ cảm nhận như vậy là đúng. Chàng đang làm những gì mình phải làm. Và điều này mang lại cho chàng một cảm giác dễ chịu.""",

    # Đoạn 6: Đừng trì hoãn - hãy hành động ngay
    """Sid chợt nhớ tới lời của Sequoia. Bà nói rằng người ta thường hay để lại việc tới ngày mai mới làm. Và Sid cũng nhớ lại một lời khuyên luôn tỏ ra hữu dụng với chàng: "Hãy hành động ngay bây giờ, đừng trì hoãn nữa."
Đúng là dường như chàng sẽ không còn cần phải làm gì thêm nữa nên chàng có thể để việc này vào ngày mai. Nhưng nếu chàng làm ngay bây giờ thì chàng sẽ có thêm một ngày trống nữa và biết đâu nó sẽ giúp thêm gì cho chàng thì sao. Vì thế Sid quyết định tranh thủ thời gian trời còn sáng để làm luôn hôm nay.
Luôn trung thành với các nguyên tắc của mình, chàng đã hành động và không trì hoãn những việc cần làm.""",

    # Đoạn 7: Khoảnh khắc Sid nhận ra giá trị của nỗ lực, không ân hận
    """Sid tự nhủ với mình:
- Dẫu sao thì ta cũng đã sống với những giấc mơ thật đẹp mấy ngày qua trong khu rừng này. Ta đã làm hết sức mình cho những điều mà ta nghĩ là đúng và cần thiết. Đúng là thật khó mà tìm được vị trí chính xác nơi Cây Bốn Lá thần kỳ sẽ mọc. Mà nếu giả sử sau cùng cây bốn lá không mọc lên ở đây thì ta cũng không còn ân hận, vì ta đã làm hết sức mình, đã làm tất cả những gì có thể làm được.""",

    # Đoạn 8: Jim nhận ra chính mình đã tạo ra may mắn - kết đầy hy vọng
    """Jim chậm rãi nói:
- Tôi đã là người tạo ra các điều kiện để câu chuyện này đến với tôi, để cho may mắn có thể mỉm cười với tôi. Chúng ta đã không tình cờ gặp nhau. Trong mấy năm qua không một ngày nào mà tôi lại không cố tìm ra cậu trong những gương mặt mà tôi nhìn thấy. Không sót người nào cả, ở mỗi góc đường, ở mỗi quán xá, ở cột đèn giao thông, ở mỗi ngóc ngách của thành phố này... Tôi tìm cậu với niềm tin rằng cậu sẽ truyền nghị lực và niềm tin cho mình. Và câu chuyện may mắn vừa rồi là một món quà vô giá đối với tôi, nó quý hơn tất cả những điều khác.
- Hôm nay gặp lại cậu và nghe câu chuyện may mắn đó. Tôi cảm giác như mình trẻ lại. Tôi không nghĩ là mình đã sáu mươi tuổi rồi. Tôi sẽ dám bắt đầu lại từ đầu.""",
]

SYSTEM_PROMPT = """Viết một lá thư tâm sự 200-350 chữ, giọng "tôi"/"mình", thủ thỉ như nói với bạn thân, ấm áp, gần gũi. 
Không dùng giọng dạy đời, không kể lại cốt truyện. 
Hãy viết như đang tâm sự từ trải nghiệm của chính mình, lấy cảm hứng từ câu chuyện nhưng không nhắc đến nhân vật gốc."""

USER_TEMPLATE = """Dựa vào tinh thần của câu chuyện sau, hãy viết một lá thư tâm sự với giọng "tôi"/"mình", như đang thủ thỉ với một người bạn thân, thật ấm áp và gần gũi:

{passage}"""


def call_gemini(passage: str, max_retries: int = 3) -> str:
    """Gọi Gemini qua Ollama API để chuyển hóa đoạn trích thành thư."""
    user_msg = USER_TEMPLATE.format(passage=passage)
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]
    }
    
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "120",
                 "http://localhost:11434/api/chat",
                 "-d", json.dumps(payload)],
                capture_output=True, text=True, timeout=130
            )
            
            if result.returncode != 0:
                print(f"  curl error (attempt {attempt+1}): {result.stderr[:200]}")
                time.sleep(3)
                continue
            
            response = json.loads(result.stdout)
            content = response.get("message", {}).get("content", "")
            
            if content and len(content) > 50:
                return content.strip()
            else:
                print(f"  Empty/short response (attempt {attempt+1})")
                time.sleep(2)
                
        except json.JSONDecodeError as e:
            print(f"  JSON decode error (attempt {attempt+1}): {e}")
            print(f"  Raw stdout[:200]: {result.stdout[:200]}")
            time.sleep(2)
        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2)
    
    return ""


def main():
    letters = []
    
    for i, passage in enumerate(PASSAGES, 1):
        print(f"\n{'='*60}")
        print(f"Đoạn {i}/8: {len(passage)} ký tự")
        print(f"{'='*60}")
        
        # Hiển thị 100 ký tự đầu của đoạn
        preview = passage[:100].replace('\n', ' ').strip()
        print(f"Preview: {preview}...")
        
        letter = call_gemini(passage)
        
        if letter:
            word_count = len(letter.split())
            print(f"✅ Thư {i}: {word_count} từ, {len(letter)} ký tự")
            print(f"   Preview: {letter[:120]}...")
        else:
            print(f"❌ Thư {i}: KHÔNG nhận được phản hồi")
            letter = ""
        
        letters.append({
            "so_thu": None,
            "noi_dung": letter,
            "nguon": "Bí Mật của May Mắn - Alex Rovira"
        })
        
        # Delay giữa các lần gọi
        if i < len(PASSAGES):
            time.sleep(2)
    
    # Xuất JSON
    output_path = "/Users/octopus/projects/999-la-thu-pipeline/ocr_output/may-man/letters_output.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(letters, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"ĐÃ XUẤT: {output_path}")
    print(f"Tổng: {len(letters)} thư")
    
    # Thống kê
    success = sum(1 for l in letters if l["noi_dung"])
    print(f"Thành công: {success}/{len(letters)}")
    
    # In đẹp
    print(f"\n{'='*60}")
    print("KẾT QUẢ JSON:")
    print(json.dumps(letters, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
