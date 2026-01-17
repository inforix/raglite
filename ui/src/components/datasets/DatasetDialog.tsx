import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useCreateDataset, useUpdateDataset } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { useEmbedders } from '@/hooks/useEmbedders';
import { useRerankModels } from '@/hooks/useRerankModels';
import { Dataset } from '@/types/dataset';

const optionalNumber = (min: number, max: number) =>
  z.preprocess(
    (value) => {
      if (value === '' || value === null || value === undefined) return undefined;
      if (typeof value === 'string' && value.trim() === '') return undefined;
      const parsed = Number(value);
      return Number.isNaN(parsed) ? undefined : parsed;
    },
    z.number().min(min).max(max).optional(),
  );

const datasetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  tenant_id: z.string().min(1, 'Tenant is required'),
  embedder: z.string().min(1, 'Embedder is required'),
  language: z.string().optional(),
  rerank_enabled: z.boolean().optional(),
  rerank_model: z.string().optional(),
  rerank_top_k: optionalNumber(1, 200),
  rerank_min_score: optionalNumber(0, 1),
});

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'zh-CN', label: 'Simplified Chinese' },
  { value: 'zh-TW', label: 'Traditional Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'hi', label: 'Hindi' },
];

type DatasetFormData = z.infer<typeof datasetSchema>;

interface DatasetDialogProps {
  open: boolean;
  onClose: () => void;
  dataset?: Dataset | null;
}

