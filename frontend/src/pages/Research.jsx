import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../components/ClerkWrapper';
import { AlertCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import StreamLog from '../components/StreamLog';
import ProgressBar from '../components/ProgressBar';
import DossierReport from '../components/DossierReport';
import AuthBanner from '../components/AuthBanner';

const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function Research() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { isSignedIn } = useAuth();
  
  const [steps, setSteps] = useState([]);
  const [dossier, setDossier] = useState(null);
  const [status, setStatus] = useState('pending'); // pending | running | complete | failed
  const [error, setError] = useState(null);
  const [streamCollapsed, setStreamCollapsed] = useState(false);
  const [toolCallsCount, setToolCallsCount] = useState(0);
  const [companyName, setCompanyName] = useState('');

  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    let eventSource = null;
    let isActive = true;

    const checkJobStatus = async () => {
      try {
        const res = await fetch(`${apiUrl}/research/${jobId}`);
        if (!res.ok) {
          throw new Error('Research job not found');
        }
        const data = await res.json();
        
        if (!isActive) return;

        if (data.status === 'complete') {
          setDossier(data.dossier);
          setCompanyName(data.dossier.company);
          setStatus('complete');
          setToolCallsCount(data.dossier.agent_metadata?.tool_calls || 0);
          setStreamCollapsed(true);
        } else if (data.status === 'failed') {
          setStatus('failed');
          setError(data.error || 'Research execution failed.');
        } else {
          setStatus(data.status);
          connectSSE();
        }
      } catch (e) {
        if (isActive) {
          setError(e.message);
          setStatus('failed');
        }
      }
    };

    const connectSSE = () => {
      eventSource = new EventSource(`${apiUrl}/research/${jobId}/stream`);

      eventSource.onmessage = (event) => {
        if (!isActive) return;
        
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'start') {
            setStatus('running');
            setCompanyName(data.company);
          } else if (data.type === 'reason') {
            setSteps(prev => [...prev, { type: 'reason', text: data.text }]);
          } else if (data.type === 'action') {
            setToolCallsCount(prev => prev + 1);
            setSteps(prev => [...prev, { type: 'action', tool: data.tool, input: data.input }]);
          } else if (data.type === 'observation') {
            setSteps(prev => [...prev, { type: 'observation', tool: data.tool, summary: data.summary }]);
          } else if (data.type === 'complete') {
            setDossier(data.dossier);
            setCompanyName(data.dossier.company);
            setStatus('complete');
            setStreamCollapsed(true);
            eventSource.close();
          } else if (data.type === 'error') {
            setError(data.message);
            setStatus('failed');
            eventSource.close();
          }
        } catch (err) {
          console.error("Failed to parse SSE message", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE stream connection error", err);
        if (statusRef.current !== 'complete') {
          eventSource.close();
        }
      };
    };

    checkJobStatus();

    return () => {
      isActive = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [jobId]);

  const handleResearchAgain = () => {
    navigate('/', { replace: true });
  };

  const renderBlocks = (count, max = 12) => {
    const filled = '■'.repeat(Math.min(count, max));
    const empty = '□'.repeat(Math.max(0, max - count));
    return `${filled}${empty}`;
  };

  const getSectionStatus = (sec, count) => {
    if (count === 0) return 'Waiting...';
    switch (sec) {
      case 'Overview':
        if (count >= 3) return 'Discovered ✓';
        return 'Populating...';
      case 'Funding':
        if (count < 3) return 'Waiting...';
        if (count >= 6) return 'Discovered ✓';
        return 'Populating...';
      case 'Key People':
        if (count < 6) return 'Waiting...';
        if (count >= 8) return 'Discovered ✓';
        return 'Populating...';
      case 'Recent News':
        if (count < 8) return 'Waiting...';
        if (count >= 10) return 'Discovered ✓';
        return 'Populating...';
      case 'Talking Points':
        if (count < 10) return 'Waiting...';
        return 'Synthesizing...';
      default:
        return 'Waiting...';
    }
  };

  return (
    <div className="min-h-[calc(100dvh-56px)] max-w-7xl mx-auto px-6 mt-8 space-y-8 bg-bg-primary">
      {/* Auth Banner Callout for Guests */}
      {status === 'complete' && !isSignedIn && (
        <div className="max-w-4xl mx-auto w-full animate-fade-in opacity-0">
          <AuthBanner />
        </div>
      )}

      {/* Status Banner for Registered Users */}
      {status === 'complete' && isSignedIn && (
        <div className="max-w-4xl mx-auto w-full bg-accent-green/10 border border-primary/20 text-accent-green rounded-lg p-3.5 text-xs font-mono flex items-center justify-between animate-pulse-once">
          <span>Dossier successfully saved to persistent archive history ✓</span>
        </div>
      )}

      {/* Columns Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start w-full">
        
        {/* Stream Log / Summary Bar */}
        <div className={`space-y-4 lg:col-span-12 ${status === 'complete' && streamCollapsed ? 'w-full' : 'lg:col-span-5'} transition-all duration-300`}>
          {status === 'complete' && streamCollapsed ? (
            <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 flex flex-row items-center justify-between gap-4 shadow-sm w-full font-mono text-xs">
              <div className="flex flex-wrap items-center gap-3 text-text-secondary">
                <span className="bg-accent-green/10 text-accent-green border border-accent-green/20 px-2 py-0.5 rounded font-semibold text-[10px] tracking-wider select-none">COMPLETE</span>
                <span>•</span>
                <span>{steps.length} steps</span>
                <span>•</span>
                <span>{dossier?.agent_metadata?.duration_seconds || 0}s elapsed</span>
                <span>•</span>
                <span>{toolCallsCount} tool calls</span>
              </div>
              <button
                onClick={() => setStreamCollapsed(false)}
                className="text-primary hover:text-accent-sage flex items-center gap-1 font-semibold cursor-pointer transition-colors duration-150"
              >
                Expand Log
                <ChevronDown size={14} />
              </button>
            </div>
          ) : (
            <div className="bg-bg-surface border border-border-subtle rounded-xl p-5 space-y-4 shadow-sm w-full animate-fade-in">
              <div className="flex items-center justify-between border-b border-border-subtle/60 pb-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-mono font-semibold text-[10px] tracking-wider uppercase text-text-secondary">
                    Agent Logs
                  </h3>
                  {status === 'complete' && (
                    <span className="bg-accent-green/10 text-accent-green border border-accent-green/20 px-1.5 py-0.5 rounded font-semibold text-[8px] tracking-wider select-none">COMPLETE</span>
                  )}
                </div>
                {status === 'complete' && (
                  <button
                    onClick={() => setStreamCollapsed(true)}
                    className="text-text-secondary hover:text-primary flex items-center gap-1 text-[11px] font-mono cursor-pointer transition-colors duration-150"
                  >
                    Collapse Log
                    <ChevronUp size={12} />
                  </button>
                )}
              </div>
              <div className="space-y-4">
                <StreamLog steps={steps} />
                {status !== 'complete' && status !== 'failed' && (
                  <ProgressBar count={toolCallsCount} />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Dossier Report or Dossier Preview / Loader */}
        <div className={`w-full ${status === 'complete' && streamCollapsed ? 'lg:col-span-12' : 'lg:col-span-7'} min-h-[400px] transition-all duration-300`}>
          {status === 'complete' && dossier ? (
            <DossierReport dossier={dossier} onResearchAgain={handleResearchAgain} />
          ) : status === 'failed' ? (
            <div className="bg-bg-surface border border-accent-red/20 rounded-xl p-8 max-w-md mx-auto text-center space-y-5 animate-fade-in shadow-md w-full">
              <AlertCircle className="text-accent-red mx-auto animate-pulse" size={42} />
              <h3 className="font-display font-medium text-xl text-text-primary">Research Failed</h3>
              <p className="text-sm text-text-secondary leading-relaxed font-sans">{error || 'An unexpected error occurred during research execution.'}</p>
              <button
                onClick={handleResearchAgain}
                className="bg-primary hover:bg-accent-sage text-bg-elevated hover:text-text-primary text-xs font-sans font-semibold py-2 px-5 rounded-lg transition-all duration-150 ease-out active:scale-[0.97] cursor-pointer shadow-sm"
              >
                Back to Search
              </button>
            </div>
          ) : (
            /* Dossier Preview Sidebar */
            <div className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8 space-y-6 w-full max-w-xl mx-auto shadow-sm animate-fade-in">
              <div className="border-b border-border-subtle pb-4">
                <h2 className="font-display font-semibold text-2xl text-text-primary tracking-tight">
                  {companyName || 'Prospect Research'}
                </h2>
                <p className="text-xs text-text-secondary font-sans mt-1.5 flex items-center gap-1.5">
                  <Loader2 className="animate-spin text-primary" size={12} />
                  Researching prospect intelligence...
                </p>
              </div>
              
              <div className="bg-bg-surface border border-border-subtle/60 rounded-lg p-4 space-y-3">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-text-secondary uppercase tracking-wider text-[10px]">Progress</span>
                  <span className="text-text-primary font-semibold">{toolCallsCount} / 12 calls</span>
                </div>
                <div className="font-mono text-xs text-primary tracking-wider select-none leading-none">
                  {renderBlocks(toolCallsCount)}
                </div>
              </div>
              
              <div className="space-y-3 font-sans text-xs">
                <h4 className="font-mono font-semibold text-[10px] tracking-wider uppercase text-text-muted">Dossier Structure</h4>
                <div className="divide-y divide-border-subtle/40 border border-border-subtle/50 rounded-lg overflow-hidden">
                  {['Overview', 'Funding', 'Key People', 'Recent News', 'Talking Points'].map((sec) => {
                    const secStatus = getSectionStatus(sec, toolCallsCount);
                    const isComplete = secStatus.includes('✓');
                    const isWorking = secStatus === 'Populating...' || secStatus === 'Synthesizing...';
                    return (
                      <div key={sec} className="flex justify-between items-center p-3 bg-bg-surface/30">
                        <span className="text-text-primary font-medium">{sec}</span>
                        <span className={`font-mono text-[10px] ${
                          isComplete ? 'text-accent-green font-semibold' : 
                          isWorking ? 'text-primary font-medium animate-pulse' : 'text-text-muted'
                        }`}>
                          {secStatus}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
