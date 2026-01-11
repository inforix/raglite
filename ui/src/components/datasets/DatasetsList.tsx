import { useState } from 'react';
import { Plus, Trash2, Edit, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useDatasets, useDeleteDataset } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { DatasetDialog } from './DatasetDialog';
import { Dataset } from '@/types/dataset';
import { Label } from '@/components/ui/label';

export function DatasetsList() {
  const [selectedTenantId, setSelectedTenantId] = useState<string>('');
  const { data: tenants } = useTenants();
  const { data: datasets, isLoading, error, refetch } = useDatasets(selectedTenantId || undefined);
  const deleteDataset = useDeleteDataset();
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this dataset?')) {
      await deleteDataset.mutateAsync(id);
    }
  };

  const handleEdit = (dataset: Dataset) => {
    setEditingDataset(dataset);
    setIsDialogOpen(true);
  };

  const handleCreate = () => {
    setEditingDataset(null);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingDataset(null);
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Error loading datasets</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Datasets</h1>
          <p className="text-muted-foreground mt-2">
            Manage your datasets and collections
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Create Dataset
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filter by Tenant</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Label htmlFor="tenant-select">Select Tenant</Label>
              <select
                id="tenant-select"
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={selectedTenantId}
                onChange={(e) => setSelectedTenantId(e.target.value)}
              >
                <option value="">All Tenants</option>
                {tenants?.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>All Datasets</CardTitle>
          <Button variant="ghost" size="icon" onClick={() => refetch?.()}>
            <RotateCw className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-muted-foreground">Loading datasets...</p>
            </div>
          ) : datasets && datasets.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Tenant ID</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {datasets.map((dataset) => (
                  <TableRow key={dataset.id}>
                    <TableCell className="font-medium">{dataset.name}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {dataset.tenant_id?.substring(0, 8)}...
                    </TableCell>
                    <TableCell>{dataset.language || 'en'}</TableCell>
                    <TableCell>
                      {dataset.created_at
                        ? new Date(dataset.created_at).toLocaleDateString()
                        : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(dataset)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(dataset.id)}
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
              <p className="text-muted-foreground">No datasets found</p>
              <Button onClick={handleCreate} className="mt-4" variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Create your first dataset
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <DatasetDialog
        open={isDialogOpen}
        onClose={handleCloseDialog}
        dataset={editingDataset}
      />
    </div>
  );
}
