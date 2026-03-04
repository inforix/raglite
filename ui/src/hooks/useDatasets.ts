import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { Dataset, CreateDatasetRequest, UpdateDatasetRequest } from '@/types/dataset';

export function useDatasets(tenantId?: string) {
  return useQuery<Dataset[], Error>({
    queryKey: QUERY_KEYS.DATASETS(tenantId),
    queryFn: async () => {
      const params = tenantId ? { tenant_id: tenantId } : {};
      const response = await api.get<Dataset[]>(API_ENDPOINTS.DATASETS, { params });
      return response.data;
    },
    enabled: !!tenantId,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateDatasetRequest) => {
      const { tenant_id, ...payload } = data;
      const response = await api.post<Dataset>(API_ENDPOINTS.DATASETS, payload, {
        params: { tenant_id },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useUpdateDataset(id: string, tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateDatasetRequest) => {
      const response = await api.put<Dataset>(API_ENDPOINTS.DATASET(id), data, {
        params: tenantId ? { tenant_id: tenantId } : {},
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DATASET(id) });
    },
  });
}

export function useDeleteDataset(tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(API_ENDPOINTS.DATASET(id), {
        params: tenantId ? { tenant_id: tenantId } : {},
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}
