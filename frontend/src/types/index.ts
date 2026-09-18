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
