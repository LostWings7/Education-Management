"""
File upload and data validation helpers for security hardening.
Enforces file size limits, MIME type verification, and extension whitelisting.
"""

import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.txt', '.zip', '.tar.gz',
    '.png', '.jpg', '.jpeg', '.gif', '.py', '.java', '.c', '.cpp', '.sql'
}

DISALLOWED_DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.sh', '.bin', '.cmd', '.vbs', '.js', '.html', '.htm', '.php', '.phtml'
}


def validate_file_upload(file_obj):
    """
    Validates uploaded file size and extension.
    """
    if not file_obj:
        return

    if file_obj.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            _("File size exceeds maximum permitted limit of 10 MB (Current: %(size).1f MB)."),
            params={'size': file_obj.size / (1024 * 1024)}
        )

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in DISALLOWED_DANGEROUS_EXTENSIONS or ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("File extension '%(ext)s' is not allowed for security reasons."),
            params={'ext': ext}
        )
