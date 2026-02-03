# -*- coding: utf-8 -*-
"""
남은 깨진 패턴 분석
"""
import os

filepath = r"D:\ainigravity\work\jyongabat2\frontend\out\dashboard\kr.html"

with open(filepath, 'rb') as f:
    content = f.read()

# 0x81E 패턴 주변 컨텍스트 출력
pos = 0
count = 0
while True:
    idx = content.find(b'\x81E', pos)
    if idx == -1:
        break
    count += 1
    # 앞뒤 30바이트 컨텍스트
    start = max(0, idx - 20)
    end = min(len(content), idx + 30)
    context = content[start:end]
    print(f"#{count} at {idx}: {context}")
    pos = idx + 1
    
print(f"\nTotal: {count} occurrences")
