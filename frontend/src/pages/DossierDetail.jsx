import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../components/ClerkWrapper';
import { AlertTriangle, Loader2, ArrowLeft, Trash2 } from 'lucide-react';
import DossierReport from '../components/DossierReport';

export default function DossierDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isSignedIn, getToken, isLoaded } = useAuth();

  const [dossierRecord, setDossierRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      navigate('/', { replace: true });
    }
  }, [isLoaded, isSignedIn, navigate]);

  useEffect(() => {
    if (!isSignedIn) return;
    
    const fetchDossier = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await getToken();
        const res = await fetch(`${apiUrl}/dossiers/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (res.status === 404) {
          throw new Error('Dossier not found or unauthorized access.');
        }
        if (!res.ok) {
          throw new Error('Failed to retrieve dossier data.');
        }
        const data = await res.json();
        setDossierRecord(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDossier();
  }, [id, isSignedIn, apiUrl, getToken]);

  const handleDelete = async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${apiUrl}/dossiers/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        navigate('/history');
      }
    } catch (e) {
      console.error("Delete operation failed", e);
    }
  };

  const handleResearchAgain = () => {
    navigate('/', { replace: true });
  };

  if (!isLoaded || loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] text-text-secondary bg-bg-primary">
        <Loader2 className="animate-spin text-primary mb-2" size={24} />
        <span className="font-sans text-xs text-text-muted">Retrieving dossier details...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto px-6 mt-16 text-center space-y-5 bg-bg-surface border border-border-subtle rounded-xl p-8 shadow-md">
        <AlertTriangle className="text-accent-red mx-auto" size={40} />
        <h3 className="font-display font-medium text-lg text-text-primary">Dossier Unavailable</h3>
        <p className="text-sm text-text-secondary leading-relaxed font-sans">{error}</p>
        <Link 
          to="/history"
          className="inline-block bg-primary hover:bg-accent-sage text-bg-elevated hover:text-text-primary text-xs font-sans font-semibold py-2 px-4 rounded-lg transition-all duration-150 ease-out active:scale-[0.98]"
        >
          Back to History
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 mt-8 space-y-6 bg-bg-primary pb-24 animate-fade-in">
      {/* Header controls */}
      <div className="flex items-center justify-between border-b border-border-subtle/60 pb-4 font-sans text-xs font-semibold">
        <Link 
          to="/history" 
          className="text-text-secondary hover:text-primary flex items-center gap-1.5 transition-all duration-200 hover:translate-x-[-2px]"
        >
          <ArrowLeft size={14} />
          Back to History
        </Link>
        <button
          onClick={() => setDeleteConfirm(true)}
          className="text-text-muted hover:text-accent-red flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Trash2 size={14} />
          Delete Dossier
        </button>
      </div>

      {/* Render core Dossier */}
      {dossierRecord && (
        <DossierReport 
          dossier={dossierRecord.dossier} 
          onResearchAgain={handleResearchAgain}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-bg-elevated border border-border-subtle rounded-2xl max-w-sm w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center gap-3 text-accent-red">
              <AlertTriangle size={24} className="animate-pulse" />
              <h3 className="font-display font-medium text-lg">Confirm Deletion</h3>
            </div>
            <p className="text-sm font-sans text-text-secondary leading-relaxed">
              Are you sure you want to permanently delete the saved research for this company? This cannot be undone.
            </p>
            <div className="flex justify-end gap-3 font-sans text-xs pt-2">
              <button
                onClick={() => setDeleteConfirm(false)}
                className="bg-bg-surface border border-border-subtle hover:bg-bg-primary text-text-primary py-2 px-4 rounded-lg transition-all duration-200 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
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
