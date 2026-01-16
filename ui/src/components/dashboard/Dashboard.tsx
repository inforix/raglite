import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Database, FileText, MessageSquare } from 'lucide-react';
import { useDatasets } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { DocumentListResponse } from '@/types/document';
import { QueryHistoryResponse } from '@/types/query';

export function Dashboard() {
  const tenantsQuery = useTenants();
  const datasetsQuery = useDatasets();
  const documentsQuery = useQuery<number, Error>({
    queryKey: ['documents-count'],
    queryFn: async () => {
      const response = await api.get<DocumentListResponse>(API_ENDPOINTS.DOCUMENTS, {
        params: { page_size: 1 },
      });
      return response.data.total;
    },
  });
  const queriesQuery = useQuery<number, Error>({
    queryKey: QUERY_KEYS.QUERIES_COUNT,
    queryFn: async () => {
      const response = await api.get<QueryHistoryResponse>(API_ENDPOINTS.QUERY_HISTORY, {
        params: { page_size: 1 },
      });
      return response.data.total;
    },
  });

  const formatMetric = (value: number | undefined, isLoading: boolean, isError: boolean) => {
    if (isLoading) {
      return '...';
    }
    if (isError || value === undefined) {
      return '-';
    }
    return String(value);
  };

  const tenantsCount = tenantsQuery.data?.length;
  const datasetsCount = datasetsQuery.data?.length;
  const documentsCount = documentsQuery.data;
  const queriesCount = queriesQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Welcome to RAGLite Admin
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Tenants</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMetric(tenantsCount, tenantsQuery.isLoading, !!tenantsQuery.error)}
            </div>
            <p className="text-xs text-muted-foreground">Total tenants</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Datasets</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMetric(datasetsCount, datasetsQuery.isLoading, !!datasetsQuery.error)}
            </div>
            <p className="text-xs text-muted-foreground">Total datasets</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMetric(documentsCount, documentsQuery.isLoading, !!documentsQuery.error)}
            </div>
            <p className="text-xs text-muted-foreground">Total documents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Queries</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMetric(queriesCount, queriesQuery.isLoading, !!queriesQuery.error)}
            </div>
            <p className="text-xs text-muted-foreground">Recent queries</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Start</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-medium">1. Create a Tenant</h3>
            <p className="text-sm text-muted-foreground">
              Start by creating a tenant to organize your data
            </p>
          </div>
          <div>
            <h3 className="font-medium">2. Add a Dataset</h3>
            <p className="text-sm text-muted-foreground">
              Create datasets within your tenant to group related documents
            </p>
          </div>
          <div>
            <h3 className="font-medium">3. Upload Documents</h3>
            <p className="text-sm text-muted-foreground">
              Upload documents to your datasets for indexing
            </p>
          </div>
          <div>
            <h3 className="font-medium">4. Query Your Data</h3>
            <p className="text-sm text-muted-foreground">
              Use the Query Chat to ask questions about your documents
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
