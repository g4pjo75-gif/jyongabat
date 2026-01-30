'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { jpAPI, PerformanceAnalysisResult, PerformanceRow, DailyStat } from '@/lib/api';
import GuideModal from '@/components/GuideModal';
import JPChartModal from '@/components/JPChartModal';

export default function JPPerformancePage() {
    const [targetType, setTargetType] = useState<'n225' | 'n400'>('n225');
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [result, setResult] = useState<PerformanceAnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [selectedGrade, setSelectedGrade] = useState<string | null>(null);
    const [showGuide, setShowGuide] = useState(false);
    const [chartModal, setChartModal] = useState<{isOpen: boolean; symbol: string; name: string}>({
        isOpen: false, symbol: '', name: ''
    });

    // Initial Date Fetch
    useEffect(() => {
        const fetchDates = async () => {
            try {
                const dates = await jpAPI.getJonggaDates(targetType);
                setAvailableDates(dates);
                // Reset selection when type changes
                setSelectedDate('');
                setResult(null);
            } catch (e) {
                console.error("Failed to fetch dates", e);
            }
        };
        fetchDates();
    }, [targetType]);

    const handleDateChange = async (dateStr: string) => {
        setSelectedDate(dateStr);
        if (!dateStr) {
            setResult(null);
            return;
        }

        setLoading(true);
        try {
            const data = await jpAPI.analyzePerformance(dateStr, targetType);
            setResult(data);
        } catch (e) {
            console.error("Analysis failed", e);
            alert("분석 데이터를 가져오는데 실패했습니다.");
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    // Helper to get stat for a date
    const getStat = (row: PerformanceRow, date: string): DailyStat | undefined => {
        return row.daily_stats.find(d => d.date === date);
    };

    const filteredRows = result?.rows.filter(row => 
        !selectedGrade || row.signal_info.grade === selectedGrade
    ) || [];

    return (
        <div className="min-h-screen bg-[var(--bg-page)] p-8">
            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="flex items-center gap-4 mb-2">
                        <Link href="/dashboard/jp" className="text-[var(--text-secondary)] hover:text-white">
                            ← Back
                        </Link>
                        <h1 className="text-3xl font-bold">🇯🇵 JP 성과 분석</h1>
                    </div>
                    <p className="text-[var(--text-secondary)]">
                        과거 시그널 포착 이후의 일본 주식 흐름 추적
                    </p>
                </div>
                
                <button
                    onClick={() => setShowGuide(true)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:border-rose-500/50 rounded-lg transition-all"
                >
                    <span>📘</span>
                    <span>사용 가이드</span>
                </button>
            </header>

            {/* Controls */}
            <div className="flex flex-wrap gap-4 mb-8 items-center bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-primary)]">
                {/* Target Toggle */}
                <div className="flex bg-black/20 p-1 rounded-lg">
                    <button
                        onClick={() => setTargetType('n225')}
                        className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                            targetType === 'n225' 
                            ? 'bg-blue-600 text-white shadow-lg' 
                            : 'text-slate-400 hover:text-white'
                        }`}
                    >
                        Nikkei 225
                    </button>
                    <button
                        onClick={() => setTargetType('n400')}
                        className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                            targetType === 'n400' 
                            ? 'bg-blue-600 text-white shadow-lg' 
                            : 'text-slate-400 hover:text-white'
                        }`}
                    >
                        Nikkei 400 (Excl)
                    </button>
                </div>

                <div className="h-6 w-px bg-white/10 mx-2" />

                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-400">포착일:</span>
                    <select 
                        value={selectedDate}
                        onChange={(e) => handleDateChange(e.target.value)}
                        className="bg-[var(--bg-elevated)] text-white px-4 py-2 rounded-lg border border-[var(--border-primary)] min-w-[160px]"
                    >
                        <option value="">날짜 선택</option>
                        {availableDates.map(date => (
                            <option key={date} value={date}>{date}</option>
                        ))}
                    </select>
                </div>

                <div className="h-6 w-px bg-white/10 mx-2" />

                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-400">등급 필터:</span>
                    <div className="flex gap-1">
                        {['S', 'A', 'B', 'C'].map(grade => (
                            <button
                                key={grade}
                                onClick={() => setSelectedGrade(prev => prev === grade ? null : grade)}
                                className={`px-3 py-1 rounded-lg text-sm font-bold transition-all ${
                                    selectedGrade === grade 
                                    ? grade === 'S' ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 
                                      grade === 'A' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50' :
                                      grade === 'B' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' :
                                      'bg-gray-500/20 text-gray-400 border border-gray-500/50'
                                    : 'bg-white/5 text-slate-500 hover:bg-white/10'
                                }`}
                            >
                                {grade}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {loading ? (
                 <div className="flex flex-col items-center justify-center h-64">
                    <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                    <div className="text-slate-400">과거 데이터를 분석 중입니다...</div>
                 </div>
            ) : result ? (
                <div className="glass-card overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="bg-white/5 border-b border-white/10 text-left">
                                    <th className="p-4 sticky left-0 bg-[#1e1e24] z-10 w-[200px]">종목</th>
                                    <th className="p-4 w-[80px]">등급</th>
                                    <th className="p-4 w-[80px]">점수</th>
                                    <th className="p-4 w-[120px] text-right border-r border-white/10">포착가</th>
                                    {result.dates.map(date => (
                                        <th key={date} className="p-4 min-w-[140px] text-center border-r border-white/5">
                                            <div className="text-xs text-slate-500">{date.slice(5)} ({getMetaDate(date)})</div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {filteredRows.map((row, i) => (
                                    <tr key={i} className="hover:bg-white/5 transition-colors">
                                        <td 
                                            className="p-4 sticky left-0 bg-[#1e1e24] z-10 border-r border-white/10 cursor-pointer hover:bg-white/10"
                                            onClick={() => setChartModal({
                                                isOpen: true,
                                                symbol: row.signal_info.stock_code,
                                                name: row.signal_info.stock_name
                                            })}
                                        >
                                            <div className="font-bold flex items-center gap-2">
                                                {row.signal_info.stock_name}
                                                <span className="text-[10px] text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity">📈</span>
                                            </div>
                                            <div className="text-xs text-slate-500">{row.signal_info.stock_code}</div>
                                        </td>
                                        <td className="p-4">
                                            <span className={`font-bold ${
                                                row.signal_info.grade === 'S' ? 'text-red-400' :
                                                row.signal_info.grade === 'A' ? 'text-purple-400' :
                                                row.signal_info.grade === 'B' ? 'text-emerald-400' : 'text-gray-400'
                                            }`}>
                                                {row.signal_info.grade}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-400">
                                            {typeof row.signal_info.score === 'object' ? row.signal_info.score.total : row.signal_info.score}
                                        </td>
                                        <td className="p-4 text-right font-mono text-slate-300 border-r border-white/10">
                                            {(row.signal_info.entry_price || row.signal_info.current_price)?.toLocaleString()}
                                        </td>
                                        {result.dates.map(date => {
                                            const stat = getStat(row, date);
                                            const isPositive = (stat?.return_pct || 0) > 0;
                                            const isZero = (stat?.return_pct || 0) === 0;
                                            const isEntryDate = date === selectedDate;
                                            
                                            return (
                                                <td key={date} className="p-3 text-center border-r border-white/5 bg-white/[0.01]">
                                                    {stat?.close ? (
                                                        <div>
                                                            <div className="text-xs text-slate-400 mb-1">
                                                                {stat.close.toLocaleString()}
                                                            </div>
                                                            {!isEntryDate && (
                                                                <div className={`font-bold ${
                                                                    isPositive ? 'text-emerald-400' : 
                                                                    isZero ? 'text-slate-500' : 'text-rose-400'
                                                                }`}>
                                                                    {isPositive ? '+' : ''}{stat.return_pct?.toFixed(2)}%
                                                                </div>
                                                            )}
                                                            {isEntryDate && (
                                                                <div className="text-[10px] bg-white/10 inline-block px-1 rounded text-slate-400">
                                                                    기준일
                                                                </div>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-slate-600">-</span>
                                                    )}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500 glass-card">
                    <div className="text-4xl mb-4">📅</div>
                    <div>분석할 기준 날짜를 선택해주세요.</div>
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
                title="JP 성과 분석 사용 가이드"
                sections={[
                    {
                        title: "📅 분석 방법",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><strong>기준 날짜 선택</strong>: 과거 스크리너 실행일을 선택합니다.</li>
                                <li>해당 날짜에 포착된 시그널의 이후 주가 흐름을 추적합니다.</li>
                                <li>포착가 대비 수익률이 일별로 표시됩니다.</li>
                            </ul>
                        )
                    },
                    {
                        title: "📊 테이블 해석",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li><span className="text-emerald-400">초록색 (+%)</span>: 포착가 대비 상승</li>
                                <li><span className="text-rose-400">빨간색 (-%))</span>: 포착가 대비 하락</li>
                                <li><strong>기준일</strong>: 시그널 포착일 (수익률 0%)</li>
                            </ul>
                        )
                    },
                    {
                        title: "🎯 활용 팁",
                        content: (
                            <ul className="list-disc list-inside space-y-1">
                                <li>등급별 필터로 S/A급 시그널의 성과를 비교하세요.</li>
                                <li>데이터가 누적될수록 승률 통계가 더 정확해집니다.</li>
                                <li>최소 2일 이상의 데이터가 필요합니다.</li>
                            </ul>
                        )
                    }
                ]}
            />
        </div>
    );
}

function getMetaDate(dateString: string) {
    const d = new Date(dateString);
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    return days[d.getDay()];
}
