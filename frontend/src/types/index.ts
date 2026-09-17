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

export interface SystemStatusState {
  frontend: {
    status: ConnectionState;
    label: string;
    details?: string;
  };
  backend: {
    status: ConnectionState;
    label: string;
    details?: string;
  };
  database: {
    status: ConnectionState;
    label: string;
    details?: string;
  };
}
