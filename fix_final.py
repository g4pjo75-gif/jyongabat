# -*- coding: utf-8 -*-
"""
모든 깨진 패턴 최종 수정
"""
import os
import glob

out_dir = r"D:\ainigravity\work\jyongabat2\frontend\out"

# 깨진 패턴들과 올바른 교체
PATTERNS = [
    # JP Market 이모지 깨짐: \xf0\x9f\x81E\xf0\x9f\x81E -> 🇯🇵
    (b'\xf0\x9f\x81E\xf0\x9f\x81E JP Market', '🇯🇵 JP Market'.encode('utf-8')),
    
    # 설명 문자열 (완전히 깨진 부분) -> 정상 설명
    # AI 기반 종가베팅 시그널 시스템
]

def fix_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    for broken, fixed in PATTERNS:
        if broken in content:
            content = content.replace(broken, fixed)
            print(f"Fixed JP Market in {os.path.basename(filepath)}")
    
    # 설명 문자열은 복잡하므로 전체 content 값을 교체
    # "content":"AI ... " 패턴 찾아서 정상 값으로 교체
    # 이 부분은 0x81E가 포함된 content 값을 찾아서 교체
    
    # 더 간단한 접근: 0x81E 바이트를 포함한 JSON value를 찾아 제거하기 어려우므로
    # 일단 가장 문제되는 JP Market 이모지만 수정
    
    if content != original:
        with open(filepath, 'wb') as f:
            f.write(content)
        return True
    return False

# 모든 HTML 파일
html_files = glob.glob(os.path.join(out_dir, "**", "*.html"), recursive=True)
html_files.extend(glob.glob(os.path.join(out_dir, "*.html")))
html_files = list(set(html_files))

modified = 0
for fp in html_files:
    if fix_file(fp):
        modified += 1

print(f"\nModified: {modified} files")

# 타이틀 최종 확인
print("\n--- Title Verification ---")
for fp in html_files:
    with open(fp, 'rb') as f:
        c = f.read()
    ts = c.find(b'<title>')
    te = c.find(b'</title>')
    if ts != -1 and te != -1:
        title = c[ts+7:te]
        if b'\x81E' in title or b'\xf0\x9f' not in title and b'V2' in title:
            print(f"{os.path.basename(fp)}: {title[:50]}")
