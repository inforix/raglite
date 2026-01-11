export interface Document {
  id: string;
  dataset_id: string;
  filename: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  language?: string | null;
  status?: string;
  source_uri?: string | null;
  created_at?: string;
}

export interface UploadDocumentRequest {
  dataset_id: string;
  file: File;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
