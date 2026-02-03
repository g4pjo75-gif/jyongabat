# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'D:\ainigravity\work\jyongabat2\frontend\out\dashboard\kr.html', 'rb') as f:
    c = f.read()

ts = c.find(b'<title>')
te = c.find(b'</title>')
title = c[ts+7:te].decode('utf-8', errors='replace')
print(f'Title: {title}')
print(f'Database box (HTML) present: {b"<div class=\"absolute bottom-8" in c}')
print(f'Database box (JSON) present: {b"absolute bottom-8 left-4 right-4" in c}')
