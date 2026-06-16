import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../components/ClerkWrapper';
import { Trash2, Plus, FileText, AlertTriangle, Loader2 } from 'lucide-react';

export default function History() {
  const { isSignedIn, getToken, isLoaded } = useAuth();
  const navigate = useNavigate();

  const [dossiers, setDossiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null); // dossier object to delete
  const [hoveredOverview, setHoveredOverview] = useState(null); // ID of item hovered
  
  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      navigate('/', { replace: true });
    }
  }, [isLoaded, isSignedIn, navigate]);

  const fetchHistory = async () => {
    if (!isSignedIn) return;
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${apiUrl}/dossiers`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setDossiers(data);
      }
    } catch (e) {
      console.error("Failed to load history dossiers", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [isSignedIn]);

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      const token = await getToken();
      const res = await fetch(`${apiUrl}/dossiers/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        setDossiers(prev => prev.filter(d => d.id !== deleteTarget.id));
      }
    } catch (e) {
      console.error("Delete operation failed", e);
    } finally {
      setDeleteTarget(null);
    }
  };

  if (!isLoaded || loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] text-text-secondary">
        <Loader2 className="animate-spin text-accent-blue mb-2" size={24} />
        <span className="font-mono text-xs">Loading history archive...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 mt-8 space-y-6">
      <div className="flex items-center justify-between border-b border-border-subtle pb-4">
        <h1 className="font-display font-bold text-2xl text-text-primary uppercase tracking-tight">
          Research History
        </h1>
        <Link 
          to="/"
          className="bg-accent-blue hover:bg-accent-blue/90 text-white font-mono text-xs font-semibold py-1.5 px-3.5 rounded flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus size={14} />
          New Research
        </Link>
      </div>

      {dossiers.length === 0 ? (
        <div className="bg-bg-surface border border-border-subtle rounded p-12 text-center space-y-4">
          <FileText className="text-text-muted mx-auto" size={36} />
          <p className="font-sans text-sm text-text-secondary">No dossiers stored. Begin a company research session to save them.</p>
          <Link
            to="/"
            className="inline-block bg-bg-elevated border border-border-subtle hover:border-accent-blue text-text-primary text-xs font-mono py-2 px-4 rounded transition-colors"
          >
            [ Start Search ]
          </Link>
        </div>
      ) : (
        <div className="space-y-3 pb-24">
          {dossiers.map((item) => {
            const innerData = item.dossier || {};
            const tpCount = innerData.talking_points?.length || 0;
            const overviewSnippet = innerData.overview 
              ? (innerData.overview.slice(0, 140) + (innerData.overview.length > 140 ? '...' : ''))
              : 'No overview details captured.';
              
            const createdDate = new Date(item.created_at).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            });

            return (
              <div 
                key={item.id}
                className="relative bg-bg-surface border border-border-subtle hover:border-accent-blue/40 rounded p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all"
                onMouseEnter={() => setHoveredOverview(item.id)}
                onMouseLeave={() => setHoveredOverview(null)}
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-3">
                    <Link 
                      to={`/dossier/${item.id}`}
                      className="font-display font-semibold text-lg text-text-primary hover:text-accent-blue tracking-tight uppercase"
                    >
                      {item.company}
                    </Link>
                    <span className="bg-bg-elevated text-text-secondary border border-border-subtle font-mono text-[10px] px-1.5 py-0.5 rounded">
                      {innerData.industry || 'Tech'}
                    </span>
                    {tpCount > 0 && (
                      <span className="bg-accent-amber/10 text-accent-amber border border-accent-amber/20 font-mono text-[10px] px-1.5 py-0.5 rounded">
                        {tpCount} outreach points
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted font-mono">
                    Researched on {createdDate}
                  </div>
                  
                  {/* Hover preview card */}
                  {hoveredOverview === item.id && (
                    <div className="absolute left-4 top-[100%] z-10 w-[calc(100%-2rem)] md:w-96 bg-bg-elevated border border-border-subtle rounded p-3 text-xs text-text-secondary leading-relaxed font-sans shadow-xl mt-1 animate-fade-in pointer-events-none">
                      <p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Overview Preview</p>
                      {overviewSnippet}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 self-end md:self-auto">
                  <Link 
                    to={`/dossier/${item.id}`}
                    className="text-xs font-mono text-accent-blue hover:underline"
                  >
                    View Dossier →
                  </Link>
                  <button
                    onClick={() => setDeleteTarget(item)}
                    className="text-text-muted hover:text-accent-red transition-colors p-1 cursor-pointer"
                    title="Delete dossier"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-bg-surface border border-border-subtle rounded max-w-sm w-full p-6 space-y-4">
            <div className="flex items-center gap-3 text-accent-red">
              <AlertTriangle size={24} />
              <h3 className="font-display font-bold text-base uppercase">Confirm Deletion</h3>
            </div>
            <p className="text-sm font-sans text-text-secondary leading-relaxed">
              Delete the dossier for <span className="text-text-primary font-semibold font-display">{deleteTarget.company}</span>? This action is permanent and cannot be undone.
            </p>
            <div className="flex justify-end gap-3 font-mono text-xs pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="bg-bg-elevated border border-border-subtle hover:bg-border-subtle text-text-primary py-2 px-3.5 rounded transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="bg-accent-red hover:bg-accent-red/90 text-white py-2 px-3.5 rounded transition-all cursor-pointer font-semibold"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
