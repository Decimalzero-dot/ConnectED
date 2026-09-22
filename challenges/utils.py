import os
import magic  # python-magic for MIME type detection
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.png', '.jpg', '.jpeg',
    '.ipynb', '.csv', '.pkt', '.zip'
}

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
    'application/json',         # .ipynb
    'text/csv',
    'application/zip',
    'application/x-zip-compressed',
    'application/octet-stream', # .pkt
    'text/plain',               # some CSV exports
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def validate_submission_file(file):
    """
    Validate uploaded file:
    - Extension must be in allowed list
    - MIME type must match
    - Size must be under 10MB
    """
    errors = []

    # Check size
    if file.size > MAX_UPLOAD_SIZE:
        errors.append(
            f"File too large ({file.size // (1024*1024)}MB). Maximum is 10MB."
        )

    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(
            f"File type '{ext}' is not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Check MIME type
    try:
        file.seek(0)
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        if mime not in ALLOWED_MIME_TYPES:
            errors.append(
                f"File content type '{mime}' is not allowed."
            )
    except Exception:
        pass  # If magic fails, extension check is still enforced

    if errors:
        raise ValidationError(errors)

    return file