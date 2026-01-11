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

interface Message {
  role: 'user' | 'assistant';
  content: string;
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
        }>;
      };

      const lines =
        data.results && data.results.length > 0
          ? data.results.slice(0, 3).map((r, idx) => {
              const label = data.rewritten && idx === 0 ? '(rewritten)' : '';
              return `• ${r.text.trim()}\n  score: ${r.score.toFixed(3)} | dataset: ${r.dataset_id} | doc: ${r.document_id} ${label}`;
            })
          : ['No results found.'];

      const assistantMessage: Message = {
        role: 'assistant',
        content: lines.join('\n'),
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
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col overflow-hidden p-6">
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <p>No messages yet. Start a conversation!</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg p-4">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              disabled={isLoading}
              className="flex-1"
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
