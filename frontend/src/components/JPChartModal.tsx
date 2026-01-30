'use client';

import { useState, useEffect } from 'react';
import { jpAPI, JPChartData } from '@/lib/api';

interface JPChartModalProps {
    symbol: string;
    name: string;
    onClose: () => void;
}

export default function JPChartModal({ symbol, name, onClose }: JPChartModalProps) {
    const [chartData, setChartData] = useState<JPChartData[]>([]);
    const [loading, setLoading] = useState(true);
    const ticker = symbol.replace('.T', '');

    useEffect(() => {
        const fetchChart = async () => {
            try {
                const data = await jpAPI.getChartData(ticker);
                setChartData(data);
            } catch (err) {
                console.error('Failed to fetch chart data:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchChart();
    }, [ticker]);

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content max-w-5xl" onClick={(e) => e.stopPropagation()}>
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">{name} ({ticker})</h2>
                    <button 
                        onClick={onClose}
                        className="text-2xl text-[var(--text-secondary)] hover:text-white"
                    >
                        ×
                    </button>
                </div>
                
                <div className="bg-slate-900 rounded-xl overflow-hidden border border-white/5 mb-4 min-h-[450px] relative">
                    {loading ? (
                        <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                             차트 데이터를 불러오는 중...
                        </div>
                    ) : (
                        <JPStockChart data={chartData} />
                    )}
                </div>

                <div className="flex justify-between items-center">
                   <div className="text-xs text-slate-500">
                      * 최근 180일간의 일봉 차트입니다.
                   </div>
                   <a 
                        href={`https://finance.yahoo.co.jp/quote/${ticker}.T`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-rose-400 hover:underline"
                    >
                        Yahoo Finance에서 더 자세히 보기 →
                    </a>
                </div>
            </div>
        </div>
    );
}

// Custom Candlestick Chart Component (Canvas)
function JPStockChart({ data }: { data: JPChartData[] }) {
    const canvasRef = (canvas: HTMLCanvasElement | null) => {
        if (!canvas || data.length === 0) return;
        
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Clear
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;

        const maxPrice = Math.max(...data.map(d => d.high));
        const minPrice = Math.min(...data.map(d => d.low));
        const priceRange = maxPrice - minPrice;

        const barWidth = chartWidth / data.length;
        const candleWidth = barWidth * 0.7;

        const getY = (price: number) => {
            return padding + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
        };

        // Grid lines
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight / 4) * i;
            const price = maxPrice - (priceRange / 4) * i;
            
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px sans-serif';
            ctx.fillText(Math.round(price).toLocaleString(), width - padding + 5, y + 3);
        }

        // Candles
        data.forEach((d, i) => {
            const x = padding + i * barWidth + barWidth / 2;
            const openY = getY(d.open);
            const closeY = getY(d.close);
            const highY = getY(d.high);
            const lowY = getY(d.low);

            const isUp = d.close >= d.open;
            const color = isUp ? '#f87171' : '#60a5fa'; // JP color: Red for Up, Blue for Down

            // Wick
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, highY);
            ctx.lineTo(x, lowY);
            ctx.stroke();

            // Body
            ctx.fillStyle = color;
            const rectHeight = Math.max(1, Math.abs(closeY - openY));
            ctx.fillRect(x - candleWidth / 2, Math.min(openY, closeY), candleWidth, rectHeight);
        });

        // Dates (Sampled)
        ctx.fillStyle = '#64748b';
        const sampleCount = 4;
        for (let i = 0; i < sampleCount; i++) {
            const idx = Math.floor((data.length - 1) * (i / (sampleCount - 1)));
            const d = data[idx];
            const x = padding + idx * barWidth + barWidth / 2;
            const dateStr = d.date.split('-').slice(1).join('/'); // MM/DD
            ctx.fillText(dateStr, x - 15, height - padding + 15);
        }
    };

    return (
        <canvas 
            ref={canvasRef} 
            width={900} 
            height={450} 
            className="w-full h-full"
        />
    );
}
