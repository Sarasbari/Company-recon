import { useEffect, useRef } from 'react';

export default function StreamLog({ steps }) {
  const containerRef = useRef(null);

  // Auto-scroll the container to the bottom as new steps arrive without page jitter
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [steps]);

  return (
    <div 
      ref={containerRef}
      className="text-xs space-y-4 max-h-[600px] overflow-y-auto border border-border-subtle bg-bg-surface p-5 rounded-xl select-text scroll-smooth"
    >
      {steps.map((step, idx) => {
        if (step.type === 'reason') {
          return (
            <div 
              key={idx} 
              className="animate-fade-in-up text-text-secondary/80 italic leading-relaxed font-sans opacity-0"
            >
              {step.text}
            </div>
          );
        }
        
        if (step.type === 'action') {
          const isSearch = step.tool === 'web_search';
          const queryOrUrl = isSearch ? step.input?.query : step.input?.url;
          return (
            <div key={idx} className="animate-fade-in-up opacity-0">
              {isSearch ? (
                <div className="flex items-center gap-2 font-mono text-[11px] leading-relaxed bg-accent-blue/10 border border-accent-blue/20 text-accent-blue rounded px-2.5 py-1 w-fit">
                  <span className="flex-shrink-0 text-xs">🔍</span>
                  <span className="break-all">{queryOrUrl}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 font-mono text-[11px] leading-relaxed bg-[#B07DFF]/10 border border-[#B07DFF]/20 text-[#B07DFF] rounded px-2.5 py-1 w-fit">
                  <span className="flex-shrink-0 text-xs">🔗</span>
                  <span className="break-all">{queryOrUrl}</span>
                </div>
              )}
            </div>
          );
        }

        if (step.type === 'observation') {
          return (
            <div 
              key={idx} 
              className="animate-fade-in-up border-l border-accent-green pl-3 py-1 text-text-secondary leading-relaxed font-sans text-xs opacity-0"
            >
              <span className="text-accent-green font-bold mr-1.5">✓</span> {step.summary}
            </div>
          );
        }

        return null;
      })}
      
      {steps.length === 0 && (
        <div className="text-text-muted italic text-center py-12 font-sans">
          Establishing stream connection to intelligence agent...
        </div>
      )}
      
    </div>
  );
}
