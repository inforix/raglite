export interface QueryHistoryItem {
  id: string;
  tenant_id: string;
  dataset_ids?: string[] | null;
  query: string;
  created_at: string;
}

export interface QueryHistoryResponse {
  items: QueryHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
