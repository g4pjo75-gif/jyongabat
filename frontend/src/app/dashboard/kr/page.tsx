'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { krAPI, KRMarketGate, Sector, BacktestSummary } from '@/lib/api';

// updated_at 필드 포함 타입 확장
interface MarketGateWithUpdate extends KRMarketGate {
    updated_at?: string;
}

export default function KRMarketOverview() {
    const [marketGate, setMarketGate] = useState<MarketGateWithUpdate | null>(null);
    const [backtest, setBacktest] = useState<BacktestSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [gateData, btData, dates] = await Promise.all([
                    krAPI.getMarketGate(),
                    krAPI.getBacktestSummary(),
                    krAPI.getMarketGateDates(),
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
        // 자동 리프레시 제거 - 사용자가 수동으로 리프레시
    }, []);

    // 날짜 변경 핸들러
    const handleDateChange = async (dateStr: string) => {
        setLoading(true);
        setSelectedDate(dateStr);
        try {
            if (dateStr === '' || dateStr === 'latest') {
                const gateData = await krAPI.getMarketGate();
                setMarketGate(gateData as MarketGateWithUpdate);
            } else {
                const gateData = await krAPI.getMarketGateHistory(dateStr);
                setMarketGate(gateData as MarketGateWithUpdate);
            }
        } catch (error) {
            console.error('Error loading history:', error);
            alert('해당 날짜의 데이터를 불러올 수 없습니다.');
        } finally {
            setLoading(false);
        }
    };

    // 수동 리프레시 핸들러
    const handleRefresh = async () => {
        if (refreshing) return;
        setRefreshing(true);
        try {
            const gateData = await krAPI.refreshMarketGate();
            setMarketGate(gateData as MarketGateWithUpdate);
        } catch (error) {
            console.error('Error refreshing data:', error);
            alert('데이터 새로고침 중 오류가 발생했습니다.');
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
            {/* Top Bar: Title & Search Placeholder */}
            <div className="flex justify-between items-center mb-2">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight">Market Overview</h1>
                    <p className="text-sm text-slate-500 font-medium mt-1">
                        {marketGate?.updated_at 
                            ? `마지막 업데이트: ${new Date(marketGate.updated_at).toLocaleString('ko-KR')}`
                            : 'Real-time KR Market Status & AI Signals'
                        }
                    </p>
                </div>
                <div className="flex gap-4">
                    {/* 날짜 선택 드롭다운 */}
                    <select 
                        value={selectedDate}
                        onChange={(e) => handleDateChange(e.target.value)}
                        className="glass-card px-4 py-2 bg-white/5 border-white/10 text-white text-sm font-medium rounded-lg cursor-pointer"
                    >
                        <option value="">최신 결과</option>
                        {availableDates.map(date => (
                            <option key={date} value={date}>{date}</option>
                        ))}
                    </select>
                    {/* 리프레시 버튼 */}
                    <button
                        onClick={handleRefresh}
                        disabled={refreshing || selectedDate !== ''}
                        className={`glass-card px-5 py-2 flex items-center gap-2 transition-all ${
                            refreshing || selectedDate !== ''
                                ? 'bg-slate-800 text-slate-600 cursor-not-allowed' 
                                : 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border-emerald-500/30'
                        }`}
                        title={selectedDate !== '' ? '최신 결과를 선택해야 리프레시 가능' : ''}
                    >
                        <span className={`text-lg ${refreshing ? 'animate-spin' : ''}`}>
                            {refreshing ? '⏳' : '🔄'}
                        </span>
                        <span className="text-xs font-bold uppercase">
                            {refreshing ? 'Refreshing...' : 'Refresh'}
                        </span>
                    </button>
                    <div className="glass-card px-4 py-2 flex items-center gap-3 bg-white/5 border-white/10">
                        <span className="text-xl">🔍</span>
                        <input type="text" placeholder="Search Tickers..." className="bg-transparent border-none outline-none text-sm w-48 text-slate-300 placeholder:text-slate-600" />
                    </div>
                </div>
            </div>

            {/* Market Gate Section (V2 Widget Style) */}
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

                {/* KOSPI Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">KOSPI Index</h2>
                        <div className="text-4xl font-black text-white">{marketGate?.kospi_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.kospi_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.kospi_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.kospi_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>

                {/* KOSDAQ Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">KOSDAQ Index</h2>
                        <div className="text-4xl font-black text-white">{marketGate?.kosdaq_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.kosdaq_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.kosdaq_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.kosdaq_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>
            </section>

            {/* Main Content Area: Sectors & Strategy */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Sector Radar (Left) */}
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
                        </div>
                    </div>
                </section>

                {/* Performance & Actions (Right) */}
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

                    <div className="glass-card p-8 bg-gradient-to-br from-blue-600/10 to-purple-600/10 border-blue-500/20">
                        <h2 className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mb-6">Fast Actions</h2>
                        <div className="space-y-4">
                            <Link href="/dashboard/kr/closing-bet" className="w-full py-4 rounded-xl font-black text-xs uppercase bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2">
                                📊 Go to Signals
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
                                        const res = await fetch('/api/kr/jongga-v2/run', { method: 'POST' });
                                        const data = await res.json();
                                        alert(`스크리닝 완료! ${data.filtered_count || 0}개 시그널 생성`);
                                        window.location.reload();
                                    } catch (error) {
                                        alert('스크리닝 실행 중 오류 발생');
                                    } finally {
                                        setRunning(false);
                                    }
                                }}
                            >
                                {running ? 'Running...' : '🔄 Run Full Screener'}
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );

}
