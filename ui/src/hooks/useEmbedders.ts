import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';

interface ModelConfig {
  id: string;
  name: string;
  endpoint: string;
  api_key?: string | null;
  model: string;
}

interface SettingsResponse {
  default_embedder: string;
  embedders: ModelConfig[];
}

export function useEmbedders() {
  return useQuery({
    queryKey: ['embedders'],
    queryFn: async () => {
      const response = await api.get<SettingsResponse>(API_ENDPOINTS.SETTINGS);
      const body = response.data;
      return {
        embedders: body?.embedders ?? [],
        defaultEmbedder: body?.default_embedder ?? '',
      };
    },
  });
}
