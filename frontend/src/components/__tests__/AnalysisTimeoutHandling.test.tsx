import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RepositoryAnalyzer } from '../RepositoryAnalyzer';
import {
  ANALYZE_TIMEOUT_MS,
  TIMEOUT_ERROR_MESSAGE,
  extractErrorDetail,
  analyzeRepository,
} from '../../services/api';

describe('Large Repository Analysis Timeout & Error Handling', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('1. Configures ANALYZE_TIMEOUT_MS to 330000 ms (5.5 minutes)', () => {
    expect(ANALYZE_TIMEOUT_MS).toBe(330000);
  });

  it('2. Extracts user-friendly timeout message for HTTP 504 responses', async () => {
    const mockResponse = {
      ok: false,
      status: 504,
      headers: new Headers({ 'X-Request-ID': 'req-timeout-504' }),
      json: async () => ({ detail: 'Repository clone timed out after 300 seconds.' }),
    } as unknown as Response;

    const message = await extractErrorDetail(mockResponse, 'Repository analysis failed');
    expect(message).toBe(
      'Repository analysis timed out. The repository may be too large or complex to analyze within the current processing limit.'
    );
    expect(message).not.toContain('signal is aborted without reason');
  });

  it('3. analyzeRepository rejects with user-friendly message when backend returns HTTP 504', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 504,
      headers: new Headers(),
      json: async () => ({ detail: 'Repository clone timed out after 300 seconds.' }),
    });

    await expect(analyzeRepository('https://github.com/torvalds/linux')).rejects.toThrow(
      'Repository analysis timed out. The repository may be too large or complex to analyze within the current processing limit.'
    );
  });

  it('4. analyzeRepository handles browser AbortError and does NOT expose "signal is aborted without reason"', async () => {
    // Simulate browser aborting with standard DOMException
    const abortErr = new Error('signal is aborted without reason');
    abortErr.name = 'AbortError';
    globalThis.fetch = vi.fn().mockRejectedValue(abortErr);

    await expect(analyzeRepository('https://github.com/tensorflow/tensorflow')).rejects.toThrow(
      TIMEOUT_ERROR_MESSAGE
    );
  });

  it('5. RepositoryAnalyzer component renders meaningful timeout message on 504 or abort', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 504,
      headers: new Headers(),
      json: async () => ({ detail: 'Repository clone timed out after 300 seconds.' }),
    });

    render(<RepositoryAnalyzer />);

    const input = screen.getByPlaceholderText(/github\.com\/owner\/repo/i);
    const submitBtn = screen.getByRole('button', { name: /Analyze/i });

    fireEvent.change(input, { target: { value: 'https://github.com/torvalds/linux' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      const errorElem = screen.getByText(
        'Repository analysis timed out. The repository may be too large or complex to analyze within the current processing limit.'
      );
      expect(errorElem).toBeDefined();
    });

    expect(screen.queryByText(/signal is aborted without reason/i)).toBeNull();
  });
});
