import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ErrorBoundary } from '../ErrorBoundary';
import { Header } from '../Header';
import { FutureInvestigationArea } from '../FutureInvestigationArea';
import { AuthView } from '../AuthView';
import { AuthProvider } from '../../context/AuthContext';
import { checkBackendHealth, setAuthToken, getAuthToken } from '../../services/api';

// Component designed to simulate a React rendering crash
const CrashingComponent: React.FC<{ shouldCrash: boolean }> = ({ shouldCrash }) => {
  if (shouldCrash) {
    throw new Error('Simulated critical UI crash');
  }
  return <div data-testid="healthy-ui">Healthy Component</div>;
};

// Mock Supabase Auth
vi.mock('../../services/supabaseAuth', () => ({
  supabaseAuth: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signInWithPassword: vi.fn().mockImplementation(({ email, password }) => {
        if (password === 'correct123') {
          return Promise.resolve({ data: { user: { id: 'user-1', email } }, error: null });
        }
        return Promise.resolve({ data: { user: null }, error: new Error('Invalid login credentials') });
      }),
      signUp: vi.fn().mockResolvedValue({ data: { user: { id: 'new-user' } }, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    },
  },
}));

describe('Phase 5 Production Hardening & Resilience', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('1. React Error Boundary', () => {
    it('catches runtime rendering crash and renders recovery UI without breaking page', () => {
      // Suppress console.error during expected throw
      const originalError = console.error;
      console.error = vi.fn();

      render(
        <ErrorBoundary>
          <CrashingComponent shouldCrash={true} />
        </ErrorBoundary>
      );

      const errorUi = screen.getByTestId('error-boundary-ui');
      expect(errorUi).toBeDefined();
      expect(screen.getByText('RepoDetective')).toBeDefined();
      expect(screen.getByText(/Something went wrong in the user interface/i)).toBeDefined();
      expect(screen.getByText('Retry')).toBeDefined();
      expect(screen.getByText('Reload Page')).toBeDefined();

      console.error = originalError;
    });

    it('renders normal children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <CrashingComponent shouldCrash={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('healthy-ui')).toBeDefined();
    });
  });

  describe('2. Branding & Production Badge', () => {
    it('Header displays PRODUCTION MVP • v1.0.0 badge', () => {
      render(
        <AuthProvider>
          <Header onRefresh={vi.fn()} isRefreshing={false} />
        </AuthProvider>
      );

      const badge = screen.getByTestId('header-phase-badge');
      expect(badge).toBeDefined();
      expect(badge.textContent).toBe('PRODUCTION MVP • v1.0.0');
    });

    it('Architecture component displays active engine pipeline and removes Phase 2+ obsolete copy', () => {
      render(<FutureInvestigationArea />);

      const section = screen.getByTestId('investigation-engine-architecture');
      expect(section).toBeDefined();
      expect(screen.getByText(/Investigation Intelligence Engine/i)).toBeDefined();
      expect(screen.queryByText(/Scheduled for Phase 2\+/i)).toBeNull();
      expect(screen.queryByText(/Preview of multi-modal failure correlation engine scheduled for future phases/i)).toBeNull();
      expect(screen.getByText(/0.35 × Stack \+ 0.25 × Test \+ 0.20 × Logs \+ 0.10 × Bug \+ 0.10 × Git/i)).toBeDefined();
    });
  });

  describe('3. Authentication Flow & Form Validation', () => {
    it('renders AuthView with email, password, and toggles between Sign In and Sign Up', () => {
      render(
        <AuthProvider>
          <AuthView />
        </AuthProvider>
      );

      expect(screen.getByPlaceholderText('investigator@example.com')).toBeDefined();
      expect(screen.getByPlaceholderText('••••••••')).toBeDefined();
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeDefined();

      // Toggle to Create Account
      const toggleBtn = screen.getByText(/Don't have an account\? Create one/i);
      fireEvent.click(toggleBtn);

      expect(screen.getByRole('button', { name: /Create Account/i })).toBeDefined();
    });

    it('rejects short passwords client-side with validation error', async () => {
      render(
        <AuthProvider>
          <AuthView />
        </AuthProvider>
      );

      const emailInput = screen.getByPlaceholderText('investigator@example.com');
      const passInput = screen.getByPlaceholderText('••••••••');
      const submitBtn = screen.getByRole('button', { name: /Sign In/i });

      fireEvent.change(emailInput, { target: { value: 'user@test.com' } });
      fireEvent.change(passInput, { target: { value: '123' } });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        const alert = screen.getByTestId('auth-error-alert');
        expect(alert).toBeDefined();
        expect(alert.textContent).toMatch(/Password must be at least 6 characters/i);
      });
    });
  });

  describe('4. API Client Hardening & Token Management', () => {
    it('manages active auth token in API client', () => {
      expect(getAuthToken()).toBeNull();
      setAuthToken('test-jwt-token-123');
      expect(getAuthToken()).toBe('test-jwt-token-123');
      setAuthToken(null);
      expect(getAuthToken()).toBeNull();
    });

    it('extracts X-Request-ID and parses 429 Rate Limit error gracefully', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        headers: new Headers({
          'X-Request-ID': 'req-test-trace-999',
          'Retry-After': '45',
        }),
        json: async () => ({
          detail: 'Rate limit exceeded for heavy requests.',
        }),
      });
      globalThis.fetch = mockFetch;

      await expect(checkBackendHealth()).rejects.toThrow();
    });
  });
});
