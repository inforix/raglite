import { useState } from 'react';
import { Trash2, Upload, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useDocuments, useDeleteDocument, useUploadDocument } from '@/hooks/useDocuments';
import { useDatasets } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

export function DocumentsList() {
  const [selectedTenantId, setSelectedTenantId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);
  
  const { data: tenants } = useTenants();
  const { data: datasets } = useDatasets(selectedTenantId || undefined);
  const { data: documents, isLoading } = useDocuments(selectedDatasetId || undefined);
  const deleteDocument = useDeleteDocument();
  const uploadDocument = useUploadDocument();

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this document?')) {
      await deleteDocument.mutateAsync(id);
    }
  };

  const handleUpload = async () => {
    if (!uploadFiles || !selectedDatasetId) return;

    for (let i = 0; i < uploadFiles.length; i++) {
      try {
        await uploadDocument.mutateAsync({
          datasetId: selectedDatasetId,
          file: uploadFiles[i],
        });
      } catch (error) {
        console.error(`Error uploading ${uploadFiles[i].name}:`, error);
      }
    }
    setUploadFiles(null);
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '-';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Documents</h1>
          <p className="text-muted-foreground mt-2">
            Upload and manage your documents
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Dataset</CardTitle>
        </CardHeader>
        <CardContent>
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
                <option value="">Select tenant</option>
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
        </CardContent>
      </Card>

      {selectedDatasetId && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border-2 border-dashed rounded-lg p-8 text-center">
                <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <Input
                  type="file"
                  multiple
                  onChange={(e) => setUploadFiles(e.target.files)}
                  className="max-w-md mx-auto"
                />
                <p className="text-sm text-muted-foreground mt-2">
                  Supports PDF, TXT, DOCX, and more
                </p>
              </div>
              
              {uploadFiles && uploadFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">
                    {uploadFiles.length} file(s) selected
                  </p>
                  <Button onClick={handleUpload} disabled={uploadDocument.isPending}>
                    <Upload className="h-4 w-4 mr-2" />
                    {uploadDocument.isPending ? 'Uploading...' : 'Upload'}
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {!selectedDatasetId ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                Select a dataset to view documents
              </p>
            </div>
          ) : isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-muted-foreground">Loading documents...</p>
            </div>
          ) : documents && documents.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">{doc.title}</TableCell>
                    <TableCell className="uppercase text-sm">
                      {doc.file_type || '-'}
                    </TableCell>
                    <TableCell>{formatFileSize(doc.file_size)}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs ${
                          doc.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : doc.status === 'processing'
                            ? 'bg-blue-100 text-blue-800'
                            : doc.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {doc.status || 'pending'}
                      </span>
                    </TableCell>
                    <TableCell>
                      {doc.created_at
                        ? new Date(doc.created_at).toLocaleDateString()
                        : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(doc.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No documents found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Upload documents to get started
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
