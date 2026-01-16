import { useState } from 'react';
import { Plus, Trash2, Edit, Key } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useTenants, useDeleteTenant, useRegenerateTenantKey } from '@/hooks/useTenants';
import { TenantDialog } from './TenantDialog';
import { Tenant } from '@/types/tenant';

export function TenantsList() {
  const { data: tenants, isLoading, error } = useTenants();
  const deleteTenant = useDeleteTenant();
  const regenerateTenantKey = useRegenerateTenantKey();
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this tenant?')) {
      await deleteTenant.mutateAsync(id);
    }
  };

  const handleEdit = (tenant: Tenant) => {
    setEditingTenant(tenant);
    setIsDialogOpen(true);
  };

  const handleCreate = () => {
    setEditingTenant(null);
    setIsDialogOpen(true);
  };

  const handleRegenerateKey = async (tenant: Tenant) => {
    const confirmed = confirm(
      `Regenerate API key for "${tenant.name}"? This will invalidate the old key.`
    );
    if (!confirmed) {
      return;
    }
    try {
      const result = await regenerateTenantKey.mutateAsync(tenant.id);
      window.prompt('New API key (copy and store it now):', result.api_key);
    } catch (err) {
      console.error('Error regenerating API key:', err);
      alert('Failed to regenerate API key.');
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingTenant(null);
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Error loading tenants</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="w-full">
          <h1 className="text-3xl font-bold">Tenants</h1>
          <div className="mt-2 flex w-full flex-wrap items-center gap-3">
            <p className="text-muted-foreground">Manage your tenants and organizations</p>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <Button onClick={handleCreate}>
                <Plus className="h-4 w-4 mr-2" />
                Create Tenant
              </Button>
            </div>
          </div>
        </div>
      </div>

      <Card>
        <CardContent className="px-0">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-muted-foreground">Loading tenants...</p>
            </div>
          ) : tenants && tenants.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>ID</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell className="font-medium">{tenant.name}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {tenant.id}
                    </TableCell>
                    <TableCell>
                      {tenant.created_at
                        ? new Date(tenant.created_at).toLocaleDateString()
                        : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRegenerateKey(tenant)}
                          aria-label="Regenerate API key"
                          title="Regenerate API key"
                        >
                          <Key className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(tenant)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(tenant.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No tenants found</p>
              <Button onClick={handleCreate} className="mt-4" variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Create your first tenant
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <TenantDialog
        open={isDialogOpen}
        onClose={handleCloseDialog}
        tenant={editingTenant}
      />
    </div>
  );
}
