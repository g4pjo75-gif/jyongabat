# app/routes/common.py
"""공통 API 라우트"""

import os
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text
from app.database import db

common_bp = Blueprint('common', __name__)

@common_bp.route('/db-check')
def db_check():
    """데이터베이스 연결 상태 확인"""
    status = {
        "connected": False,
        "db_url": "Unknown",
        "error": None
    }
    
    try:
        # DB URL 마스킹
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        token_env = os.environ.get('TURSO_AUTH_TOKEN')
        status['token_present'] = bool(token_env)
        status['token_length'] = len(token_env) if token_env else 0
        
        if '@' in db_uri:
            # Mask password/token if present
            prefix = db_uri.split('@')[0]
            # Show scheme
            scheme = db_uri.split('://')[0]
            host = db_uri.split('@')[1].split('?')[0] if '@' in db_uri else 'hidden'
            status['db_url'] = f"{scheme}://***@{host}"
        else:
            status['db_url'] = db_uri
            
        # 연결 테스트
        with db.session.begin():
            db.session.execute(text('SELECT 1'))
        
        status["connected"] = True
        status["message"] = "Database connection successful"
        
    except Exception as e:
        status["error"] = str(e)
        status["message"] = "Database connection failed"
        
    return jsonify(status)


@common_bp.route('/portfolio')
def get_portfolio_data():
    """포트폴리오 데이터"""
    try:
        # 종가베팅 최신 데이터에서 포트폴리오 구성
        json_path = os.path.join('data', 'jongga_v2_latest.json')
        
        if not os.path.exists(json_path):
            return jsonify({
                'key_stats': {},
                'holdings_distribution': [],
                'top_holdings': [],
            })
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = data.get('signals', [])
        
        # 상위 종목
        top_holdings = []
        for s in signals[:10]:
            top_holdings.append({
                'ticker': s.get('stock_code', ''),
                'name': s.get('stock_name', ''),
                'price': s.get('current_price', 0),
                'score': s.get('score', {}).get('total', 0) if isinstance(s.get('score'), dict) else 0,
                'grade': s.get('grade', ''),
                'change_pct': s.get('change_pct', 0),
            })
        
        # 통계
        key_stats = {
            'total_signals': len(signals),
            'avg_score': sum(
                s.get('score', {}).get('total', 0) if isinstance(s.get('score'), dict) else 0 
                for s in signals
            ) / len(signals) if signals else 0,
        }
        
        # 시장별 분포
        by_market = data.get('by_market', {})
        holdings_distribution = [
            {'label': market, 'value': count, 'color': '#3b82f6' if market == 'KOSPI' else '#10b981'}
            for market, count in by_market.items()
        ]
        
        return jsonify({
            'key_stats': key_stats,
            'holdings_distribution': holdings_distribution,
            'top_holdings': top_holdings,
            'latest_date': data.get('date', ''),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/system/data-status')
def get_data_status():
    """데이터 파일 상태 조회"""
    data_files = [
        {'name': 'Jongga V2 Latest', 'path': 'data/jongga_v2_latest.json'},
    ]
    
    files_status = []
    for file_info in data_files:
        path = file_info['path']
        exists = os.path.exists(path)
        
        if exists:
            stat = os.stat(path)
            size_bytes = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            elif size_bytes > 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes} B"
            
            row_count = None
            if path.endswith('.json'):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if 'signals' in data:
                        row_count = len(data['signals'])
                except:
                    pass
            
            files_status.append({
                'name': file_info['name'],
                'path': path,
                'exists': True,
                'lastModified': mtime.isoformat(),
                'size': size_str,
                'rowCount': row_count,
            })
        else:
            files_status.append({
                'name': file_info['name'],
                'path': path,
                'exists': False,
            })
    
    return jsonify({
        'files': files_status,
    })
