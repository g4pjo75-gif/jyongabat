# -*- coding: utf-8 -*-
"""
JSON 내부 Database 박스 제거 스크립트
"""
import os
import glob
import re

out_dir = r"D:\ainigravity\work\jyongabat2\frontend\out"

def fix_json_database(filepath):
    """JSON 내부 Database 박스 제거"""
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    # JSON형태의 Database 박스 패턴
    # [\"$\",\"div\",null,{\"className\":\"absolute bottom-8 left-4 right-4\",...Database...Connected to In-Memory...}]
    
    # 패턴 1: 직접 바이트 치환
    db_pattern = b'[\\"$\\",\\"div\\",null,{\\"className\\":\\"absolute bottom-8 left-4 right-4\\"'
    
    while db_pattern in content:
        start = content.find(db_pattern)
        if start == -1:
            break
        
        # 해당 JSON 객체의 끝 찾기 (균형 맞는 괄호)
        bracket_count = 0
        end = start
        found_start = False
        for i in range(start, len(content)):
            if content[i:i+1] == b'[':
                bracket_count += 1
                found_start = True
            elif content[i:i+1] == b']':
                bracket_count -= 1
                if found_start and bracket_count == 0:
                    end = i + 1
                    break
        
        if end > start:
            # 앞에 쉼표가 있으면 같이 제거
            if start > 0 and content[start-1:start] == b',':
                start -= 1
            content = content[:start] + content[end:]
        else:
            break
    
    if content != original:
        with open(filepath, 'wb') as f:
            f.write(content)
        return True
    return False

# 모든 HTML 파일 처리
html_files = glob.glob(os.path.join(out_dir, "**", "*.html"), recursive=True)
html_files.extend(glob.glob(os.path.join(out_dir, "*.html")))
html_files = list(set(html_files))

modified = 0
for fp in html_files:
    try:
        if fix_json_database(fp):
            print(f"Modified: {os.path.basename(fp)}")
            modified += 1
    except Exception as e:
        print(f"Error: {fp}: {e}")

print(f"\nTotal: {modified} files")
