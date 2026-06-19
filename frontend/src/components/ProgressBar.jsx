export default function ProgressBar({ count, max = 12 }) {
  const percentage = Math.min((count / max) * 100, 100);
  
  return (
    <div className="space-y-1.5 font-sans text-[11px] w-full">
      <div className="flex justify-between text-text-secondary font-mono text-[10px] tracking-wider uppercase">
        <span>AGENT TOOL USAGE</span>
        <span className="text-text-primary font-semibold">{count} / {max} calls</span>
      </div>
      <div className="h-2 bg-bg-primary rounded-full overflow-hidden border border-border-subtle/50">
        <div 
          className="h-full bg-primary transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] rounded-full" 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
