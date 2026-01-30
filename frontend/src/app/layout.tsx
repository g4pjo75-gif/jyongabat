import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "종가베팅 V2 | AI Stock Analysis",
  description: "AI 기반 종가베팅 시그널 시스템",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased text-slate-200">
        <div className="main-layout font-sans">
          {/* Sidebar */}
          <aside className="sidebar">
            <div className="flex items-center gap-3 mb-10 px-2">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/20">
                CB
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight text-white leading-none">Closing Bet</h1>
                <p className="text-[10px] text-blue-400 font-semibold uppercase tracking-wider mt-1">AI Stock Analysis</p>
              </div>
            </div>

            <nav className="space-y-1">
              <SidebarLink href="/dashboard/kr" icon="🏠" label="Overview" />
              <SidebarLink href="/dashboard/kr/closing-bet" icon="📈" label="KR Market" />
              <SidebarLink href="/dashboard/kr/vcp" icon="📊" label="VCP Signals" />
              <SidebarLink href="/dashboard/kr/performance" icon="📅" label="History Analysis" />
              
              <div className="pt-4 pb-2 px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">🇯🇵 JP Market</div>
              <SidebarLink href="/dashboard/jp" icon="🗾" label="JP Overview" />
              <SidebarLink href="/dashboard/jp/n225" icon="🔴" label="Nikkei 225" />
              <SidebarLink href="/dashboard/jp/n400" icon="🟠" label="Nikkei 400 (Excl)" />
              <SidebarLink href="/dashboard/jp/vcp" icon="📊" label="JP VCP Signals" />
              <SidebarLink href="/dashboard/jp/performance" icon="📅" label="JP Performance" />
              
              <SidebarLink href="/dashboard/us" icon="🌎" label="US Market" />
              <SidebarLink href="#" icon="🌍" label="Economy" disabled />
            </nav>


            <div className="absolute bottom-8 left-4 right-4">
              <div className="glass-card p-4 bg-blue-600/10 border-blue-500/20">
                <div className="text-[10px] font-bold text-blue-400 uppercase mb-1">Database</div>
                <div className="text-xs text-slate-300">Connected to In-Memory</div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="content-area bg-[var(--bg-page)]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function SidebarLink({ href, icon, label, disabled = false }: { href: string; icon: string; label: string; disabled?: boolean }) {
  const isActive = typeof window !== 'undefined' && window.location.pathname === href;
  
  return (
    <a 
      href={disabled ? '#' : href} 
      className={`sidebar-link ${isActive ? 'active' : ''} ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className="text-xl">{icon}</span>
      <span className="flex-1">{label}</span>
      {isActive && <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
    </a>
  );
}

