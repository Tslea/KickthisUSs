"""
Test script per validare il supporto multi-contenuto

Testa la validazione, categorizzazione e organizzazione dei file
per tutti i tipi di contenuto supportati.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'config'))

# Import diretto dal file
import importlib.util
spec = importlib.util.spec_from_file_location("github_config", 
    os.path.join(project_root, "config", "github_config.py"))
github_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(github_config)

# Aliases per funzioni
get_content_type_from_extension = github_config.get_content_type_from_extension
is_file_allowed_for_project = github_config.is_file_allowed_for_project
SUPPORTED_FILE_FORMATS = github_config.SUPPORTED_FILE_FORMATS
FILE_SIZE_LIMITS = github_config.FILE_SIZE_LIMITS
PROJECT_STRUCTURE = github_config.PROJECT_STRUCTURE


def test_content_type_detection():
    """Test rilevamento automatico tipo contenuto"""
    print("Testing Content Type Detection...\n")
    
    test_cases = [
        # Software
        ('.py', 'software'),
        ('.js', 'software'),
        ('.tsx', 'software'),
        
        # Hardware
        ('.stl', 'hardware'),
        ('.kicad_pcb', 'hardware'),
        ('.step', 'hardware'),
        
        # Design
        ('.psd', 'design'),
        ('.fig', 'design'),
        ('.ai', 'design'),
        ('.svg', 'design'),
        
        # Documentation
        ('.pdf', 'documentation'),
        ('.docx', 'documentation'),
        ('.md', 'documentation'),
        
        # Media
        ('.mp4', 'media'),
        ('.mp3', 'media'),
        ('.gif', 'media'),
    ]
    
    for extension, expected_type in test_cases:
        detected = get_content_type_from_extension(extension)
        status = '✅' if detected == expected_type else '❌'
        print(f"{status} {extension:15} -> {detected:15} (expected: {expected_type})")
    
    print()


def test_project_compatibility():
    """Test compatibilità file con tipo progetto"""
    print("🔍 Testing Project Compatibility...\n")
    
    test_cases = [
        # Software project
        ('software', '.py', True),
        ('software', '.psd', False),  # Design file in software project
        ('software', '.md', True),    # Docs always allowed
        
        # Design project
        ('design', '.psd', True),
        ('design', '.py', False),
        ('design', '.pdf', True),     # Docs allowed
        
        # Mixed project
        ('mixed', '.py', True),
        ('mixed', '.psd', True),
        ('mixed', '.mp4', True),      # Everything allowed
    ]
    
    for project_type, extension, expected in test_cases:
        allowed = is_file_allowed_for_project(extension, project_type)
        status = '✅' if allowed == expected else '❌'
        result = 'ALLOWED' if allowed else 'BLOCKED'
        print(f"{status} {project_type:12} + {extension:10} -> {result:10} (expected: {'ALLOWED' if expected else 'BLOCKED'})")
    
    print()


def test_file_organization():
    """Test organizzazione file nelle directory"""
    print("📁 Testing File Organization...\n")
    
    from services.github_service import GitHubService
    
    service = GitHubService()
    
    # Test Design files
    design_files = [
        {'name': 'logo.svg', 'content': 'svg content'},
        {'name': 'mockup.fig', 'content': 'figma content'},
        {'name': 'icon.psd', 'content': 'psd content'},
        {'name': 'export.png', 'content': 'png content'}
    ]
    
    organized = service.organize_files_by_content_type(design_files, 'design')
    
    print("Design files organized:")
    for directory, files in organized.items():
        print(f"  📂 {directory}/")
        for file in files:
            print(f"    📄 {file['name']}")
    print()
    
    # Test Media files
    media_files = [
        {'name': 'promo.mp4', 'content': 'video'},
        {'name': 'podcast.mp3', 'content': 'audio'},
        {'name': 'animation.gif', 'content': 'gif'},
        {'name': 'photo.jpg', 'content': 'image'}
    ]
    
    organized = service.organize_files_by_content_type(media_files, 'media')
    
    print("Media files organized:")
    for directory, files in organized.items():
        print(f"  📂 {directory}/")
        for file in files:
            print(f"    📄 {file['name']}")
    print()


def test_file_validation():
    """Test validazione upload file"""
    print("✔️ Testing File Validation...\n")
    
    from services.github_service import GitHubService
    
    service = GitHubService()
    
    test_files = [
        # Valid files
        {'name': 'script.py', 'size': 5 * 1024 * 1024, 'content_type': 'software'},  # 5MB
        {'name': 'logo.psd', 'size': 50 * 1024 * 1024, 'content_type': 'design'},    # 50MB
        {'name': 'video.mp4', 'size': 200 * 1024 * 1024, 'content_type': 'media'},   # 200MB
        
        # Invalid files (too large)
        {'name': 'huge.py', 'size': 20 * 1024 * 1024, 'content_type': 'software'},   # 20MB > 10MB limit
        {'name': 'massive.psd', 'size': 150 * 1024 * 1024, 'content_type': 'design'}, # 150MB > 100MB limit
    ]
    
    for file_data in test_files:
        validation = service.validate_file_upload(file_data, file_data['content_type'])
        
        status = '✅' if validation['valid'] else '❌'
        size_mb = validation['size_mb']
        
        print(f"{status} {file_data['name']:20} ({size_mb:.1f}MB)")
        if not validation['valid']:
            print(f"   ⚠️  {validation['error']}")
    
    print()


def test_file_preview_info():
    """Test informazioni preview file"""
    print("👁️ Testing File Preview Info...\n")
    
    from services.github_service import GitHubService
    
    service = GitHubService()
    
    test_files = [
        {'name': 'image.png'},
        {'name': 'video.mp4'},
        {'name': 'audio.mp3'},
        {'name': 'document.pdf'},
        {'name': 'code.py'},
        {'name': 'model.stl'},
        {'name': 'design.psd'},
    ]
    
    for file_data in test_files:
        info = service.get_file_preview_info(file_data)
        
        previewable = '👁️' if info['previewable'] else '📥'
        print(f"{info['icon']} {info['filename']:20} {previewable} {info['preview_type']:10} [{info['content_type']}]")
    
    print()


def show_supported_formats():
    """Mostra tutti i formati supportati"""
    print("📋 Supported File Formats\n")
    
    for content_type, formats in SUPPORTED_FILE_FORMATS.items():
        print(f"\n{content_type.upper()}")
        print("=" * 50)
        
        if isinstance(formats, list):
            print(f"  Formats: {', '.join(formats[:10])}")
            if len(formats) > 10:
                print(f"  ... and {len(formats) - 10} more")
        elif isinstance(formats, dict):
            for category, exts in formats.items():
                print(f"  {category:15} -> {', '.join(exts[:5])}")
                if len(exts) > 5:
                    print(f"  {' ' * 15}    ... and {len(exts) - 5} more")
    
    print("\n" + "=" * 50)
    print("\nFile Size Limits:")
    for content_type, limit_mb in FILE_SIZE_LIMITS.items():
        print(f"  {content_type:15} -> {limit_mb} MB")
    
    print()


def show_directory_structures():
    """Mostra strutture directory per tipo progetto"""
    print("📁 Project Directory Structures\n")
    
    for project_type, structure in PROJECT_STRUCTURE.items():
        print(f"\n{project_type.upper()}")
        print("=" * 50)
        print(f"project-{project_type}/")
        for folder, description in structure.items():
            print(f"├── {folder}/")
            print(f"│   └── {description}")
    
    print()


if __name__ == '__main__':
    # Fix encoding for Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    print("=" * 60)
    print("TEST: CONTENT TYPES VALIDATION TEST SUITE")
    print("=" * 60)
    print()
    
    # Run all tests
    test_content_type_detection()
    test_project_compatibility()
    test_file_organization()
    test_file_validation()
    test_file_preview_info()
    
    print("\n" + "=" * 60)
    print("📊 REFERENCE INFORMATION")
    print("=" * 60)
    print()
    
    show_supported_formats()
    show_directory_structures()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
