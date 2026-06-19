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
          setStatus('complete');
          setToolCallsCount(data.dossier.agent_metadata?.tool_calls || 0);
          setStreamCollapsed(false);
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
          } else if (data.type === 'reason') {
            setSteps(prev => [...prev, { type: 'reason', text: data.text }]);
          } else if (data.type === 'action') {
            setToolCallsCount(prev => prev + 1);
            setSteps(prev => [...prev, { type: 'action', tool: data.tool, input: data.input }]);
          } else if (data.type === 'observation') {
            setSteps(prev => [...prev, { type: 'observation', tool: data.tool, summary: data.summary }]);
          } else if (data.type === 'complete') {
            setDossier(data.dossier);
            setStatus('complete');
            setStreamCollapsed(false);
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

  return (
    <div className="min-h-[calc(100vh-56px)] max-w-7xl mx-auto px-6 mt-8 space-y-8 bg-bg-primary">
      {/* Auth Banner Callout for Guests */}
      {status === 'complete' && !isSignedIn && (
        <div className="max-w-4xl mx-auto w-full animate-fade-in">
          <AuthBanner />
        </div>
      )}

      {/* Status Banner for Registered Users */}
      {status === 'complete' && isSignedIn && (
        <div className="max-w-4xl mx-auto w-full bg-accent-sage/10 border border-primary/20 text-primary rounded-lg p-3.5 text-xs font-mono flex items-center justify-between animate-pulse-once">
          <span>Dossier successfully saved to persistent archive history ✓</span>
        </div>
      )}

      {/* Columns Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start w-full">
        
        {/* Left Side: Agent Logs Stream */}
        <div className={`space-y-4 lg:col-span-4 ${status === 'complete' && streamCollapsed ? 'lg:col-span-3' : 'lg:col-span-5'} w-full transition-all duration-500`}>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-border-subtle/60 pb-3">
              <h3 className="font-mono font-semibold text-[10px] tracking-wider uppercase text-text-secondary">
                Agent Logs
              </h3>
              {status === 'complete' && (
                <button
                  onClick={() => setStreamCollapsed(!streamCollapsed)}
                  className="text-text-secondary hover:text-primary flex items-center gap-1 text-[11px] font-mono cursor-pointer transition-colors duration-200"
                >
                  {streamCollapsed ? 'Expand Log' : 'Collapse Log'}
                  {streamCollapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
                </button>
              )}
            </div>

            {!streamCollapsed && (
              <div className="space-y-4">
                <StreamLog steps={steps} />
                {status !== 'complete' && status !== 'failed' && (
                  <ProgressBar count={toolCallsCount} />
                )}
              </div>
            )}

            {streamCollapsed && (
              <div className="text-xs font-mono text-text-secondary space-y-1.5 py-1">
                <p>Status: <span className="text-primary font-semibold uppercase">Complete</span></p>
                <p>Tool calls: <span className="text-text-primary font-semibold">{toolCallsCount}</span></p>
                <p>Time: <span className="text-text-primary font-semibold">{dossier?.agent_metadata?.duration_seconds}s</span></p>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Dossier Renders or Loader */}
        <div className={`lg:col-span-8 ${status === 'complete' && streamCollapsed ? 'lg:col-span-9' : 'lg:col-span-7'} flex flex-col justify-center min-h-[400px] w-full transition-all duration-500`}>
          {status === 'complete' && dossier ? (
            <DossierReport dossier={dossier} onResearchAgain={handleResearchAgain} />
          ) : status === 'failed' ? (
            <div className="bg-bg-surface border border-accent-red/20 rounded-xl p-8 max-w-md mx-auto text-center space-y-5 animate-fade-in shadow-md w-full">
              <AlertCircle className="text-accent-red mx-auto animate-pulse" size={42} />
              <h3 className="font-display font-medium text-xl text-text-primary">Research Failed</h3>
              <p className="text-sm text-text-secondary leading-relaxed font-sans">{error || 'An unexpected error occurred during research execution.'}</p>
              <button
                onClick={handleResearchAgain}
                className="bg-primary hover:bg-accent-sage text-bg-elevated hover:text-text-primary text-xs font-sans font-semibold py-2 px-5 rounded-lg transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] hover:scale-[1.03] active:scale-[0.97] cursor-pointer shadow-sm"
              >
                Back to Search
              </button>
            </div>
          ) : (
            <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 text-center space-y-5 max-w-md mx-auto w-full shadow-md animate-pulse">
              <Loader2 className="text-primary animate-spin mx-auto" size={32} />
              <h3 className="font-display font-medium text-lg tracking-tight text-text-primary">Research in Progress</h3>
              <p className="text-xs text-text-secondary font-sans leading-relaxed">
                The intelligence agent is gathering prospect information. Please wait while the dossier is compiled. Average research duration is 15-45 seconds.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
