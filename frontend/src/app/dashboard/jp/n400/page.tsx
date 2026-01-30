'use client';

import JPSignalsPage from '@/components/JPSignalsPage';

export default function N400Page() {
    return (
        <JPSignalsPage 
            type="n400" 
            title="🇯🇵 Nikkei 400 (Excl) Signals" 
            description="JPX Nikkei 400 (Excluding 225) AI Closing Bet (Top 30)" 
        />
    );
}
