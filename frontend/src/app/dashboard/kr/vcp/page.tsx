'use client';

import { useEffect, useState } from 'react';
import { krAPI } from '@/lib/api';
import GuideModal from '@/components/GuideModal';

interface KRSignal {
    ticker: string;
    name: string;
    score?: number | { total?: number };
    contraction_ratio?: number;
    foreign_5d?: number;
    inst_5d?: number;
    entry_price?: number;
    current_price?: number;
    return_pct?: number;
    gemini_recommendation?: { action: string; reason: string };
}

// score값 추출 헬퍼 함수
const getScoreValue = (score: number | { total?: number } | undefined): number => {
    if (score === undefined || score === null) return 0;
    if (typeof score === 'number') return score;
    if (typeof score === 'object' && 'total' in score) return score.total || 0;
    return 0;
};


export default function VCPSignalsPage() {
    const [signals, setSignals] = useState<KRSignal[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [showGuide, setShowGuide] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<string>('');
    const [signalDate, setSignalDate] = useState<string>('');
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');

    useEffect(() => {
        loadSignals();
        loadAvailableDates();
    }, []);

    const loadAvailableDates = async () => {
        try {
            const dates = await krAPI.getVCPDates();
            setAvailableDates(dates);
        } catch (error) {
            console.error('Failed to load VCP dates:', error);
        }
    };

    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                const vcpRes = await fetch('/api/kr/vcp/latest').then(r => r.json());
                setSignals(vcpRes.signals || []);
            } else {
                const vcpRes = await krAPI.getVCPHistory(dateStr) as unknown as {signals?: KRSignal[]};
                const rawSignals = vcpRes.signals || [];
                // 과거 데이터 로드 시, 당시의 current_price를 entry_price(포착가)로 설정
                setSignals(rawSignals.map(s => ({
                    ...s,
                    entry_price: s.current_price,  // 당시 가격을 포착가로 보존
                    return_pct: 0 // 초기 수익률 0
                })));
            }
        } catch (error) {
            console.error('Failed to load VCP history:', error);
            alert('해당 날짜의 데이터를 불러올 수 없습니다.');
        } finally {
            setLoading(false);
        }
    };

    // Real-time price updates (every 60s)
    // Real-time price updates
    useEffect(() => {
        if (loading || signals.length === 0) return;

        const updatePrices = async () => {
            try {
                const tickers = signals.map(s => s.ticker);
                if (tickers.length === 0) return;

                const res = await fetch('/api/kr/realtime-prices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tickers })
                });
                const prices = await res.json();

                if (Object.keys(prices).length > 0) {
                    setSignals(prev => prev.map(s => {
                        if (prices[s.ticker]) {
                            const current = prices[s.ticker];
                            // entry_price가 없으면 기존(로딩시) current_price를 사용
                            const entry = s.entry_price || s.current_price || 0;
                            let ret = 0;
                            if (entry > 0) {
                                ret = ((current - entry) / entry) * 100;
                            }
                            return { ...s, current_price: current, return_pct: ret, entry_price: entry };
                        }
                        return s;
                    }));
                    setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
                }
            } catch (e) {
                console.error('Price update failed:', e);
            }
        };

        // 초기 로딩 후 즉시 실행
        updatePrices();

        // 이후 60초마다 갱신
        const interval = setInterval(updatePrices, 60000);
        return () => clearInterval(interval);
    }, [signals.length]); // signals.length가 변할 때(로딩 완료 시) 실행

    const loadSignals = async () => {
        setLoading(true);
        try {
            const [vcpRes] = await Promise.all([
                fetch('/api/kr/vcp/latest').then(r => r.json()),
            ]);
            const rawSignals = vcpRes.signals || [];
            // 최신 데이터 로드 시에도 현재가를 포착가로 설정 (기준점 마련)
            setSignals(rawSignals.map((s: KRSignal) => ({
                ...s,
                entry_price: s.current_price
            })));
            
            const genAt = vcpRes.updated_at;
            if (genAt) {
                const d = new Date(genAt);
                setSignalDate(d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
            }
            setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
        } catch (error) {
            console.error('Failed to load signals:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRunScreener = async () => {
        if (running) return;
        setRunning(true);
        try {
            const res = await fetch('/api/kr/vcp/run', { method: 'POST' });
            if (res.status === 202 || res.status === 200) {
                // Polling start
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await fetch('/api/kr/screener/status');
                        const status = await statusRes.json();
                        
                        if (!status.isRunning) {
                            clearInterval(pollInterval);
                            setRunning(false);
                            alert(status.message || '스크리닝 완료');
                            await loadSignals();
                        }
                    } catch (e) {
                        console.error('Polling error:', e);
                        clearInterval(pollInterval);
                        setRunning(false);
                    }
                }, 3000);
            } else {
                throw new Error('API error');
            }
        } catch (e: any) {
            console.error('Screening error:', e);
            alert(`스크리닝 실행 중 오류가 발생했습니다: ${e.message || 'Unknown error'}`);
            setRunning(false);
        }
    };

    // 수급 데이터를 억/만 단위로 포맷
    const formatFlow = (value: number | undefined) => {
        if (value === undefined || value === null) return '-';
        const absValue = Math.abs(value);
        if (absValue >= 100000000) {
            return `${(value / 100000000).toFixed(1)}억`;
        } else if (absValue >= 10000) {
            return `${(value / 10000).toFixed(0)}만`;
        }
        return value.toLocaleString();
    };


    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center">
                <div className="text-2xl text-[var(--text-secondary)]">Loading VCP Signals...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--bg-page)] p-8">
            {/* Navigation */}
            <nav className="flex items-center gap-4 text-sm mb-6">
                <a href="/dashboard/kr" className="text-gray-400 hover:text-white transition-colors">
                    ← Overview
                </a>
                <span className="text-gray-600">|</span>
                <a href="/dashboard/kr/closing-bet" className="text-gray-400 hover:text-white transition-colors">
                    종가베팅
                </a>
                <span className="text-gray-600">|</span>
                <span className="text-rose-400 font-medium">VCP 시그널</span>
            </nav>

            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-rose-500/20 bg-rose-500/5 text-xs text-rose-400 font-medium mb-4">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
                        Volatility Contraction Pattern
                    </div>
                    <h2 className="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
                        VCP <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-amber-400">Signals</span>
                    </h2>
                    <p className="text-gray-400 text-lg">Mark Minervini 스타일 VCP 패턴 + 외국인/기관 수급 분석</p>
                </div>
                
                <button
                    onClick={() => setShowGuide(true)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:border-blue-500/50 rounded-lg transition-all"
                >
                    <span>📘</span>
                    <span>사용 가이드</span>
                </button>
            </header>

            {/* Stats */}
            <div className="grid grid-cols-5 gap-4 mb-8">
                {/* 날짜 선택 드롭다운 */}
                <div className="glass-card p-4">
                    <div className="text-xs text-gray-500 mb-2">날짜 선택</div>
                    <select
                        value={selectedDate}
                        onChange={(e) => handleDateChange(e.target.value)}
                        className="w-full bg-[var(--bg-elevated)] border border-white/10 rounded-lg px-3 py-2 text-white text-sm cursor-pointer"
                    >
                        <option value="" className="bg-[var(--bg-elevated)] text-white">최신 결과 (Latest)</option>
                        {availableDates.map(date => (
                            <option key={date} value={date} className="bg-[var(--bg-elevated)] text-white">{date}</option>
                        ))}
                    </select>
                </div>
                <div className="glass-card p-4 text-center">
                    <div className="text-3xl font-bold text-rose-400">{signals.length}</div>
                    <div className="text-xs text-gray-500 mt-1">Active Signals</div>
                </div>
                <div className="glass-card p-4 text-center">
                    <div className="text-3xl font-bold text-amber-400">{signalDate || '-'}</div>
                    <div className="text-xs text-gray-500 mt-1">Signal Date</div>
                </div>
                <div className="glass-card p-4 text-center">
                    <div className="text-3xl font-bold text-emerald-400">{lastUpdated || '-'}</div>
                    <div className="text-xs text-gray-500 mt-1">Last Updated</div>
                </div>
                <button
                    disabled={running || selectedDate !== ''}
                    onClick={handleRunScreener}
                    className={`glass-card p-4 text-center transition-all cursor-pointer ${
                        running || selectedDate !== '' ? 'bg-white/10 opacity-50' : 'hover:bg-white/5'
                    }`}
                    title={selectedDate !== '' ? '최신 결과를 선택해야 스크리너 실행 가능' : ''}
                >
                    {running ? (
                        <div className="w-6 h-6 border-2 border-rose-500/30 border-t-rose-500 rounded-full animate-spin mx-auto mb-1"></div>
                    ) : (
                        <div className="text-2xl mb-1">🔄</div>
                    )}
                    <div className="text-xs text-gray-500">{running ? 'Running...' : 'Run Screener'}</div>
                </button>
            </div>

            {/* Signals Table */}
            <div className="glass-card overflow-hidden">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>종목</th>
                            <th>VCP 점수</th>
                            <th>수축비율</th>
                            <th>외인 5일</th>
                            <th>기관 5일</th>
                            <th>포착가(Date)</th>
                            <th>현재가(Real)</th>
                            <th>수익률</th>
                        </tr>
                    </thead>
                    <tbody>
                        {signals.length === 0 ? (
                            <tr>
                                <td colSpan={8} className="text-center py-12 text-gray-500">
                                    <div className="text-4xl mb-4">📭</div>
                                    <div>VCP 시그널이 없습니다</div>
                                </td>
                            </tr>
                        ) : (
                            signals.map((signal, idx) => (
                                <tr key={`${signal.ticker || 'sig'}-${idx}`} className="hover:bg-white/5">
                                    <td>
                                        <div className="font-bold text-white">{signal.name}</div>
                                        <div className="text-xs text-gray-500 font-mono">{signal.ticker}</div>
                                    </td>
                                    <td>
                                        <span className={`font-bold ${getScoreValue(signal.score) >= 70 ? 'text-emerald-400' : getScoreValue(signal.score) >= 50 ? 'text-amber-400' : 'text-gray-400'}`}>
                                            {getScoreValue(signal.score) > 0 ? getScoreValue(signal.score).toFixed(1) : '-'}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-rose-500 to-amber-500 rounded-full"
                                                    style={{ width: `${(signal.contraction_ratio || 0) * 100}%` }}
                                                ></div>
                                            </div>
                                            <span className="text-xs text-gray-400">{((signal.contraction_ratio || 0) * 100).toFixed(0)}%</span>
                                        </div>
                                    </td>
                                    <td className={`font-mono ${(signal.foreign_5d || 0) >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                                        {formatFlow(signal.foreign_5d)}
                                    </td>
                                    <td className={`font-mono ${(signal.inst_5d || 0) >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                                        {formatFlow(signal.inst_5d)}
                                    </td>
                                    <td className="font-mono">{signal.entry_price?.toLocaleString() || '-'}</td>
                                    <td className="font-mono font-bold">{signal.current_price?.toLocaleString() || '-'}</td>
                                    <td className={`font-mono font-bold ${(signal.return_pct || 0) >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                                        {(signal.return_pct || 0) >= 0 ? '+' : ''}{(signal.return_pct || 0).toFixed(2)}%
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Legend */}
            <div className="mt-6 flex items-center gap-6 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-red-400"></span>
                    상승/순매수
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                    하락/순매도
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    VCP 70+
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    VCP 50-70
                </span>
            </div>

            <GuideModal
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
                title="VCP 스크리너 사용 가이드"
                sections={[
                    {
                        title: "🔍 분석 로직 (Analysis Logic)",
                        content: (
                            <div className="space-y-2 text-sm">
                                <p><strong>종합 점수 (Total Score)</strong>는 아래 두 가지 요소를 가중 합산하여 산출됩니다 (100점 만점).</p>
                                <ul className="list-disc list-inside space-y-1 ml-2 text-gray-300">
                                    <li><strong>수급 점수 (Supply Score, 70%)</strong>: 최근 5일간 외국인/기관의 순매수 강도</li>
                                    <li><strong>VCP 점수 (Pattern Score, 30%)</strong>: 변동성 수축 강도 및 기술적 패턴</li>
                                </ul>
                            </div>
                        )
                    },
                    {
                        title: "📊 세부 채점 기준 (Scoring Criteria)",
                        content: (
                            <div className="space-y-4 text-sm">
                                <div>
                                    <div className="font-bold text-amber-400 mb-1">1. VCP 수축 비율 (Contraction Ratio)</div>
                                    <p className="text-xs text-gray-400 mb-1">계산식: (최근 20일 고저폭 ÷ 이전 20일 고저폭)</p>
                                    <ul className="list-disc list-inside space-y-1 ml-2 text-gray-300">
                                        <li><strong>0.4 이하</strong> (매우 강한 수축): <span className="text-emerald-400">100점</span></li>
                                        <li><strong>0.6 이하</strong> (강한 수축): <span className="text-emerald-400">80점</span></li>
                                        <li><strong>0.8 이하</strong> (보통): 50점</li>
                                        <li><strong>0.8 초과</strong> (수축 미흡): 20점</li>
                                    </ul>
                                </div>
                                <div>
                                    <div className="font-bold text-red-400 mb-1">2. 수급 점수 (Supply Score)</div>
                                    <p className="text-xs text-gray-400 mb-1">최근 5일 누적 순매수 기준 (1억원당 약 1점 가산)</p>
                                    <ul className="list-disc list-inside space-y-1 ml-2 text-gray-300">
                                        <li>외국인/기관 <strong>양매수(Double Buy)</strong> 시 높은 점수</li>
                                        <li>순매도 발생 시 감점 처리</li>
                                        <li>기본 50점(중립)에서 시작하여 최대 100점, 최소 0점</li>
                                    </ul>
                                </div>
                            </div>
                        )
                    },
                    {
                        title: "🏅 등급 가이드 (Grade Guide)",
                        content: (
                            <div className="space-y-2 text-sm">
                                <ul className="list-disc list-inside space-y-2">
                                    <li>
                                        <span className="text-emerald-400 font-bold">A등급 (70점↑)</span>: 
                                        <span className="text-gray-300"> 강력한 수급 유입 + 완벽한 수축 패턴. (즉시 관심)</span>
                                    </li>
                                    <li>
                                        <span className="text-amber-400 font-bold">B등급 (60점↑)</span>: 
                                        <span className="text-gray-300"> 수급은 양호하나 패턴이 완성 단계임. (타이밍 관찰)</span>
                                    </li>
                                    <li>
                                        <span className="text-gray-500 font-bold">C등급 (60점↓)</span>: 
                                        <span className="text-gray-300"> 수급이 부족하거나 변동성이 여전히 큼.</span>
                                    </li>
                                </ul>
                            </div>
                        )
                    }
                ]}
            />
        </div>
    );
}
