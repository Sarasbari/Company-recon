import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ClerkProvider } from './components/ClerkWrapper';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Research from './pages/Research';
import History from './pages/History';
import DossierDetail from './pages/DossierDetail';

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "mock_key";

export default function App() {
  return (
    <ClerkProvider publishableKey={clerkPubKey}>
      <BrowserRouter>
        <div className="min-h-screen bg-bg-primary text-text-primary selection:bg-accent-blue selection:text-white font-sans flex flex-col">
          <Navbar />
          <div className="flex-grow">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/research/:jobId" element={<Research />} />
              <Route path="/history" element={<History />} />
              <Route path="/dossier/:id" element={<DossierDetail />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </ClerkProvider>
  );
}
