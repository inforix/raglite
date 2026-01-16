import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { Tenant, CreateTenantRequest, UpdateTenantRequest } from '@/types/tenant';

export function useTenants() {
  return useQuery<Tenant[], Error>({
    queryKey: QUERY_KEYS.TENANTS,
    queryFn: async () => {
      const response = await api.get<Tenant[]>(API_ENDPOINTS.TENANTS);
      return response.data;
    },
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateTenantRequest) => {
      const response = await api.post<Tenant>(API_ENDPOINTS.TENANTS, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TENANTS });
    },
  });
}

export function useUpdateTenant(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateTenantRequest) => {
      const response = await api.put<Tenant>(API_ENDPOINTS.TENANT(id), data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TENANTS });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TENANT(id) });
    },
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(API_ENDPOINTS.TENANT(id));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TENANTS });
    },
  });
}
