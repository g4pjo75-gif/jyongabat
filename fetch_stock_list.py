"""
상위 시가총액 종목 리스트 생성 스크립트 (FinanceDataReader 사용)
KOSPI 상위 200개 + KOSDAQ 상위 100개 추출하여 engine/stock_list_data.py 생성
"""

import os
import FinanceDataReader as fdr
from datetime import datetime

def generate_stock_list():
    print(f"Fetching stock data using FinanceDataReader...")

    try:
        # 1. KOSPI 상위 200 (시가총액 기준)
        print("Fetching KOSPI stocks...")
        df_kospi = fdr.StockListing('KOSPI')
        # Marcap 순으로 정렬 (Marcap이 없으면 거래량이나 다른 기준으로 대체 가능하지만 보통 존재함)
        if 'Marcap' in df_kospi.columns:
            kospi_top200 = df_kospi.sort_values(by='Marcap', ascending=False).head(200)
        else:
            print("Warning: 'Marcap' column not found in KOSPI listing. Using 'Stocks' order.")
            kospi_top200 = df_kospi.head(200)
            
        kospi_list = []
        for _, row in kospi_top200.iterrows():
            code = row['Code']
            name = row['Name']
            kospi_list.append((f"{code}.KS", name, "KOSPI"))

        # 2. KOSDAQ 상위 100 (시가총액 기준)
        print("Fetching KOSDAQ stocks...")
        df_kosdaq = fdr.StockListing('KOSDAQ')
        if 'Marcap' in df_kosdaq.columns:
            kosdaq_top100 = df_kosdaq.sort_values(by='Marcap', ascending=False).head(100)
        else:
            print("Warning: 'Marcap' column not found in KOSDAQ listing. Using 'Stocks' order.")
            kosdaq_top100 = df_kosdaq.head(100)
            
        kosdaq_list = []
        for _, row in kosdaq_top100.iterrows():
            code = row['Code']
            name = row['Name']
            kosdaq_list.append((f"{code}.KQ", name, "KOSDAQ"))

        # 3. 파일 생성
        output_path = os.path.join("engine", "stock_list_data.py")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Auto-generated stock list by fetch_stock_list.py (via FinanceDataReader)\n")
            f.write(f"# Generated at: {datetime.now()}\n\n")
            
            f.write("KR_TOP_STOCKS = [\n")
            
            f.write("    # KOSPI Top 200\n")
            for item in kospi_list:
                f.write(f"    {str(item)},\n")
                
            f.write("\n    # KOSDAQ Top 100\n")
            for item in kosdaq_list:
                f.write(f"    {str(item)},\n")
                
            f.write("]\n")
            
        print(f"Successfully generated {output_path}")
        print(f"KOSPI: {len(kospi_list)}, KOSDAQ: {len(kosdaq_list)}")
        
    except Exception as e:
        print(f"Error generating stock list: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_stock_list()
