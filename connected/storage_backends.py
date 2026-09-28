from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class PublicMediaStorage(S3Boto3Storage):
    """For profile images — publicly accessible."""
    bucket_name = settings.PUBLIC_BUCKET_NAME
    default_acl = 'public-read'
    querystring_auth = False  # No signed URLs needed — public
    custom_domain = None      # Use R2 public URL directly


class PrivateMediaStorage(S3Boto3Storage):
    """For submission files — requires authorization."""
    bucket_name = settings.PRIVATE_BUCKET_NAME
    default_acl = 'private'
    querystring_auth = True   # Signed URLs
    querystring_expire = 3600  # 1 hour