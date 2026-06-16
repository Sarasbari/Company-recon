import React, { useState } from 'react';
import { SignInButton } from './ClerkWrapper';
import { ShieldAlert, X } from 'lucide-react';

export default function AuthBanner() {
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  return (
    <div className="bg-bg-elevated border border-accent-blue/20 rounded p-4 flex items-center justify-between gap-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <ShieldAlert className="text-accent-blue flex-shrink-0" size={20} />
        <div className="text-sm font-sans">
          <p className="text-text-primary font-semibold">Guest Session</p>
          <p className="text-text-secondary text-xs mt-0.5">Sign in to save this dossier to your persistent research history archive.</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <SignInButton mode="modal">
          <button className="bg-accent-blue hover:bg-accent-blue/90 text-white font-sans text-xs font-semibold py-1.5 px-3 rounded transition-all cursor-pointer">
            Sign In
          </button>
        </SignInButton>
        <button 
          onClick={() => setVisible(false)}
          className="text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
