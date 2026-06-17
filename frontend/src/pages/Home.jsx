import React, { useState, useEffect, useRef } from 'react';
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
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] px-6">
      <div className="w-full max-w-lg text-center space-y-8">
        {/* Title Block */}
        <div className="space-y-2">
          <h1 className="font-display font-bold text-4xl text-text-primary uppercase tracking-tight">
            company-recon
          </h1>
          <p className="font-sans text-sm text-text-secondary">
            Prospect intelligence, automated
          </p>
        </div>

        {/* Input Form */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
          className="space-y-3"
        >
          <div className="relative flex items-center">
            <input
              ref={inputRef}
              type="text"
              placeholder="Company name (e.g. Razorpay)"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (e.target.value.trim()) setError('');
              }}
              disabled={loading}
              className="w-full h-[52px] bg-bg-surface border border-border-subtle focus:border-accent-blue focus:outline-none rounded px-4 text-text-primary placeholder:text-text-muted font-sans text-base transition-colors"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2.5 h-[36px] px-4 bg-accent-blue hover:bg-accent-blue/90 disabled:bg-bg-elevated text-white text-xs font-mono font-semibold rounded transition-colors flex items-center justify-center cursor-pointer"
            >
              {loading ? 'Starting...' : 'Research →'}
            </button>
          </div>
          {error && (
            <p className="text-left text-xs font-mono text-accent-red pl-1">
              {error}
            </p>
          )}
        </form>

        {/* Suggestion Chips */}
        <div className="flex items-center justify-center gap-2 text-xs font-mono">
          <span className="text-text-muted">TRY:</span>
          {['Razorpay', 'Stripe', 'Zomato'].map((name) => (
            <button
              key={name}
              onClick={() => handleSuggestionClick(name)}
              disabled={loading}
              className="text-text-secondary hover:text-accent-blue border border-border-subtle bg-bg-surface hover:bg-bg-elevated px-2 py-1 rounded transition-colors cursor-pointer"
            >
              {name}
            </button>
          ))}
        </div>

        {/* User Search Stat */}
        {isSignedIn && historyCount !== null && (
          <div className="text-[11px] font-mono text-text-muted">
            You've researched <span className="text-accent-green font-semibold">{historyCount}</span> companies in this workspace
          </div>
        )}
      </div>
    </div>
  );
}
