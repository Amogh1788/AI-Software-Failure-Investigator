import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { InvestigationList } from '../InvestigationList';
import { InvestigationManager } from '../InvestigationManager';
import * as api from '../../services/api';
import type { Investigation, Repository, InvestigationDetail as IDetail, InvestigationAnalysis } from '../../types';

// Mock the API module
vi.mock('../../services/api', () => ({
  getInvestigations: vi.fn(),
  getRepositories: vi.fn(),
  getInvestigation: vi.fn(),
  getInvestigationAnalysis: vi.fn(),
  analyzeInvestigation: vi.fn(),
  updateInvestigation: vi.fn(),
  addEvidence: vi.fn(),
  deleteEvidence: vi.fn(),
  deleteInvestigation: vi.fn(),
}));

const mockRepo: Repository = {
  id: 'repo-1',
  project_id: null,
  github_url: 'https://github.com/test/repo',
  owner: 'test',
  name: 'repo',
  default_branch: 'main',
  description: 'Test repo',
  primary_language: 'Java',
  total_files: 5,
  source_files: 3,
  analyzed_at: '2026-09-19T00:00:00Z',
  created_at: '2026-09-19T00:00:00Z',
};

describe('Investigation Status Synchronization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('InvestigationList displays all 4 statuses accurately: DRAFT, READY, ANALYZING, COMPLETED', () => {
    const testCases: Investigation[] = [
      {
        id: 'inv-draft',
        repository_id: 'repo-1',
        title: 'Draft Issue',
        description: 'Draft desc',
        status: 'draft',
        evidence_count: 1,
        created_at: '2026-09-19T00:00:00Z',
        updated_at: '2026-09-19T00:00:00Z',
      },
      {
        id: 'inv-ready',
        repository_id: 'repo-1',
        title: 'Ready Issue',
        description: 'Ready desc',
        status: 'ready',
        evidence_count: 4,
        created_at: '2026-09-19T00:00:00Z',
        updated_at: '2026-09-19T00:00:00Z',
      },
      {
        id: 'inv-analyzing',
        repository_id: 'repo-1',
        title: 'Analyzing Issue',
        description: 'Analyzing desc',
        status: 'analyzing',
        evidence_count: 4,
        created_at: '2026-09-19T00:00:00Z',
        updated_at: '2026-09-19T00:00:00Z',
      },
      {
        id: 'inv-completed',
        repository_id: 'repo-1',
        title: 'Completed Issue',
        description: 'Completed desc',
        status: 'completed',
        evidence_count: 4,
        created_at: '2026-09-19T00:00:00Z',
        updated_at: '2026-09-19T00:00:00Z',
      },
    ];

    render(
      <InvestigationList
        investigations={testCases}
        repositories={[mockRepo]}
        selectedId={null}
        onSelectInvestigation={() => {}}
      />
    );

    // Verify Draft badge
    const draftBadge = screen.getByTestId('status-badge-draft');
    expect(draftBadge).toBeDefined();
    expect(draftBadge.textContent).toMatch(/draft/i);

    // Verify Ready badge
    const readyBadge = screen.getByTestId('status-badge-ready');
    expect(readyBadge).toBeDefined();
    expect(readyBadge.textContent).toMatch(/ready/i);

    // Verify Analyzing badge
    const analyzingBadge = screen.getByTestId('status-badge-analyzing');
    expect(analyzingBadge).toBeDefined();
    expect(analyzingBadge.textContent).toMatch(/analyzing/i);

    // Verify Completed badge (proves completed is NOT rendered as draft)
    const completedBadge = screen.getByTestId('status-badge-completed');
    expect(completedBadge).toBeDefined();
    expect(completedBadge.textContent).toMatch(/completed/i);
  });

  it('proves investigation starts as READY, analysis completes, and returning to list shows COMPLETED', async () => {
    let currentStatus: 'ready' | 'analyzing' | 'completed' = 'ready';

    const initialInvestigation: Investigation = {
      id: 'inv-123',
      repository_id: 'repo-1',
      title: 'Checkout Failure Investigation',
      description: 'paymentTotal is null',
      status: 'ready',
      evidence_count: 4,
      created_at: '2026-09-19T10:00:00Z',
      updated_at: '2026-09-19T10:00:00Z',
    };

    // Dynamic backend response reflecting current database state
    vi.mocked(api.getInvestigations).mockImplementation(async () => [
      {
        ...initialInvestigation,
        status: currentStatus,
      },
    ]);

    vi.mocked(api.getRepositories).mockResolvedValue([mockRepo]);

    const mockDetail: IDetail = {
      investigation: { ...initialInvestigation, status: 'ready' },
      repository: mockRepo,
      evidence: [
        {
          id: 'ev-1',
          investigation_id: 'inv-123',
          evidence_type: 'bug_report',
          title: 'Bug Report',
          content: 'Bug details',
          filename: 'bug_report.txt',
          byte_size: 100,
          created_at: '2026-09-19T10:00:00Z',
        },
        {
          id: 'ev-2',
          investigation_id: 'inv-123',
          evidence_type: 'application_log',
          title: 'App Logs',
          content: 'Log content',
          filename: 'app.log',
          byte_size: 200,
          created_at: '2026-09-19T10:00:00Z',
        },
        {
          id: 'ev-3',
          investigation_id: 'inv-123',
          evidence_type: 'stack_trace',
          title: 'Stack Trace',
          content: 'NullPointerException at CheckoutService.java:42',
          filename: 'trace.txt',
          byte_size: 150,
          created_at: '2026-09-19T10:00:00Z',
        },
        {
          id: 'ev-4',
          investigation_id: 'inv-123',
          evidence_type: 'test_output',
          title: 'Test Output',
          content: 'testApplyFlashSaleDiscount FAILED',
          filename: 'test.log',
          byte_size: 180,
          created_at: '2026-09-19T10:00:00Z',
        },
      ],
    };

    vi.mocked(api.getInvestigation).mockImplementation(async () => ({
      ...mockDetail,
      investigation: {
        ...mockDetail.investigation,
        status: currentStatus,
      },
    }));

    vi.mocked(api.getInvestigationAnalysis).mockRejectedValue(new Error('Not found'));

    const mockAnalysisResult: InvestigationAnalysis = {
      id: 'analysis-1',
      investigation_id: 'inv-123',
      engine_version: '1.0.0',
      status: 'completed',
      summary: 'Analysis completed successfully',
      failure_chain: [],
      ranked_candidates: [
        {
          file_path: 'src/CheckoutService.java',
          evidence_score: 0.95,
          evidence_strength: 'high',
          supporting_evidence: ['Stack trace match'],
          signals: {
            stack_trace_score: 1.0,
            test_failure_score: 0.9,
            logs_score: 0.8,
            bug_report_score: 0.7,
            git_recency_score: 0.8,
          },
        },
      ],
      relevant_commits: [],
      evidence_signals: {
        stack_trace_signal: 1.0,
        test_failure_signal: 0.9,
        logs_tfidf_signal: 0.8,
        bug_report_tfidf_signal: 0.7,
        git_history_signal: 0.8,
        score_formula: 'w1*S + w2*T + w3*L + w4*B + w5*G',
        score_disclaimer: 'Rankings reflect statistical and heuristic correlation.',
      },
      run_duration_ms: 120,
      created_at: '2026-09-19T10:05:00Z',
    };

    vi.mocked(api.analyzeInvestigation).mockImplementation(async () => {
      // Backend completes analysis and updates investigation status in DB
      currentStatus = 'completed';
      return mockAnalysisResult;
    });

    // 1. Render InvestigationManager
    render(<InvestigationManager />);

    // Wait for data to load in list view
    await waitFor(() => {
      expect(screen.getByText('Checkout Failure Investigation')).toBeDefined();
    });

    // Step 1 check: Starts as READY in list
    const initialReadyBadge = screen.getByTestId('status-badge-ready');
    expect(initialReadyBadge).toBeDefined();
    expect(initialReadyBadge.textContent).toMatch(/ready/i);
    expect(screen.queryByTestId('status-badge-completed')).toBeNull();

    // 2. Select / open investigation case
    fireEvent.click(screen.getByText('Checkout Failure Investigation'));

    // Wait for InvestigationDetail to load
    await waitFor(() => {
      expect(screen.getByTitle('Run investigation intelligence engine')).toBeDefined();
    });

    // 3. Click "Run Engine"
    const runButton = screen.getByTitle('Run investigation intelligence engine');
    fireEvent.click(runButton);

    // Wait for analysis to complete and success message to show
    await waitFor(() => {
      expect(api.analyzeInvestigation).toHaveBeenCalledWith('inv-123');
      expect(screen.getByText(/Investigation analysis completed successfully/i)).toBeDefined();
    });

    // 4. Return from InvestigationDetail to InvestigationList by clicking Close ("X")
    const closeButton = screen.getByTitle('Close detail view');
    fireEvent.click(closeButton);

    // 5. Verification: Returning to the list displays COMPLETED, not stale READY or DRAFT
    await waitFor(() => {
      const completedBadge = screen.getByTestId('status-badge-completed');
      expect(completedBadge).toBeDefined();
      expect(completedBadge.textContent).toMatch(/completed/i);
    });

    expect(screen.queryByTestId('status-badge-draft')).toBeNull();
    expect(screen.queryByTestId('status-badge-ready')).toBeNull();
  });

  it('refreshing the Investigation Cases section retrieves the latest status', async () => {
    let currentStatus: 'draft' | 'ready' | 'completed' = 'draft';

    const testInv: Investigation = {
      id: 'inv-refresh-test',
      repository_id: 'repo-1',
      title: 'Sync Refresh Test Case',
      description: 'Testing refresh status update',
      status: 'draft',
      evidence_count: 2,
      created_at: '2026-09-19T10:00:00Z',
      updated_at: '2026-09-19T10:00:00Z',
    };

    vi.mocked(api.getInvestigations).mockImplementation(async () => [
      {
        ...testInv,
        status: currentStatus,
      },
    ]);
    vi.mocked(api.getRepositories).mockResolvedValue([mockRepo]);

    render(<InvestigationManager />);

    // Initially loads as DRAFT
    await waitFor(() => {
      const draftBadge = screen.getByTestId('status-badge-draft');
      expect(draftBadge).toBeDefined();
      expect(draftBadge.textContent).toMatch(/draft/i);
    });

    // Backend status updates externally (e.g. ready or completed)
    currentStatus = 'completed';

    // Click "Refresh" button
    const refreshButton = screen.getByTitle('Refresh investigations');
    fireEvent.click(refreshButton);

    // List updates to show COMPLETED
    await waitFor(() => {
      const completedBadge = screen.getByTestId('status-badge-completed');
      expect(completedBadge).toBeDefined();
      expect(completedBadge.textContent).toMatch(/completed/i);
    });
    expect(screen.queryByTestId('status-badge-draft')).toBeNull();
  });
});
