import logging
from typing import List, Dict, Optional
import git
from app.core.config import settings

logger = logging.getLogger("ai_investigator.git_history_analyzer")


class GitHistoryAnalyzer:
    """Analyzes recent Git history from a cloned repository."""

    @classmethod
    def extract_recent_commits(cls, repo: git.Repo, max_count: Optional[int] = None) -> List[Dict]:
        """
        Extract recent commit metadata (up to max_count, defaults to 50).
        Extracts only metadata; never stores full diffs or entire source code.
        """
        limit = max_count or settings.MAX_COMMITS_TO_ANALYZE
        commits_data: List[Dict] = []

        try:
            for commit in repo.iter_commits(max_count=limit):
                # Count files changed in this commit
                files_changed_count = 0
                try:
                    stats = commit.stats
                    files_changed_count = len(stats.files)
                except Exception:
                    files_changed_count = 0

                # Extract ISO timestamp with timezone
                committed_at_str = None
                try:
                    committed_at_str = commit.committed_datetime.isoformat()
                except Exception:
                    pass

                author_name = None
                author_email = None
                if commit.author:
                    author_name = commit.author.name
                    author_email = commit.author.email

                # Shorten message to first line / summary, preserving clean headline
                raw_msg = (commit.message or "").strip()

                commits_data.append({
                    "commit_hash": commit.hexsha,
                    "author_name": author_name,
                    "author_email": author_email,
                    "commit_message": raw_msg,
                    "committed_at": committed_at_str,
                    "files_changed": files_changed_count,
                })
        except Exception as exc:
            logger.warning(f"Error iterating git commits: {exc}")

        return commits_data

    @staticmethod
    def get_default_branch(repo: git.Repo) -> str:
        """Determine default or active branch name."""
        try:
            return repo.active_branch.name
        except Exception:
            try:
                # If in detached HEAD state, look at head reference or remotes
                for ref in repo.references:
                    if ref.name in ("main", "master", "origin/main", "origin/master"):
                        return ref.name.split("/")[-1]
                return "main"
            except Exception:
                return "main"
