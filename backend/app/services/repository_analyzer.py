import os
import logging
from typing import Dict, List, Tuple, Optional
from app.core.config import settings

logger = logging.getLogger("ai_investigator.repository_analyzer")

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    "target",
    "coverage",
    ".gradle",
    ".idea",
    ".vscode",
    "bin",
    "obj",
    ".pytest_cache",
    ".next",
    ".nuxt",
}

BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".img",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".class", ".jar", ".pyc", ".pyo", ".wasm", ".db", ".sqlite",
}

# Mapping: extension -> (Language Name, is_source_code)
EXTENSION_LANGUAGE_MAP: Dict[str, Tuple[str, bool]] = {
    # Python
    ".py": ("Python", True),
    ".pyi": ("Python", True),
    # JavaScript / TypeScript
    ".js": ("JavaScript", True),
    ".jsx": ("JavaScript", True),
    ".mjs": ("JavaScript", True),
    ".cjs": ("JavaScript", True),
    ".ts": ("TypeScript", True),
    ".tsx": ("TypeScript", True),
    # Java / JVM
    ".java": ("Java", True),
    ".kt": ("Kotlin", True),
    ".kts": ("Kotlin", True),
    ".scala": ("Scala", True),
    ".groovy": ("Groovy", True),
    # C / C++ / C#
    ".c": ("C", True),
    ".h": ("C", True),
    ".cpp": ("C++", True),
    ".cc": ("C++", True),
    ".cxx": ("C++", True),
    ".hpp": ("C++", True),
    ".cs": ("C#", True),
    # Go / Rust
    ".go": ("Go", True),
    ".rs": ("Rust", True),
    # PHP / Ruby / Swift
    ".php": ("PHP", True),
    ".rb": ("Ruby", True),
    ".swift": ("Swift", True),
    # Web & Query
    ".html": ("HTML", False),
    ".htm": ("HTML", False),
    ".css": ("CSS", False),
    ".scss": ("CSS", False),
    ".sass": ("CSS", False),
    ".less": ("CSS", False),
    ".sql": ("SQL", True),
    # Shell / Scripting
    ".sh": ("Shell", True),
    ".bash": ("Shell", True),
    ".zsh": ("Shell", True),
    ".ps1": ("PowerShell", True),
    # Config / Docs (non-source files)
    ".json": ("JSON", False),
    ".yaml": ("YAML", False),
    ".yml": ("YAML", False),
    ".toml": ("TOML", False),
    ".xml": ("XML", False),
    ".md": ("Markdown", False),
    ".txt": ("Text", False),
}


class RepositoryAnalyzer:
    """Performs safe static analysis on a cloned repository directory."""

    @classmethod
    def analyze(cls, repo_dir: str) -> Dict:
        """
        Scan files within repo_dir, extracting structural and language metadata.
        Never executes any code.
        """
        files_metadata: List[Dict] = []
        language_loc: Dict[str, int] = {}
        language_file_count: Dict[str, int] = {}
        total_files = 0
        source_files = 0

        for root, dirs, files in os.walk(repo_dir):
            # Prune ignored directories in-place to avoid descending into them
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for filename in files:
                if total_files >= settings.MAX_REPO_FILES:
                    logger.warning(f"Hit maximum file scan limit ({settings.MAX_REPO_FILES}) in {repo_dir}")
                    break

                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")

                # Exclude root hidden files (e.g. .gitignore is fine, but .git internals are skipped)
                if rel_path.startswith(".git/"):
                    continue

                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    file_size = 0

                language_info = EXTENSION_LANGUAGE_MAP.get(ext)
                if language_info:
                    language, is_source = language_info
                else:
                    language = "Binary" if ext in BINARY_EXTENSIONS else (ext[1:].upper() if ext else "Unknown")
                    is_source = False

                loc = 0
                if ext not in BINARY_EXTENSIONS and file_size <= settings.MAX_FILE_SIZE_BYTES:
                    loc = cls._count_lines(full_path)

                if is_source:
                    source_files += 1
                    language_loc[language] = language_loc.get(language, 0) + loc
                    language_file_count[language] = language_file_count.get(language, 0) + 1

                total_files += 1
                files_metadata.append({
                    "path": rel_path,
                    "extension": ext or None,
                    "language": language,
                    "file_size": file_size,
                    "lines_of_code": loc,
                    "is_source_file": is_source,
                })

            if total_files >= settings.MAX_REPO_FILES:
                break

        # Determine primary language (highest LOC among source languages, fallback to highest file count)
        primary_language = None
        if language_loc:
            # Sort by LOC desc, then file count desc
            sorted_langs = sorted(
                language_loc.keys(),
                key=lambda lang: (language_loc[lang], language_file_count.get(lang, 0)),
                reverse=True,
            )
            primary_language = sorted_langs[0]

        return {
            "total_files": total_files,
            "source_files": source_files,
            "primary_language": primary_language,
            "files": files_metadata,
            "language_breakdown": language_file_count,
        }

    @staticmethod
    def _count_lines(file_path: str) -> int:
        """Count lines of text in a file safely."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
