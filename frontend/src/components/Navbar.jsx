import React from 'react';
import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton, SignInButton } from './ClerkWrapper';

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 h-[56px] bg-bg-surface border-b border-border-subtle px-6 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-1.5 font-display font-bold text-lg text-text-primary tracking-wide hover:opacity-90">
        company-recon
        <span className="w-1.5 h-1.5 rounded-full bg-accent-blue inline-block"></span>
      </Link>
      
      <nav className="flex items-center gap-6">
        <SignedIn>
          <Link to="/history" className="text-sm font-sans font-medium text-text-secondary hover:text-accent-blue transition-colors">
            History
          </Link>
          <div className="flex items-center">
            <UserButton afterSignOutUrl="/" />
          </div>
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button className="text-sm font-sans font-medium text-text-secondary hover:text-accent-blue transition-colors cursor-pointer">
              Sign In
            </button>
          </SignInButton>
        </SignedOut>
      </nav>
    </header>
  );
}
