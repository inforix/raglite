import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Users, Database, FileText, MessageSquare } from 'lucide-react';
import { useDatasets } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { api } from '@/lib/api';
import { API_ENDPOINTS, QUERY_KEYS } from '@/lib/constants';
import { DocumentListResponse } from '@/types/document';
import { QueryHistoryResponse, QueryDailyStatsResponse } from '@/types/query';

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
  const dailyQueriesQuery = useQuery<QueryDailyStatsResponse, Error>({
    queryKey: QUERY_KEYS.QUERIES_DAILY,
    queryFn: async () => {
      const response = await api.get<QueryDailyStatsResponse>(API_ENDPOINTS.QUERY_STATS_DAILY, {
        params: { days: 14 },
      });
      return response.data;
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
  const dailyItems = dailyQueriesQuery.data?.items ?? [];
  const hasDailyData = dailyItems.length > 0;

  const chartWidth = 640;
  const chartHeight = 220;
  const chartPadding = 28;
  const maxCount = Math.max(...dailyItems.map((item) => item.count), 1);
  const innerWidth = chartWidth - chartPadding * 2;
  const innerHeight = chartHeight - chartPadding * 2;
  const points = dailyItems.map((item, index) => {
    const ratio = dailyItems.length === 1 ? 0.5 : index / (dailyItems.length - 1);
    const x = chartPadding + ratio * innerWidth;
    const y = chartPadding + (1 - item.count / maxCount) * innerHeight;
    return { x, y, ...item };
  });
  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`).join(' ');
  const startLabel = dailyItems[0]?.date;
  const endLabel = dailyItems[dailyItems.length - 1]?.date;

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
          <CardTitle>Daily Queries</CardTitle>
          <CardDescription>Queries per day over the last two weeks</CardDescription>
        </CardHeader>
        <CardContent>
          {dailyQueriesQuery.isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-muted-foreground">Loading chart...</p>
            </div>
          ) : dailyQueriesQuery.error ? (
            <div className="text-center py-12">
              <p className="text-destructive">Failed to load query stats</p>
            </div>
          ) : hasDailyData ? (
            <div className="w-full">
              <svg
                viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                className="w-full h-56"
                role="img"
                aria-label="Daily queries line chart"
              >
                <defs>
                  <linearGradient id="queriesLine" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity="0" />
                  </linearGradient>
                </defs>
                {[0, 0.5, 1].map((ratio) => {
                  const y = chartPadding + ratio * innerHeight;
                  return (
                    <line
                      key={ratio}
                      x1={chartPadding}
                      y1={y}
                      x2={chartWidth - chartPadding}
                      y2={y}
                      stroke="hsl(var(--border))"
                      strokeOpacity="0.5"
                      strokeDasharray="4 6"
                    />
                  );
                })}
                {linePath && (
                  <>
                    <path
                      d={`${linePath} L${chartWidth - chartPadding},${chartHeight - chartPadding} L${chartPadding},${chartHeight - chartPadding} Z`}
                      fill="url(#queriesLine)"
                    />
                    <path
                      d={linePath}
                      fill="none"
                      stroke="hsl(var(--chart-1))"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </>
                )}
                {points.map((point) => (
                  <circle
                    key={point.date}
                    cx={point.x}
                    cy={point.y}
                    r="4"
                    fill="hsl(var(--chart-1))"
                    stroke="hsl(var(--background))"
                    strokeWidth="2"
                  />
                ))}
              </svg>
              <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                <span>{startLabel || ''}</span>
                <span>Max: {maxCount}</span>
                <span>{endLabel || ''}</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No query activity yet</p>
            </div>
          )}
        </CardContent>
      </Card>

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