export function DatasetDialog({ open, onClose, dataset }: DatasetDialogProps) {
  const { data: tenants } = useTenants();
  const { data: embedderData, isLoading: embeddersLoading } = useEmbedders();
  const { data: rerankData, isLoading: rerankLoading } = useRerankModels();
  const createDataset = useCreateDataset();
  const updateDataset = useUpdateDataset(dataset?.id || '');
  const defaultEmbedder = embedderData?.defaultEmbedder || '';
  const embedderOptions = embedderData?.embedders || [];
  const firstEmbedder = embedderOptions[0]?.name || '';
  const defaultRerankModel = rerankData?.defaultRerankModel || '';
  const rerankOptions = rerankData?.rerankModels || [];
  const [confirmReembed, setConfirmReembed] = useState(false);
  const tenantOptions = tenants || [];
  const hasTenantOption = dataset ? tenantOptions.some((t) => t.id === dataset.tenant_id) : true;

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<DatasetFormData>({
    resolver: zodResolver(datasetSchema),
    defaultValues: {
      name: '',
      tenant_id: '',
      language: 'en',
      embedder: '',
      rerank_enabled: false,
      rerank_model: '',
      rerank_top_k: undefined,
      rerank_min_score: undefined,
    },
  });

  useEffect(() => {
    const fallbackEmbedder = dataset?.embedder || defaultEmbedder || firstEmbedder || '';
    const fallbackLanguage = dataset?.language || 'en';
    const fallbackRerankModel = dataset?.rerank_model || '';
    const fallbackRerankEnabled = dataset?.rerank_enabled ?? false;
    const fallbackRerankTopK = dataset?.rerank_top_k ?? undefined;
    const fallbackRerankMinScore = dataset?.rerank_min_score ?? undefined;
    if (dataset) {
      reset({
        name: dataset.name,
        tenant_id: dataset.tenant_id,
        language: fallbackLanguage,
        embedder: fallbackEmbedder,
        rerank_enabled: fallbackRerankEnabled,
        rerank_model: fallbackRerankModel,
        rerank_top_k: fallbackRerankTopK,
        rerank_min_score: fallbackRerankMinScore,
      });
    } else {
      reset({
        name: '',
        tenant_id: '',
        language: 'en',
        embedder: fallbackEmbedder,
        rerank_enabled: false,
        rerank_model: '',
        rerank_top_k: undefined,
        rerank_min_score: undefined,
      });
    }
    setConfirmReembed(false);
  }, [dataset, reset, defaultEmbedder, firstEmbedder, open]);

  const embedderValue = watch('embedder');
  const embedderChanged = Boolean(dataset && embedderValue && embedderValue !== dataset.embedder);
  const rerankEnabled = watch('rerank_enabled');
  const rerankModelValue = watch('rerank_model');
  const hasRerankOptions = rerankOptions.length > 0 || Boolean(defaultRerankModel);

  const onSubmit = async (data: DatasetFormData) => {
    try {
      if (dataset) {
        if (embedderChanged && !confirmReembed) {
          return;
        }
        await updateDataset.mutateAsync({
          name: data.name,
          embedder: data.embedder,
          confirm_embedder_change: embedderChanged,
          language: data.language,
          rerank_enabled: data.rerank_enabled,
          rerank_model: data.rerank_model,
          rerank_top_k: data.rerank_top_k,
          rerank_min_score: data.rerank_min_score,
        });
      } else {
        await createDataset.mutateAsync(data);
      }
      onClose();
    } catch (error) {
      console.error('Error saving dataset:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{dataset ? 'Edit Dataset' : 'Create Dataset'}</DialogTitle>
          <DialogDescription>
            {dataset
              ? 'Update the dataset information'
              : 'Create a new dataset to group related documents'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              placeholder="My Dataset"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="tenant_id">Tenant</Label>
            <select
              id="tenant_id"
              className="w-full h-10 px-3 rounded-md border border-input bg-background"
              {...register('tenant_id')}
              disabled={!!dataset}
            >
              <option value="">Select a tenant</option>
              {!hasTenantOption && dataset && (
                <option value={dataset.tenant_id}>
                  {dataset.tenant_id}
                </option>
              )}
              {tenants?.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
            {errors.tenant_id && (
              <p className="text-sm text-destructive">{errors.tenant_id.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="embedder">Embedder</Label>
            <select
              id="embedder"
              className="w-full h-10 px-3 rounded-md border border-input bg-background"
              {...register('embedder')}
              disabled={embeddersLoading || embedderOptions.length === 0}
            >
              <option value="">Select an embedder</option>
              {embedderOptions.map((embedder) => (
                <option key={embedder.id} value={embedder.name}>
                  {embedder.name}
                </option>
              ))}
            </select>
            {embedderOptions.length === 0 && !embeddersLoading && (
              <p className="text-sm text-muted-foreground">
                No embedders configured. Add one in Settings first.
              </p>
            )}
            {errors.embedder && (
              <p className="text-sm text-destructive">{errors.embedder.message}</p>
            )}
          </div>

          {embedderChanged && (
            <div className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-medium">Changing the embedder will re-embed all documents in this dataset.</p>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={confirmReembed}
                  onChange={(e) => setConfirmReembed(e.target.checked)}
                  className="h-4 w-4"
                />
                <span>I understand and want to trigger a re-embed.</span>
              </label>
            </div>
          )}

          <div className="space-y-2">
            <Label>Rerank</Label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                {...register('rerank_enabled')}
                disabled={!hasRerankOptions || rerankLoading}
                className="h-4 w-4"
              />
              <span>Enable rerank for query results</span>
            </label>
            {!hasRerankOptions && !rerankLoading && (
              <p className="text-sm text-muted-foreground">
                No rerank models configured. Add one in Settings first.
              </p>
            )}
          </div>

          {rerankEnabled && (
            <div className="space-y-4 rounded-md border border-border/70 bg-muted/30 p-3">
              <div className="space-y-2">
                <Label htmlFor="rerank_model">Rerank model</Label>
                <select
                  id="rerank_model"
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  {...register('rerank_model')}
                  disabled={rerankLoading || (!hasRerankOptions && rerankOptions.length === 0)}
                >
                  <option value="">Use default</option>
                  {rerankOptions.map((model) => (
                    <option key={model.id} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                {!defaultRerankModel && rerankModelValue === '' && (
                  <p className="text-sm text-muted-foreground">
                    Default rerank model is not set. Choose a model or set a default in Settings.
                  </p>
                )}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="rerank_top_k">Rerank top K</Label>
                  <Input
                    id="rerank_top_k"
                    type="number"
                    min="1"
                    max="200"
                    placeholder="e.g. 20"
                    {...register('rerank_top_k')}
                  />
                  <p className="text-xs text-muted-foreground">
                    Limit how many retrieved chunks are reranked.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rerank_min_score">Rerank min score</Label>
                  <Input
                    id="rerank_min_score"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    placeholder="e.g. 0.3"
                    {...register('rerank_min_score')}
                  />
                  <p className="text-xs text-muted-foreground">
                    Filter reranked results below this threshold.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="language">Language</Label>
            <select
              id="language"
              className="w-full h-10 px-3 rounded-md border border-input bg-background"
              {...register('language')}
            >
              <option value="">Select a language</option>
              {languageOptions.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
            {errors.language && (
              <p className="text-sm text-destructive">{errors.language.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">
              {dataset ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
