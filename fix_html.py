# -*- coding: utf-8 -*-
"""
HTML 파일 바이트 수준 수정 스크립트
"""
import os
import glob
import re

out_dir = r"D:\ainigravity\work\jyongabat2\frontend\out"

# UTF-8 인코딩된 한글
TITLE_UTF8 = '종가베팅 V2 | AI Stock Analysis'.encode('utf-8')
DESC_UTF8 = 'AI 기반 종가베팅 시그널 시스템'.encode('utf-8')
JP_MARKET_UTF8 = '🇯🇵 JP Market'.encode('utf-8')

def fix_html_file(filepath):
    """바이트 수준에서 HTML 파일 수정"""
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 타이틀 태그 전체 교체 (정규식 대신 간단한 방법)
    title_start = content.find(b'<title>')
    title_end = content.find(b'</title>')
    if title_start != -1 and title_end != -1:
        new_title = b'<title>' + TITLE_UTF8 + b'</title>'
        content = content[:title_start] + new_title + content[title_end+8:]
    
    # 2. 메타 설명 수정
    desc_start = content.find(b'name="description" content="')
    if desc_start != -1:
        desc_content_start = desc_start + len(b'name="description" content="')
        desc_end = content.find(b'"/>', desc_content_start)
        if desc_end != -1:
            new_desc = b'name="description" content="' + DESC_UTF8 + b'"/>'
            content = content[:desc_start] + new_desc + content[desc_end+3:]
    
    # 3. JP Market 라벨 수정 (깨진 바이트 -> UTF-8)
    content = content.replace(b'\x81E\x81E JP Market', JP_MARKET_UTF8)
    
    # 4. Database 박스 제거 (HTML 내)
    db_html = b'<div class="absolute bottom-8 left-4 right-4"><div class="glass-card p-4 bg-blue-600/10 border-blue-500/20"><div class="text-[10px] font-bold text-blue-400 uppercase mb-1">Database</div><div class="text-xs text-slate-300">Connected to In-Memory</div></div></div>'
    content = content.replace(db_html, b'')
    
    # 5. JSON의 Database 박스 제거는 복잡해서 별도로
    # 화면에 보이는 HTML 직접 태그는 위에서 제거됨
    
    if content != original_content:
        with open(filepath, 'wb') as f:
            f.write(content)
        return True
    return False

# 모든 HTML 파일 처리
html_files = glob.glob(os.path.join(out_dir, "**", "*.html"), recursive=True)
html_files.extend(glob.glob(os.path.join(out_dir, "*.html")))
html_files = list(set(html_files))

modified_count = 0
for filepath in html_files:
    try:
        if fix_html_file(filepath):
            print(f"Modified: {os.path.basename(filepath)}")
            modified_count += 1
    except Exception as e:
        print(f"Error in {filepath}: {e}")

print(f"\nTotal modified: {modified_count} files")
