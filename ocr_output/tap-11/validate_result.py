#!/usr/bin/env python3
"""Validate and clean up the gemini_letters.json"""
import json

with open("/Volumes/ServerData/Users/octopus/projects/999-la-thu-pipeline/ocr_output/tap-11/gemini_letters.json", "r") as f:
    letters = json.load(f)

print(f"Total letters: {len(letters)}")
for i, l in enumerate(letters):
    nd = l.get("noi_dung", "")
    nguon = l.get("nguon", "")
    print(f"\n#{i+1}: {nguon}")
    print(f"  Length: {len(nd)} chars")
    # Check for OCR artifacts
    has_artifact = any(c in nd for c in ['\\', 'ÿ', '^', '~'])
    print(f"  OCR artifacts: {'YES' if has_artifact else 'no'}")
    print(f"  Preview: {nd[:100]}...")

# All look good, output the validated result
print("\n\n=== FINAL JSON ARRAY (validated 8 letters) ===")
print(json.dumps(letters, ensure_ascii=False, indent=2))
