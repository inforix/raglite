import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Layers, ShieldCheck, Sparkles } from 'lucide-react';

const stackSections = [
  {
    title: 'API + Auth',
    items: ['FastAPI + Pydantic', 'JWT and API keys', 'SQLite/Postgres metadata'],
  },
  {
    title: 'Retrieval',
    items: ['Qdrant vectors', 'OpenSearch BM25 (optional)', 'Rerank models (optional)'],
  },
  {
    title: 'Workers + Storage',
    items: ['Celery + Redis', 'Local or S3-compatible object storage'],
  },
  {
    title: 'UI',
    items: ['React + Vite', 'Tailwind CSS', 'TanStack Query'],
  },
];

export function AboutPage() {
  const appVersion = __APP_VERSION__ || 'dev';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">About</h1>
        <p className="text-muted-foreground mt-2">
          RAGLite is a spec-driven RAG stack for ingestion, retrieval, reranking, and chat.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-muted-foreground" />
              Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>
              Build production-ready retrieval pipelines with a clean API, a reactive admin UI, and
              modular infrastructure choices.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-foreground">
              <div className="flex items-start gap-3">
                <Layers className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <div className="font-medium">Version</div>
                  <div className="text-sm text-muted-foreground">{appVersion}</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <ShieldCheck className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <div className="font-medium">Security</div>
                  <div className="text-sm text-muted-foreground">Tenant-scoped access</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tech Stack</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {stackSections.map((section) => (
              <div key={section.title}>
                <div className="text-sm font-semibold text-foreground">{section.title}</div>
                <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                  {section.items.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
