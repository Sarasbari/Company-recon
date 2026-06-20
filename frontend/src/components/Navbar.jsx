import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton, SignInButton } from './ClerkWrapper';

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 h-[56px] bg-bg-primary/80 backdrop-blur-md border-b border-border-subtle/60 px-6 flex items-center justify-between transition-all duration-300">
      <Link to="/" className="flex items-center gap-1.5 font-display font-semibold text-xl text-text-primary tracking-tight active:scale-[0.98] transition-transform duration-150 ease-out">
        company-recon
        <span className="w-2 h-2 rounded-full bg-primary inline-block"></span>
      </Link>
      
      <nav className="flex items-center gap-6">
        <SignedIn>
          <Link to="/history" className="text-sm font-sans font-medium text-text-secondary hover:text-primary transition-all duration-300 hover:translate-y-[-1px] active:translate-y-0">
            History
          </Link>
          <div className="flex items-center">
            <UserButton afterSignOutUrl="/" />
          </div>
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button className="text-sm font-sans font-medium text-text-secondary hover:text-primary transition-all duration-300 hover:translate-y-[-1px] active:translate-y-0 cursor-pointer">
              Sign In
            </button>
          </SignInButton>
        </SignedOut>
      </nav>
    </header>
  );
}
