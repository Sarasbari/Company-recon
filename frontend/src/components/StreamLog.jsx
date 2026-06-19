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
      className="text-xs space-y-4 max-h-[600px] overflow-y-auto border border-border-subtle bg-bg-elevated p-5 rounded-xl select-text scroll-smooth"
    >
      {steps.map((step, idx) => {
        if (step.type === 'reason') {
          return (
            <div key={idx} className="animate-fade-in-up text-text-secondary italic pl-3 border-l border-primary/30 py-0.5 leading-relaxed font-sans">
              {step.text}
            </div>
          );
        }
        
        if (step.type === 'action') {
          const isSearch = step.tool === 'web_search';
          const queryOrUrl = isSearch ? step.input?.query : step.input?.url;
          return (
            <div key={idx} className="animate-fade-in-up flex items-start gap-2.5 font-mono text-[11px] leading-relaxed">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold tracking-wider ${
                isSearch 
                  ? 'bg-primary/10 text-primary border border-primary/20' 
                  : 'bg-accent-clay/10 text-accent-clay border border-accent-clay/20'
              }`}>
                {isSearch ? 'SEARCH' : 'FETCH'}
              </span>
              <span className="text-text-primary self-center break-all">
                {queryOrUrl}
              </span>
            </div>
          );
        }

        if (step.type === 'observation') {
          return (
            <div key={idx} className="animate-fade-in-up border-l-2 border-accent-sage bg-bg-surface pl-3 py-2 text-text-secondary leading-relaxed rounded-r font-sans">
              <span className="text-primary font-bold mr-1">✓</span> {step.summary}
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
