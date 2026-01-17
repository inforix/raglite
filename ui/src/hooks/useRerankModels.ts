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
  default_rerank_model?: string | null;
  rerank_models?: ModelConfig[];
}

export function useRerankModels() {
  return useQuery<{ rerankModels: ModelConfig[]; defaultRerankModel: string }, Error>({
    queryKey: ['rerank-models'],
    queryFn: async () => {
      const response = await api.get<SettingsResponse>(API_ENDPOINTS.SETTINGS);
      const body = response.data;
      return {
        rerankModels: body?.rerank_models ?? [],
        defaultRerankModel: body?.default_rerank_model ?? '',
      };
    },
  });
}
