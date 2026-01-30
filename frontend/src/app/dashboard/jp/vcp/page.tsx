'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { jpAPI, JPVCPResult } from '@/lib/api';
import GuideModal from '@/components/GuideModal';
import JPChartModal from '@/components/JPChartModal';

export default function JPVCPSignalsPage() {
    const [signals, setSignals] = useState<JPVCPResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [showGuide, setShowGuide] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<string>('');
    const [signalDate, setSignalDate] = useState<string>('');
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [chartModal, setChartModal] = useState<{isOpen: boolean; symbol: string; name: string}>({
        isOpen: false, symbol: '', name: ''
    });

    useEffect(() => {
        loadSignals();
        loadAvailableDates();
    }, []);

    const loadAvailableDates = async () => {
        try {
            const dates = await jpAPI.getVCPDates();
            setAvailableDates(dates);
        } catch (error) {
            console.error('Failed to load JP VCP dates:', error);
        }
    };

    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                await loadSignals();
            } else {
                const res = await jpAPI.getVCPHistory(dateStr);
                const rawSignals = res.signals || [];
                // 과거 데이터 로드 시, 당시의 current_price를 entry_price로 설정
                setSignals(rawSignals.map(s => ({
                    ...s,
                    entry_price: s.current_price,
                    return_pct: 0
                })));
                setSignalDate(dateStr);
            }
        } catch (error) {
            console.error('Failed to load JP VCP history:', error);
            alert('해당 날짜의 데이터를 불러올 수 없습니다.');
        } finally {
            setLoading(false);
        }
    };

    const loadSignals = async () => {
        setLoading(true);
        try {
            const res = await jpAPI.getVCPLatest();
            const rawSignals = res.signals || [];
            
            // 포착가 설정
            setSignals(rawSignals.map(s => ({
                ...s,
                entry_price: s.current_price,
                return_pct: 0
            })));
            
            if (res.generated_at) {
                const d = new Date(res.generated_at);
                setSignalDate(d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
                setLastUpdated(d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
            }
        } catch (error) {
            console.error('Failed to load JP VCP signals:', error);
        } finally {
            setLoading(false);
        }
    };

    // Real-time price updates
    useEffect(() => {
        if (loading || signals.length === 0) return;

        const updatePrices = async () => {
            try {
                const tickers = signals.map(s => s.code);
                if (tickers.length === 0) return;

                const res = await fetch('/api/jp/realtime-prices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tickers })
                });
                const prices = await res.json();

                if (Object.keys(prices).length > 0) {
                    setSignals(prev => prev.map(s => {
                        if (prices[s.code]) {
                            const current = prices[s.code];
                            const entry = s.entry_price || s.current_price || 0;
                            let ret = 0;
                            if (entry > 0) {
                                ret = ((current - entry) / entry) * 100;
                            }
                            return { ...s, current_price: current, return_pct: ret };
                        }
                        return s;
                    }));
                    setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
                }
            } catch (e) {
                console.error('Price update failed:', e);
            }
        };

        updatePrices();
        const interval = setInterval(updatePrices, 60000);
        return () => clearInterval(interval);
    }, [signals, loading]);

    const handleRunScreener = async () => {
        if (running) return;
        setRunning(true);
        try {
            await jpAPI.runVCPScreener();
            
            const pollInterval = setInterval(async () => {
                try {
                    const status = await jpAPI.getScreenerStatus();
                    if (!status.isRunning) {
                        clearInterval(pollInterval);
                        setRunning(false);
                        alert(status.message || 'JP VCP 스캔 완료');
                        await loadSignals();
                    }
                } catch (e) {
                    console.error('Polling error:', e);
                    clearInterval(pollInterval);
                    setRunning(false);
                }
            }, 3000);
        } catch (error) {
            console.error('Screening error:', error);
            alert('스크리너 실행 중 오류가 발생했습니다.');
            setRunning(false);
        }
    };

    const formatFlow = (value: number | undefined) => {
        if (value === undefined || value === null || value === 0) return '-';
        return value.toLocaleString();
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center">
                <div className="text-2xl text-[var(--text-secondary)]">Loading JP VCP Signals...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--bg-page)] p-8">
            {/* Navigation */}
            <nav className="flex items-center gap-4 text-sm mb-6">
                <Link href="/dashboard/jp" className="text-gray-400 hover:text-white transition-colors">
                    ← Overview
                </Link>
                <span className="text-gray-600">|</span>
                <Link href="/dashboard/jp/n225" className="text-gray-400 hover:text-white transition-colors">
                    Nikkei 225
                </Link>
                <span className="text-gray-600">|</span>
                <span className="text-rose-400 font-medium">VCP 시그널</span>
            </nav>

            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-rose-500/20 bg-rose-500/5 text-xs text-rose-400 font-medium mb-4">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
                        Japan Market Volatility Contraction
                    </div>
                    <h2 className="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
                        VCP <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-amber-400">Signals</span>
                    </h2>
                    <p className="text-gray-400 text-lg">니케이 225/400 상위 종목 대상 VCP + 수급 분석</p>
                </div>
                
                <button
                    onClick={() => setShowGuide(true)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:border-rose-500/50 rounded-lg transition-all"
                >
                    <span>📘</span>
                    <span>사용 가이드</span>
                </button>
            </header>

            {/* Stats */}
            <div className="grid grid-cols-5 gap-4 mb-8">
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
                            <th>포착가</th>
                            <th>현재가</th>
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
                                <tr key={`${signal.code}-${idx}`} className="hover:bg-white/5">
                                    <td 
                                        className="cursor-pointer hover:bg-white/10 transition-colors"
                                        onClick={() => setChartModal({
                                            isOpen: true,
                                            symbol: signal.code,
                                            name: signal.name
                                        })}
                                    >
                                        <div className="font-bold text-white flex items-center gap-2">
                                            {signal.name}
                                            <span className="text-[10px] text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity">📈</span>
                                        </div>
                                        <div className="text-xs text-gray-500 font-mono">{signal.code} | {signal.sector}</div>
                                    </td>
                                    <td>
                                        <span className={`font-bold ${signal.vcp_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                            {signal.vcp_score?.toFixed(1)}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-rose-500 to-amber-500 rounded-full"
                                                    style={{ width: `${Math.min(100, (signal.contraction_ratio || 0) * 100)}%` }}
                                                ></div>
                                            </div>
                                            <span className="text-xs text-gray-400">{((signal.contraction_ratio || 0) * 100).toFixed(0)}%</span>
                                        </div>
                                    </td>
                                    <td className={`font-mono ${signal.foreign_5d > 0 ? 'text-red-400' : signal.foreign_5d < 0 ? 'text-blue-400' : 'text-gray-500'}`}>
                                        {formatFlow(signal.foreign_5d)}
                                    </td>
                                    <td className={`font-mono ${signal.inst_5d > 0 ? 'text-red-400' : signal.inst_5d < 0 ? 'text-blue-400' : 'text-gray-500'}`}>
                                        {formatFlow(signal.inst_5d)}
                                    </td>
                                    <td className="font-mono text-gray-400">
                                        {signal.entry_price?.toLocaleString()}
                                    </td>
                                    <td className="font-mono font-bold text-white">
                                        {signal.current_price?.toLocaleString()}
                                    </td>
                                    <td className={`font-mono font-bold ${ (signal.return_pct || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
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
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    Excellent (80+)
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    Good (60-80)
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-red-400"></span>
                    수급 유입 (Buy)
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                    수급 이탈 (Sell)
                </span>
            </div>

            {/* Chart Modal */}
            {chartModal.isOpen && (
                <JPChartModal 
                    symbol={chartModal.symbol} 
                    name={chartModal.name}
                    onClose={() => setChartModal({isOpen: false, symbol: '', name: ''})}
                />
            )}

            <GuideModal
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
                title="JP VCP 시그널 가이드"
                sections={[
                    {
                        title: "🎯 분석 대상",
                        content: (
                            <p className="text-sm text-slate-300">
                                니케이 225 및 니케이 400 &apos;종가베팅 스크리너&apos;에서 이미 기술적 우위가 확인된 **상위 60개 종목**을 분석 대상으로 합니다.
                            </p>
                        )
                    },
                    {
                        title: "📐 VCP 수축 점수 (50%)",
                        content: (
                            <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                                <li><strong>수축 비율</strong>: 최근 변동성이 이전보다 얼마나 줄어들었는지를 측정합니다.</li>
                                <li>비율이 0.8 이하일 때 &apos;에너지가 응축됨&apos;으로 간주하며 점수가 높아집니다.</li>
                            </ul>
                        )
                    },
                    {
                        title: "💰 수급 점수 (50%)",
                        content: (
                            <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                                <li>외국인 및 기관의 대량 매수 흐름을 추적합니다. (현재 보강 중)</li>
                                <li>거래량 폭증과 가격 지지선을 결합하여 수급의 질을 평가합니다.</li>
                            </ul>
                        )
                    },
                    {
                        title: "🏆 등급 기준",
                        content: (
                            <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                                <li><strong>S급 (80점↑)</strong>: 변동성이 극도로 수축되어 곧 분출이 예상되는 종목</li>
                                <li><strong>A급 (70점↑)</strong>: 수급과 차트 패턴이 매우 조화로운 상태</li>
                                <li><strong>B급 (60점↑)</strong>: 관심 종목으로 등록하고 관찰할 가치가 있는 종목</li>
                            </ul>
                        )
                    }
                ]}
            />
        </div>
    );
}
