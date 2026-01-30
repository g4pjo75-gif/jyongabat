import asyncio
import os
import json
import yfinance as yf
import pandas as pd
import numpy as np

async def debug_scan():
    data_dir = os.path.join(os.getcwd(), 'data', 'jp')
    targets = []
    codes_seen = set()
    
    for type_key in ['n225', 'n400']:
        path = os.path.join(data_dir, f'jongga_v2_{type_key}_latest.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                signals = data.get('signals', [])
                for s in signals:
                    code = s['code']
                    if code not in codes_seen:
                        targets.append(s)
                        codes_seen.add(code)

    print(f"Total Targets: {len(targets)}")
    
    skipped_reasons = {}
    valid_count = 0
    
    for stock in targets:
        code = stock['code']
        ticker = f"{code}.T"
        try:
            df = yf.download(ticker, period="3mo", progress=False)
            if df.empty:
                skipped_reasons['empty_df'] = skipped_reasons.get('empty_df', 0) + 1
                continue
            if len(df) < 40:
                skipped_reasons['insufficient_data'] = skipped_reasons.get('insufficient_data', 0) + 1
                continue
            
            valid_count += 1
        except Exception as e:
            skipped_reasons[f'error_{type(e).__name__}'] = skipped_reasons.get(f'error_{type(e).__name__}', 0) + 1
            
    print(f"Valid Stocks: {valid_count}")
    print(f"Skipped Reasons: {skipped_reasons}")

if __name__ == "__main__":
    asyncio.run(debug_scan())
