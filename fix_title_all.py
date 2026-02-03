# -*- coding: utf-8 -*-
"""
바이트 직접 교체로 모든 깨진 타이틀 수정
"""
import os
import glob

out_dir = r"D:\ainigravity\work\jyongabat2\frontend\out"

# UTF-8 인코딩된 한글 바이트
TITLE_UTF8 = '종가베팅 V2'.encode('utf-8')  # \xec\xa2\x85\xea\xb0\x80\xeb\xb2\xa0\xed\x8c\x85 V2
DESC_UTF8 = 'AI 기반 종가베팅 시그널 시스템'.encode('utf-8')

# 깨진 패턴들
BROKEN_PATTERNS = [
    # 깨진 "종가베팅 V2" 패턴
    (b'\x81E\x81E\xb0\x80\x81E\xa0\xfa\xa8\x81EV2', TITLE_UTF8),
    # 다른 가능한 패턴들
    (b'\x81E\x81E\xb0\x80\x81E', '종가베'.encode('utf-8')),
]

def fix_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    # 깨진 패턴 교체
    for broken, fixed in BROKEN_PATTERNS:
        if broken in content:
            content = content.replace(broken, fixed)
            print(f"  Fixed pattern in {os.path.basename(filepath)}")
    
    # 추가: 0x81E 로 시작하는 모든 깨진 문자열 제거 시도
    # 더 포괄적인 접근: V2 | AI 앞의 깨진 바이트들을 종가베팅으로 교체
    # 패턴: ...V2 | AI Stock Analysis (앞 부분이 깨진 경우)
    
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

# 검증
print("\n--- Verification ---")
with open(os.path.join(out_dir, "dashboard", "kr.html"), 'rb') as f:
    c = f.read()
    broken_count = c.count(b'\x81E')
    print(f"kr.html: {broken_count} broken patterns remaining")
