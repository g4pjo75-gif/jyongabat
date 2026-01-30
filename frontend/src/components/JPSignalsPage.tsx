'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { jpAPI, JPSignal, JPSignalsResponse } from '@/lib/api';
import GuideModal from '@/components/GuideModal';
import JPChartModal from '@/components/JPChartModal';

interface JPSignalsPageProps {
    type: 'n225' | 'n400';
    title: string;
    description: string;
}

export default function JPSignalsPage({ type, title, description }: JPSignalsPageProps) {
    const [data, setData] = useState<JPSignalsResponse | null>(null);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [selectedGrade, setSelectedGrade] = useState<string | null>(null);
    const [chartModal, setChartModal] = useState<{isOpen: boolean; symbol: string; name: string}>({
        isOpen: false, symbol: '', name: ''
    });
    const [showGuide, setShowGuide] = useState(false);

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const [latestData, dates] = await Promise.all([
                    jpAPI.getJonggaLatest(type),
                    jpAPI.getJonggaDates(type),
                ]);
                setData(latestData);
                setAvailableDates(dates);
            } catch (error) {
                console.error('Error fetching data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchInitialData();
    }, [type]);

    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                const latestData = await jpAPI.getJonggaLatest(type);
                setData(latestData);
            } else {
                const historyData = await jpAPI.getJonggaHistory(dateStr, type);
                setData(historyData);
            }
        } catch {
            console.error('Date change error');
        } finally {
            setLoading(false);
        }
    };
    const handleRunScreener = async () => {
        if (running) return;
        setRunning(true);
        try {
            await jpAPI.runScreener(type); // Runs specific type in backend
            
            // Polling
            const pollInterval = setInterval(async () => {
                try {
                    const status = await jpAPI.getScreenerStatus();
                    
                    if (!status.isRunning) {
                        clearInterval(pollInterval);
                        setRunning(false);
                        alert(`스크리닝 완료! ${status.message}`);
                        // Refresh data for current type
                        const latestData = await jpAPI.getJonggaLatest(type);
                        setData(latestData);
                    }
                } catch (e) {
                    console.error('Polling error:', e);
                    clearInterval(pollInterval);
                    setRunning(false);
                }
            }, 3000);
        } catch {
            alert('스크리닝 실행 중 오류가 발생했습니다.');
            setRunning(false);
        }
    };

    // Real-time price polling
    useEffect(() => {
        if (loading || !data?.signals || data.signals.length === 0) return;

        const updatePrices = async () => {
            try {
                const tickers = data.signals.map(s => s.code);
                if (tickers.length === 0) return;

                const prices = await jpAPI.getRealtimePrices(tickers);

                if (Object.keys(prices).length > 0) {
                    setData(prev => {
                        if (!prev) return null;
                        return {
                            ...prev,
                            signals: prev.signals.map(s => {
                                if (prices[s.code]) {
                                    const current = prices[s.code];
                                    return { 
                                        ...s, 
                                        close: current,
                                    };
                                }
                                return s;
                            })
                        };
                    });
                }
            } catch (e) {
                console.error('Price update failed:', e);
            }
        };

        const interval = setInterval(updatePrices, 60000);
        updatePrices();
        return () => clearInterval(interval);
    }, [data?.generated_at, loading, type, data?.signals]);

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center">
                <div className="text-2xl text-[var(--text-secondary)]">Loading {title}...</div>
            </div>
        );
    }

    const displayedSignals = (data?.signals || []).slice(0, 30); // Ensure Limit 30

    return (
        <div className="min-h-screen bg-[var(--bg-page)] p-8">
            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="flex items-center gap-4 mb-2">
                        <Link href="/dashboard/jp" className="text-[var(--text-secondary)] hover:text-white">
                            ← Back
                        </Link>
                        <h1 className="text-3xl font-bold">{title}</h1>
                    </div>
                    <p className="text-[var(--text-secondary)]">
                        {description} | Top 30 Selected
                    </p>
                </div>
                
                <div className="flex gap-4">
                    <Link
                        href={`/dashboard/jp/performance?type=${type}`}
                        className="flex items-center gap-2 px-4 py-2.5 bg-blue-600/20 border border-blue-500/30 text-blue-400 hover:text-white hover:border-blue-500/50 rounded-lg transition-all"
                    >
                        <span>📉</span>
                        <span className="text-xs font-bold uppercase">View Performance</span>
                    </Link>
                    <button
                        onClick={() => setShowGuide(true)}
                        className="flex items-center gap-2 px-4 py-2.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:border-rose-500/50 rounded-lg transition-all"
                    >
                        <span>📘</span>
                        <span>사용 가이드</span>
                    </button>
                </div>
            </header>

            {/* Controls */}
            <div className="flex flex-wrap gap-4 mb-8 items-center">
                <select 
                    value={selectedDate}
                    onChange={(e) => handleDateChange(e.target.value)}
                    className="bg-[var(--bg-elevated)] text-white px-4 py-2 rounded-lg border border-[var(--border-primary)]"
                >
                    <option value="">최신 결과</option>
                    {availableDates.map(date => (
                        <option key={date} value={date}>{date}</option>
                    ))}
                </select>

                <div className="flex-1" />

                <div className="text-sm text-[var(--text-secondary)]">
                    {data?.generated_at && `날짜: ${new Date(data.generated_at).toLocaleTimeString('ko-KR')}`}
                    {' | '}
                    {data?.total_scanned ? (
                        <span className="text-blue-400 font-bold mr-2">
                             분석 대상: {data.total_scanned}개
                        </span>
                    ) : null}
                     | 포착 시그널: {displayedSignals.length}개
                </div>

                <button 
                    disabled={running}
                    onClick={handleRunScreener}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold transition-all ${
                        running 
                        ? 'bg-gray-600 cursor-not-allowed opacity-50' 
                        : 'bg-gradient-to-r from-rose-600 to-orange-600 hover:from-rose-500 hover:to-orange-500 text-white shadow-lg shadow-rose-500/20'
                    }`}
                >
                    {running ? (
                        <>
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                            실행 중...
                        </>
                    ) : (
                        <>🔄 스크리너 실행</>
                    )}
                </button>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                {['S', 'A', 'B', 'C'].map((grade) => {
                    const count = displayedSignals.filter(s => s.grade === grade).length;
                    const isActive = selectedGrade === grade;
                    
                    return (
                        <div 
                            key={grade} 
                            onClick={() => setSelectedGrade(prev => prev === grade ? null : grade)}
                            className={`glass-card p-4 text-center cursor-pointer transition-all hover:bg-white/5 border border-transparent ${
                                isActive ? 'border-rose-500 bg-rose-500/10 shadow-lg shadow-rose-500/10' : ''
                            }`}
                        >
                            <div className={`text-3xl font-bold mb-1 ${
                                grade === 'S' ? 'text-red-400' :
                                grade === 'A' ? 'text-purple-400' :
                                grade === 'B' ? 'text-emerald-400' : 'text-gray-400'
                            }`}>
                                {count}
                            </div>
                            <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${
                                grade === 'S' ? 'grade-s' :
                                grade === 'A' ? 'grade-a' :
                                grade === 'B' ? 'grade-b' : 'grade-c'
                            }`}>
                                {grade}級
                            </div>
                            {isActive && (
                                <div className="text-[10px] text-rose-400 mt-2 font-bold animate-pulse">
                                    ● 선택됨
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Signals Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {displayedSignals
                    .filter(s => !selectedGrade || s.grade === selectedGrade)
                    .map((signal) => (
                    <JPSignalCard 
                        key={signal.code} 
                        signal={signal} 
                        onOpenChart={() => setChartModal({
                            isOpen: true, 
                            symbol: signal.code, 
                            name: signal.name
                        })}
                    />
                ))}
            </div>

            {displayedSignals.length === 0 && (
                <div className="glass-card p-12 text-center">
                    <div className="text-4xl mb-4">📭</div>
                    <h3 className="text-xl font-bold mb-2">시그널 없음</h3>
                    <p className="text-[var(--text-secondary)]">
                        상단의 &quot;스크리너 실행&quot; 버튼을 클릭하여 시그널을 생성하세요.
                    </p>
                </div>
            )}

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
                title="JP 종가베팅 가이드 (V2 Logic)"
                sections={[
                    {
                        title: "🧮 12점 만점 평가 시스템",
                        content: (
                            <div className="space-y-3 text-sm text-gray-300">
                                <p>총 7가지 항목을 정밀 분석하여 점수를 산출합니다.</p>
                                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                                    <li className="bg-white/5 p-2 rounded">🔥 <strong>뉴스/재료 (3.0)</strong>: 호재 키워드 및 AI 분석</li>
                                    <li className="bg-white/5 p-2 rounded">📊 <strong>거래대금 (3.0)</strong>: 5000억/1000억/100억 기준</li>
                                    <li className="bg-white/5 p-2 rounded">📈 <strong>차트 패턴 (2.0)</strong>: 신고가 경신, 이평선 돌파</li>
                                    <li className="bg-white/5 p-2 rounded">🕯️ <strong>캔들 (1.0)</strong>: 양봉 마감 여부</li>
                                    <li className="bg-white/5 p-2 rounded">🧱 <strong>기간 조정 (1.0)</strong>: 7일간 변동폭 20% 이내 횡보</li>
                                    <li className="bg-white/5 p-2 rounded">💰 <strong>수급 (2.0)</strong>: 외국인/기관 순매수 포착</li>
                                    <li className="bg-white/5 p-2 rounded border border-cyan-500/30">📐 <strong>기술적 지표 (3.0)</strong>: RSI, 볼린저, MACD</li>
                                </ul>
                            </div>
                        )
                    },
                    {
                        title: "📐 기술적 지표 상세 (Technical Alpha)",
                        content: (
                            <div className="space-y-2 text-sm text-gray-300">
                                <ul className="list-disc list-inside space-y-1">
                                    <li><strong>RSI (14)</strong>: 50~70 구간(상승세), 70~80(강한 매수세) 가산점.</li>
                                    <li><strong>Bollinger Bands</strong>: 상단 돌파 시 강력 매수, 밴드 폭 축소(Squeeze) 시 급변동 전조 감지.</li>
                                    <li><strong>MACD</strong>: 골든크로스 및 0선 돌파 시 가산점.</li>
                                </ul>
                            </div>
                        )
                    },
                    {
                        title: "🏆 등급별 대응 전략 (Action Guide)",
                        content: (
                            <div className="space-y-2 text-sm">
                                <div className="p-2 bg-red-900/30 border border-red-500/30 rounded">
                                    <span className="text-red-400 font-bold block mb-1">👑 S급 (Try): 8.0점 이상</span>
                                    <span className="text-gray-400 text-xs">강력한 상승 모멘텀과 수급/재료가 일치. 적극 공략 대상.</span>
                                </div>
                                <div className="p-2 bg-purple-900/30 border border-purple-500/30 rounded">
                                    <span className="text-purple-400 font-bold block mb-1">🚀 A급 (Strong): 6.0점 이상</span>
                                    <span className="text-gray-400 text-xs">상승 추세가 확인된 우량주. 주도주 가능성 높음.</span>
                                </div>
                                <div className="p-2 bg-emerald-900/30 border border-emerald-500/30 rounded">
                                    <span className="text-emerald-400 font-bold block mb-1">👀 B급 (Watch): 4.0점 이상</span>
                                    <span className="text-gray-400 text-xs">조건은 좋으나 단기 과열 가능성 있음. 눌림목 공략 권장.</span>
                                </div>
                            </div>
                        )
                    }
                ]}
            />
        </div>
    );
}

