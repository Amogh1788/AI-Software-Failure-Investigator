import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AnalysisReportView } from '../AnalysisReportView';
import type { InvestigationAnalysis } from '../../types';

describe('Analysis Report Consistency', () => {
  it('displays 875bcf7 as top relevant commit and executive summary matches Git history classification', () => {
    const mockAnalysis: InvestigationAnalysis = {
      id: 'run-1',
      investigation_id: 'inv-1',
      engine_version: '1.0.0',
      status: 'completed',
      summary: "Investigation identified 'CheckoutService.java' in method 'processCheckout' around line 21 as the primary failure candidate with an evidence score of 0.80 (HIGH evidence strength) triggered by 'NullPointerException'. Correlated with 875bcf7a ('refactor(checkout): add FLASHSALE discount promo tier') — Likely regression-introducing commit. Evidence score is a weighted measure of supporting evidence across stack traces, test assertions, logs, bug reports, and Git history, and is not a probability.",
      failure_chain: [
        {
          step_number: 1,
          phase: 'Trigger Event',
          title: 'Failure Trigger Initiated',
          description: 'Checkout 500 failure',
          source: 'Bug Report',
          location: null,
        },
        {
          step_number: 2,
          phase: 'Fault Location',
          title: 'Defect manifested in CheckoutService.java',
          description: "Highest evidence candidate (src/CheckoutService.java) encountered invalid state during execution. Evidence strength: HIGH (0.80). Correlated with 875bcf7a ('refactor(checkout): add FLASHSALE discount promo tier') — Likely regression-introducing commit.",
          source: 'Static Code Analysis',
          location: 'src/CheckoutService.java:21',
        },
      ],
      ranked_candidates: [
        {
          file_path: 'src/CheckoutService.java',
          function_name: 'processCheckout',
          line_number: 21,
          evidence_score: 0.8,
          evidence_strength: 'high',
          supporting_evidence: ['Frame match'],
          signals: {
            stack_trace_score: 1.0,
            test_failure_score: 1.0,
            logs_score: 0.5,
            bug_report_score: 0.4,
            git_recency_score: 0.9,
            final_score: 0.8,
          },
        },
      ],
      relevant_commits: [
        {
          commit_hash: '875bcf7a1786',
          author_name: 'Test Dev',
          committed_at: '2026-09-19T15:25:27Z',
          commit_message: 'refactor(checkout): add FLASHSALE discount promo tier',
          relevance_reason: 'Likely regression-introducing commit. Modified suspicious code area in CheckoutService.java (introduced terms: discount, flashsale, null); preceded test commit',
        },
        {
          commit_hash: '6d5ff2db974b',
          author_name: 'Test Dev',
          committed_at: '2026-09-19T15:25:27Z',
          commit_message: 'test: add unit test for checkout service',
          relevance_reason: 'Regression-detection/testing commit. Added or updated unit tests (CheckoutServiceTest.java)',
        },
        {
          commit_hash: '2a2701b0d6cb',
          author_name: 'Test Dev',
          committed_at: '2026-09-19T15:25:26Z',
          commit_message: 'feat: add checkout service and payment pipeline',
          relevance_reason: 'Baseline setup commit. Introduced initial implementation of CheckoutService.java',
        },
        {
          commit_hash: '24705a6faca0',
          author_name: 'Test Dev',
          committed_at: '2026-09-19T15:25:26Z',
          commit_message: 'feat: initial payment and controller setup',
          relevance_reason: 'Baseline setup commit. Introduced initial implementation of CheckoutController.java, PaymentRequestBuilder.java',
        },
      ],
      evidence_signals: {
        stack_trace_signal: 1.0,
        test_failure_signal: 1.0,
        logs_tfidf_signal: 0.5,
        bug_report_tfidf_signal: 0.4,
        git_history_signal: 0.9,
        score_formula: '0.35 * stack + 0.25 * test + 0.20 * logs + 0.10 * bug + 0.10 * git',
        score_disclaimer: 'Evidence score is a weighted measure of supporting evidence and is not a probability.',
      },
      run_duration_ms: 250,
      created_at: '2026-09-20T17:30:00Z',
    };

    render(<AnalysisReportView analysis={mockAnalysis} />);

    // 1. UI shows 875bcf7 as top relevant commit
    const topHash = screen.getByText('875bcf7');
    expect(topHash).toBeDefined();

    // 2. Executive summary references 875bcf7 and Likely regression-introducing commit
    const matchingElements = screen.getAllByText(/refactor\(checkout\): add FLASHSALE discount promo tier/);
    expect(matchingElements.length).toBeGreaterThanOrEqual(2);
    
    // Executive summary contains the canonical regression wording
    const summaryElement = matchingElements.find((el) => el.tagName.toLowerCase() === 'p');
    expect(summaryElement).toBeDefined();
    expect(summaryElement?.textContent).toContain('875bcf7a');
    expect(summaryElement?.textContent).toContain('Likely regression-introducing commit');

    // 3. UI Correlated Git History shows 875bcf7 with Likely regression-introducing commit
    const reasonText = screen.getByText(/Modified suspicious code area in CheckoutService\.java/);
    expect(reasonText).toBeDefined();

    // 4. UI does NOT show 2a2701b or 24705a6 as regression-introducing
    const baselineItems = screen.getAllByText(/Baseline setup commit/);
    expect(baselineItems.length).toBe(2);
    expect(screen.queryByText(/2a2701b.*Likely regression-introducing/)).toBeNull();
    expect(screen.queryByText(/24705a6.*Likely regression-introducing/)).toBeNull();
  });
});
