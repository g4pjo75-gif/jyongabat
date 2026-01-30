'use client';

import JPSignalsPage from '@/components/JPSignalsPage';

export default function N225Page() {
    return (
        <JPSignalsPage 
            type="n225" 
            title="🇯🇵 Nikkei 225 Signals" 
            description="Nikkei 225 Constituents AI Closing Bet (Top 30)" 
        />
    );
}
