import React from 'react';

interface GuideSection {
    title: string;
    content: React.ReactNode;
}

interface GuideModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    sections: GuideSection[];
}

export default function GuideModal({ isOpen, onClose, title, sections }: GuideModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={onClose}>
            <div 
                className="w-full max-w-2xl bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
                    <div className="flex items-center gap-2">
                        <span className="text-2xl">📘</span>
                        <h2 className="text-xl font-bold">{title}</h2>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-2 text-[var(--text-secondary)] hover:text-white rounded-full hover:bg-[var(--hover-bg)] transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    <div className="space-y-8">
                        {sections.map((section, idx) => (
                            <div key={idx} className="space-y-3">
                                <h3 className="text-lg font-bold text-blue-400 flex items-center gap-2">
                                    <span className="w-1.5 h-6 bg-blue-500 rounded-full"></span>
                                    {section.title}
                                </h3>
                                <div className="pl-3.5 border-l border-[var(--border-color)] ml-0.5">
                                    <div className="text-[var(--text-secondary)] leading-relaxed space-y-2">
                                        {section.content}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex justify-end">
                    <button 
                        onClick={onClose}
                        className="px-6 py-2.5 bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/20"
                    >
                        확인
                    </button>
                </div>
            </div>
        </div>
    );
}
