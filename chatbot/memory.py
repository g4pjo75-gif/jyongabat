#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager - 사용자별 장기 메모리 관리
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional


class MemoryManager:
    """사용자별 장기 메모리 관리"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_file = os.path.join(self.memory_dir, f'memory_{user_id}.json')
        self._memory = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """파일에서 메모리 로드"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save(self):
        """메모리를 파일에 저장"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self._memory, f, ensure_ascii=False, indent=2)
    
    def add(self, key: str, value: str) -> str:
        """메모리 추가"""
        self._memory[key] = {
            'value': value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self._save()
        return f"✅ 메모리 저장: {key} = {value}"
    
    def update(self, key: str, value: str) -> str:
        """메모리 업데이트"""
        if key not in self._memory:
            return self.add(key, value)
        
        self._memory[key]['value'] = value
        self._memory[key]['updated_at'] = datetime.now().isoformat()
        self._save()
        return f"✅ 메모리 업데이트: {key} = {value}"
    
    def remove(self, key: str) -> str:
        """메모리 삭제"""
        if key in self._memory:
            del self._memory[key]
            self._save()
            return f"✅ 메모리 삭제: {key}"
        return f"❌ 존재하지 않는 키: {key}"
    
    def get(self, key: str) -> Optional[str]:
        """메모리 조회"""
        if key in self._memory:
            return self._memory[key]['value']
        return None
    
    def view(self) -> Dict[str, Any]:
        """전체 메모리 조회"""
        return self._memory
    
    def clear(self) -> str:
        """전체 메모리 삭제"""
        self._memory = {}
        self._save()
        return "✅ 모든 메모리가 삭제되었습니다."
    
    def format_for_prompt(self) -> str:
        """프롬프트용 포맷팅"""
        if not self._memory:
            return ""
        
        text = "## 사용자 정보 (장기 메모리)\n"
        for key, data in self._memory.items():
            text += f"- **{key}**: {data['value']}\n"
        return text
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 반환"""
        return {
            'user_id': self.user_id,
            'items': self._memory,
            'count': len(self._memory)
        }
