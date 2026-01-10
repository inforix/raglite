export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface QueryRequest {
  query: string;
  tenant_id?: string;
  dataset_id?: string;
  conversation_id?: string;
}

export interface QueryResponse {
  answer: string;
  sources?: Array<{
    document_id: string;
    title: string;
    chunk: string;
    score: number;
  }>;
}
