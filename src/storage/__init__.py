"""File storage (owner: P3): MinIO / S3 via boto3, e.g. user avatars.

Planned contract: ``upload_file(key: str, data: bytes, content_type: str) -> str`` and
``get_file_url(key: str) -> str`` (presigned URL). Store only the key in the database.
"""
