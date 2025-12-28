# 📋 Quick Reference: Content Types API

## Import

```python
from config import github_config
from services.github_service import GitHubService

# Or use loader
from utils.github_config_loader import (
    get_content_type_from_extension,
    is_file_allowed_for_project,
    SUPPORTED_FILE_FORMATS,
    FILE_SIZE_LIMITS
)
```

---

## Detect Content Type

```python
# From file extension
content_type = github_config.get_content_type_from_extension('.psd')
# Returns: 'design'

content_type = github_config.get_content_type_from_extension('.mp4')
# Returns: 'media'

content_type = github_config.get_content_type_from_extension('.py')
# Returns: 'software'
```

---

## Validate File

```python
service = GitHubService()

file_data = {
    'name': 'logo.psd',
    'size': 50 * 1024 * 1024  # 50MB
}

validation = service.validate_file_upload(file_data, 'design')

if validation['valid']:
    print(f"✅ File OK ({validation['size_mb']:.1f}MB)")
else:
    print(f"❌ Error: {validation['error']}")
```

---

## Organize Files

```python
service = GitHubService()

files = [
    {'name': 'logo.svg', 'content': '...'},
    {'name': 'mockup.fig', 'content': '...'},
    {'name': 'icon.psd', 'content': '...'}
]

organized = service.organize_files_by_content_type(files, 'design')

# Returns:
# {
#   'logos/': [{'name': 'logo.svg', ...}],
#   'mockups/': [{'name': 'mockup.fig', ...}],
#   'assets/': [{'name': 'icon.psd', ...}]
# }
```

---

## Get Preview Info

```python
service = GitHubService()

file_data = {'name': 'video.mp4'}
info = service.get_file_preview_info(file_data)

# Returns:
# {
#   'filename': 'video.mp4',
#   'extension': 'mp4',
#   'content_type': 'media',
#   'icon': '🎥',
#   'previewable': True,
#   'preview_type': 'video'
# }
```

---

## Check Project Compatibility

```python
# Check if file is allowed in project type
allowed = github_config.is_file_allowed_for_project('.psd', 'software')
# Returns: False (design file not allowed in software project)

allowed = github_config.is_file_allowed_for_project('.psd', 'design')
# Returns: True

allowed = github_config.is_file_allowed_for_project('.py', 'mixed')
# Returns: True (mixed projects accept everything)
```

---

## Constants

### Content Types
```python
from app.models import CONTENT_TYPES

CONTENT_TYPES = {
    'software': '💻 Software/Codice',
    'hardware': '🔧 Hardware/Elettronica',
    'design': '🎨 Design Grafico',
    'documentation': '📄 Documentazione',
    'media': '🎬 Media/Audio/Video',
    'mixed': '🔀 Misto'
}
```

### Size Limits
```python
from utils.github_config_loader import FILE_SIZE_LIMITS

FILE_SIZE_LIMITS = {
    'software': 10,      # 10 MB
    'hardware': 50,      # 50 MB
    'design': 100,       # 100 MB
    'documentation': 20, # 20 MB
    'media': 500,        # 500 MB
    'default': 50
}
```

---

## Database Models

### Solution
```python
from app.models import Solution

solution = Solution(
    task_id=123,
    submitted_by_user_id=1,
    solution_content="Description",
    content_type='design',  # ⭐ NEW
    is_approved=False
)
```

### SolutionFile
```python
from app.models import SolutionFile

file = SolutionFile(
    solution_id=456,
    original_filename='logo.psd',
    stored_filename='uuid-logo.psd',
    file_path='/uploads/uuid-logo.psd',
    file_type='visual',
    content_type='design',      # ⭐ NEW
    content_category='logo',    # ⭐ NEW
    file_size=52428800,
    mime_type='image/vnd.adobe.photoshop'
)
```

---

## Migration

### Run Migration
```bash
python migrations/add_content_type_fields.py
```

### Rollback
```bash
python migrations/add_content_type_fields.py downgrade
```

---

## Testing

### Run All Tests
```bash
python test_content_types.py
```

### Specific Test
```python
from test_content_types import test_content_type_detection

test_content_type_detection()
```

---

## Common Patterns

