// API utility functions

const API_BASE = '';  // Empty = use Next.js proxy

export async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache',
            ...options?.headers,
        }
    });
    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }
    return response.json();
}

// Types
export interface KRMarketGate {
    status: string;
    score: number;
    label: string;
    reasons: string[];
    sectors: Sector[];
    kospi_close?: number;
    kospi_change_pct?: number;
    kosdaq_close?: number;
    kosdaq_change_pct?: number;
}

export interface Sector {
    name: string;
    signal: string;
    change_pct: number;
    score: number;
}

export interface KRSignal {
    stock_code: string;
    stock_name: string;
    market: string;
    grade: string;
    score: ScoreDetail;
    checklist: ChecklistDetail;
    current_price: number;
    entry_price: number;
    stop_price: number;
    target_price: number;
    change_pct: number;
    trading_value: number;
    return_pct?: number;
    news_items?: NewsItem[];
}

export interface ScoreDetail {
    news: number;
    volume: number;
    chart: number;
    candle: number;
    consolidation: number;
    supply: number;
    llm_reason: string;
    total: number;
}

export interface ChecklistDetail {
    has_news: boolean;
    news_sources: string[];
    is_new_high: boolean;
    is_breakout: boolean;
    supply_positive: boolean;
    volume_surge: boolean;
}

export interface NewsItem {
    title: string;
    source: string;
    published_at: string;
    url: string;
}

export interface KRSignalsResponse {
    signals: KRSignal[];
    count: number;
    generated_at?: string;
}

export interface ScreenerResult {
    date: string;
    total_candidates: number;
    filtered_count: number;
    signals: KRSignal[];
    updated_at: string;
}

export interface BacktestStats {
    status: string;
    count: number;
    win_rate: number;
    avg_return: number;
    message?: string;
}

export interface BacktestSummary {
    vcp: BacktestStats;
    closing_bet: BacktestStats;
}

// API Functions
export const krAPI = {
    getMarketGate: () => fetchAPI<KRMarketGate>('/api/kr/market-gate'),
    refreshMarketGate: () => fetchAPI<KRMarketGate>('/api/kr/market-gate?refresh=true'),
    getMarketGateDates: () => fetchAPI<string[]>('/api/kr/market-gate/dates'),
    getMarketGateHistory: (date: string) => fetchAPI<KRMarketGate>(`/api/kr/market-gate/history/${date}`),
    getSignals: () => fetchAPI<KRSignalsResponse>('/api/kr/signals'),
    getAIAnalysis: () => fetchAPI<ScreenerResult>('/api/kr/ai-analysis'),
    getJonggaLatest: () => fetchAPI<ScreenerResult>('/api/kr/jongga-v2/latest'),
    getJonggaDates: () => fetchAPI<string[]>('/api/kr/jongga-v2/dates'),
    getJonggaHistory: (date: string) => fetchAPI<ScreenerResult>(`/api/kr/jongga-v2/history/${date}`),
    getBacktestSummary: () => fetchAPI<BacktestSummary>('/api/kr/backtest-summary'),
    getVCPDates: () => fetchAPI<string[]>('/api/kr/vcp/dates'),
    getVCPHistory: (date: string) => fetchAPI<ScreenerResult>(`/api/kr/vcp/history/${date}`),
    analyzePerformance: (date: string) => fetchAPI<PerformanceAnalysisResult>('/api/kr/performance/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date })
    }),
}; // End of krAPI

export interface DailyStat {
    date: string;
    close: number | null;
    return_pct: number | null;
}

export interface PerformanceRow {
    signal_info: KRSignal;
    daily_stats: DailyStat[];
}

export interface PerformanceAnalysisResult {
    dates: string[];
    rows: PerformanceRow[];
}

// === JP Market Types ===
export interface JPMarketGate {
    status: string;
    score: number;
    label: string;
    reasons: string[];
    sectors: Sector[];
    nikkei_close?: number;
    nikkei_change_pct?: number;
    topix_close?: number;
    topix_change_pct?: number;
    updated_at?: string;
}

export interface JPSignal {
    code: string;
    name: string;
    sector: string;
    market: string;
    close: number;
    change_pct: number;
    grade: string;
    score: number;
    target_price?: number;
    score_detail?: {
        news: number;
        volume: number;
        chart: number;
        candle: number;
        consolidation: number;
        supply: number;
        technical?: number; // Added
    };
    news?: { title: string; source: string }[];
}

