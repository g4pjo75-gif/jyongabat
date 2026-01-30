import requests
from bs4 import BeautifulSoup
import traceback

def test_scrape():
    code = "005930"
    # Use news.naver (container)
    url = f"https://finance.naver.com/item/news.naver?code={code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Fetching {url}...")
    try:
        res = requests.get(url, headers=headers)
        print(f"Status: {res.status_code}")
        print(f"Encoding from header: {res.encoding}")
        
        # news.naver is likely EUC-KR
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # List all iframes
        iframes = soup.select('iframe')
        print(f"Total iframes found: {len(iframes)}")
        
        target_src = None
        for i, frame in enumerate(iframes):
            src = frame.get('src')
            title = frame.get('title')
            print(f"Iframe {i}: src={src}, title={title}")
            
            if title == '뉴스' or (src and 'news_news.naver' in src):
                target_src = src
        
            print(f"Target iframe src: {target_src}")
            news_url = f"https://finance.naver.com{target_src}"
            print(f"Fetching iframe: {news_url}")
            
            # Add Referer
            sub_headers = headers.copy()
            sub_headers['Referer'] = url
            
            # Try UTF-8 first (or both)
            try:
                 sub_soup = BeautifulSoup(sub_res.content.decode('utf-8', 'replace'), 'html.parser')
                 rows = sub_soup.select('table.type5 tbody tr')
                 print(f"News rows found (UTF-8): {len(rows)}")
                 if len(rows) > 0 and len(rows) < 2:
                      print(f"Row 0: {rows[0]}")
            except: pass
            
            # fallback to EUC-KR
            if len(rows) < 2:
                sub_soup = BeautifulSoup(sub_res.content.decode('euc-kr', 'replace'), 'html.parser')
                rows = sub_soup.select('table.type5 tbody tr')
                print(f"News rows found (EUC-KR): {len(rows)}")
            
            first_valid_row = None
            for tr in rows:
                title = tr.select_one('td.title a')
                if title:
                    print(f"News: {title.get_text(strip=True)}")
                    if not first_valid_row: first_valid_row = tr
            
            if not first_valid_row:
                 print("No valid news rows found.")
                 # Print first 500 chars of sub_res logic to see why
                 print(f"Sub page content preview: {sub_res.content.decode('euc-kr', 'replace')[:500]}")
        else:
            print("No suitable iframe found.")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_scrape()