### Upload Handler
```python
def handle_file_upload(file, project_type):
    # Get extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Detect content type
    content_type = get_content_type_from_extension(ext)
    
    # Validate
    file_data = {
        'name': filename,
        'size': len(file.read())
    }
    file.seek(0)  # Reset after read
    
    service = GitHubService()
    validation = service.validate_file_upload(file_data, content_type)
    
    if not validation['valid']:
        return {'error': validation['error']}, 400
    
    # Check project compatibility
    if not is_file_allowed_for_project(ext, project_type):
        return {'error': f'File type {ext} not allowed for {project_type} projects'}, 400
    
    # Proceed with upload...
    return {'success': True}
```

### Solution Creation with Content Type
```python
def create_solution_with_files(task_id, user_id, files):
    # Detect content type from first file
    first_file = files[0]
    ext = os.path.splitext(first_file.filename)[1]
    content_type = get_content_type_from_extension(ext)
    
    # Create solution
    solution = Solution(
        task_id=task_id,
        submitted_by_user_id=user_id,
        solution_content="Multi-file solution",
        content_type=content_type
    )
    db.session.add(solution)
    db.session.flush()
    
    # Add files
    for file in files:
        ext = os.path.splitext(file.filename)[1]
        file_content_type = get_content_type_from_extension(ext)
        
        solution_file = SolutionFile(
            solution_id=solution.id,
            original_filename=file.filename,
            stored_filename=f"{uuid4()}-{file.filename}",
            file_path=save_file(file),
            file_type='source',
            content_type=file_content_type,
            file_size=len(file.read()),
            mime_type=file.content_type
        )
        db.session.add(solution_file)
    
    db.session.commit()
    return solution
```

### GitHub Sync with Content Type
```python
def sync_solution_to_github(solution_id):
    solution = Solution.query.get(solution_id)
    files = solution.files.all()
    
    service = GitHubService()
    
    # Organize files by content type
    file_data = [{'name': f.original_filename, 'content': read_file(f.file_path)} 
                 for f in files]
    
    organized = service.organize_files_by_content_type(
        file_data, 
        solution.content_type
    )
    
    # Upload to GitHub in organized structure
    for directory, dir_files in organized.items():
        for file in dir_files:
            service.upload_solution_files(
                repo_name=f"project-{solution.task.project_id}",
                branch=f"solution-{solution.id}",
                files=[{'name': file['name'], 'path': f"{directory}/{file['name']}", 'content': file['content']}]
            )
```

---

## Error Handling

```python
try:
    content_type = get_content_type_from_extension(ext)
    
    if content_type == 'mixed':
        # Unsupported file type
        raise ValueError(f"File type {ext} is not supported")
    
    validation = service.validate_file_upload(file_data, content_type)
    
    if not validation['valid']:
        # Validation failed
        raise ValueError(validation['error'])
    
except ValueError as e:
    logger.error(f"File validation error: {e}")
    return {'error': str(e)}, 400

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {'error': 'Internal server error'}, 500
```

---

## Frontend Integration

### Form Selection
```html
<select name="content_type" required>
    <option value="software">💻 Software/Codice</option>
    <option value="hardware">🔧 Hardware</option>
    <option value="design">🎨 Design Grafico</option>
    <option value="documentation">📄 Documentazione</option>
    <option value="media">🎬 Media</option>
    <option value="mixed">🔀 Misto</option>
</select>
```

### Client-side Validation
```javascript
const FILE_SIZE_LIMITS = {
    software: 10 * 1024 * 1024,      // 10 MB
    hardware: 50 * 1024 * 1024,      // 50 MB
    design: 100 * 1024 * 1024,       // 100 MB
    documentation: 20 * 1024 * 1024, // 20 MB
    media: 500 * 1024 * 1024,        // 500 MB
};

function validateFile(file, contentType) {
    const limit = FILE_SIZE_LIMITS[contentType] || FILE_SIZE_LIMITS.software;
    
    if (file.size > limit) {
        alert(`File too large! Max size: ${limit / (1024*1024)}MB`);
        return false;
    }
    
    return true;
}
```

---

## Useful Queries

### Get all solutions by content type
```python
design_solutions = Solution.query.filter_by(content_type='design').all()
```

### Get files by category
```python
logos = SolutionFile.query.filter_by(content_category='logo').all()
```

### Count by type
```python
from sqlalchemy import func

counts = db.session.query(
    Solution.content_type,
    func.count(Solution.id)
).group_by(Solution.content_type).all()
```

---

*Quick Reference v2.0*
*Last Updated: December 2024*
