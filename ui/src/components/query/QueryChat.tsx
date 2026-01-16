import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useTenants } from '@/hooks/useTenants';
import { useDatasets } from '@/hooks/useDatasets';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';

interface SourceItem {
  text: string;
  score: number;
  dataset_id: string;
  document_id: string;
  source_uri?: string;
  meta?: Record<string, any> | null;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceItem[];
  rewritten?: string;
}

export function QueryChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTenantId, setSelectedTenantId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: tenants } = useTenants();
  const { data: datasets } = useDatasets(selectedTenantId || undefined);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const truncateText = (text: string, maxLength = 280) => {
    if (text.length <= maxLength) return text.trim();
    return `${text.slice(0, maxLength).trimEnd()}...`;
  };

  const splitSentences = (text: string) => {
    const normalized = text.replace(/\s+/g, ' ').trim();
    if (!normalized) return [];
    const matches = normalized.match(/[^.!?。！？]+[.!?。！？]?/g);
    if (!matches) return [];
    return matches.map((sentence) => sentence.trim()).filter(Boolean);
  };

  const getQueryTokens = (question: string) => {
    const asciiTokens = question
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((word) => word.length > 2);
    if (asciiTokens.length > 0) return asciiTokens;
    const trimmed = question.trim();
    return trimmed ? [trimmed] : [];
  };

  const buildAnswer = (question: string, results: SourceItem[]) => {
    if (results.length === 0) {
      return 'I could not find relevant passages in the selected dataset. Try rephrasing or broadening the question.';
    }

    const tokens = getQueryTokens(question);
    const sentences = results
      .slice(0, 3)
      .flatMap((result) => splitSentences(result.text));

    if (sentences.length === 0) {
      return `Here's a concise answer based on the retrieved documents: ${truncateText(
        results[0].text,
        320,
      )}`;
    }

    const scored = sentences.map((sentence) => {
      let score = 0;
      tokens.forEach((token) => {
        if (!token) return;
        if (/^[a-z0-9]+$/.test(token)) {
          if (sentence.toLowerCase().includes(token)) score += 1;
        } else if (sentence.includes(token)) {
          score += 2;
        }
      });
      return { sentence, score };
    });

    const hasSignal = scored.some((item) => item.score > 0);
    const sorted = [...scored].sort(
      (a, b) => b.score - a.score || a.sentence.length - b.sentence.length,
    );
    const selected: string[] = [];
    const pool = hasSignal ? sorted : scored;

    for (const item of pool) {
      if (!selected.includes(item.sentence)) {
        selected.push(item.sentence);
      }
      if (selected.length >= 2) break;
    }

    const summary = selected.join(' ');
    return `Here's a concise answer based on the retrieved documents: ${summary}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    if (!selectedDatasetId) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Please select a dataset to query.' },
      ]);
      return;
    }

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const payload = {
        query: userMessage.content,
        dataset_ids: [selectedDatasetId],
        k: 5,
        rewrite: true,
      };
      const response = await api.post(API_ENDPOINTS.QUERY, payload);
      const data = response.data as {
        query: string;
        rewritten?: string;
        results: Array<{
          text: string;
          score: number;
          dataset_id: string;
          document_id: string;
          source_uri?: string;
          meta?: Record<string, any> | null;
        }>;
      };

      const results = data.results ?? [];
      const answer = buildAnswer(data.query || userMessage.content, results);

      const assistantMessage: Message = {
        role: 'assistant',
        content: answer,
        sources: results.map((r) => ({
          text: r.text,
          score: r.score,
          dataset_id: r.dataset_id,
          document_id: r.document_id,
          source_uri: r.source_uri,
          meta: r.meta ?? null,
        })),
        rewritten: data.rewritten,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Query error:', error);
      const detail = error?.response?.data?.detail;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Query failed${detail ? `: ${detail}` : ''}` },
      ]);
      setIsLoading(false);
      return;
    }
    setIsLoading(false);
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Query Chat</h1>
        <p className="text-muted-foreground mt-2">
          Ask questions about your documents
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Tenant</Label>
          <select
            className="w-full h-10 px-3 rounded-md border border-input bg-background"
            value={selectedTenantId}
            onChange={(e) => {
              setSelectedTenantId(e.target.value);
              setSelectedDatasetId('');
            }}
          >
            <option value="">Select tenant (optional)</option>
            {tenants?.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <Label>Dataset</Label>
          <select
            className="w-full h-10 px-3 rounded-md border border-input bg-background"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            disabled={!selectedTenantId}
          >
            <option value="">Select dataset</option>
            {datasets?.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="border-b border-border/60">
          <CardTitle>Conversation</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
          <div className="flex-1 overflow-y-auto space-y-6 px-6 py-6 bg-muted/10">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <p className="text-base font-medium text-foreground">
                  Ask a question to search your documents.
                </p>
                <p className="text-sm mt-2">
                  I will summarize what I find and show the sources.
                </p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="h-9 w-9 rounded-full bg-foreground text-background flex items-center justify-center text-xs font-semibold">
                      AI
                    </div>
                  )}
                  <div
                    className={`max-w-[78%] rounded-2xl px-4 py-3 shadow-sm ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background border border-border/60'
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-6">
                      {message.content}
                    </p>
                    {message.role === 'assistant' &&
                      message.sources &&
                      message.sources.length > 0 && (
                        <div className="mt-4 border-t border-border/60 pt-3 space-y-2 text-xs text-muted-foreground">
                          <p className="uppercase tracking-wide text-[11px] font-semibold">
                            Sources
                          </p>
                          <div className="grid gap-2">
                            {message.sources.map((source, sourceIndex) => (
                              <div
                                key={`${source.document_id}-${sourceIndex}`}
                                className="rounded-lg border border-border/50 bg-muted/40 p-3"
                              >
                                <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-wide">
                                  <span className="font-semibold text-foreground">
                                    Source {sourceIndex + 1}
                                  </span>
                                  <span>score {source.score.toFixed(3)}</span>
                                  {source.dataset_id && (
                                    <span>dataset {source.dataset_id}</span>
                                  )}
                                  {source.document_id && (
                                    <span>doc {source.document_id}</span>
                                  )}
                                </div>
                                <p className="mt-2 text-xs leading-5 text-foreground/80">
                                  {truncateText(source.text)}
                                </p>
                                {source.source_uri && (
                                  <p className="mt-2 text-[11px] text-muted-foreground">
                                    {source.source_uri}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                  </div>
                  {message.role === 'user' && (
                    <div className="h-9 w-9 rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-foreground/70">
                      You
                    </div>
                  )}
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-background border border-border/60 rounded-2xl p-4">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex gap-2 border-t border-border/60 bg-background px-4 py-4"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              disabled={isLoading}
              className="flex-1 h-11"
            />
            <Button type="submit" disabled={isLoading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
