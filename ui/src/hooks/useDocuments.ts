import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { Document, DocumentListResponse } from '@/types/document';

export function useDocuments(datasetId?: string) {
  return useQuery<Document[], Error>({
    queryKey: QUERY_KEYS.DOCUMENTS(datasetId),
    queryFn: async () => {
      const params = datasetId ? { dataset_id: datasetId } : {};
      const response = await api.get<DocumentListResponse>(API_ENDPOINTS.DOCUMENTS, { params });
      return response.data.items;
    },
    enabled: !!datasetId,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ datasetId, file }: { datasetId: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dataset_id', datasetId);

      const response = await api.post<Document>(API_ENDPOINTS.DOCUMENT_UPLOAD, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENTS(variables.datasetId) });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(API_ENDPOINTS.DOCUMENT(id));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DOCUMENTS() });
    },
  });
}
