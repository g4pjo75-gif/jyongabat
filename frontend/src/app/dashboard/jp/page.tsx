'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { jpAPI, JPMarketGate, Sector, BacktestStats } from '@/lib/api';
import GuideModal from '@/components/GuideModal';

interface MarketGateWithUpdate extends JPMarketGate {
    updated_at?: string;
}

export default function JPMarketOverview() {
    const [marketGate, setMarketGate] = useState<MarketGateWithUpdate | null>(null);
    const [backtest, setBacktest] = useState<{ closing_bet: BacktestStats } | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [showGuide, setShowGuide] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [gateData, btData, dates] = await Promise.all([
                    jpAPI.getMarketGate(),
                    jpAPI.getBacktestSummary(),
                    jpAPI.getMarketGateDates(),
                ]);
                setMarketGate(gateData as MarketGateWithUpdate);
                setBacktest(btData);
                setAvailableDates(dates);
            } catch (error) {
                console.error('Error fetching data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                const gateData = await jpAPI.getMarketGate();
                setMarketGate(gateData as MarketGateWithUpdate);
            } else {
                const gateData = await jpAPI.getMarketGateHistory(dateStr);
                setMarketGate(gateData as MarketGateWithUpdate);
            }
        } catch (error) {
            console.error('Error loading history:', error);
            alert('해당 날짜의 데이터를 불러올 수 없습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleRefresh = async () => {
        if (refreshing) return;
        setRefreshing(true);
        try {
            const gateData = await jpAPI.refreshMarketGate();
            setMarketGate(gateData as MarketGateWithUpdate);
        } catch (error) {
            console.error('Error refreshing data:', error);
            alert('데이터 갱신 중 오류가 발생했습니다.');
        } finally {
            setRefreshing(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center">
                <div className="text-2xl text-[var(--text-secondary)]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="space-y-10">
            {/* Top Bar */}
            <div className="flex justify-between items-center mb-2">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight">🇯🇵 JP Market Overview</h1>
                    <p className="text-sm text-slate-500 font-medium mt-1">
                        {marketGate?.updated_at 
                            ? `最終更新: ${new Date(marketGate.updated_at).toLocaleString('ja-JP')}`
                            : 'Tokyo Stock Exchange - Nikkei 225 & TOPIX'
                        }
                    </p>
                </div>
                <div className="flex gap-4">
                    <button
                        onClick={() => setShowGuide(true)}
                        className="glass-card px-4 py-2 flex items-center gap-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border-blue-500/30 transition-all"
                    >
                        <span>📘</span>
                        <span className="text-xs font-bold">가이드</span>
                    </button>
                    <select 
                        value={selectedDate}
                        onChange={(e) => handleDateChange(e.target.value)}
                        className="glass-card px-4 py-2 bg-white/5 border-white/10 text-white text-sm font-medium rounded-lg cursor-pointer"
                    >
                        <option value="">最新結果</option>
                        {availableDates.map(date => (
                            <option key={date} value={date}>{date}</option>
                        ))}
                    </select>
                    <button
                        onClick={handleRefresh}
                        disabled={refreshing || selectedDate !== ''}
                        className={`glass-card px-5 py-2 flex items-center gap-2 transition-all ${
                            refreshing || selectedDate !== ''
                                ? 'bg-slate-800 text-slate-600 cursor-not-allowed' 
                                : 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border-emerald-500/30'
                        }`}
                    >
                        <span className={`text-lg ${refreshing ? 'animate-spin' : ''}`}>
                            {refreshing ? '⏳' : '🔄'}
                        </span>
                        <span className="text-xs font-bold uppercase">
                            {refreshing ? 'Refreshing...' : 'Refresh'}
                        </span>
                    </button>
                </div>
            </div>

            {/* Market Gate Section */}
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Gate Score Card */}
                <div className="glass-card p-8 relative overflow-hidden flex flex-col justify-between min-h-[200px]">
                    <div className={`absolute top-0 right-0 w-48 h-48 rounded-full blur-[100px] opacity-20 ${
                        marketGate?.status === 'GREEN' ? 'bg-emerald-500' : 
                        marketGate?.status === 'RED' ? 'bg-rose-500' : 'bg-amber-500'
                    }`} />
                    
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">
                            Security Gate Status
                        </h2>
                        <div className="flex items-baseline gap-3">
                            <span className={`text-6xl font-black ${
                                marketGate?.status === 'GREEN' ? 'text-emerald-400' : 
                                marketGate?.status === 'RED' ? 'text-rose-400' : 'text-amber-400'
                            }`}>
                                {marketGate?.score ?? 50}
                            </span>
                            <span className="text-xl font-bold text-slate-600">/ 100</span>
                        </div>
                        <div className={`text-xl font-black mt-2 tracking-tight ${
                            marketGate?.status === 'GREEN' ? 'text-emerald-400' : 
                            marketGate?.status === 'RED' ? 'text-rose-400' : 'text-amber-400'
                        }`}>
                            {marketGate?.label ?? 'NEUTRAL'}
                        </div>
                    </div>
                    
                    <div className="mt-8 flex gap-2">
                        {marketGate?.reasons?.slice(0, 2).map((reason, i) => (
                            <span key={i} className="text-[10px] font-bold px-2 py-1 rounded bg-white/5 text-slate-400 border border-white/5 whitespace-nowrap">
                                {reason}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Nikkei 225 Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">日経225</h2>
                        <div className="text-4xl font-black text-white">{marketGate?.nikkei_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.nikkei_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.nikkei_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.nikkei_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>

                {/* TOPIX Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">TOPIX</h2>
                        <div className="text-4xl font-black text-white">{marketGate?.topix_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.topix_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.topix_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.topix_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>
            </section>

            {/* Main Content Area */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Sector Momentum */}
                <section className="xl:col-span-2">
                    <div className="flex justify-between items-end mb-6">
                        <h2 className="text-xl font-black text-white px-2">Sector Momentum</h2>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active Sectors</span>
                    </div>
                    <div className="glass-card p-8">
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            {marketGate?.sectors?.map((sector: Sector) => (
                                <div key={sector.name} className="p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
                                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 truncate">{sector.name}</div>
                                    <div className={`text-xl font-black ${
                                        sector.signal === 'bullish' ? 'text-emerald-400' :
                                        sector.signal === 'bearish' ? 'text-rose-400' : 'text-slate-400'
                                    }`}>
                                        {sector.change_pct >= 0 ? '+' : ''}{sector.change_pct.toFixed(2)}%
                                    </div>
                                    <div className="w-full h-1 bg-white/5 rounded-full mt-3 overflow-hidden">
                                        <div 
                                            className={`h-full ${sector.change_pct >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`}
                                            style={{ width: `${Math.min(100, Math.abs(sector.change_pct) * 10)}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                            {(!marketGate?.sectors || marketGate.sectors.length === 0) && (
                                <div className="col-span-4 text-center text-slate-500 py-8">
                                    섹터 데이터가 없습니다
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* Actions */}
                <section className="space-y-8">
                    <div className="glass-card p-8">
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6 font-black">AI Closing Bet Stats</h2>
                        <div className="space-y-6">
                            <div className="flex justify-between items-center">
                                <span className="text-sm font-bold text-slate-400">Winning Rate</span>
                                <span className="text-2xl font-black text-emerald-400">{backtest?.closing_bet?.win_rate ?? 0}%</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm font-bold text-slate-400">Total Signals</span>
                                <span className="text-2xl font-black text-blue-400">{backtest?.closing_bet?.count ?? 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm font-bold text-slate-400">Avg. Return</span>
                                <span className={`text-2xl font-black ${(backtest?.closing_bet?.avg_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {(backtest?.closing_bet?.avg_return ?? 0) >= 0 ? '+' : ''}{backtest?.closing_bet?.avg_return ?? 0}%
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-8 bg-gradient-to-br from-rose-600/10 to-orange-600/10 border-rose-500/20">
                        <h2 className="text-[10px] font-bold text-rose-400 uppercase tracking-widest mb-6">Fast Actions</h2>
                        <div className="space-y-4">
                            <Link href="/dashboard/jp/n225" className="w-full py-4 rounded-xl font-black text-xs uppercase bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-500/20 transition-all flex items-center justify-center gap-2">
                                📊 Nikkei 225 Signals
                            </Link>
                            <Link href="/dashboard/jp/n400" className="w-full py-4 rounded-xl font-black text-xs uppercase bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-500/20 transition-all flex items-center justify-center gap-2">
                                📊 Other Nikkei 400 Signals
                            </Link>

                            <button 
                                disabled={running}
                                className={`w-full py-4 rounded-xl font-black text-xs uppercase transition-all flex items-center justify-center gap-2 ${
                                    running 
                                    ? 'bg-slate-800 text-slate-600 cursor-not-allowed' 
                                    : 'bg-white/5 hover:bg-white/10 text-white border border-white/10'
                                }`}
                                onClick={async () => {
                                    if (running) return;
                                    setRunning(true);
                                    try {
                                        await jpAPI.runScreener();
                                        alert('스크리닝이 시작되었습니다.');
                                    } catch {
                                        alert('스크리닝 실행 중 오류가 발생했습니다.');
                                    } finally {
                                        setRunning(false);
                                    }
                                }}
                            >
                                {running ? 'Running...' : '🔄 Run JP Screener (All)'}
                            </button>
                        </div>
                    </div>
                </section>
            </div>

            <GuideModal
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
                title="JP Market Overview 가이드"
                sections={[
                    {
                        title: "🗾 Market Gate란?",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><strong>Security Gate Status</strong>: 닛케이225와 TOPIX 변동률 기반 시장 상태 점수 (0~100)</li>
                                <li><strong>GREEN (70+)</strong>: 강세장 - 적극적 매수 가능</li>
                                <li><strong>YELLOW (40~70)</strong>: 보합세 - 선별적 진입</li>
                                <li><strong>RED (~40)</strong>: 약세장 - 관망 권장</li>
                            </ul>
                        )
                    },
                    {
                        title: "📊 Sector Momentum",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li>일본 주요 섹터 ETF의 일일 변동률을 표시합니다.</li>
                                <li><span className="text-emerald-400">초록색</span>: 상승 섹터 / <span className="text-rose-400">빨간색</span>: 하락 섹터</li>
                                <li>강한 섹터에 속한 종목이 모멘텀을 받을 가능성이 높습니다.</li>
                            </ul>
                        )
                    },
                    {
                        title: "⚡ 빠른 시작",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><strong>Go to Signals</strong>: JP 종가베팅 시그널 페이지로 이동</li>
                                <li><strong>Run JP Screener</strong>: AI 스크리너 실행 (JPX Nikkei 400 종목 분석)</li>
                                <li>매일 15:00(도쿄 시간) 장 마감 전 스크리너 실행을 권장합니다.</li>
                            </ul>
                        )
                    }
                ]}
            />
        </div>
    );
}
