import React from 'react';

export default function ProgressBar({ count, max = 12 }) {
  const percentage = Math.min((count / max) * 100, 100);
  
  return (
    <div className="space-y-1.5 font-mono text-[11px] w-full">
      <div className="flex justify-between text-text-secondary">
        <span>AGENT TOOL USAGE</span>
        <span className="text-text-primary font-semibold">{count} / {max} calls</span>
      </div>
      <div className="h-1 bg-bg-elevated rounded-full overflow-hidden border border-border-subtle/30">
        <div 
          className="h-full bg-accent-blue transition-all duration-300 ease-out" 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
