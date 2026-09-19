import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import git

from app.models.analysis import (
    EvidenceStrength,
    CandidateSignals,
    FailureCandidate,
    FailureChainStep,
    RelevantCommit,
    EvidenceSignalsSummary,
)

# Weight distribution explicitly defined per specification
WEIGHT_STACK_TRACE = 0.35
WEIGHT_TEST_FAILURE = 0.25
WEIGHT_LOGS = 0.20
WEIGHT_BUG_REPORT = 0.10
WEIGHT_GIT_RECENCY = 0.10


class IntelligenceEngine:
    """
    Investigation Intelligence Engine v1.
    Deterministic, explainable evidence correlation without external LLMs or vector databases.
    """

    @classmethod
    def analyze(
        cls,
        repo_dir: str,
        git_repo: Optional[git.Repo],
        evidence_items: List[Dict[str, Any]],
    ) -> Tuple[List[FailureCandidate], List[FailureChainStep], List[RelevantCommit], EvidenceSignalsSummary, str]:
        """
        Execute full intelligence correlation workflow.
        Returns:
          (ranked_candidates, failure_chain, relevant_commits, evidence_signals_summary, executive_summary)
        """
        # 1. Partition evidence by type
        bug_reports = [e["content"] for e in evidence_items if e.get("evidence_type") == "bug_report"]
        app_logs = [e["content"] for e in evidence_items if e.get("evidence_type") == "application_log"]
        stack_traces = [e["content"] for e in evidence_items if e.get("evidence_type") == "stack_trace"]
        test_outputs = [e["content"] for e in evidence_items if e.get("evidence_type") == "test_output"]

        combined_bug_report = "\n".join(bug_reports)
        combined_logs = "\n".join(app_logs)
        combined_stack_trace = "\n".join(stack_traces)
        combined_test_output = "\n".join(test_outputs)

        # 2. Extract structured elements from stack trace
        stack_frames = cls._parse_stack_trace_frames(combined_stack_trace)
        root_exception = cls._extract_root_exception(combined_stack_trace)

        # 3. Extract test failure details
        failing_tests, test_tested_classes = cls._parse_test_failures(combined_test_output)

        # 4. Enumerate candidate source files from repository
        source_files = cls._collect_repository_source_files(repo_dir)
        if not source_files:
            return [], [], [], cls._empty_signals_summary(), "No source files found in repository."

        # 5. Compute TF-IDF similarities between evidence texts and source files
        tfidf_bug = cls._compute_tfidf_similarity(combined_bug_report, source_files)
        tfidf_logs = cls._compute_tfidf_similarity(combined_logs, source_files)
        tfidf_tests = cls._compute_tfidf_similarity(combined_test_output, source_files)

        # 6. Analyze Git history correlation
        git_file_scores, relevant_commits = cls._correlate_git_history(
            git_repo, source_files, combined_bug_report, combined_logs
        )

        # 7. Score each candidate file using explicit normalized formula
        candidates: List[FailureCandidate] = []
        for rel_path, file_content in source_files.items():
            # Signal 1: Stack Trace Match [0, 1]
            st_score, st_func, st_line, st_evidence = cls._evaluate_stack_trace_signal(
                rel_path, file_content, stack_frames
            )

            # Signal 2: Test Failure Correlation [0, 1]
            tf_score, tf_evidence = cls._evaluate_test_failure_signal(
                rel_path, failing_tests, test_tested_classes, tfidf_tests.get(rel_path, 0.0)
            )

            # Signal 3: Application Logs TF-IDF [0, 1]
            log_sim = tfidf_logs.get(rel_path, 0.0)
            log_score, log_evidence = cls._evaluate_log_signal(rel_path, combined_logs, log_sim)

            # Signal 4: Bug Report TF-IDF [0, 1]
            bug_sim = tfidf_bug.get(rel_path, 0.0)
            bug_score, bug_evidence = cls._evaluate_bug_report_signal(rel_path, combined_bug_report, bug_sim)

            # Signal 5: Git Recency / Blame [0, 1]
            git_score = git_file_scores.get(rel_path, 0.0)
            git_evidence = []
            if git_score > 0.0:
                git_evidence.append(f"Modified in recent Git commits touching incident regression area")

            # Final Evidence Score: weighted formula
            final_score = (
                WEIGHT_STACK_TRACE * st_score +
                WEIGHT_TEST_FAILURE * tf_score +
                WEIGHT_LOGS * log_score +
                WEIGHT_BUG_REPORT * bug_score +
                WEIGHT_GIT_RECENCY * git_score
            )
            final_score = round(min(1.0, max(0.0, final_score)), 4)

            # Compile supporting evidence bullets
            all_evidence = st_evidence + tf_evidence + log_evidence + bug_evidence + git_evidence

            # Determine Evidence Strength rating
            if final_score >= 0.70:
                strength = EvidenceStrength.HIGH
            elif final_score >= 0.40:
                strength = EvidenceStrength.MODERATE
            else:
                strength = EvidenceStrength.LOW

            # Only retain candidates with non-zero supporting evidence
            if final_score > 0.05 or all_evidence:
                candidates.append(
                    FailureCandidate(
                        file_path=rel_path,
                        function_name=st_func,
                        line_number=st_line,
                        evidence_score=final_score,
                        evidence_strength=strength,
                        supporting_evidence=all_evidence,
                        signals=CandidateSignals(
                            stack_trace_score=round(st_score, 4),
                            test_failure_score=round(tf_score, 4),
                            logs_score=round(log_score, 4),
                            bug_report_score=round(bug_score, 4),
                            git_recency_score=round(git_score, 4),
                            final_score=final_score,
                        ),
                    )
                )

        # Sort candidates descending by evidence score
        candidates.sort(key=lambda c: c.evidence_score, reverse=True)

        # 8. Construct Probable Failure Chain
        failure_chain = cls._construct_failure_chain(
            candidates, stack_frames, root_exception, combined_bug_report, failing_tests
        )

        # 9. Aggregate Signals Summary
        signals_summary = cls._compute_signals_summary(candidates)

        # 10. Generate Explainable Executive Summary
        summary = cls._generate_summary(candidates, root_exception, failure_chain, relevant_commits)

        return candidates, failure_chain, relevant_commits, signals_summary, summary

    # =========================================================================
    # NLP & Statistical TF-IDF Vectorization
    # =========================================================================

    @classmethod
    def _compute_tfidf_similarity(cls, query_text: str, source_files: Dict[str, str]) -> Dict[str, float]:
        """
        Calculate cosine similarity between query evidence text and each source file
        using scikit-learn TfidfVectorizer.
        """
        if not query_text.strip() or not source_files:
            return {path: 0.0 for path in source_files}

        corpus = [query_text]
        file_keys = list(source_files.keys())
        for path in file_keys:
            corpus.append(source_files[path])

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                token_pattern=r"(?u)\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b",
                max_features=5000,
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # Cosine similarity between query (index 0) and each document (index 1..N)
            query_vec = tfidf_matrix[0:1]
            doc_vecs = tfidf_matrix[1:]
            sims = cosine_similarity(query_vec, doc_vecs).flatten()

            results = {}
            for i, path in enumerate(file_keys):
                score = float(sims[i])
                results[path] = round(max(0.0, min(1.0, score)), 4)
            return results
        except Exception:
            return {path: 0.0 for path in source_files}

    # =========================================================================
    # Stack Trace & Exception Parsing
    # =========================================================================

    @classmethod
    def _parse_stack_trace_frames(cls, stack_text: str) -> List[Dict[str, Any]]:
        """
        Extract stack trace frames across Python, Java, and JavaScript/TypeScript.
        """
        frames: List[Dict[str, Any]] = []

        # Java pattern: at com.pkg.Class.method(Class.java:123)
        java_pattern = re.compile(
            r"at\s+([a-zA-Z0-9_$.]+)\.([a-zA-Z0-9_$]+)\(([a-zA-Z0-9_$]+\.[a-zA-Z]+):(\d+)\)"
        )
        for m in java_pattern.finditer(stack_text):
            frames.append({
                "class_name": m.group(1),
                "function_name": m.group(2),
                "filename": m.group(3),
                "line_number": int(m.group(4)),
            })

        # Python pattern: File "path/to/file.py", line 123, in func_name
        py_pattern = re.compile(
            r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+([a-zA-Z0-9_]+)'
        )
        for m in py_pattern.finditer(stack_text):
            filename = os.path.basename(m.group(1))
            frames.append({
                "path": m.group(1),
                "filename": filename,
                "line_number": int(m.group(2)),
                "function_name": m.group(3),
            })

        # Node pattern: at funcName (path/to/file.js:123:45) or at path/to/file.js:123:45
        node_pattern = re.compile(
            r"at\s+(?:([a-zA-Z0-9_$.<>]+)\s+\()?([^:()]+):(\d+):(?:\d+)\)?"
        )
        for m in node_pattern.finditer(stack_text):
            func = m.group(1) or "anonymous"
            filepath = m.group(2).strip()
            filename = os.path.basename(filepath)
            try:
                line_num = int(m.group(3))
                frames.append({
                    "function_name": func,
                    "path": filepath,
                    "filename": filename,
                    "line_number": line_num,
                })
            except Exception:
                pass

        return frames

    @classmethod
    def _extract_root_exception(cls, text: str) -> Optional[str]:
        """Extract the root exception type and message."""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            if "Exception:" in ln or "Error:" in ln or "NullPointerException" in ln:
                return ln
        return None

    # =========================================================================
    # Test Failure Parsing
    # =========================================================================

    @classmethod
    def _parse_test_failures(cls, test_output: str) -> Tuple[List[str], List[str]]:
        """Extract failing test names and target class/module names."""
        failing_tests: List[str] = []
        tested_classes: List[str] = []

        # Java Maven/Gradle: Running com.pkg.MyClassTest or MyClassTest > testMethod FAILED
        for m in re.finditer(r"Running\s+([a-zA-Z0-9_$.]+)", test_output):
            test_cls = m.group(1).split(".")[-1]
            failing_tests.append(test_cls)
            if test_cls.endswith("Test"):
                tested_classes.append(test_cls[:-4])

        # Python pytest: FAILED tests/test_foo.py::test_bar
        for m in re.finditer(r"FAILED\s+([^:]+)::([a-zA-Z0-9_]+)", test_output):
            test_file = os.path.basename(m.group(1))
            failing_tests.append(f"{test_file}::{m.group(2)}")
            if test_file.startswith("test_"):
                tested_classes.append(test_file[5:].split(".")[0])

        return failing_tests, tested_classes

    # =========================================================================
    # Evaluation Signals
    # =========================================================================

    @classmethod
    def _evaluate_stack_trace_signal(
        cls, rel_path: str, file_content: str, stack_frames: List[Dict[str, Any]]
    ) -> Tuple[float, Optional[str], Optional[int], List[str]]:
        """Compute normalized [0, 1] stack trace match score."""
        if not stack_frames:
            return 0.0, None, None, []

        filename = os.path.basename(rel_path)
        base_no_ext = os.path.splitext(filename)[0]

        evidence = []
        best_score = 0.0
        best_func = None
        best_line = None

        for idx, frame in enumerate(stack_frames):
            frame_file = frame.get("filename", "")
            frame_class = frame.get("class_name", "")

            is_match = (
                filename == frame_file
                or (frame_file and rel_path.endswith(frame_file))
                or (frame_class and base_no_ext in frame_class)
            )

            if is_match:
                # Frame weight: highest for frames closest to error origin
                pos_weight = 1.0 if idx == 0 else max(0.4, 1.0 - (idx * 0.15))
                if pos_weight > best_score:
                    best_score = pos_weight
                    best_func = frame.get("function_name")
                    best_line = frame.get("line_number")
                    evidence.append(
                        f"Directly referenced in stack trace at {filename}:{best_line} in method '{best_func}'"
                    )

        return best_score, best_func, best_line, evidence

    @classmethod
    def _evaluate_test_failure_signal(
        cls, rel_path: str, failing_tests: List[str], tested_classes: List[str], tfidf_sim: float
    ) -> Tuple[float, List[str]]:
        """Compute normalized [0, 1] test failure correlation score."""
        filename = os.path.basename(rel_path)
        base_no_ext = os.path.splitext(filename)[0]

        evidence = []
        score = 0.0

        # Direct tested target (e.g. CheckoutService tested by CheckoutServiceTest)
        if any(base_no_ext == target for target in tested_classes):
            score = 1.0
            evidence.append(f"Direct target of failing unit test suite")
        elif any(base_no_ext in test for test in failing_tests):
            score = 0.85
            evidence.append(f"Referenced in failing test report")
        elif tfidf_sim > 0.15:
            score = min(0.70, tfidf_sim * 1.5)
            evidence.append(f"Correlated with test assertion failure tokens (TF-IDF: {tfidf_sim:.2f})")

        return score, evidence

    @classmethod
    def _evaluate_log_signal(
        cls, rel_path: str, logs_text: str, tfidf_sim: float
    ) -> Tuple[float, List[str]]:
        """Compute normalized [0, 1] logs similarity score."""
        filename = os.path.basename(rel_path)
        base_no_ext = os.path.splitext(filename)[0]

        evidence = []
        base_score = tfidf_sim

        # Check explicit mention in logs
        if re.search(r"\b" + re.escape(base_no_ext) + r"\b", logs_text):
            base_score = max(base_score, 0.75)
            evidence.append(f"Component '{base_no_ext}' explicitly recorded in application error logs")
        elif tfidf_sim > 0.10:
            evidence.append(f"Vocabulary matched error log telemetry (TF-IDF: {tfidf_sim:.2f})")

        return min(1.0, base_score), evidence

    @classmethod
    def _evaluate_bug_report_signal(
        cls, rel_path: str, bug_text: str, tfidf_sim: float
    ) -> Tuple[float, List[str]]:
        """Compute normalized [0, 1] bug report similarity score."""
        filename = os.path.basename(rel_path)
        base_no_ext = os.path.splitext(filename)[0]

        evidence = []
        base_score = tfidf_sim

        # Check explicit mention of class/component in bug report
        if re.search(r"\b" + re.escape(base_no_ext) + r"\b", bug_text, re.IGNORECASE):
            base_score = max(base_score, 0.70)
            evidence.append(f"Referenced in bug report description or reproduction steps")
        elif tfidf_sim > 0.10:
            evidence.append(f"Correlated with bug report keywords (TF-IDF: {tfidf_sim:.2f})")

        return min(1.0, base_score), evidence

    @classmethod
    def _correlate_git_history(
        cls,
        repo: Optional[git.Repo],
        source_files: Dict[str, str],
        bug_report: str,
        logs: str,
    ) -> Tuple[Dict[str, float], List[RelevantCommit]]:
        """Extract recent commits touching candidate files and calculate recency score [0, 1]."""
        file_scores = {path: 0.0 for path in source_files}
        relevant_commits: List[RelevantCommit] = []

        if not repo:
            return file_scores, []

        try:
            commits = list(repo.iter_commits(max_count=20))
            if not commits:
                return file_scores, []

            # Extract incident keywords for message matching
            incident_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", (bug_report + " " + logs).lower()))

            for idx, commit in enumerate(commits):
                msg = (commit.message or "").strip()
                commit_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", msg.lower()))
                common_terms = incident_words.intersection(commit_words)

                # Weight by commit recency (1.0 for head, decreasing)
                recency_factor = max(0.2, 1.0 - (idx * 0.15))

                # Identify files touched by commit
                touched_files: List[str] = []
                try:
                    stats = commit.stats
                    touched_files = list(stats.files.keys())
                except Exception:
                    pass

                matched_any = False
                for tfile in touched_files:
                    # Match relative path or basename
                    for rel_path in source_files:
                        if rel_path.endswith(tfile) or tfile.endswith(rel_path) or os.path.basename(rel_path) == os.path.basename(tfile):
                            file_scores[rel_path] = max(file_scores[rel_path], recency_factor)
                            matched_any = True

                # Check if commit message matches incident keywords
                if common_terms or matched_any:
                    reason = []
                    if matched_any:
                        reason.append("Modified candidate failure files")
                    if common_terms:
                        top_terms = list(common_terms)[:3]
                        reason.append(f"Commit message matches incident terms: {', '.join(top_terms)}")

                    relevant_commits.append(
                        RelevantCommit(
                            commit_hash=commit.hexsha[:8],
                            author_name=commit.author.name if commit.author else "Unknown",
                            committed_at=commit.committed_datetime.isoformat() if hasattr(commit, "committed_datetime") else None,
                            commit_message=msg.splitlines()[0] if msg else "No commit message",
                            relevance_reason="; ".join(reason),
                        )
                    )
        except Exception:
            pass

        return file_scores, relevant_commits[:5]

    # =========================================================================
    # Failure Chain Construction
    # =========================================================================

    @classmethod
    def _construct_failure_chain(
        cls,
        candidates: List[FailureCandidate],
        stack_frames: List[Dict[str, Any]],
        root_exception: Optional[str],
        bug_report: str,
        failing_tests: List[str],
    ) -> List[FailureChainStep]:
        """Synthesize probable causal failure sequence from evidence progression."""
        steps: List[FailureChainStep] = []
        step_num = 1

        # Step 1: Trigger
        trigger_summary = "Client operation triggered under incident conditions."
        if bug_report:
            first_line = bug_report.splitlines()[0]
            if len(first_line) > 10:
                trigger_summary = first_line[:120]

        steps.append(
            FailureChainStep(
                step_number=step_num,
                phase="Trigger Event",
                title="Failure Trigger Initiated",
                description=trigger_summary,
                source="Bug Report",
                location=None,
            )
        )
        step_num += 1

        # Step 2: Entrypoint
        if len(stack_frames) > 1:
            outer_frame = stack_frames[-1]
            steps.append(
                FailureChainStep(
                    step_number=step_num,
                    phase="Service Entrypoint",
                    title=f"Request received at {outer_frame.get('filename')}",
                    description=f"Invocation entered through method '{outer_frame.get('function_name')}' at line {outer_frame.get('line_number')}.",
                    source="Stack Trace / Logs",
                    location=f"{outer_frame.get('filename')}:{outer_frame.get('line_number')}",
                )
            )
            step_num += 1

        # Step 3: Fault Location
        if candidates:
            primary = candidates[0]
            loc_str = primary.file_path
            if primary.line_number:
                loc_str += f":{primary.line_number}"

            steps.append(
                FailureChainStep(
                    step_number=step_num,
                    phase="Fault Location",
                    title=f"Defect manifested in {os.path.basename(primary.file_path)}",
                    description=(
                        f"Highest evidence candidate ({primary.file_path}) encountered invalid state during execution. "
                        f"Evidence strength: {primary.evidence_strength.value.upper()} ({primary.evidence_score:.2f})."
                    ),
                    source="Static Code Analysis",
                    location=loc_str,
                )
            )
            step_num += 1

        # Step 4: Exception Manifestation
        exc_str = root_exception or "Unhandled runtime exception"
        exc_loc = None
        if stack_frames:
            exc_loc = f"{stack_frames[0].get('filename')}:{stack_frames[0].get('line_number')}"

        steps.append(
            FailureChainStep(
                step_number=step_num,
                phase="Exception Manifestation",
                title="Unhandled Exception Raised",
                description=exc_str[:150],
                source="Stack Trace",
                location=exc_loc,
            )
        )
        step_num += 1

        # Step 5: Test Failure
        if failing_tests:
            steps.append(
                FailureChainStep(
                    step_number=step_num,
                    phase="Test Assertion Failure",
                    title="Automated Test Assertion Failed",
                    description=f"Regression caught by test suite: {failing_tests[0]}",
                    source="Failing Test Output",
                    location=failing_tests[0],
                )
            )

        return steps

    # =========================================================================
    # Summaries & Utilities
    # =========================================================================

    @classmethod
    def _compute_signals_summary(cls, candidates: List[FailureCandidate]) -> EvidenceSignalsSummary:
        """Calculate aggregate signal maximums across top candidates."""
        if not candidates:
            return cls._empty_signals_summary()

        top = candidates[0]
        return EvidenceSignalsSummary(
            stack_trace_signal=top.signals.stack_trace_score,
            test_failure_signal=top.signals.test_failure_score,
            logs_tfidf_signal=top.signals.logs_score,
            bug_report_tfidf_signal=top.signals.bug_report_score,
            git_history_signal=top.signals.git_recency_score,
        )

    @classmethod
    def _empty_signals_summary(cls) -> EvidenceSignalsSummary:
        return EvidenceSignalsSummary(
            stack_trace_signal=0.0,
            test_failure_signal=0.0,
            logs_tfidf_signal=0.0,
            bug_report_tfidf_signal=0.0,
            git_history_signal=0.0,
        )

    @classmethod
    def _generate_summary(
        cls,
        candidates: List[FailureCandidate],
        root_exception: Optional[str],
        failure_chain: List[FailureChainStep],
        relevant_commits: List[RelevantCommit],
    ) -> str:
        """Synthesize explainable narrative."""
        if not candidates:
            return "No suspicious candidate files could be correlated with the provided evidence artifacts."

        primary = candidates[0]
        fname = os.path.basename(primary.file_path)
        func_part = f" in method '{primary.function_name}'" if primary.function_name else ""
        line_part = f" around line {primary.line_number}" if primary.line_number else ""

        exc_part = f" triggered by '{root_exception}'" if root_exception else ""

        commit_part = ""
        if relevant_commits:
            rc = relevant_commits[0]
            commit_part = f" Correlated with recent commit {rc.commit_hash} ('{rc.commit_message}')."

        summary = (
            f"Investigation identified '{fname}'{func_part}{line_part} as the primary failure candidate "
            f"with an evidence score of {primary.evidence_score:.2f} ({primary.evidence_strength.value.upper()} evidence strength){exc_part}."
            f"{commit_part} "
            f"Evidence score is a weighted measure of supporting evidence across stack traces, test assertions, logs, bug reports, and Git history, and is not a probability."
        )
        return summary

    @classmethod
    def _collect_repository_source_files(cls, repo_dir: str) -> Dict[str, str]:
        """Read source code text from repository up to safety limits."""
        source_files: Dict[str, str] = {}
        ignored_dirs = {".git", "node_modules", "venv", "__pycache__", ".idea", "dist", "build", "target"}
        valid_exts = {".java", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb", ".cs", ".php", ".cpp", ".c", ".h"}

        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
                    try:
                        # Safety limit: read up to 256 KB per source file for analysis
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read(262144)
                            source_files[rel_path] = content
                    except Exception:
                        pass
        return source_files
