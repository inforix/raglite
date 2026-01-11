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
import { Dataset } from '@/types/dataset';

const datasetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  tenant_id: z.string().min(1, 'Tenant is required'),
  embedder: z.string().min(1, 'Embedder is required'),
  language: z.string().optional(),
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
  const createDataset = useCreateDataset();
  const updateDataset = useUpdateDataset(dataset?.id || '');
  const defaultEmbedder = embedderData?.defaultEmbedder || '';
  const embedderOptions = embedderData?.embedders || [];
  const firstEmbedder = embedderOptions[0]?.name || '';
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
    },
  });

  useEffect(() => {
    const fallbackEmbedder = dataset?.embedder || defaultEmbedder || firstEmbedder || '';
    const fallbackLanguage = dataset?.language || 'en';
    if (dataset) {
      reset({
        name: dataset.name,
        tenant_id: dataset.tenant_id,
        language: fallbackLanguage,
        embedder: fallbackEmbedder,
      });
    } else {
      reset({ name: '', tenant_id: '', language: 'en', embedder: fallbackEmbedder });
    }
    setConfirmReembed(false);
  }, [dataset, reset, defaultEmbedder, firstEmbedder, open]);

  const embedderValue = watch('embedder');
  const embedderChanged = Boolean(dataset && embedderValue && embedderValue !== dataset.embedder);

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
