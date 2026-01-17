import { useCallback, useState } from 'react';
import type { DragEvent } from 'react';
import { Trash2, Upload, FileText, RefreshCw, Pencil, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useDocuments, useDeleteDocument, useUpdateDocument, useUploadDocument } from '@/hooks/useDocuments';
import { useDatasets } from '@/hooks/useDatasets';
import { useTenants } from '@/hooks/useTenants';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import type { Document } from '@/types/document';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export function DocumentsList() {
  const [selectedTenantId, setSelectedTenantId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isRenameOpen, setIsRenameOpen] = useState(false);
  const [renameDocument, setRenameDocument] = useState<Document | null>(null);
  const [renameFilename, setRenameFilename] = useState('');
  
  const { data: tenants } = useTenants();
  const { data: datasets } = useDatasets(selectedTenantId || undefined);
  const { data: documents, isLoading, isFetching, refetch } = useDocuments(selectedDatasetId || undefined);
  const deleteDocument = useDeleteDocument();
  const uploadDocument = useUploadDocument();
  const updateDocument = useUpdateDocument();

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
    setIsUploadOpen(false);
  };

  const handleRenameStart = (doc: Document) => {
    setRenameDocument(doc);
    setRenameFilename(doc.filename || '');
    setIsRenameOpen(true);
  };

  const handleRename = async () => {
    if (!renameDocument) return;
    const trimmed = renameFilename.trim();
    if (!trimmed) return;
    await updateDocument.mutateAsync({
      id: renameDocument.id,
      filename: trimmed,
      datasetId: renameDocument.dataset_id,
    });
    setIsRenameOpen(false);
    setRenameDocument(null);
    setRenameFilename('');
  };

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      setUploadFiles(event.dataTransfer.files);
    }
  }, []);

  const extractFilename = (disposition?: string) => {
    if (!disposition) return undefined;
    const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utfMatch?.[1]) {
      try {
        return decodeURIComponent(utfMatch[1]);
      } catch {
        return utfMatch[1];
      }
    }
    const asciiMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
    return asciiMatch?.[1];
  };

  const handleDownload = async (doc: Document) => {
    try {
      const response = await api.get(API_ENDPOINTS.DOCUMENT_DOWNLOAD(doc.id), {
        params: { dataset_id: doc.dataset_id },
        responseType: 'blob',
      });
      const disposition = response.headers['content-disposition'] as string | undefined;
      const filename = extractFilename(disposition) || doc.filename || `document-${doc.id}`;
      const blobUrl = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('Failed to download document:', error);
      alert('Failed to download document.');
    }
  };

  const formatFileSize = (bytes?: number | null) => {
    if (!bytes) return '-';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="w-full">
          <h1 className="text-3xl font-bold">Documents</h1>
          <div className="mt-2 flex w-full flex-wrap items-center gap-3">
            <p className="text-muted-foreground">Upload and manage your documents</p>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground">Tenant</Label>
                <select
                  className="h-9 w-44 rounded-md border border-input bg-background px-3 text-sm"
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

              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground">Dataset</Label>
                <select
                  className="h-9 w-48 rounded-md border border-input bg-background px-3 text-sm"
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

              <Button
                variant="outline"
                size="icon"
                onClick={() => refetch()}
                disabled={!selectedDatasetId || isLoading || isFetching}
                title="Refresh"
              >
                <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                onClick={() => setIsUploadOpen(true)}
                disabled={!selectedDatasetId}
                variant="outline"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload
              </Button>
            </div>
          </div>
        </div>
      </div>

      <Card>
        
        <CardContent className="px-0">
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
                  <TableHead>Filename</TableHead>
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
                    <TableCell className="font-medium">{doc.filename || doc.id}</TableCell>
                    <TableCell className="uppercase text-sm">
                      {doc.mime_type || '-'}
                    </TableCell>
                    <TableCell>{formatFileSize(doc.size_bytes)}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs ${
                          doc.status === 'completed' || doc.status === 'succeeded' || doc.status === 'success'
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
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDownload(doc)}
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRenameStart(doc)}
                          title="Rename"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(doc.id)}
                          title="Delete"
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
              <p className="text-muted-foreground">No documents found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Upload documents to get started
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload documents</DialogTitle>
            <DialogDescription>
              Choose files or drag and drop them below to upload to the selected dataset.
            </DialogDescription>
          </DialogHeader>
          <div
            className={`border-2 border-dashed rounded-lg p-6 text-center transition ${
              isDragging ? 'border-primary bg-primary/5' : 'border-muted'
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">
              Drag files here or click below to browse
            </p>
            <Input
              type="file"
              multiple
              onChange={(e) => setUploadFiles(e.target.files)}
              className="mt-4 w-full cursor-pointer"
            />
          </div>

          {uploadFiles && uploadFiles.length > 0 && (
            <div className="text-sm text-muted-foreground">
              {uploadFiles.length} file(s) selected
            </div>
          )}

          <DialogFooter className="mt-2">
            <Button
              onClick={handleUpload}
              disabled={!uploadFiles || uploadFiles.length === 0 || uploadDocument.isPending || !selectedDatasetId}
            >
              {uploadDocument.isPending ? 'Uploading...' : 'Start upload'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={isRenameOpen}
        onOpenChange={(open) => {
          setIsRenameOpen(open);
          if (!open) {
            setRenameDocument(null);
            setRenameFilename('');
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename document</DialogTitle>
            <DialogDescription>
              Update the filename for this document.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="rename-filename">Filename</Label>
            <Input
              id="rename-filename"
              value={renameFilename}
              onChange={(e) => setRenameFilename(e.target.value)}
              placeholder="Enter a filename"
            />
          </div>
          <DialogFooter className="mt-2">
            <Button
              onClick={handleRename}
              disabled={
                !renameDocument ||
                updateDocument.isPending ||
                renameFilename.trim().length === 0 ||
                renameFilename.trim() === (renameDocument?.filename || '')
              }
            >
              {updateDocument.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
