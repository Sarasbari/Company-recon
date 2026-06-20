import { useState, useEffect } from 'react';
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

  useEffect(() => {
    if (!isSignedIn) return;

    const fetchHistory = async () => {
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

    fetchHistory();
  }, [isSignedIn, apiUrl, getToken]);

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
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] text-text-secondary bg-bg-primary">
        <Loader2 className="animate-spin text-primary mb-2" size={24} />
        <span className="font-sans text-xs text-text-muted">Loading history archive...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 mt-8 space-y-6 bg-bg-primary">
      <div className="flex items-center justify-between border-b border-border-subtle/60 pb-4">
        <h1 className="font-display font-medium text-3xl text-text-primary tracking-tight">
          Research History
        </h1>
        <Link 
          to="/"
          className="bg-primary hover:bg-accent-sage text-bg-elevated hover:text-text-primary font-sans text-xs font-semibold py-2 px-4 rounded-lg flex items-center gap-1.5 transition-all duration-150 ease-out active:scale-[0.97] cursor-pointer shadow-sm"
        >
          <Plus size={14} />
          New Research
        </Link>
      </div>

      {dossiers.length === 0 ? (
        <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 text-center space-y-5 shadow-sm">
          <FileText className="text-text-muted mx-auto" size={36} />
          <p className="font-sans text-sm text-text-secondary">No dossiers stored. Begin a company research session to save them.</p>
          <Link
            to="/"
            className="inline-block bg-bg-elevated border border-border-subtle hover:border-primary text-text-primary text-xs font-sans font-semibold py-2 px-4 rounded-lg transition-all duration-150 ease-out active:scale-[0.98]"
          >
            Start Search
          </Link>
        </div>
      ) : (
        <div className="space-y-4 pb-24">
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
                className="relative bg-bg-surface border border-border-subtle hover:border-primary/30 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-150 shadow-sm"
                onMouseEnter={() => setHoveredOverview(item.id)}
                onMouseLeave={() => setHoveredOverview(null)}
              >
                <div className="flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <Link 
                      to={`/dossier/${item.id}`}
                      className="font-display font-semibold text-lg text-text-primary hover:text-primary transition-colors duration-200"
                    >
                      {item.company}
                    </Link>
                    <span className="bg-bg-elevated text-text-secondary border border-border-subtle/60 font-sans text-[10px] px-2 py-0.5 rounded-md">
                      {innerData.industry || 'Tech'}
                    </span>
                    {tpCount > 0 && (
                      <span className="bg-accent-amber/10 text-accent-amber border border-accent-amber/20 font-sans text-[10px] font-medium px-2 py-0.5 rounded-md">
                        {tpCount} outreach points
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted font-sans">
                    Researched on {createdDate}
                  </div>
                  
                  {/* Hover preview card */}
                  {hoveredOverview === item.id && (
                    <div className="absolute left-4 top-[105%] z-20 w-[calc(100%-2rem)] md:w-96 bg-bg-elevated border border-border-subtle rounded-xl p-4 text-xs text-text-secondary leading-relaxed font-sans shadow-xl mt-1 animate-fade-in pointer-events-none">
                      <p className="font-mono text-[9px] text-text-muted mb-1.5 uppercase tracking-wider">Overview Preview</p>
                      {overviewSnippet}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 self-end md:self-auto">
                  <Link 
                    to={`/dossier/${item.id}`}
                    className="text-xs font-semibold text-primary hover:text-accent-sage hover:underline transition-colors"
                  >
                    View Dossier →
                  </Link>
                  <button
                    onClick={() => setDeleteTarget(item)}
                    className="text-text-muted hover:text-accent-red hover:scale-110 transition-all p-1 cursor-pointer"
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
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-bg-elevated border border-border-subtle rounded-2xl max-w-sm w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center gap-3 text-accent-red">
              <AlertTriangle size={24} className="animate-pulse" />
              <h3 className="font-display font-medium text-lg">Confirm Deletion</h3>
            </div>
            <p className="text-sm font-sans text-text-secondary leading-relaxed">
              Delete the dossier for <span className="text-text-primary font-semibold font-display">{deleteTarget.company}</span>? This action is permanent and cannot be undone.
            </p>
            <div className="flex justify-end gap-3 font-sans text-xs pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="bg-bg-surface border border-border-subtle hover:bg-bg-primary text-text-primary py-2 px-4 rounded-lg transition-all duration-200 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="bg-accent-red hover:bg-accent-red/90 text-white font-semibold py-2 px-4 rounded-lg transition-all duration-150 ease-out active:scale-[0.97] cursor-pointer"
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
