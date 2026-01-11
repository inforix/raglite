import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';

interface SettingsResponse {
  default_embedder: string;
  allowed_embedders: string[];
  default_chat_model: string;
  allowed_chat_models: string[];
}

export function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [defaultEmbedder, setDefaultEmbedder] = useState('');
  const [defaultChatModel, setDefaultChatModel] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchSettings = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get<SettingsResponse>(API_ENDPOINTS.SETTINGS);
      const body = response.data;
      setData(body);
      setDefaultEmbedder(body.default_embedder);
      setDefaultChatModel(body.default_chat_model);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.put<SettingsResponse>(API_ENDPOINTS.SETTINGS, {
        default_embedder: defaultEmbedder,
        default_chat_model: defaultChatModel,
      });
      setData(response.data);
      setSuccess('Settings saved.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const disabled = loading || saving || !data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure default embedding and chat models (OpenAI-compatible endpoints).
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Embedding</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Default embedder</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={defaultEmbedder}
                onChange={(e) => setDefaultEmbedder(e.target.value)}
                disabled={disabled}
              >
                {data?.allowed_embedders.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Models should be exposed via an OpenAI-compatible embeddings API.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Chat</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Default chat model</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={defaultChatModel}
                onChange={(e) => setDefaultChatModel(e.target.value)}
                disabled={disabled}
              >
                {data?.allowed_chat_models.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Uses an OpenAI-compatible chat/completions endpoint.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {(error || success) && (
        <div
          className={`rounded-md border px-4 py-3 text-sm ${
            error ? 'border-destructive/50 text-destructive' : 'border-emerald-500/50 text-emerald-700'
          }`}
        >
          {error || success}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" onClick={fetchSettings} disabled={loading}>
          Reload
        </Button>
        <Button onClick={handleSave} disabled={disabled}>
          {saving ? 'Saving...' : 'Save settings'}
        </Button>
      </div>
    </div>
  );
}
