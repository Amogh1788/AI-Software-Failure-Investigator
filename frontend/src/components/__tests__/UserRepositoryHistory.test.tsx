import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RepositoryAnalyzer } from '../RepositoryAnalyzer';
import * as api from '../../services/api';
import type { Repository } from '../../types';

vi.mock('../../services/api', async () => {
  const actual = await vi.importActual('../../services/api');
  return {
    ...actual,
    getRepositories: vi.fn(),
    getRepositoryFiles: vi.fn().mockResolvedValue([]),
    getRepositoryCommits: vi.fn().mockResolvedValue([]),
    analyzeRepository: vi.fn(),
    deleteRepositoryHistory: vi.fn(),
  };
});

const mockRepos: Repository[] = [
  {
    id: 'repo-1-uuid',
    project_id: null,
    github_url: 'https://github.com/facebook/react',
    owner: 'facebook',
    name: 'react',
    default_branch: 'main',
    description: 'React library',
    primary_language: 'JavaScript',
    total_files: 100,
    source_files: 80,
    analyzed_at: '2026-09-20T12:00:00Z',
    created_at: '2026-09-20T12:00:00Z',
  },
  {
    id: 'repo-2-uuid',
    project_id: null,
    github_url: 'https://github.com/pallets/flask',
    owner: 'pallets',
    name: 'flask',
    default_branch: 'main',
    description: 'Flask microframework',
    primary_language: 'Python',
    total_files: 50,
    source_files: 45,
    analyzed_at: '2026-09-21T12:00:00Z',
    created_at: '2026-09-21T12:00:00Z',
  },
];

describe('User-Scoped Repository History & History Deletion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Requirement K: History dropdown renders 'X' remove action for entries
  it('Requirement K: History dropdown renders "X" remove action for entries', async () => {
    vi.mocked(api.getRepositories).mockResolvedValue(mockRepos);

    render(<RepositoryAnalyzer />);

    // Wait for repositories to load and dropdown trigger to render
    await waitFor(() => {
      expect(screen.getAllByText('facebook/react').length).toBeGreaterThan(0);
    });

    // Open the History dropdown
    const historyTrigger = screen.getByRole('button', { name: /facebook\/react/i });
    fireEvent.click(historyTrigger);

    // Verify both repositories and their remove buttons are visible
    expect(screen.getByText('pallets/flask')).toBeDefined();

    const removeBtnReact = screen.getByRole('button', {
      name: 'Remove facebook/react from history',
    });
    const removeBtnFlask = screen.getByRole('button', {
      name: 'Remove pallets/flask from history',
    });

    expect(removeBtnReact).toBeDefined();
    expect(removeBtnFlask).toBeDefined();
  });

  // Requirement L: Clicking 'X' calls delete API and updates local dropdown state on success
  it('Requirement L: Clicking "X" calls delete API and updates local dropdown state on success', async () => {
    vi.mocked(api.getRepositories).mockResolvedValue([...mockRepos]);
    vi.mocked(api.deleteRepositoryHistory).mockResolvedValue();

    render(<RepositoryAnalyzer />);

    await waitFor(() => {
      expect(screen.getAllByText('facebook/react').length).toBeGreaterThan(0);
    });

    // Open dropdown
    const historyTrigger = screen.getByRole('button', { name: /facebook\/react/i });
    fireEvent.click(historyTrigger);

    // Click remove on flask
    const removeBtnFlask = screen.getByRole('button', {
      name: 'Remove pallets/flask from history',
    });
    fireEvent.click(removeBtnFlask);

    // Verify API was called with Flask's repo ID
    await waitFor(() => {
      expect(api.deleteRepositoryHistory).toHaveBeenCalledWith('repo-2-uuid');
    });

    // Verify Flask is removed from the dropdown list
    await waitFor(() => {
      expect(screen.queryByText('pallets/flask')).toBeNull();
    });

    // React should still be in the dropdown
    expect(screen.getAllByText('facebook/react').length).toBeGreaterThan(0);
  });

  // Requirement M: Failed delete retains repository in list and displays error message
  it('Requirement M: Failed delete retains repository in list and displays error message', async () => {
    vi.mocked(api.getRepositories).mockResolvedValue([...mockRepos]);
    vi.mocked(api.deleteRepositoryHistory).mockRejectedValue(
      new Error('Forbidden: Not authorized to remove this repository from history.')
    );

    render(<RepositoryAnalyzer />);

    await waitFor(() => {
      expect(screen.getAllByText('facebook/react').length).toBeGreaterThan(0);
    });

    // Open dropdown
    const historyTrigger = screen.getByRole('button', { name: /facebook\/react/i });
    fireEvent.click(historyTrigger);

    // Click remove on react
    const removeBtnReact = screen.getByRole('button', {
      name: 'Remove facebook/react from history',
    });
    fireEvent.click(removeBtnReact);

    // Verify error is displayed
    await waitFor(() => {
      expect(
        screen.getByText('Forbidden: Not authorized to remove this repository from history.')
      ).toBeDefined();
    });

    // Crucial: The repository must NOT be silently removed on failure
    expect(screen.getAllByText('facebook/react').length).toBeGreaterThan(0);
    expect(screen.getByText('pallets/flask')).toBeDefined();
  });

  // Empty state handling
  it('Displays empty state message when user has no repository history', async () => {
    vi.mocked(api.getRepositories).mockResolvedValue([]);

    render(<RepositoryAnalyzer />);

    await waitFor(() => {
      expect(screen.getByText('No repository history')).toBeDefined();
    });

    // Open dropdown
    const historyTrigger = screen.getByRole('button', { name: /No repository history/i });
    fireEvent.click(historyTrigger);

    // Verify empty state text
    expect(screen.getByText('No repository history yet.')).toBeDefined();
    expect(
      screen.getByText('Analyze a public GitHub repository to see it here.')
    ).toBeDefined();
  });
});
