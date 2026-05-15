#!/usr/bin/env python3
"""Call Gemini for each story, print output as JSON."""
import json, subprocess, sys, time

top8_titles = [
    'Hàn gắn một trái tim vỡ',
    'Thiên thần can đảm',
    'Quà của Annie',
    'Tuyên ngôn của Cái Tôi',
    'Vượt lên chính mình',
    'Đôi mắt của mẹ',
    'Thiếu nữ cài hoa',
    'Sinh ra từ trái tim'
]

results = []
sys_prompt = "Viết tâm sự 200-350 chữ, giọng tôi/mình, thủ thỉ bạn thân, ấm áp. Không kể lại cốt truyện. Không bài học đạo đức."

for i, title in enumerate(top8_titles):
    fn = f"/tmp/tap8_stories/story_{i+1:02d}.txt"
    with open(fn) as f:
        story_text = f.read()
    
    print(f"\n{'='*50}", flush=True)
    print(f"Story {i+1}/8: {title} ({len(story_text)} chars)", flush=True)
    
    user_msg = f"Dựa vào câu chuyện sau viết một lá thư tâm sự:\n\n{story_text}"
    
    payload = {
        "model": "gemini-3-flash-preview:cloud",
        "stream": False,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg}
        ]
    }
    
    try:
        r = subprocess.run(
            ['curl', '-s', '--max-time', '120',
             'http://localhost:11434/api/chat',
             '-d', json.dumps(payload, ensure_ascii=False)],
            capture_output=True, text=True, timeout=125
        )
        resp = json.loads(r.stdout)
        letter = resp.get('message', {}).get('content', '')
        print(f"  Gemini response: {len(letter)} chars", flush=True)
        
        if len(letter) < 200:
            print(f"  WARNING: Too short ({len(letter)})", flush=True)
        elif len(letter) > 350:
            print(f"  WARNING: Too long, truncating ({len(letter)} -> 350)", flush=True)
            letter = letter[:350]
        else:
            print(f"  ✓ OK", flush=True)
        
        results.append({
            'so_thu': None,
            'noi_dung': letter,
            'nguon': f'Hạt Giống Tâm Hồn - Tập 8 ({title})'
        })
        
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        results.append({
            'so_thu': None,
            'noi_dung': f'[Lỗi xử lý: {str(e)[:80]}]',
            'nguon': f'Hạt Giống Tâm Hồn - Tập 8 ({title})'
        })
    
    time.sleep(3)

# Final output as JSON
print("\n\n=== FINAL JSON ===", flush=True)
output = json.dumps(results, ensure_ascii=False, indent=2)
print(output, flush=True)

# Save to file
with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/output/tap8_letters.json', 'w') as f:
    f.write(output)