export interface JPVCPResult {
    code: string;
    name: string;
    market: string;
    sector: string;
    score: number;
    grade: string;
    vcp_score: number;
    supply_score: number;
    contraction_ratio: number;
    foreign_5d: number;
    inst_5d: number;
    is_double_buy: boolean;
    current_price: number;
    change_pct: number;
    entry_price?: number;
    return_pct?: number;
    updated_at: string;
}

export interface JPSignalsResponse {
    signals: JPSignal[];
    filtered_count: number;
    total_scanned?: number;
    generated_at?: string;
}

export interface JPVCPResponse {
    signals: JPVCPResult[];
    total_count: number;
    updated_at: string;
    generated_at?: string;
}

export interface JPChartData {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

// === JP API Functions ===
export const jpAPI = {
    getMarketGate: () => fetchAPI<JPMarketGate>('/api/jp/market-gate'),
    refreshMarketGate: () => fetchAPI<JPMarketGate>('/api/jp/market-gate?refresh=true'),
    getMarketGateDates: () => fetchAPI<string[]>('/api/jp/market-gate/dates'),
    getMarketGateHistory: (date: string) => fetchAPI<JPMarketGate>(`/api/jp/market-gate/history/${date}`),
    getSignals: () => fetchAPI<JPSignalsResponse>('/api/jp/signals'),
    
    // Updated for Split View
    getJonggaLatest: (type: 'n225' | 'n400' = 'n225') => fetchAPI<JPSignalsResponse>(`/api/jp/jongga-v2/latest?type=${type}`),
    getJonggaDates: (type: 'n225' | 'n400' = 'n225') => fetchAPI<string[]>(`/api/jp/jongga-v2/dates?type=${type}`),
    getJonggaHistory: (date: string, type: 'n225' | 'n400' = 'n225') => fetchAPI<JPSignalsResponse>(`/api/jp/jongga-v2/history/${date}?type=${type}`),
    
    runScreener: (type: 'n225' | 'n400' | 'all' = 'all') => fetchAPI<{ status: string; message: string }>(`/api/jp/jongga-v2/run?type=${type}`, {
        method: 'POST',
    }),
    getBacktestSummary: () => fetchAPI<{ closing_bet: BacktestStats }>('/api/jp/backtest-summary'),
    getScreenerStatus: () => fetchAPI<{ isRunning: boolean; task: string; message: string }>('/api/jp/screener/status'),
    analyzePerformance: (date: string, type: 'n225' | 'n400' = 'n225') => fetchAPI<PerformanceAnalysisResult>('/api/jp/performance/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, type })
    }),
    getRealtimePrices: (tickers: string[]) => fetchAPI<Record<string, number>>('/api/jp/realtime-prices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers })
    }),
    getChartData: (code: string) => fetchAPI<JPChartData[]>(`/api/jp/chart/${code}`),
    getVCPLatest: () => fetchAPI<JPVCPResponse>('/api/jp/vcp/latest'),
    getVCPDates: () => fetchAPI<string[]>('/api/jp/vcp/dates'),
    getVCPHistory: (date: string) => fetchAPI<JPVCPResponse>(`/api/jp/vcp/history/${date}`),
    runVCPScreener: () => fetchAPI<{ status: string; message: string }>('/api/jp/vcp/run', {
        method: 'POST',
    }),
};
// === US Market Types ===
export interface USMarketGate {
    status: string;
    score: number;
    label: string;
    reasons: string[];
    sectors: Sector[];
    nasdaq_close?: number;
    nasdaq_change_pct?: number;
    sp500_close?: number;
    sp500_change_pct?: number;
    dow_close?: number;
    dow_change_pct?: number;
    updated_at?: string;
}

// === US API Functions ===
export const usAPI = {
    getMarketGate: () => fetchAPI<USMarketGate>('/api/us/market-gate'),
    refreshMarketGate: () => fetchAPI<USMarketGate>('/api/us/market-gate?refresh=true'),
    getMarketGateDates: () => fetchAPI<string[]>('/api/us/market-gate/dates'),
    getMarketGateHistory: (date: string) => fetchAPI<USMarketGate>(`/api/us/market-gate/history/${date}`),
    getBacktestSummary: () => fetchAPI<{ closing_bet: BacktestStats }>('/api/us/backtest-summary'),
};
