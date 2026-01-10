export interface Document {
  id: string;
  dataset_id: string;
  title: string;
  content?: string;
  file_type?: string;
  file_size?: number;
  chunk_count?: number;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  created_at?: string;
  updated_at?: string;
}

export interface UploadDocumentRequest {
  dataset_id: string;
  file: File;
}
