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
import { useCreateTenant, useUpdateTenant } from '@/hooks/useTenants';
import { Tenant } from '@/types/tenant';

const tenantSchema = z.object({
  name: z.string().min(1, 'Name is required'),
});

type TenantFormData = z.infer<typeof tenantSchema>;

interface TenantDialogProps {
  open: boolean;
  onClose: () => void;
  tenant?: Tenant | null;
}

export function TenantDialog({ open, onClose, tenant }: TenantDialogProps) {
  const createTenant = useCreateTenant();
  const updateTenant = useUpdateTenant(tenant?.id || '');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema),
  });

  useEffect(() => {
    if (tenant) {
      reset({ name: tenant.name });
    } else {
      reset({ name: '' });
    }
  }, [tenant, reset]);

  const onSubmit = async (data: TenantFormData) => {
    try {
      if (tenant) {
        await updateTenant.mutateAsync(data);
      } else {
        await createTenant.mutateAsync(data);
      }
      onClose();
    } catch (error) {
      console.error('Error saving tenant:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{tenant ? 'Edit Tenant' : 'Create Tenant'}</DialogTitle>
          <DialogDescription>
            {tenant
              ? 'Update the tenant information'
              : 'Create a new tenant to organize your data'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              placeholder="My Organization"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">
              {tenant ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
