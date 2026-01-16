export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/v1/auth/login',
  LOGOUT: '/v1/auth/logout',
  ME: '/v1/auth/me',
  REFRESH: '/v1/auth/refresh',
  
  // Tenants
  TENANTS: '/v1/tenants',
  TENANT: (id: string) => `/v1/tenants/${id}`,
  TENANT_REGENERATE_KEY: (id: string) => `/v1/tenants/${id}/regenerate-key`,
  
  // Datasets
  DATASETS: '/v1/datasets',
  DATASET: (id: string) => `/v1/datasets/${id}`,
  
  // Documents
  DOCUMENTS: '/v1/documents',
  DOCUMENT: (id: string) => `/v1/documents/${id}`,
  DOCUMENT_UPLOAD: '/v1/documents/upload',
  
  // Query
  QUERY: '/v1/query',
  QUERY_STREAM: '/v1/query/stream',
  QUERY_HISTORY: '/v1/query/history',
  QUERY_STATS_DAILY: '/v1/query/stats/daily',

  // Settings
  SETTINGS: '/v1/settings',
  SETTINGS_EMBEDDERS: '/v1/settings/embedders',
  SETTINGS_EMBEDDER: (id: string) => `/v1/settings/embedders/${id}`,
  SETTINGS_CHAT_MODELS: '/v1/settings/chat-models',
  SETTINGS_CHAT_MODEL: (id: string) => `/v1/settings/chat-models/${id}`,
};

export const QUERY_KEYS = {
  TENANTS: ['tenants'],
  TENANT: (id: string) => ['tenant', id],
  DATASETS: (tenantId?: string) => ['datasets', tenantId],
  DATASET: (id: string) => ['dataset', id],
  DOCUMENTS: (datasetId?: string) => ['documents', datasetId],
  DOCUMENT: (id: string) => ['document', id],
  ME: ['me'],
  QUERIES_COUNT: ['queries-count'],
  QUERIES_DAILY: ['queries-daily'],
};
