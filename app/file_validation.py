# app/file_validation.py
"""
Advanced file validation utilities for secure file uploads.
Validates MIME types, file sizes, and provides security checks.
"""

import os
from werkzeug.datastructures import FileStorage
from flask import current_app

# Try to import python-magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError) as e:
    MAGIC_AVAILABLE = False
    print(f"⚠️  WARNING: python-magic not available ({e}). MIME type validation will be limited.")
    print("⚠️  Install libmagic for full MIME type detection:")
    print("⚠️  - Windows: pip install python-magic-bin")
    print("⚠️  - Linux: apt-get install libmagic1")
    print("⚠️  - macOS: brew install libmagic")


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


def validate_file_size(file: FileStorage, max_size: int = None) -> bool:
    """
    Validate file size against maximum allowed size.
    
    Args:
        file: Werkzeug FileStorage object
        max_size: Maximum size in bytes (uses MAX_CONTENT_LENGTH from config if not provided)
    
    Returns:
        bool: True if valid
    
    Raises:
        FileValidationError: If file exceeds max size
    """
    if max_size is None:
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    
    # Get file size by seeking to end
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer to beginning
    
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        raise FileValidationError(
            f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB)"
        )
    
    return True


def validate_mime_type(file: FileStorage, allowed_mime_types: set = None) -> str:
    """
    Validate actual MIME type of file content (not just extension).
    Falls back to extension-based validation if python-magic is not available.
    
    Args:
        file: Werkzeug FileStorage object
        allowed_mime_types: Set of allowed MIME types (uses ALLOWED_MIME_TYPES from config if not provided)
    
    Returns:
        str: Detected MIME type (or 'unknown/extension-based' if magic not available)
    
    Raises:
        FileValidationError: If MIME type is not allowed
    """
    if allowed_mime_types is None:
        allowed_mime_types = current_app.config.get('ALLOWED_MIME_TYPES', set())
    
    try:
        # If python-magic is not available, fall back to extension-based validation
        if not MAGIC_AVAILABLE:
            current_app.logger.warning(
                "python-magic not available, using extension-based validation (less secure)"
            )
            # Simple extension to MIME type mapping
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            mime_map = {
                'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'gif': 'image/gif', 'webp': 'image/webp', 'pdf': 'application/pdf',
                'txt': 'text/plain', 'py': 'text/x-python', 'js': 'text/javascript',
                'html': 'text/html', 'css': 'text/css', 'json': 'application/json',
                'xml': 'application/xml', 'md': 'text/markdown',
                'zip': 'application/zip', 'tar': 'application/x-tar', 'gz': 'application/gzip'
            }
            detected_mime = mime_map.get(ext, 'application/octet-stream')
            
            # Check if guessed MIME type is allowed
            if detected_mime not in allowed_mime_types and 'application/octet-stream' not in allowed_mime_types:
                raise FileValidationError(
                    f"File type '{detected_mime}' (based on extension) is not allowed. Allowed types: {', '.join(sorted(allowed_mime_types))}"
                )
            return detected_mime
        
        # Read first 2048 bytes for MIME detection (enough for most file types)
        file_header = file.read(2048)
        file.seek(0)  # Reset file pointer
        
        # Detect MIME type using python-magic
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file_header)
        
        # Check if detected MIME type is allowed
        if detected_mime not in allowed_mime_types:
            raise FileValidationError(
                f"File type '{detected_mime}' is not allowed. Allowed types: {', '.join(sorted(allowed_mime_types))}"
            )
        
        return detected_mime
        
    except Exception as e:
        if isinstance(e, FileValidationError):
            raise
        raise FileValidationError(f"Error detecting file MIME type: {str(e)}")


def validate_filename(filename: str) -> bool:
    """
    Validate filename for security issues.
    
    Args:
        filename: Original filename
    
    Returns:
        bool: True if valid
    
    Raises:
        FileValidationError: If filename contains suspicious patterns
    """
    if not filename:
        raise FileValidationError("Filename cannot be empty")
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise FileValidationError("Filename contains invalid characters (path traversal attempt)")
    
    # Check for null bytes
    if '\x00' in filename:
        raise FileValidationError("Filename contains null bytes")
    
    # Check for extension
    if '.' not in filename:
        raise FileValidationError("Filename must have an extension")
    
    return True


def validate_file_upload(file: FileStorage, check_mime: bool = True, check_size: bool = True) -> dict:
    """
    Comprehensive file validation with multiple security checks.
    
    Args:
        file: Werkzeug FileStorage object
        check_mime: Whether to validate MIME type
        check_size: Whether to validate file size
    
    Returns:
        dict: Validation results with 'valid', 'mime_type', 'size', 'errors' keys
    
    Example:
        result = validate_file_upload(file)
        if result['valid']:
            # Process file
            pass
        else:
            # Handle errors
            return jsonify({'error': result['errors']}), 400
    """
    result = {
        'valid': False,
        'mime_type': None,
        'size': 0,
        'errors': []
    }
    
    try:
        # Validate filename
        validate_filename(file.filename)
        
        # Validate file size
        if check_size:
            validate_file_size(file)
        
        # Get file size
        file.seek(0, os.SEEK_END)
        result['size'] = file.tell()
        file.seek(0)
        
        # Validate MIME type
        if check_mime:
            result['mime_type'] = validate_mime_type(file)
        
        result['valid'] = True
        return result
        
    except FileValidationError as e:
        result['errors'].append(str(e))
        return result
    except Exception as e:
        result['errors'].append(f"Unexpected error during file validation: {str(e)}")
        return result


def get_safe_filename(filename: str) -> str:
    """
    Generate a safe filename by removing dangerous characters.
    
    Args:
        filename: Original filename
    
    Returns:
        str: Sanitized filename
    """
    from werkzeug.utils import secure_filename
    import uuid
    
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)
    
    if not safe_name:
        # If secure_filename returns empty string, generate random name
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
        safe_name = f"{uuid.uuid4().hex}.{ext}"
    
    return safe_name


# Antivirus scanning hook (to be implemented with ClamAV or similar)
def scan_file_for_malware(file_path: str) -> bool:
    """
    Placeholder for antivirus scanning.
    Integrate with ClamAV, VirusTotal API, or similar service.
    
    Args:
        file_path: Path to file to scan
    
    Returns:
        bool: True if file is clean, False if malware detected
    
    TODO: Implement actual antivirus scanning
    Examples:
        - ClamAV: pyclamd library
        - VirusTotal: virustotal-python library
        - AWS S3 + Antivirus: bucket-antivirus-function
    """
    current_app.logger.warning(
        f"Antivirus scanning not implemented! File {file_path} was not scanned for malware."
    )
    # For now, always return True (no scan performed)
    # In production, integrate with actual antivirus service
    return True
