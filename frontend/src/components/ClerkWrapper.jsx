import * as RealClerk from '@clerk/clerk-react';
import * as MockClerk from './MockClerk';

const isMock = !import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || import.meta.env.VITE_CLERK_PUBLISHABLE_KEY === 'mock_key';

export const ClerkProvider = isMock ? MockClerk.MockClerkProvider : RealClerk.ClerkProvider;
export const useAuth = isMock ? MockClerk.useAuth : RealClerk.useAuth;
export const useUser = isMock ? MockClerk.useUser : RealClerk.useUser;
export const SignedIn = isMock ? MockClerk.SignedIn : RealClerk.SignedIn;
export const SignedOut = isMock ? MockClerk.SignedOut : RealClerk.SignedOut;
export const SignInButton = isMock ? MockClerk.SignInButton : RealClerk.SignInButton;
export const UserButton = isMock ? MockClerk.UserButton : RealClerk.UserButton;
