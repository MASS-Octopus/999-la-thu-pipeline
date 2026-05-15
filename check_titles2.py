#!/usr/bin/env python3
"""Look at title start regions for top 8 stories."""
with open('/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-8/full.txt', 'r') as f:
    lines = f.readlines()

# Top 8 stories by line range:
# Story 1 (Score 8, Thanh Phương, Love Is Just Like A Broken Arm): starts after previous ending (line 660-662 area), ends at line 823
# Story 2 (Score 8, Thanh Phương, Angle Of Courage): starts after story ~line 2313, ends at line 2531
# Story 3 (Score 7, Thanh Phương, Goodwill): starts after ~line 254, ends at line 490
# Story 4 (Score 7, Nguyễn Đoàn, My Declaration Of Self-Esteem): starts after ~line 824, ends at line 913
# Story 5 (Score 7, Lê Lai, Internet): starts after ~line 1183, ends at line 1435
# Story 6 (Score 7, Nguyễn Ngân, My Own Experience): starts after story before ~2313, ends at line 2312 (this is story before Angle of Courage?)
# Story 7 (Score 6, Thành Nhân, Flower In Her Hair): starts after ~line 1487, ends at line 1755
# Story 8 (Score 6, Thanh Phương, From The Heart): starts after ~line 2595, ends at line 2893

# Let me find the story starts for each
print("=== Story 1: Love Is Just Like A Broken Arm starts ===")
# Story before this ends at line 660 (Hồng Nhung / Theo The Other Johnny)
# Next story starts right after
for i in range(663, 690):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 2: Angle Of Courage starts ===")
# Previous story ends at ~2313 (My Own Experience)
# Need to find the title area 
for i in range(2314, 2345):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 3: Goodwill (Quà của Annie) starts ===")
for i in range(255, 282):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 5: Lê Lai/Internet (score 7) starts ===")
for i in range(1184, 1215):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 6: My Own Experience starts ===")
# Before this story: story ends at ~2113 (Thanh Giang / Then You Still Have Hope)
for i in range(2114, 2145):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 7: Flower In Her Hair starts ===")
for i in range(1487, 1515):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 8: From The Heart starts ===")
for i in range(2595, 2625):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")

print("\n=== Story 4: My Declaration Of Self-Esteem (Tuyên ngôn) starts ===")
for i in range(827, 850):
    if i < len(lines):
        print(f" L{i+1}: {lines[i].rstrip()}")
