export type ConnectionState = 'connected' | 'disconnected' | 'checking';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface BackendHealthResponse {
  status: string;
  service: string;
}

export interface DatabaseHealthResponse {
  status: 'connected' | 'disconnected';
  database: string;
  message: string;
}

export interface StatusCardInfo {
  status: ConnectionState;
  label: string;
  details?: string;
  isRefreshing?: boolean;
}

export interface SystemStatusState {
  frontend: StatusCardInfo;
  backend: StatusCardInfo;
  database: StatusCardInfo;
}

// Phase 2 Repository Interfaces
export interface Repository {
  id: string;
  project_id: string | null;
  github_url: string;
  owner: string;
  name: string;
  default_branch: string | null;
  description: string | null;
  primary_language: string | null;
  total_files: number;
  source_files: number;
  analyzed_at: string;
  created_at: string;
}

export interface RepositoryFile {
  id: string;
  repository_id: string;
  path: string;
  extension: string | null;
  language: string | null;
  file_size: number;
  lines_of_code: number;
  is_source_file: boolean;
  created_at: string;
}

export interface RepositoryCommit {
  id: string;
  repository_id: string;
  commit_hash: string;
  author_name: string | null;
  author_email: string | null;
  commit_message: string | null;
  committed_at: string | null;
  files_changed: number;
  created_at?: string;
}

export interface RepositoryDetail {
  repository: Repository;
  files: RepositoryFile[];
  commits: RepositoryCommit[];
  language_breakdown: Record<string, number>;
}

export interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileTreeNode[];
  file?: RepositoryFile;
}
