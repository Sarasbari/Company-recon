import React, { createContext, useContext, useState } from 'react';

const MockClerkContext = createContext(null);

export function MockClerkProvider({ children }) {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [user, setUser] = useState(null);

  const login = () => {
    setIsSignedIn(true);
    setUser({
      id: 'mock_user_123',
      fullName: 'Sarasbari Demo',
      imageUrl: 'https://api.dicebear.com/7.x/bottts/svg?seed=saras'
    });
  };

  const logout = () => {
    setIsSignedIn(false);
    setUser(null);
  };

  const getToken = async () => 'mock_token_123';

  return (
    <MockClerkContext.Provider value={{ isSignedIn, user, login, logout, getToken }}>
      {children}
    </MockClerkContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(MockClerkContext);
  if (!context) return { isSignedIn: false, getToken: async () => null, isLoaded: true };
  return {
    isSignedIn: context.isSignedIn,
    getToken: context.getToken,
    isLoaded: true
  };
}

export function useUser() {
  const context = useContext(MockClerkContext);
  if (!context) return { user: null, isLoaded: true };
  return {
    user: context.user,
    isLoaded: true
  };
}

export function SignedIn({ children }) {
  const { isSignedIn } = useAuth();
  return isSignedIn ? <>{children}</> : null;
}

export function SignedOut({ children }) {
  const { isSignedIn } = useAuth();
  return !isSignedIn ? <>{children}</> : null;
}

export function SignInButton({ children }) {
  const context = useContext(MockClerkContext);
  
  const handleClick = (e) => {
    e.preventDefault();
    if (context) context.login();
  };

  if (React.isValidElement(children)) {
    return React.cloneElement(children, { onClick: handleClick });
  }
  return <button onClick={handleClick}>{children}</button>;
}

export function UserButton() {
  const context = useContext(MockClerkContext);
  const [open, setOpen] = useState(false);

  if (!context || !context.isSignedIn) return null;

  return (
    <div className="relative">
      <button 
        onClick={() => setOpen(!open)}
        className="w-8 h-8 rounded-full border border-border-subtle overflow-hidden cursor-pointer focus:outline-none bg-bg-elevated flex items-center justify-center hover:border-accent-blue"
      >
        <img src={context.user?.imageUrl} alt="user" className="w-6 h-6 object-contain" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-bg-elevated border border-border-subtle rounded p-2 text-xs font-mono shadow-xl z-50">
          <p className="px-2 py-1.5 text-text-primary border-b border-border-subtle/50 font-sans font-semibold mb-1">
            {context.user?.fullName}
          </p>
          <button 
            onClick={() => { context.logout(); setOpen(false); }}
            className="w-full text-left px-2 py-1.5 hover:bg-bg-surface text-accent-red rounded cursor-pointer transition-colors"
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
