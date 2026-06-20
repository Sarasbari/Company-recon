import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../components/ClerkWrapper';

export default function Home() {
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyCount, setHistoryCount] = useState(null);
  
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { isSignedIn, getToken } = useAuth();

  // Focus input automatically on page load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Fetch search history stats for signed in users
  useEffect(() => {
    if (isSignedIn) {
      const fetchCount = async () => {
        try {
          const token = await getToken();
          const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
          const res = await fetch(`${apiUrl}/dossiers`, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          if (res.ok) {
            const data = await res.json();
            setHistoryCount(data.length);
          }
        } catch (e) {
          console.error("Failed to retrieve user statistics", e);
        }
      };
      fetchCount();
    }
  }, [isSignedIn, getToken]);

  const handleSubmit = async (companyName) => {
    const term = (companyName || query).trim();
    if (!term) {
      setError('Enter a company name');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (isSignedIn) {
        const token = await getToken();
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${apiUrl}/research`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ company: term })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to start research');
      }

      const data = await res.json();
      navigate(`/research/${data.job_id}`, { state: { dossierId: data.dossier_id } });
    } catch (e) {
      console.error(e);
      setError(e.message || 'Unable to initiate research. Please check backend connection.');
      setLoading(false);
    }
  };

  const handleSuggestionClick = (name) => {
    setQuery(name);
    handleSubmit(name);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] px-6 bg-bg-primary">
      <div className="w-full max-w-lg text-center space-y-10">
        {/* Title Block */}
        <div className="space-y-3 animate-fade-in-up">
          <h1 className="font-display font-medium text-5xl md:text-6xl text-text-primary tracking-tight flex items-center justify-center gap-2">
            company-recon
            <span className="w-3 h-3 rounded-full bg-primary inline-block animate-pulse"></span>
          </h1>
          <p className="font-sans text-sm text-text-secondary max-w-sm mx-auto">
            Prospect intelligence, compiled in real-time.
          </p>
        </div>

        {/* Input Form */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
          className="space-y-4 animate-fade-in-up [animation-delay:150ms] opacity-0 [animation-fill-mode:forwards]"
        >
          <div className="relative flex items-center">
            <input
              ref={inputRef}
              type="text"
              placeholder="Enter company name (e.g. Stripe)"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (e.target.value.trim()) setError('');
              }}
              disabled={loading}
              className="w-full h-[54px] bg-bg-surface border border-border-subtle focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/8 rounded-xl px-5 text-text-primary placeholder:text-text-muted/70 font-sans text-base transition-all duration-300 shadow-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 h-[38px] px-5 bg-primary hover:bg-accent-sage text-bg-elevated hover:text-text-primary text-xs font-sans font-semibold rounded-lg transition-all duration-150 ease-out active:scale-[0.97] disabled:bg-bg-elevated disabled:text-text-muted flex items-center justify-center cursor-pointer shadow-sm"
            >
              {loading ? 'Starting...' : 'Research →'}
            </button>
          </div>
          {error && (
            <p className="text-left text-xs font-mono text-accent-red pl-2 animate-fade-in">
              {error}
            </p>
          )}
        </form>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-sans animate-fade-in-up [animation-delay:300ms] opacity-0 [animation-fill-mode:forwards]">
          <span className="text-text-muted font-mono uppercase tracking-wider text-[10px]">TRY:</span>
          {['Razorpay', 'Stripe', 'Zomato'].map((name) => (
            <button
              key={name}
              onClick={() => handleSuggestionClick(name)}
              disabled={loading}
              className="text-text-secondary hover:text-text-primary border border-border-subtle bg-bg-surface hover:bg-bg-elevated px-3 py-1 rounded-full transition-colors duration-150 ease-out active:scale-95 cursor-pointer shadow-sm"
            >
              {name}
            </button>
          ))}
        </div>

        {/* User Search Stat */}
        {isSignedIn && historyCount !== null && (
          <div className="text-[11px] font-mono text-text-muted animate-fade-in-up [animation-delay:450ms] opacity-0 [animation-fill-mode:forwards]">
            You've compiled <span className="text-primary font-semibold border-b border-primary/20 pb-0.5">{historyCount} dossiers</span> in this workspace
          </div>
        )}
      </div>
    </div>
  );
}
