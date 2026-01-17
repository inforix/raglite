import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';

interface ModelConfig {
  id: string;
  name: string;
  endpoint: string;
  api_key?: string;
  model: string;
  type: 'embedder' | 'chat' | 'rerank';
}

interface SettingsResponse {
  default_embedder: string;
  default_chat_model: string;
  default_rerank_model?: string | null;
  embedders: ModelConfig[];
  chat_models: ModelConfig[];
  rerank_models: ModelConfig[];
}

interface ModelFormState {
  name: string;
  endpoint: string;
  api_key: string;
  model: string;
}

const emptyForm: ModelFormState = {
  name: '',
  endpoint: '',
  api_key: '',
  model: '',
};

export function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [embedders, setEmbedders] = useState<ModelConfig[]>([]);
  const [chatModels, setChatModels] = useState<ModelConfig[]>([]);
  const [rerankModels, setRerankModels] = useState<ModelConfig[]>([]);
  const [defaultEmbedder, setDefaultEmbedder] = useState('');
  const [defaultChatModel, setDefaultChatModel] = useState('');
  const [defaultRerankModel, setDefaultRerankModel] = useState('');
  const [newEmbedder, setNewEmbedder] = useState<ModelFormState>(emptyForm);
  const [newChatModel, setNewChatModel] = useState<ModelFormState>(emptyForm);
  const [newRerankModel, setNewRerankModel] = useState<ModelFormState>(emptyForm);
  const [editingEmbedder, setEditingEmbedder] = useState<string | null>(null);
  const [editingChatModel, setEditingChatModel] = useState<string | null>(null);
  const [editingRerankModel, setEditingRerankModel] = useState<string | null>(null);
  const [editEmbedderForm, setEditEmbedderForm] = useState<ModelFormState | null>(null);
  const [editChatForm, setEditChatForm] = useState<ModelFormState | null>(null);
  const [editRerankForm, setEditRerankForm] = useState<ModelFormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchSettings = async (silent = false) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const response = await api.get<SettingsResponse>(API_ENDPOINTS.SETTINGS);
      const body = response.data;
      const embList = body?.embedders ?? [];
      const chatList = body?.chat_models ?? [];
      const rerankList = body?.rerank_models ?? [];
      setData(body);
      setEmbedders(embList);
      setChatModels(chatList);
      setRerankModels(rerankList);
      setDefaultEmbedder(body?.default_embedder || embList[0]?.name || '');
      setDefaultChatModel(body?.default_chat_model || chatList[0]?.name || '');
      setDefaultRerankModel(body?.default_rerank_model || '');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load settings.');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSaveDefaults = async (
    nextEmbedder: string,
    nextChatModel: string,
    nextRerankModel: string,
    prevEmbedder: string,
    prevChatModel: string,
    prevRerankModel: string,
  ) => {
    if (!data) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.put<SettingsResponse>(API_ENDPOINTS.SETTINGS, {
        default_embedder: nextEmbedder,
        default_chat_model: nextChatModel,
        default_rerank_model: nextRerankModel,
      });
      setData(response.data);
      setSuccess('Default models updated.');
      fetchSettings(true);
    } catch (err: any) {
      setDefaultEmbedder(prevEmbedder);
      setDefaultChatModel(prevChatModel);
      setDefaultRerankModel(prevRerankModel);
      setError(err?.response?.data?.detail || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const endpointForType = (type: 'embedder' | 'chat' | 'rerank', id?: string) => {
    if (type === 'embedder') {
      return id ? API_ENDPOINTS.SETTINGS_EMBEDDER(id) : API_ENDPOINTS.SETTINGS_EMBEDDERS;
    }
    if (type === 'chat') {
      return id ? API_ENDPOINTS.SETTINGS_CHAT_MODEL(id) : API_ENDPOINTS.SETTINGS_CHAT_MODELS;
    }
    return id ? API_ENDPOINTS.SETTINGS_RERANK_MODEL(id) : API_ENDPOINTS.SETTINGS_RERANK_MODELS;
  };

  const handleCreateModel = async (type: 'embedder' | 'chat' | 'rerank') => {
    const form = type === 'embedder' ? newEmbedder : type === 'chat' ? newChatModel : newRerankModel;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.post<ModelConfig>(endpointForType(type), {
        ...form,
        api_key: form.api_key || null,
      });
      if (type === 'embedder') {
        setNewEmbedder(emptyForm);
      } else if (type === 'chat') {
        setNewChatModel(emptyForm);
      } else {
        setNewRerankModel(emptyForm);
      }
      setSuccess(`${type === 'embedder' ? 'Embedder' : type === 'chat' ? 'Chat model' : 'Rerank model'} added.`);
      await fetchSettings(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save model.');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item: ModelConfig, type: 'embedder' | 'chat' | 'rerank') => {
    if (type === 'embedder') {
      setEditingEmbedder(item.id);
      setEditEmbedderForm({
        name: item.name,
        endpoint: item.endpoint,
        api_key: item.api_key || '',
        model: item.model,
      });
    } else if (type === 'chat') {
      setEditingChatModel(item.id);
      setEditChatForm({
        name: item.name,
        endpoint: item.endpoint,
        api_key: item.api_key || '',
        model: item.model,
      });
    } else {
      setEditingRerankModel(item.id);
      setEditRerankForm({
        name: item.name,
        endpoint: item.endpoint,
        api_key: item.api_key || '',
        model: item.model,
      });
    }
  };

  const cancelEdit = (type: 'embedder' | 'chat' | 'rerank') => {
    if (type === 'embedder') {
      setEditingEmbedder(null);
      setEditEmbedderForm(null);
    } else if (type === 'chat') {
      setEditingChatModel(null);
      setEditChatForm(null);
    } else {
      setEditingRerankModel(null);
      setEditRerankForm(null);
    }
  };

  const handleUpdateModel = async (type: 'embedder' | 'chat' | 'rerank') => {
    const editId = type === 'embedder' ? editingEmbedder : type === 'chat' ? editingChatModel : editingRerankModel;
    const form = type === 'embedder' ? editEmbedderForm : type === 'chat' ? editChatForm : editRerankForm;
    if (!editId || !form) return;

    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.put<ModelConfig>(endpointForType(type, editId), {
        ...form,
        api_key: form.api_key || null,
      });
      setSuccess(`${type === 'embedder' ? 'Embedder' : type === 'chat' ? 'Chat model' : 'Rerank model'} updated.`);
      cancelEdit(type);
      await fetchSettings(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update model.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteModel = async (type: 'embedder' | 'chat' | 'rerank', id: string) => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.delete(endpointForType(type, id));
      setSuccess(`${type === 'embedder' ? 'Embedder' : type === 'chat' ? 'Chat model' : 'Rerank model'} deleted.`);
      if (type === 'embedder' && editingEmbedder === id) cancelEdit('embedder');
      if (type === 'chat' && editingChatModel === id) cancelEdit('chat');
      if (type === 'rerank' && editingRerankModel === id) cancelEdit('rerank');
      await fetchSettings(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete model.');
    } finally {
      setSaving(false);
    }
  };

  const disabled = loading || saving || !data;

  const renderModelRow = (item: ModelConfig, type: 'embedder' | 'chat' | 'rerank') => {
    const isEditing =
      type === 'embedder'
        ? editingEmbedder === item.id
        : type === 'chat'
          ? editingChatModel === item.id
          : editingRerankModel === item.id;
    const form = type === 'embedder' ? editEmbedderForm : type === 'chat' ? editChatForm : editRerankForm;
    const setForm = type === 'embedder' ? setEditEmbedderForm : type === 'chat' ? setEditChatForm : setEditRerankForm;

    if (isEditing && form) {
      return (
        <div key={item.id} className="space-y-3 rounded-md border p-3">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={saving}
            />
            <Input
              placeholder="Model (e.g. text-embedding-3-large)"
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
              disabled={saving}
            />
            <Input
              className="md:col-span-2"
              placeholder="Endpoint (e.g. https://api.openai.com/v1)"
              value={form.endpoint}
              onChange={(e) => setForm({ ...form, endpoint: e.target.value })}
              disabled={saving}
            />
            <Input
              className="md:col-span-2"
              type="password"
              placeholder="API key"
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              disabled={saving}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => cancelEdit(type)} disabled={saving}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => handleUpdateModel(type)} disabled={saving}>
              Save
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div key={item.id} className="flex flex-col gap-2 rounded-md border p-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{item.name}</span>
            <span className="text-xs text-muted-foreground">{item.model}</span>
          </div>
          <p className="text-xs text-muted-foreground break-all">{item.endpoint || 'No endpoint set'}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => startEdit(item, type)} disabled={disabled}>
            Edit
          </Button>
          <Button variant="destructive" size="sm" onClick={() => handleDeleteModel(type, item.id)} disabled={disabled}>
            Delete
          </Button>
        </div>
      </div>
    );
  };

  const renderCreateForm = (type: 'embedder' | 'chat' | 'rerank') => {
    const form = type === 'embedder' ? newEmbedder : type === 'chat' ? newChatModel : newRerankModel;
    const setForm = type === 'embedder' ? setNewEmbedder : type === 'chat' ? setNewChatModel : setNewRerankModel;

    return (
      <div className="space-y-3 rounded-md border border-dashed p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <Input
            placeholder="Name (identifier)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            disabled={saving}
          />
          <Input
            placeholder="Model (e.g. gpt-4o-mini)"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            disabled={saving}
          />
          <Input
            className="md:col-span-2"
            placeholder="Endpoint (OpenAI-compatible base URL)"
            value={form.endpoint}
            onChange={(e) => setForm({ ...form, endpoint: e.target.value })}
            disabled={saving}
          />
          <Input
            className="md:col-span-2"
            type="password"
            placeholder="API key"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            disabled={saving}
          />
        </div>
        <div className="flex justify-end">
          <Button size="sm" onClick={() => handleCreateModel(type)} disabled={saving}>
            Add {type === 'embedder' ? 'embedder' : type === 'chat' ? 'chat model' : 'rerank model'}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage default models and maintain OpenAI-compatible endpoints for embedding, chat, and rerank.
        </p>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Embedding models</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Default embedder</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={defaultEmbedder}
                onChange={(e) => {
                  const nextValue = e.target.value;
                  const prevEmbedder = defaultEmbedder;
                  const prevChat = defaultChatModel;
                  const prevRerank = defaultRerankModel;
                  setDefaultEmbedder(nextValue);
                  void handleSaveDefaults(nextValue, defaultChatModel, defaultRerankModel, prevEmbedder, prevChat, prevRerank);
                }}
                disabled={disabled || embedders.length === 0}
              >
                {embedders.map((opt) => (
                  <option key={opt.id} value={opt.name}>
                    {opt.name}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Targets an embeddings endpoint compatible with the OpenAI API.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Configured embedders</Label>
              {embedders.length === 0 ? (
                <p className="text-sm text-muted-foreground">No embedders configured yet.</p>
              ) : (
                <div className="space-y-3">{embedders.map((item) => renderModelRow(item, 'embedder'))}</div>
              )}
            </div>

            <div className="space-y-3">
              <Label>Add new embedder</Label>
              {renderCreateForm('embedder')}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Chat models</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Default chat model</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={defaultChatModel}
                onChange={(e) => {
                  const nextValue = e.target.value;
                  const prevEmbedder = defaultEmbedder;
                  const prevChat = defaultChatModel;
                  const prevRerank = defaultRerankModel;
                  setDefaultChatModel(nextValue);
                  void handleSaveDefaults(defaultEmbedder, nextValue, defaultRerankModel, prevEmbedder, prevChat, prevRerank);
                }}
                disabled={disabled || chatModels.length === 0}
              >
                {chatModels.map((opt) => (
                  <option key={opt.id} value={opt.name}>
                    {opt.name}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Uses a chat/completions endpoint compatible with OpenAI.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Configured chat models</Label>
              {chatModels.length === 0 ? (
                <p className="text-sm text-muted-foreground">No chat models configured yet.</p>
              ) : (
                <div className="space-y-3">{chatModels.map((item) => renderModelRow(item, 'chat'))}</div>
              )}
            </div>

            <div className="space-y-3">
              <Label>Add new chat model</Label>
              {renderCreateForm('chat')}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rerank models</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Default rerank model</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={defaultRerankModel}
                onChange={(e) => {
                  const nextValue = e.target.value;
                  const prevEmbedder = defaultEmbedder;
                  const prevChat = defaultChatModel;
                  const prevRerank = defaultRerankModel;
                  setDefaultRerankModel(nextValue);
                  void handleSaveDefaults(defaultEmbedder, defaultChatModel, nextValue, prevEmbedder, prevChat, prevRerank);
                }}
                disabled={disabled}
              >
                <option value="">None</option>
                {rerankModels.map((opt) => (
                  <option key={opt.id} value={opt.name}>
                    {opt.name}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Uses a rerank endpoint compatible with Cohere's /v1/rerank.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Configured rerank models</Label>
              {rerankModels.length === 0 ? (
                <p className="text-sm text-muted-foreground">No rerank models configured yet.</p>
              ) : (
                <div className="space-y-3">{rerankModels.map((item) => renderModelRow(item, 'rerank'))}</div>
              )}
            </div>

            <div className="space-y-3">
              <Label>Add new rerank model</Label>
              {renderCreateForm('rerank')}
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
        <Button variant="outline" onClick={() => fetchSettings()} disabled={loading}>
          Reload
        </Button>
      </div>
    </div>
  );
}
