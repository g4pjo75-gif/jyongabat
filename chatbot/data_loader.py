#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chatbot Data Loader - 챗봇에서 사용할 시장 데이터 로드
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


def fetch_all_data() -> Dict[str, Any]:
    """
    챗봇에서 사용할 전체 시장 데이터 로드
    
    Returns:
        Dict with keys: market, vcp_stocks, sector_scores
    """
    result = {
        "market": {},
        "vcp_stocks": [],
        "sector_scores": {}
    }
    
    # 1. 종가베팅 V2 시그널 데이터 로드
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    jongga_path = os.path.join(data_dir, 'jongga_v2_latest.json')
    
    if os.path.exists(jongga_path):
        try:
            with open(jongga_path, 'r', encoding='utf-8') as f:
                jongga_data = json.load(f)
            
            # VCP 종목 리스트로 변환
            signals = jongga_data.get('signals', [])
            for signal in signals:
                score = signal.get('score', {})
                if isinstance(score, dict):
                    total_score = score.get('total', 0)
                else:
                    total_score = score if isinstance(score, (int, float)) else 0
                
                result["vcp_stocks"].append({
                    "ticker": signal.get('stock_code', ''),
                    "name": signal.get('stock_name', ''),
                    "score": total_score,
                    "supply_demand_score": total_score,
                    "supply_demand_stage": signal.get('grade', ''),
                    "is_double_buy": False,  # 수급 데이터 없으면 False
                    "foreign_5d": 0,
                    "inst_5d": 0,
                    "foreign_trend": "N/A",
                    "inst_trend": "N/A",
                    "current_price": signal.get('current_price', 0),
                    "change_pct": signal.get('change_pct', 0),
                })
        except Exception as e:
            print(f"Error loading jongga data: {e}")
    
    # 2. Market Gate 데이터 로드 (실시간 조회)
    try:
        from market_gate import run_kr_market_gate
        gate_result = run_kr_market_gate()
        
        result["market"] = {
            "kospi": gate_result.get('kospi_close', 0),
            "kosdaq": gate_result.get('kosdaq_close', 0),
            "market_gate": gate_result.get('gate', 'NEUTRAL'),
            "usd_krw": 0  # 환율 데이터 필요 시 추가
        }
        
        # 섹터 점수
        for sector in gate_result.get('sectors', []):
            result["sector_scores"][sector.get('name', '')] = sector.get('score', 50)
            
    except Exception as e:
        print(f"Error loading market gate: {e}")
        result["market"] = {"market_gate": "NEUTRAL"}
    
    return result


def get_top_vcp_stocks(n: int = 10) -> List[Dict]:
    """
    상위 N개 VCP 종목 반환
    
    Args:
        n: 반환할 종목 수
    
    Returns:
        VCP 종목 리스트
    """
    data = fetch_all_data()
    stocks = data.get("vcp_stocks", [])
    
    # 점수 기준 정렬
    stocks.sort(key=lambda x: x.get('supply_demand_score', 0), reverse=True)
    
    return stocks[:n]


def search_stock(query: str) -> Optional[Dict]:
    """
    종목 검색
    
    Args:
        query: 종목명 또는 코드
    
    Returns:
        종목 정보 또는 None
    """
    data = fetch_all_data()
    stocks = data.get("vcp_stocks", [])
    
    query_lower = query.lower()
    
    for stock in stocks:
        name = stock.get('name', '').lower()
        ticker = stock.get('ticker', '').lower()
        
        if query_lower in name or query_lower in ticker:
            return stock
    
    return None


def get_market_summary() -> Dict[str, Any]:
    """
    시장 요약 정보 반환
    """
    data = fetch_all_data()
    market = data.get("market", {})
    vcp_stocks = data.get("vcp_stocks", [])
    
    return {
        "kospi": market.get("kospi", 0),
        "kosdaq": market.get("kosdaq", 0),
        "market_gate": market.get("market_gate", "NEUTRAL"),
        "total_vcp_stocks": len(vcp_stocks),
        "top_3": get_top_vcp_stocks(3),
        "updated_at": datetime.now().isoformat()
    }
