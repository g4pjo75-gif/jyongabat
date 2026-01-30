'use client';

import { useState, useEffect } from 'react';
import { usAPI, USMarketGate, Sector } from '@/lib/api';
import GuideModal from '@/components/GuideModal';

interface MarketGateWithUpdate extends USMarketGate {
    updated_at?: string;
}

export default function USMarketOverview() {
    const [marketGate, setMarketGate] = useState<MarketGateWithUpdate | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [showGuide, setShowGuide] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [gateData, dates] = await Promise.all([
                    usAPI.getMarketGate(),
                    usAPI.getMarketGateDates(),
                ]);
                setMarketGate(gateData as MarketGateWithUpdate);
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
                const gateData = await usAPI.getMarketGate();
                setMarketGate(gateData as MarketGateWithUpdate);
            } else {
                const gateData = await usAPI.getMarketGateHistory(dateStr);
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
            const gateData = await usAPI.refreshMarketGate();
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
                <div className="text-2xl text-[var(--text-secondary)]">Loading US Market Data...</div>
            </div>
        );
    }

    return (
        <div className="space-y-10">
            {/* Top Bar */}
            <div className="flex justify-between items-center mb-2">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight">🇺🇸 US Market Overview (미국 시장 요약)</h1>
                    <p className="text-sm text-slate-500 font-medium mt-1">
                        {marketGate?.updated_at 
                            ? `마지막 업데이트: ${new Date(marketGate.updated_at).toLocaleString('ko-KR')}`
                            : 'Wall Street - 나스닥, S&P 500 & 다우 지수'
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
                        <option value="">최신 결과</option>
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
                            {refreshing ? '갱신 중...' : '새로고침'}
                        </span>
                    </button>
                </div>
            </div>

            {/* Market Gate Section */}
            <section className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Gate Score Card */}
                <div className="glass-card p-8 relative overflow-hidden flex flex-col justify-between min-h-[200px]">
                    <div className={`absolute top-0 right-0 w-48 h-48 rounded-full blur-[100px] opacity-20 ${
                        marketGate?.status === 'GREEN' ? 'bg-emerald-500' : 
                        marketGate?.status === 'RED' ? 'bg-rose-500' : 'bg-amber-500'
                    }`} />
                    
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">
                            Security Gate Status (시장 보안 게이트)
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
                            {marketGate?.label ?? '보합'}
                        </div>
                    </div>
                </div>

                {/* NASDAQ Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">나스닥 (NASDAQ)</h2>
                        <div className="text-3xl font-black text-white">{marketGate?.nasdaq_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.nasdaq_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.nasdaq_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.nasdaq_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>

                {/* S&P 500 Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">S&P 500</h2>
                        <div className="text-3xl font-black text-white">{marketGate?.sp500_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.sp500_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.sp500_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.sp500_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>

                {/* DOW Widget */}
                <div className="glass-card p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6">다우 지수 (DOW)</h2>
                        <div className="text-3xl font-black text-white">{marketGate?.dow_close?.toLocaleString() ?? '-'}</div>
                    </div>
                    <div className={`flex items-center gap-2 font-bold ${
                        (marketGate?.dow_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                        <span className="text-lg">{(marketGate?.dow_change_pct ?? 0) >= 0 ? '▲' : '▼'}</span>
                        <span className="text-2xl">{Math.abs(marketGate?.dow_change_pct ?? 0).toFixed(2)}%</span>
                    </div>
                </div>
            </section>

            {/* Main Content Area */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Sector Momentum */}
                <section className="xl:col-span-2">
                    <div className="flex justify-between items-end mb-6">
                        <h2 className="text-xl font-black text-white px-2">섹터 모멘텀 (Sector Momentum)</h2>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">주요 섹터 (ETF)</span>
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
                                    섹터 데이터가 없습니다.
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* Actions Placeholder */}
                <section className="space-y-8">
                    <div className="glass-card p-8 bg-gradient-to-br from-indigo-600/10 to-blue-600/10 border-indigo-500/20">
                        <h2 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-6">준비 중</h2>
                        <div className="space-y-4">
                            <div className="w-full py-4 rounded-xl font-black text-xs uppercase bg-slate-800 text-slate-500 flex items-center justify-center gap-2 cursor-not-allowed">
                                📊 US 종가베팅 (개발 중)
                            </div>
                            <div className="w-full py-4 rounded-xl font-black text-xs uppercase bg-slate-800 text-slate-500 flex items-center justify-center gap-2 cursor-not-allowed">
                                🔄 US 스크리너 실행
                            </div>
                            <p className="text-[10px] text-slate-500 text-center px-4 leading-relaxed">
                                US 시장 종가베팅 전략 및 스크리너 로직은 현재 개발 중입니다.
                                실시간 지수 트래킹 및 섹터 모멘텀은 활성화되어 있습니다.
                            </p>
                        </div>
                    </div>
                </section>
            </div>

            <GuideModal
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
                title="미국 시장 개요 가이드"
                sections={[
                    {
                        title: "🗽 시장 게이트 (Market Gate)",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><strong>나스닥 & S&P 500</strong>: 시장의 방향성을 결정하는 핵심 지수입니다.</li>
                                <li><strong>점수 (0-100)</strong>: 종합적인 시장 건강도 점수입니다.</li>
                                <li><strong>초록색 (GREEN)</strong>: 긍정적 모멘텀. 적극적인 트레이딩이 가능합니다.</li>
                                <li><strong>빨간색 (RED)</strong>: 높은 리스크. 방어적인 포지션을 권장합니다.</li>
                            </ul>
                        )
                    },
                    {
                        title: "📈 섹터 ETF",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><strong>XLK, XLF 등</strong>: 월스트리트의 표준 섹터 ETF들을 추적합니다.</li>
                                <li>오늘 어떤 섹터가 시장을 주도하고 있는지 확인할 수 있습니다.</li>
                            </ul>
                        )
                    }
                ]}
            />
        </div>
    );
}
