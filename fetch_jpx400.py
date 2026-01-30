
import requests
import pandas as pd
import io

def fetch_jpx400():
    url = 'https://ja.wikipedia.org/wiki/JPX%E6%97%A5%E7%B5%8C%E3%82%A4%E3%83%B3%E3%83%87%E3%83%83%E3%82%AF%E3%82%B9400'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # pandas로 테이블 파싱
        tables = pd.read_html(io.StringIO(response.text))
        
        # 위키피디아 구조상 구성 종목 테이블을 찾아야 함
        # 보통 큰 테이블이 있음
        target_table = None
        for df in tables:
            if len(df) > 300: # 400개 가까운 테이블 찾기
                target_table = df
                break
        
        if target_table is None:
            # 300개 이상이 없으면 가장 긴 것
            target_table = max(tables, key=len)
            
        print(f"Found table with {len(target_table)} rows")
        print(target_table.columns)
        
        # 데이터프레임을 리스트로 변환하기 좋게 출력
        # 예상 컬럼: 코드, 종목명, 업종 등
        # 위키피디아 테이블 컬럼명을 확인해야 함
        print(target_table.head())
        
        return target_table
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    df = fetch_jpx400()
    if df is not None:
        df.to_csv("jpx400_raw.csv", index=False, encoding='utf-8-sig')
