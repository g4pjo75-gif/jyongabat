# -*- coding: utf-8 -*-
"""
HTML 파일 분석 및 수정 스크립트
"""
import os

filepath = r"D:\ainigravity\work\jyongabat2\frontend\out\dashboard\kr.html"

# 바이트로 읽어서 분석
with open(filepath, 'rb') as f:
    content_bytes = f.read()

# title 태그 부분 찾기
title_start = content_bytes.find(b'<title>')
title_end = content_bytes.find(b'</title>')
if title_start != -1 and title_end != -1:
    title = content_bytes[title_start:title_end+8]
    print("Title bytes:", title[:100])
    print("Title hex:", title[:100].hex())

# Database 부분 찾기
db_start = content_bytes.find(b'absolute bottom-8')
if db_start != -1:
    print("\nDatabase section found at:", db_start)
    print("Context:", content_bytes[db_start-20:db_start+100])
