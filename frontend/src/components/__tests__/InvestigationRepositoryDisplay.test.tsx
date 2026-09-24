import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { InvestigationList } from '../InvestigationList';
import { InvestigationDetail } from '../InvestigationDetail';
import * as api from '../../services/api';
import type { Investigation, Repository, InvestigationDetail as IDetail } from '../../types';

vi.mock('../../services/api', () => ({
  getInvestigation: vi.fn(),
  getInvestigationAnalysis: vi.fn(),
  updateInvestigation: vi.fn(),
  analyzeInvestigation: vi.fn(),
  addEvidence: vi.fn(),
  deleteEvidence: vi.fn(),
}));

const mockLinkedRepo: Repository = {
  id: 'repo-abc',
  project_id: null,
  github_url: 'https://github.com/Amogh1788/AI-SFI-Checkout-Testbed',
  owner: 'Amogh1788',
  name: 'AI-SFI-Checkout-Testbed',
  default_branch: 'main',
  description: 'Testbed repository',
  primary_language: 'Java',
  total_files: 42,
  source_files: 30,
  analyzed_at: '2026-09-20T10:00:00Z',
  created_at: '2026-09-20T10:00:00Z',
};

const mockFallbackRepo: Repository = {
  id: 'repo-fallback',
  project_id: null,
  github_url: 'https://github.com/octocat/Hello-World',
  owner: 'octocat',
  name: 'Hello-World',
  default_branch: 'main',
  description: 'Octocat repository',
  primary_language: 'Python',
  total_files: 10,
  source_files: 8,
  analyzed_at: '2026-09-20T10:00:00Z',
  created_at: '2026-09-20T10:00:00Z',
};

describe('Investigation Linked Repository Display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays owner/name from inv.repository even when repositories list is empty', () => {
    const inv: Investigation = {
      id: 'inv-1',
      repository_id: mockLinkedRepo.id,
      title: 'FLASHSale Checkout Failure',
      description: '504 Gateway Timeout',
      status: 'ready',
      evidence_count: 4,
      created_at: '2026-09-20T12:00:00Z',
      updated_at: '2026-09-20T12:00:00Z',
      repository: mockLinkedRepo,
    };

    render(
      <InvestigationList
        investigations={[inv]}
        repositories={[]} // Empty repositories prop
        selectedId={null}
        onSelectInvestigation={() => {}}
      />
    );

    expect(screen.getByText('Amogh1788/AI-SFI-Checkout-Testbed')).toBeDefined();
    expect(screen.queryByText('Unknown Repository')).toBeNull();
    expect(screen.queryByText('Repository unavailable')).toBeNull();
  });

  it('falls back to repositories array if inv.repository is not attached', () => {
    const inv: Investigation = {
      id: 'inv-2',
      repository_id: mockFallbackRepo.id,
      title: 'Legacy Investigation Without Linked Repo Field',
      description: null,
      status: 'draft',
      evidence_count: 1,
      created_at: '2026-09-20T12:00:00Z',
      updated_at: '2026-09-20T12:00:00Z',
      repository: null,
    };

    render(
      <InvestigationList
        investigations={[inv]}
        repositories={[mockFallbackRepo]}
        selectedId={null}
        onSelectInvestigation={() => {}}
      />
    );

    expect(screen.getByText('octocat/Hello-World')).toBeDefined();
    expect(screen.queryByText('Unknown Repository')).toBeNull();
  });

  it('displays "Repository unavailable" when repository is completely unresolvable', () => {
    const inv: Investigation = {
      id: 'inv-3',
      repository_id: 'unknown-repo-id',
      title: 'Orphaned Investigation Case',
      description: null,
      status: 'draft',
      evidence_count: 0,
      created_at: '2026-09-20T12:00:00Z',
      updated_at: '2026-09-20T12:00:00Z',
      repository: null,
    };

    render(
      <InvestigationList
        investigations={[inv]}
        repositories={[]} // No matching repo
        selectedId={null}
        onSelectInvestigation={() => {}}
      />
    );

    expect(screen.getByText('Repository unavailable')).toBeDefined();
    expect(screen.queryByText('Unknown Repository')).toBeNull();
  });

  it('InvestigationDetail displays owner/name when repository is linked', async () => {
    const detail: IDetail = {
      investigation: {
        id: 'inv-100',
        repository_id: mockLinkedRepo.id,
        title: 'Checkout Failure Test',
        description: 'Detail test',
        status: 'ready',
        evidence_count: 0,
        created_at: '2026-09-20T12:00:00Z',
        updated_at: '2026-09-20T12:00:00Z',
        repository: mockLinkedRepo,
      },
      repository: mockLinkedRepo,
      evidence: [],
    };

    vi.mocked(api.getInvestigation).mockResolvedValue(detail);
    vi.mocked(api.getInvestigationAnalysis).mockRejectedValue(new Error('No analysis'));

    render(
      <InvestigationDetail
        investigationId="inv-100"
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Amogh1788/AI-SFI-Checkout-Testbed')).toBeDefined();
    });
    expect(screen.queryByText('Repository unavailable')).toBeNull();
    expect(screen.queryByText('Unknown Repository')).toBeNull();
  });

  it('InvestigationDetail displays "Repository unavailable" when repository is null', async () => {
    const detail: IDetail = {
      investigation: {
        id: 'inv-101',
        repository_id: 'deleted-repo-id',
        title: 'Unlinked Detail Test',
        description: null,
        status: 'draft',
        evidence_count: 0,
        created_at: '2026-09-20T12:00:00Z',
        updated_at: '2026-09-20T12:00:00Z',
        repository: null,
      },
      repository: null,
      evidence: [],
    };

    vi.mocked(api.getInvestigation).mockResolvedValue(detail);
    vi.mocked(api.getInvestigationAnalysis).mockRejectedValue(new Error('No analysis'));

    render(
      <InvestigationDetail
        investigationId="inv-101"
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Repository unavailable')).toBeDefined();
    });
    expect(screen.queryByText('Unknown Repository')).toBeNull();
  });
});
