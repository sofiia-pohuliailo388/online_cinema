"""File storage (owner: P3): S3-compatible object storage (Silo / MinIO), e.g. user avatars.

Public contract: ``upload_file``, ``delete_file``, ``get_file_url`` in ``src.storage.s3``.
Only object keys are stored in the database; links are generated on demand.
"""
