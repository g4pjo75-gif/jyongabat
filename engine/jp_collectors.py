"""
일본 시장 데이터 수집기 - yfinance 기반
JPX Nikkei 400 종목 대상
"""

import asyncio
import aiohttp
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import pandas as pd
import os
import re

from engine.jp_config import JPSignalConfig
from engine.models import StockData, ChartData, SupplyData, NewsItem
from engine.jp_stock_list import JPX_NIKKEI_400


class JPXCollector:
    """JPX(도쿄증권거래소) 데이터 수집기 (yfinance 기반)"""
    
    def __init__(self, config: JPSignalConfig = None):
        self.config = config or JPSignalConfig()
        self._session = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=600)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def get_top_gainers(self, sector: str = None, top_n: int = 30) -> List[StockData]:
        """상승률 상위 종목 조회 (yfinance Batch Download)"""
        try:
            import yfinance as yf
            
            result = []
            
            # 1. 대상 종목 선정
            if sector:
                stocks_to_check = [s for s in JPX_NIKKEI_400 if s[2] == sector]
            else:
                stocks_to_check = JPX_NIKKEI_400

            # 2. 티커 리스트 생성 (.T 제거된 코드를 키로 매핑)
            code_map = {s[0]: s for s in stocks_to_check}  # "6501.T": (ticker, name, sector)
            tickers = list(code_map.keys())
            
            # 3. yfinance 배치 다운로드 (청크 단위: 100개)
            # 400개 한 번에 하면 가끔 누락될 수 있어 청크 나눔
            chunk_size = 100
            for i in range(0, len(tickers), chunk_size):
                chunk = tickers[i:i+chunk_size]
                
                try:
                    # threads=True로 병렬 다운로드
                    df = yf.download(chunk, period="5d", progress=False, threads=True, group_by='ticker')
                    
                    if df.empty:
                        continue

                    # DataFrame 구조 처리
                    # MultiIndex인 경우와 SingleIndex인 경우 처리
                    is_multi = isinstance(df.columns, pd.MultiIndex)
                    
                    for ticker in chunk:
                        try:
                            # 데이터 추출
                            if is_multi:
                                try:
                                    hist = df[ticker].dropna()
                                except KeyError:
                                    continue
                            else:
                                if len(chunk) == 1:
                                    hist = df.dropna()
                                else:
                                    # should not happen with group_by='ticker' usually
                                    continue
                                    
                            if hist.empty or len(hist) < 2:
                                continue

                            # 종가, 전일종가, 거래량
                            # yfinance 최신 버전은 'Close', 'Volume' 등 대소문자 주의
                            # 보통 'Close', 'Volume'
                            close = float(hist['Close'].iloc[-1])
                            prev_close = float(hist['Close'].iloc[-2])
                            volume = int(hist['Volume'].iloc[-1])

                            if prev_close <= 0:
                                continue

                            change_pct = ((close - prev_close) / prev_close) * 100
                            trading_value = close * volume

                            # 필터링
                            if trading_value < self.config.min_trading_value:
                                continue
                            if change_pct < self.config.min_change_pct or change_pct > self.config.max_change_pct:
                                continue
                            
                            # 정보 매핑
                            origin_info = code_map.get(ticker)
                            if not origin_info:
                                continue
                                
                            _, name, sec = origin_info
                            
                            # 제외 키워드 체크
                            if any(kw in name for kw in self.config.exclude_keywords):
                                continue
                            
                            code = ticker.replace(".T", "")
                            
                            result.append(StockData(
                                code=code,
                                name=name,
                                market="TSE",
                                sector=sec,
                                close=close,
                                change_pct=round(change_pct, 2),
                                volume=volume,
                                trading_value=int(trading_value),
                                marcap=0,
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception as e:
                    print(f"Batch download error: {e}")
                    continue
            
            # 등락률 정렬
            result.sort(key=lambda x: x.change_pct, reverse=True)
            
            return result[:top_n]
            
        except Exception as e:
            print(f"[JPX] 상승률 조회 오류: {e}")
            return []
    
    async def get_stock_detail(self, code: str) -> Optional[StockData]:
        """종목 상세 정보 조회"""
        try:
            import yfinance as yf
            
            # 코드 변환 (6501 -> 6501.T)
            ticker = f"{code}.T" if not code.endswith(".T") else code
            
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            high_52w = float(hist['High'].max()) if not hist.empty else 0
            
            return StockData(
                code=code.replace(".T", ""),
                name=info.get('longName', info.get('shortName', code)),
                market="TSE",
                high_52w=high_52w
            )
        except Exception as e:
            print(f"[JPX] 상세 정보 조회 오류 ({code}): {e}")
            return None
    
    async def get_chart_data(self, code: str, days: int = 60) -> List[ChartData]:
        """차트 데이터 조회"""
        try:
            import yfinance as yf
            
            ticker = f"{code}.T" if not code.endswith(".T") else code
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            
            if hist.empty:
                return []
            
            result = []
            for idx, row in hist.tail(days).iterrows():
                result.append(ChartData(
                    date=idx.date() if hasattr(idx, 'date') else idx,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                ))
            
            return result
            
        except Exception as e:
            print(f"[JPX] 차트 데이터 조회 오류 ({code}): {e}")
            return []
    
    async def get_supply_data(self, code: str) -> Optional[SupplyData]:
        """수급 데이터 조회 (yfinance는 수급 미지원, 기본값 반환)"""
        return SupplyData(
            code=code,
            foreign_buy_5d=0,
            foreign_buy_20d=0,
            inst_buy_5d=0,
            inst_buy_20d=0,
        )


class YahooJapanNewsCollector:
    """Yahoo Finance Japan 뉴스 수집기"""
    
    MAJOR_SOURCES = {
        "日経": 0.95,
        "日本経済新聞": 0.95,
        "ロイター": 0.9,
        "Bloomberg": 0.9,
        "時事通信": 0.85,
        "共同通信": 0.85,
        "朝日新聞": 0.8,
        "読売新聞": 0.8,
        "毎日新聞": 0.8,
        "産経新聞": 0.8,
        "東洋経済": 0.85,
        "ダイヤモンド": 0.85,
    }
    
    def __init__(self, config: JPSignalConfig = None):
        self.config = config or JPSignalConfig()
        self._session = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=600)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def get_stock_news(self, code: str, limit: int = 5, stock_name: str = "") -> List[NewsItem]:
        """종목 관련 뉴스 수집 (Yahoo Finance Japan)
        
        Yahoo Finance Japan 뉴스 URL 패턴:
        https://finance.yahoo.co.jp/quote/{code}.T/news
        """
        try:
            from bs4 import BeautifulSoup
            
            # 코드 정리 (6501 -> 6501.T)
            ticker = code if code.endswith(".T") else f"{code}.T"
            
            # 뉴스 페이지 URL
            news_url = f"https://finance.yahoo.co.jp/quote/{ticker}/news"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
            
            news_list = []
            
            async with self._session.get(news_url, headers=headers) as response:
                if response.status != 200:
                    # 뉴스 페이지 접근 실패 시 헤드라인 뉴스로 폴백
                    return await self._get_headline_news(stock_name, limit)
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Yahoo Finance Japan 뉴스 리스트 파싱
                # 뉴스 아이템 선택자 (페이지 구조에 따라 조정 필요)
                news_items = soup.select('li[class*="NewsItem"]') or soup.select('article') or soup.select('div[class*="news"] a')
                
                for item in news_items[:limit * 2]:
                    try:
                        # 링크와 제목 추출
                        link_tag = item.find('a') if item.name != 'a' else item
                        if not link_tag:
                            continue
                        
                        title = link_tag.get_text(strip=True)
                        link = link_tag.get('href', '')
                        
                        if not title or len(title) < 5:
                            continue
                        
                        # URL 정규화
                        if link.startswith('/'):
                            link = f"https://finance.yahoo.co.jp{link}"
                        
                        # 소스 추정
                        source = "Yahoo Finance Japan"
                        reliability = 0.7
                        
                        for src, rel in self.MAJOR_SOURCES.items():
                            if src in title:
                                source = src
                                reliability = rel
                                break
                        
                        # 중복 체크
                        if any(n.title == title for n in news_list):
                            continue
                        
                        news_list.append(NewsItem(
                            title=title,
                            summary="",
                            source=source,
                            url=link,
                            reliability=reliability,
                        ))
                        
                        if len(news_list) >= limit:
                            break
                            
                    except Exception:
                        continue
            
            # 뉴스가 없으면 헤드라인으로 폴백
            if not news_list and stock_name:
                return await self._get_headline_news(stock_name, limit)
            
            return news_list
            
        except Exception as e:
            print(f"[JP News] 뉴스 수집 오류 ({code}): {e}")
            return []
    
    async def _get_headline_news(self, stock_name: str, limit: int = 5) -> List[NewsItem]:
        """헤드라인 뉴스에서 종목 관련 뉴스 검색"""
        try:
            from bs4 import BeautifulSoup
            
            # Yahoo Finance Japan 헤드라인
            headline_url = "https://finance.yahoo.co.jp/news/headline"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
            
            news_list = []
            
            async with self._session.get(headline_url, headers=headers) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 뉴스 링크 찾기
                links = soup.find_all('a', href=True)
                
                for link in links:
                    try:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if not title or len(title) < 10:
                            continue
                        
                        # 종목명이 포함된 뉴스 필터링
                        if stock_name and stock_name not in title:
                            continue
                        
                        if href.startswith('/'):
                            href = f"https://finance.yahoo.co.jp{href}"
                        
                        if '/news/' not in href:
                            continue
                        
                        news_list.append(NewsItem(
                            title=title,
                            summary="",
                            source="Yahoo Finance Japan",
                            url=href,
                            reliability=0.7,
                        ))
                        
                        if len(news_list) >= limit:
                            break
                            
                    except Exception:
                        continue
            
            return news_list
            
        except Exception as e:
            print(f"[JP News] 헤드라인 뉴스 수집 오류: {e}")
            return []
    
    async def get_news_content(self, url: str) -> str:
        """뉴스 본문 크롤링"""
        try:
            from bs4 import BeautifulSoup
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    return ""
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Yahoo Finance Japan 뉴스 본문
                content_div = soup.select_one('div[class*="article"]') or soup.select_one('article')
                if content_div:
                    return content_div.get_text(strip=True)[:500]
                
                return ""
                
        except Exception as e:
            return ""


# 테스트용 함수
async def test_jpx_collector():
    """JPX Collector 테스트"""
    async with JPXCollector() as collector:
        print("\n[1] Top Gainers...")
        stocks = await collector.get_top_gainers(top_n=5)
        for stock in stocks:
            print(f"  {stock.code} {stock.name}: {stock.change_pct:+.2f}%")
        
        # Specific Stock Details
        print("\n[2] Stock Details (6501 Hitachi)...")
        detail = await collector.get_stock_detail("6501")
        if detail:
            print(f"  {detail.name}, 52w High: {detail.high_52w:,.0f} Yen")
        
        # Chart Data
        print("\n[3] Chart Data...")
        charts = await collector.get_chart_data("6501", days=5)
        for c in charts:
            print(f"  {c.date}: Open {c.open:,.0f} / Close {c.close:,.0f}")
    
    print("\n=== News Collection Test ===")
    async with YahooJapanNewsCollector() as news_collector:
        news = await news_collector.get_stock_news("6501", limit=3, stock_name="日立")
        for n in news:
            print(f"  [{n.source}] {n.title[:50]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_jpx_collector())
