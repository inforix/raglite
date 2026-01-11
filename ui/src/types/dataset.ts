export interface Dataset {
  id: string;
  tenant_id: string;
  name: string;
  embedder?: string;
  description?: string;
  language?: string;
  created_at?: string;
  updated_at?: string;
  document_count?: number;
}

export interface CreateDatasetRequest {
  tenant_id: string;
  name: string;
  embedder: string;
  description?: string;
  language?: string;
}

export interface UpdateDatasetRequest {
  name?: string;
  embedder?: string;
  description?: string;
  confirm_embedder_change?: boolean;
  language?: string;
}
