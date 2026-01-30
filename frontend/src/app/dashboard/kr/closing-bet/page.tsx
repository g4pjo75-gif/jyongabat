'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { krAPI, KRSignal, ScreenerResult } from '@/lib/api';
import GuideModal from '@/components/GuideModal';

export default function JonggaV2Page() {
    const [data, setData] = useState<ScreenerResult | null>(null);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [showGuide, setShowGuide] = useState(false);
    const [chartModal, setChartModal] = useState<{isOpen: boolean; symbol: string; name: string}>({
        isOpen: false, symbol: '', name: ''
    });
    const [selectedGrade, setSelectedGrade] = useState<string | null>(null);

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const [latestData, dates] = await Promise.all([
                    krAPI.getJonggaLatest(),
                    krAPI.getJonggaDates(),
                ]);
                setData(latestData);
                // 초기 로드시 entry_price 설정
                if (latestData && latestData.signals) {
                    latestData.signals = latestData.signals.map(s => ({
                        ...s,
                        entry_price: s.current_price,
                        return_pct: 0
                    }));
                }
                setAvailableDates(dates);
            } catch (error) {
                console.error('Error fetching data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchInitialData();
    }, []);

    // 실시간 가격 업데이트 (60초 주기)
    useEffect(() => {
        if (loading || !data?.signals || data.signals.length === 0) return;

        const updatePrices = async () => {
            try {
                const tickers = data.signals.map(s => s.stock_code); // closing-bet uses stock_code instead of ticker? Check API types.
                // Assuming KRSignal has stock_code. VCP uses ticker. Let's check type definition or usage.
                // In SignalCard usage: signal.stock_code. So allow stock_code.
                if (tickers.length === 0) return;

                const res = await fetch('/api/kr/realtime-prices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tickers })
                });
                const prices = await res.json();

                if (Object.keys(prices).length > 0) {
                    setData(prev => {
                        if (!prev) return null;
                        return {
                            ...prev,
                            signals: prev.signals.map(s => {
                                const code = s.stock_code; // krAPI uses stock_code for Jongga
                                if (prices[code]) {
                                    const current = prices[code];
                                    const entry = s.entry_price || s.current_price || 0;
                                    let ret = 0;
                                    if (entry > 0) {
                                        ret = ((current - entry) / entry) * 100;
                                    }
                                    return { 
                                        ...s, 
                                        current_price: current, 
                                        return_pct: ret,
                                        entry_price: entry 
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
        updatePrices(); // Run immediately once
        return () => clearInterval(interval);
    }, [data?.date, loading]); // signal list dependency

    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                const latestData = await krAPI.getJonggaLatest();
                if (latestData && latestData.signals) {
                    latestData.signals = latestData.signals.map(s => ({
                        ...s,
                        entry_price: s.current_price,
                        return_pct: 0
                    }));
                }
                setData(latestData);
            } else {
                const historyData = await krAPI.getJonggaHistory(dateStr);
                // 과거 데이터: 당시 가격을 entry_price로 보존
                if (historyData && historyData.signals) {
                    historyData.signals = historyData.signals.map(s => ({
                        ...s,
                        entry_price: s.current_price, // 당시 종가
                        return_pct: 0
                    }));
                }
                setData(historyData);
            }
        } catch {
            console.error('Date change error:');
        } finally {
            setLoading(false);
        }
    };

    const handleRunScreener = async () => {
        if (running) return;
        setRunning(true);
        try {
            const res = await fetch('/api/kr/jongga-v2/run', { method: 'POST' });
            
            if (res.status === 202 || res.status === 200) {
                // Polling start
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await fetch('/api/kr/screener/status');
                        const status = await statusRes.json();
                        
                        if (!status.isRunning) {
                            clearInterval(pollInterval);
                            setRunning(false);
                            alert(`스크리닝 완료! ${status.message}`);
                            const latestData = await krAPI.getJonggaLatest();
                            setData(latestData);
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
        } catch {
            alert('스크리닝 실행 중 오류가 발생했습니다.');
            setRunning(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center">
                <div className="text-2xl text-[var(--text-secondary)]">Loading signals...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--bg-page)] p-8">
            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="flex items-center gap-4 mb-2">
                        <Link href="/dashboard/kr" className="text-[var(--text-secondary)] hover:text-white">
                            ← Back
                        </Link>
                        <h1 className="text-3xl font-bold">📈 종가베팅 V2</h1>
                    </div>
                    <p className="text-[var(--text-secondary)]">
                        AI 기반 종가베팅 시그널 | 12점 점수 시스템
                    </p>
                </div>
                
                <button
                    onClick={() => setShowGuide(true)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:border-blue-500/50 rounded-lg transition-all"
                >
                    <span>📘</span>
                    <span>사용 가이드</span>
                </button>
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
                    {data?.date && `날짜: ${data.date}`}
                    {' | '}
                    총 {data?.signals?.length ?? 0}개 시그널
                </div>

                <button 
                    disabled={running}
                    onClick={handleRunScreener}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold transition-all ${
                        running 
                        ? 'bg-gray-600 cursor-not-allowed opacity-50' 
                        : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-lg shadow-blue-500/20'
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
                    const count = data?.signals?.filter(s => s.grade === grade).length ?? 0;
                    const isActive = selectedGrade === grade;
                    
                    return (
                        <div 
                            key={grade} 
                            onClick={() => setSelectedGrade(prev => prev === grade ? null : grade)}
                            className={`glass-card p-4 text-center cursor-pointer transition-all hover:bg-white/5 border border-transparent ${
                                isActive ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/10' : ''
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
                                {grade}급
                            </div>
                            {/* 선택됨 표시 (옵션) */}
                            {isActive && (
                                <div className="text-[10px] text-blue-400 mt-2 font-bold animate-pulse">
                                    ● Viewing
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Signals Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {(data?.signals || [])
                    .filter(s => !selectedGrade || s.grade === selectedGrade)
                    .map((signal) => (
                    <SignalCard 
                        key={signal.stock_code} 
                        signal={signal} 
                        onOpenChart={() => setChartModal({
                            isOpen: true, 
                            symbol: signal.stock_code, 
                            name: signal.stock_name
                        })}
                    />
                ))}
            </div>

            {(!data?.signals || data.signals.length === 0) && (
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
                <ChartModal 
                    symbol={chartModal.symbol} 
                    name={chartModal.name}
                    onClose={() => setChartModal({isOpen: false, symbol: '', name: ''})}
                />
            )}
            
            <GuideModal
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
                title="종가베팅 사용 가이드"
                sections={[
                    {
                        title: "🎯 베팅 로직 (Strategy Logic)",
                        content: (
                            <div className="space-y-2 text-sm">
                                <ul className="list-disc list-inside space-y-1 ml-2 text-gray-300">
                                    <li><strong>15:00 이후 포착</strong>: 장 마감 직전 수급이 급증하고 추세가 살아있는 종목을 선별합니다.</li>
                                    <li><strong>12점 만점 시스템</strong>: 재료, 수급, 거래량, 기술적 지표를 정량화하여 4단계로 평가합니다.</li>
                                    <li><strong>AI 분석 결합</strong>: 뉴스 키워드 분석 및 LLM 기반의 재료 가치 평가가 반영됩니다.</li>
                                </ul>
                            </div>
                        )
                    },
                    {
                        title: "📊 채점 기준 및 배점 (Scoring Criteria)",
                        content: (
                            <div className="space-y-4 text-sm">
                                <div>
                                    <div className="font-bold text-amber-400 mb-1">총 12점 만점 + α</div>
                                    <ul className="list-disc list-inside space-y-1 ml-2 text-gray-300">
                                        <li><strong>재료/뉴스 (0-3점)</strong>: 긍정 키워드, AI 뉴스 점수 반영 (3점: 강력 호재)</li>
                                        <li><strong>거래대금 (0-3점)</strong>: 메이저 자금 유입 확인 (3점: 5000억↑, 2점: 1000억↑)</li>
                                        <li><strong>차트 패턴 (0-2점)</strong>: 신고가 영역(95%↑) 및 이평선 정배열 돌파(+1점)</li>
                                        <li><strong>수급 현황 (0-2점)</strong>: 외국인/기관 순매수 유입 여부 (양매수 시 +2점)</li>
                                        <li><strong>캔들/조정 (0-2점)</strong>: 양봉 마감 및 기간 횡보 후 돌파 여부</li>
                                    </ul>
                                </div>
                            </div>
                        )
                    },
                    {
                        title: "🏅 등급별 대응 전략 (Action Guide)",
                        content: (
                            <div className="space-y-2 text-sm">
                                <ul className="list-disc list-inside space-y-2">
                                    <li>
                                        <span className="text-red-400 font-bold">Try (S급, 8점↑)</span>: 
                                        <span className="text-gray-300"> 강력한 확신. 비중 100% 진입 가능. (익일 갭상승 확률 높음)</span>
                                    </li>
                                    <li>
                                        <span className="text-purple-400 font-bold">Strong (A급, 6점↑)</span>: 
                                        <span className="text-gray-300"> 긍정적 시그널. 주도주 가능성. (비중 50~70% 권장)</span>
                                    </li>
                                    <li>
                                        <span className="text-emerald-400 font-bold">Watch (B급, 4점↑)</span>: 
                                        <span className="text-gray-300"> 조건은 좋으나 단기 과열 가능성. (조정 시 진입)</span>
                                    </li>
                                    <li>
                                        <span className="text-gray-500 font-bold">Pass (C급)</span>: 
                                        <span className="text-gray-300"> 관망 권장.</span>
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

// Signal Card Component
function SignalCard({ signal, onOpenChart }: { 
    signal: KRSignal; 
    onOpenChart: () => void;
}) {
    const score = typeof signal.score === 'object' ? signal.score : null;
    const totalScore = score?.total ?? 0;
    
    return (
        <div className="glass-card p-6 relative overflow-hidden group hover:border-blue-500/50 transition-all">
            {/* Header: Name, Ticker, Grade */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">{signal.stock_name}</h3>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold border border-blue-500/20 uppercase tracking-tighter">
                            {signal.market}
                        </span>
                    </div>
                    <div className="text-xs text-slate-500 font-mono tracking-wider">{signal.stock_code}</div>
                </div>
                <div className={`px-4 py-1.5 rounded-xl font-black text-lg shadow-lg ${
                    signal.grade === 'S' ? 'grade-s shadow-red-500/20' :
                    signal.grade === 'A' ? 'grade-a shadow-purple-500/20' :
                    signal.grade === 'B' ? 'grade-b shadow-emerald-500/20' : 'grade-c'
                }`}>
                    {signal.grade}
                </div>
            </div>

            {/* Price & Score Grid */}
            <div className="grid grid-cols-2 gap-6 mb-6">
                {/* Left: Prices */}
                <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">현재가 (Real)</div>
                    <div className="flex items-baseline gap-2 mb-4">
                        <span className="text-3xl font-black text-white">{signal.current_price?.toLocaleString()}</span>
                        <span className={`text-sm font-bold ${signal.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {signal.change_pct >= 0 ? '▲' : '▼'} {Math.abs(signal.change_pct || 0).toFixed(2)}%
                        </span>
                    </div>
                </div>

                {/* Right: Total Score Circular-style */}
                <div className="flex flex-col items-center justify-center bg-white/5 rounded-2xl border border-white/5 p-2">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">종합 점수</div>
                    <div className="text-2xl font-black text-blue-400">{totalScore}<span className="text-xs text-slate-500 font-normal"> / 12</span></div>
                </div>
            </div>

            {/* Metric Bars (Horizontal Gauge Style) */}
            {score && (
                <div className="space-y-3 mb-6">
                    <MetricBar label="뉴스/재료" value={score.news} max={3} color="bg-amber-400" />
                    <MetricBar label="수급 (외인/기관)" value={score.supply} max={2} color="bg-emerald-400" />
                    <MetricBar label="거래량" value={score.volume} max={3} color="bg-blue-400" />
                    <MetricBar label="차트/캔들" value={score.chart + (score.candle || 0)} max={3} color="bg-purple-400" />
                </div>
            )}

            {/* Price Plan Grid */}
            <div className="price-grid mb-6">
                <div className="price-item">
                    <div className="price-label">포착가</div>
                    <div className="price-value text-slate-300">{signal.entry_price?.toLocaleString()}</div>
                </div>
                <div className="price-item">
                    <div className="price-label">수익률</div>
                    <div className={`price-value font-bold ${(signal.return_pct || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {(signal.return_pct || 0) > 0 ? '+' : ''}{(signal.return_pct || 0).toFixed(2)}%
                    </div>
                </div>
                <div className="price-item">
                    <div className="price-label">목표가</div>
                    <div className="price-value text-blue-400">{signal.target_price?.toLocaleString()}</div>
                </div>
                <div className="price-item">
                    <div className="price-label">기대수익</div>
                    <div className="price-value text-amber-400">+{( ((signal.target_price || 0) / (signal.entry_price || 1) - 1) * 100 ).toFixed(1)}%</div>
                </div>
            </div>



            {/* News Context */}
            {signal.news_items && signal.news_items.length > 0 && (
                <div className="space-y-1.5 mb-6">
                    {signal.news_items.slice(0, 1).map((news, i) => (
                        <a 
                            key={i} 
                            href={news.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors bg-white/5 p-2 rounded-lg border border-transparent hover:border-white/10"
                        >
                            <span className="shrink-0 text-amber-500">🔥</span>
                            <span className="truncate flex-1">{news.title}</span>
                        </a>
                    ))}
                </div>
            )}

            {/* Footer Actions */}
            <div className="flex gap-2">
                <button 
                    onClick={onOpenChart}
                    className="flex-1 bg-white/10 hover:bg-white/20 text-white text-xs font-bold py-3 rounded-xl transition-all border border-white/5 flex items-center justify-center gap-2"
                >
                    🎥 차트 보기
                </button>
                <button 
                    className="w-12 h-12 bg-amber-400 hover:bg-amber-300 text-black rounded-xl flex items-center justify-center text-xl transition-all shadow-lg shadow-amber-400/20"
                    title="공유"
                >
                    💬
                </button>
            </div>
        </div>
    );
}

function MetricBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
    const percentage = (value / max) * 100;
    return (
        <div className="metric-container">
            <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                <span className="text-slate-500">{label}</span>
                <span className={value > 0 ? color.replace('bg-', 'text-') : 'text-slate-600'}>
                    {value} <span className="text-slate-700">/ {max}</span>
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


// Chart Modal Component
function ChartModal({ symbol, name, onClose }: { 
    symbol: string; 
    name: string;
    onClose: () => void;
}) {
    const chartUrl = `https://ssl.pstatic.net/imgfinance/chart/item/area/day/${symbol}.png`;
    
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content max-w-3xl" onClick={(e) => e.stopPropagation()}>
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">{name} ({symbol})</h2>
                    <button 
                        onClick={onClose}
                        className="text-2xl text-[var(--text-secondary)] hover:text-white"
                    >
                        ×
                    </button>
                </div>
                <img 
                    src={chartUrl} 
                    alt={`${name} 차트`}
                    className="w-full rounded-lg"
                />
                <div className="mt-4 flex gap-2 justify-end">
                    <a 
                        href={`https://finance.naver.com/item/main.nhn?code=${symbol}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary text-sm"
                    >
                        네이버 금융에서 보기
                    </a>
                </div>
            </div>
        </div>
    );
}
