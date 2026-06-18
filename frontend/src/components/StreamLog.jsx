import React, { useEffect, useRef } from 'react';

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
      className="font-mono text-xs space-y-4 max-h-[600px] overflow-y-auto border border-border-subtle bg-bg-surface p-4 rounded select-text scroll-smooth"
    >
      {steps.map((step, idx) => {
        if (step.type === 'reason') {
          return (
            <div key={idx} className="animate-fade-in-up text-text-secondary italic pl-2 border-l border-border-subtle/50 py-0.5 leading-relaxed">
              {step.text}
            </div>
          );
        }
        
        if (step.type === 'action') {
          const isSearch = step.tool === 'web_search';
          const queryOrUrl = isSearch ? step.input?.query : step.input?.url;
          return (
            <div key={idx} className="animate-fade-in-up flex items-start gap-2">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                isSearch 
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20' 
                  : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
              }`}>
                {isSearch ? '🔍 SEARCH' : '🔗 FETCH'}
              </span>
              <span className="text-text-primary self-center break-all">
                {queryOrUrl}
              </span>
            </div>
          );
        }

        if (step.type === 'observation') {
          return (
            <div key={idx} className="animate-fade-in-up border-l-2 border-accent-green bg-accent-green/5 pl-3 py-2 text-text-secondary leading-relaxed rounded-r">
              <span className="text-accent-green font-bold mr-1">✓</span> {step.summary}
            </div>
          );
        }

        return null;
      })}
      
      {steps.length === 0 && (
        <div className="text-text-muted italic text-center py-12">
          Establishing stream connection to intelligence agent...
        </div>
      )}
      
    </div>
  );
}
