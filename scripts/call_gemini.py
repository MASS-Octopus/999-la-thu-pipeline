#!/usr/bin/env python3
"""
Gọi Gemini API (qua Ollama) để chuyển hóa các đoạn văn Hae Min thành thư tâm sự.
Đầu vào: JSON array các passage đã chọn
Đầu ra: JSON array các lá thư
"""
import json, subprocess, time, sys

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemini-3-flash-preview:cloud"
SYSTEM_PROMPT = """Viết một lá thư tâm sự 200-350 chữ, giọng "tôi"/"mình", thủ thỉ như nói chuyện với bạn thân, ấm áp. Giữ tinh thần thiền và giọng văn Hae Min. Không bài học đạo đức. Không kể lại nội dung gốc. Viết bằng tiếng Việt tự nhiên, giàu cảm xúc."""

def call_gemini(passage_text):
    """Gọi Gemini API chuyển hóa một passage thành thư"""
    user_msg = f"""Dựa vào đoạn chiêm nghiệm sau, viết một lá thư tâm sự:

{passage_text}"""
    
    payload = {
        "model": MODEL,
        "stream": False,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_msg}
        ]
    }
    
    cmd = [
        "curl", "-s", "--max-time", "120",
        OLLAMA_URL,
        "-d", json.dumps(payload, ensure_ascii=False)
    ]
    
    for attempt in range(2):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=130
            )
            
            if result.returncode != 0:
                print(f"  Attempt {attempt+1}: curl failed with code {result.returncode}")
                print(f"  stderr: {result.stderr[:200]}")
                time.sleep(3)
                continue
            
            response = json.loads(result.stdout)
            content = response.get("message", {}).get("content", "").strip()
            
            if content:
                return content
            else:
                print(f"  Attempt {attempt+1}: empty response, retrying...")
                print(f"  Raw: {result.stdout[:300]}")
                time.sleep(3)
        except json.JSONDecodeError as e:
            print(f"  Attempt {attempt+1}: JSON parse error: {e}")
            print(f"  Raw output: {result.stdout[:300]}")
            time.sleep(3)
        except Exception as e:
            print(f"  Attempt {attempt+1}: Error: {e}")
            time.sleep(3)
    
    return None

def main():
    with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/data/selected_passages.json', 'r', encoding='utf-8') as f:
        passages = json.load(f)
    
    print(f"Processing {len(passages)} passages...")
    
    letters = []
    for i, p in enumerate(passages):
        print(f"\n{'='*60}")
        print(f"Passage {i+1}/{len(passages)}: Score={p['score']}, Chapter={p['chapter']}")
        print(f"Source text length: {len(p['text'])} chars")
        print(f"Source preview: {p['text'][:100]}...")
        print(f"Calling Gemini...")
        
        letter = call_gemini(p['text'])
        
        if letter:
            print(f"SUCCESS! Letter length: {len(letter)} chars")
            print(f"Preview: {letter[:100]}...")
            letters.append({
                "so_thu": None,
                "noi_dung": letter,
                "nguon": "Bước Chậm Lại Giữa Thế Gian Vội Vã - Hae Min",
                "doan_goc_score": p['score'],
                "chuong": p['chapter']
            })
        else:
            print(f"FAILED after 2 attempts! Skipping...")
            # Add placeholder
            letters.append({
                "so_thu": None,
                "noi_dung": f"[Không thể tạo thư - Gemini API lỗi] {p['text'][:100]}",
                "nguon": "Bước Chậm Lại Giữa Thế Gian Vội Vã - Hae Min",
                "doan_goc_score": p['score'],
                "chuong": p['chapter']
            })
        
        # Brief pause between calls
        time.sleep(1)
    
    # Save output
    output_path = '/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/data/hae_min_letters.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(letters, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Done! {len([l for l in letters if l['noi_dung'] and not l['noi_dung'].startswith('[Không')])}/{len(letters)} letters created successfully.")
    print(f"Saved to: {output_path}")

if __name__ == '__main__':
    main()
