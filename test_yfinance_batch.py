
import yfinance as yf
import pandas as pd

tickers = ["005930.KS", "000660.KS", "003380.KQ"] 
print(f"Downloading {tickers}...")

# Replicate backend logic
df = yf.download(tickers, period="5d", group_by='ticker', progress=False, threads=False)

print("\n--- DataFrame Shape ---")
print(df.shape)

print("\n--- DataFrame Head ---")
print(df.head())

print("\n--- DataFrame Tail ---")
print(df.tail())

print("\n--- Checking Values ---")
for t in tickers:
    try:
        if t in df.columns.levels[0]:
            series = df[t]['Close']
            print(f"\n[{t}] Close Series:")
            print(series)
            
            # Check dropna
            valid_series = series.dropna()
            if not valid_series.empty:
                print(f"Last Valid Value (dropna().iloc[-1]): {valid_series.iloc[-1]}")
            else:
                print("Series is empty after dropna!")
                
            last_val = series.iloc[-1]
            print(f"Raw Last Value (iloc[-1]): {last_val}")
            
    except Exception as e:
        print(f"Error checking {t}: {e}")