// Signal Card Component
function JPSignalCard({ signal, onOpenChart }: { 
    signal: JPSignal; 
    onOpenChart: () => void;
}) {
    const scoreDetail = signal.score_detail;
    const totalScore = signal.score ?? 0;
    
    return (
        <div className="glass-card p-6 relative overflow-hidden group hover:border-rose-500/50 transition-all">
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-xl font-bold text-white group-hover:text-rose-400 transition-colors">{signal.name}</h3>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 font-bold border border-rose-500/20 uppercase tracking-tighter">
                            TSE
                        </span>
                    </div>
                    <div className="text-xs text-slate-500 font-mono tracking-wider">{signal.code}</div>
                    <div className="text-[10px] text-slate-600 mt-1">{signal.sector}</div>
                </div>
                <div className={`px-4 py-1.5 rounded-xl font-black text-lg shadow-lg ${
                    signal.grade === 'S' ? 'grade-s shadow-red-500/20' :
                    signal.grade === 'A' ? 'grade-a shadow-purple-500/20' :
                    signal.grade === 'B' ? 'grade-b shadow-emerald-500/20' : 'grade-c'
                }`}>
                    {signal.grade}
                </div>
            </div>

            {/* Price & Score */}
            <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">현재가</div>
                    <div className="flex items-baseline gap-2 mb-4">
                        <span className="text-3xl font-black text-white">{signal.close?.toLocaleString()}</span>
                        <span className={`text-sm font-bold ${signal.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {signal.change_pct >= 0 ? '▲' : '▼'} {Math.abs(signal.change_pct || 0).toFixed(2)}%
                        </span>
                    </div>
                </div>

                <div className="flex flex-col items-center justify-center bg-white/5 rounded-2xl border border-white/5 p-2">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">종합 점수</div>
                    <div className="text-2xl font-black text-rose-400">
                        {totalScore.toFixed(1)}
                        <span className="text-xs text-slate-500 font-normal"> / 12+</span>
                    </div>
                </div>
            </div>

            {/* Metric Bars */}
            {scoreDetail && (
                <div className="space-y-3 mb-6">
                    <div className="grid grid-cols-2 gap-2">
                         <MetricBar label="뉴스/재료" value={scoreDetail.news} max={3} color="bg-amber-400" />
                         <MetricBar label="기술적지표" value={scoreDetail.technical || 0} max={3} color="bg-cyan-400" />
                    </div>
                    <MetricBar label="거래량" value={scoreDetail.volume} max={3} color="bg-blue-400" />
                    <MetricBar label="차트/캔들" value={(scoreDetail.chart || 0) + (scoreDetail.candle || 0) + (scoreDetail.consolidation || 0)} max={4} color="bg-purple-400" />
                </div>
            )}

            {/* Price Plan Grid */}
            <div className="price-grid mb-6">
                <div className="price-item">
                    <div className="price-label">포착가</div>
                    <div className="price-value text-slate-300">{signal.close?.toLocaleString()}</div>
                </div>
                <div className="price-item">
                    <div className="price-label">수익률</div>
                    <div className={`price-value font-bold ${(signal.change_pct || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {(signal.change_pct || 0) > 0 ? '+' : ''}{(signal.change_pct || 0).toFixed(2)}%
                    </div>
                </div>
                <div className="price-item">
                    <div className="price-label">목표가</div>
                    <div className="price-value text-rose-400">
                        {signal.target_price?.toLocaleString() || Math.round((signal.close || 0) * 1.05).toLocaleString()}
                    </div>
                </div>
                <div className="price-item">
                    <div className="price-label">기대수익</div>
                    <div className="price-value text-amber-400">
                        +{signal.target_price 
                            ? (((signal.target_price / (signal.close || 1)) - 1) * 100).toFixed(1)
                            : '5.0'}%
                    </div>
                </div>
            </div>

            {/* News */}
            {signal.news && signal.news.length > 0 && (
                <div className="space-y-1.5 mb-6">
                    {signal.news.slice(0, 1).map((news, i) => (
                        <div 
                            key={i} 
                            className="flex items-center gap-2 text-xs text-slate-400 bg-white/5 p-2 rounded-lg border border-transparent"
                        >
                            <span className="shrink-0 text-amber-500">🔥</span>
                            <span className="truncate flex-1">{news.title}</span>
                            <span className="text-slate-600 text-[10px]">{news.source}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Footer */}
            <div className="flex gap-2">
                <button 
                    onClick={onOpenChart}
                    className="flex-1 bg-white/10 hover:bg-white/20 text-white text-xs font-bold py-3 rounded-xl transition-all border border-white/5 flex items-center justify-center gap-2"
                >
                    📈 차트 보기
                </button>
            </div>
        </div>
    );
}

function MetricBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
    const percentage = Math.min(100, (value / max) * 100);
    return (
        <div className="metric-container">
            <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                <span className="text-slate-500">{label}</span>
                <span className={value > 0 ? color.replace('bg-', 'text-') : 'text-slate-600'}>
                    {value.toFixed(1)} <span className="text-slate-700">/ {max}</span>
                </span>
            </div>
            <div className="metric-bar">
                <div 
                    className={`metric-fill ${color} shadow-[0_0_10px_rgba(0,0,0,0.5)]`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}
