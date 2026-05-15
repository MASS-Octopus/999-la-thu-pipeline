#!/usr/bin/env python3
"""Get full text for top 8 stories with proper title extraction."""
import re, json

# Map English source names to likely Vietnamese titles based on known Hạt Giống Tâm Hồn content
# and context from the OCR
title_map = {
    'Love Is Just Like A Broken Arm': 'Hàn gắn một trái tim vỡ',
    'Goodwill': 'Quà của Annie',
    'My Declaration Of Self-Esteem': 'Tuyên ngôn của Cái Tôi',
    'Flower In Her Hair': 'Thiếu nữ cài hoa',
    'From The Heart': 'Sinh ra từ trái tim',
    'Angle Of Courage': None,  # need to check
    'Internet': None,  # multiple internet ones, need context
    'My Own Experience': None,  # need to check
    'Puppy Love': None,
    'Then You Still Have Hope': None,
    'Switching Roles': None,
    'Unconditional Love': None,
    'Take A Childs Hand': 'Hãy nắm lấy bàn tay',
    'Practical Magic': None,
    'Promises': 'Lời hứa',
    'He trusted Me, Until...': 'Lòng tin',
    'The Secrets of Success': None,
    'Peak Experience': 'Tiến về phía trước',
    'Colour Of Friendship': 'Sắc màu tình bạn',
    'Would You Tell Them?': 'Lá thư cho đời sau',
    'My fathers Hands': 'Bàn tay cha',
    'Execellence': None,
    'Farewell Gift': None,
    'Dont Change The World': 'Đừng thay đổi thế giới',
    'The Town Drunk And The Portrait Painter': 'Bức chân dung',
}

# But first, let me look at the specific page regions for each top story
# to find the actual titles in the OCR text

with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

# Find story #5 (Internet by Lê Lai) - the one that scored 7
# Need to look at the lines around the title
# Lê Lai Internet appears at line 1435-1436
print("=== Story #5 (Lê Lai / Internet, Score 7) title region ===")
for i in range(1405, 1440):
    if i < len(lines):
        print(f"  L{i+1}: {lines[i].rstrip()}")

print("\n=== Story #6 (Nguyễn Ngân / My Own Experience, Score 7) title region ===")
for i in range(2280, 2320):
    if i < len(lines):
        print(f"  L{i+1}: {lines[i].rstrip()}")

print("\n=== Story #2 (Thanh Phương / Angle Of Courage, Score 8) title region ===")
for i in range(2495, 2540):
    if i < len(lines):
        print(f"  L{i+1}: {lines[i].rstrip()}")

print("\n=== Story #1 (Thanh Phương / Love Is Just Like A Broken Arm, Score 8) ===")
# This is the Shanna/điều này có giúp ích story - look at beginning
for i in range(494, 540):
    if i < len(lines):
        print(f"  L{i+1}: {lines[i].rstrip()}")
