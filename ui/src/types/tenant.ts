export interface Tenant {
  id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateTenantRequest {
  name: string;
}

export interface UpdateTenantRequest {
  name: string;
}

export interface TenantKeyResponse {
  tenant_id: string;
  api_key: string;
  created_at: string;
}
