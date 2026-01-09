from workers.worker import task


@task()
def ingest_document(*args, **kwargs):
    raise NotImplementedError("Ingestion task is not implemented yet.")


@task()
def reindex_dataset(*args, **kwargs):
    raise NotImplementedError("Reindex task is not implemented yet.")

