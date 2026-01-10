import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useEffect } from 'react';
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
import { Dataset } from '@/types/dataset';

const datasetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  tenant_id: z.string().min(1, 'Tenant is required'),
  language: z.string().optional(),
});

type DatasetFormData = z.infer<typeof datasetSchema>;

interface DatasetDialogProps {
  open: boolean;
  onClose: () => void;
  dataset?: Dataset | null;
}

export function DatasetDialog({ open, onClose, dataset }: DatasetDialogProps) {
  const { data: tenants } = useTenants();
  const createDataset = useCreateDataset();
  const updateDataset = useUpdateDataset(dataset?.id || '');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DatasetFormData>({
    resolver: zodResolver(datasetSchema),
  });

  useEffect(() => {
    if (dataset) {
      reset({
        name: dataset.name,
        tenant_id: dataset.tenant_id,
        language: dataset.language || '',
      });
    } else {
      reset({ name: '', tenant_id: '', language: 'en' });
    }
  }, [dataset, reset]);

  const onSubmit = async (data: DatasetFormData) => {
    try {
      if (dataset) {
        await updateDataset.mutateAsync({
          name: data.name,
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
            <Label htmlFor="language">Language</Label>
            <Input
              id="language"
              placeholder="en"
              {...register('language')}
            />
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
