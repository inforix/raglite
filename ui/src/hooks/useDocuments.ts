import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { Document, DocumentListResponse } from '@/types/document';

export function useDocuments(datasetId?: string, tenantId?: string) {
  return useQuery<Document[], Error>({
    queryKey: QUERY_KEYS.DOCUMENTS(tenantId, datasetId),
    queryFn: async () => {
      const params =
        datasetId && tenantId
          ? { dataset_id: datasetId, tenant_id: tenantId }
          : {};
      const response = await api.get<DocumentListResponse>(API_ENDPOINTS.DOCUMENTS, { params });
      return response.data.items;
    },
    enabled: !!datasetId && !!tenantId,
  });
}

export function useUploadDocument(tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ datasetId, file }: { datasetId: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dataset_id', datasetId);

      const response = await api.post<Document>(API_ENDPOINTS.DOCUMENT_UPLOAD, formData, {
        params: tenantId ? { tenant_id: tenantId } : {},
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENTS() });
    },
  });
}

export function useDeleteDocument(tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(API_ENDPOINTS.DOCUMENT(id), {
        params: tenantId ? { tenant_id: tenantId } : {},
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENTS() });
    },
  });
}

export function useUpdateDocument(tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables: { id: string; filename: string; datasetId?: string }) => {
      const response = await api.put<Document>(API_ENDPOINTS.DOCUMENT(variables.id), {
        filename: variables.filename,
      }, {
        params: tenantId ? { tenant_id: tenantId } : {},
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENTS() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENT(variables.id) });
    },
  });
}
