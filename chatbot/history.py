#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History Manager - 대화 히스토리 관리
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any


class HistoryManager:
    """대화 히스토리 관리 (최근 N개 유지)"""
    
    MAX_HISTORY = 10  # 최근 10개 대화만 유지
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.history_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, f'history_{user_id}.json')
        self._history = self._load()
    
    def _load(self) -> List[Dict[str, str]]:
        """파일에서 히스토리 로드"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save(self):
        """히스토리를 파일에 저장"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)
    
    def add(self, role: str, content: str):
        """대화 추가"""
        self._history.append({
            'role': role,
            'parts': [{'text': content}],
            'timestamp': datetime.now().isoformat()
        })
        
        # 최대 개수 유지
        if len(self._history) > self.MAX_HISTORY * 2:  # user + model 쌍
            self._history = self._history[-(self.MAX_HISTORY * 2):]
        
        self._save()
    
    def get_recent(self, n: int = None) -> List[Dict[str, Any]]:
        """최근 N개 대화 반환 (Gemini 형식)"""
        n = n or self.MAX_HISTORY
        recent = self._history[-(n * 2):]
        
        # Gemini 형식으로 변환 (timestamp 제거)
        return [{'role': h['role'], 'parts': h['parts']} for h in recent]
    
    def count(self) -> int:
        """히스토리 개수"""
        return len(self._history)
    
    def clear(self) -> str:
        """히스토리 초기화"""
        self._history = []
        self._save()
        return "✅ 대화 히스토리가 초기화되었습니다."
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 반환"""
        return {
            'user_id': self.user_id,
            'count': len(self._history),
            'max_history': self.MAX_HISTORY
        }
