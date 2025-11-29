"""
Test Script per ZIP Upload Feature
Verifica che i componenti base funzionino correttamente
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.zip_processor import ZipProcessor, validate_zip_structure
from app.storage_helper import StorageHelper
import tempfile
import zipfile


def test_zip_processor():
    """Test ZipProcessor base functionality"""
    print("🧪 Testing ZipProcessor...")
    
    # Crea un ZIP temporaneo per testing
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
        zip_path = temp_zip.name
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # Aggiungi file di test
            zf.writestr('test.py', 'print("Hello World")')
            zf.writestr('README.md', '# Test Project\n\nThis is a test.')
            zf.writestr('requirements.txt', 'flask\nrequests\n')
            zf.writestr('src/main.py', 'def main():\n    pass')
        
        print(f"✅ Created test ZIP: {zip_path}")
        
        # Test estrazione
        processor = ZipProcessor()
        
        try:
            # Simula FileStorage
            class FakeFileStorage:
                def __init__(self, path):
                    self.filename = os.path.basename(path)
                    self.stream = open(path, 'rb')
                
                def seek(self, *args):
                    return self.stream.seek(*args)
                
                def tell(self):
                    return self.stream.tell()
                
                def close(self):
                    self.stream.close()
            
            fake_file = FakeFileStorage(zip_path)
            
            # Estrai
            files = processor.extract_zip(fake_file)
            print(f"✅ Extracted {len(files)} files")
            
            # Valida
            is_valid, error = validate_zip_structure(files)
            if is_valid:
                print("✅ ZIP structure valid")
            else:
                print(f"❌ ZIP validation failed: {error}")
            
            # Rileva tipo progetto
            project_type = processor.detect_project_type(files)
            print(f"✅ Detected project type: {project_type}")
            
            # Calcola stats
            stats = processor.calculate_diff_stats(files, base_files=None)
            print(f"✅ Diff stats: {stats}")
            
            # Cleanup
            fake_file.close()
            processor.cleanup()
            print("✅ ZipProcessor test PASSED")
            
        except Exception as e:
            print(f"❌ ZipProcessor test FAILED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup temp file
            if os.path.exists(zip_path):
                os.remove(zip_path)


def test_storage_helper():
    """Test StorageHelper base functionality"""
    print("\n🧪 Testing StorageHelper...")
    
    try:
        helper = StorageHelper()
        print(f"✅ StorageHelper initialized")
        print(f"   Upload folder: {helper.upload_folder}")
        print(f"   Local max size: {helper.LOCAL_MAX_SIZE / 1024 / 1024:.1f}MB")
        print(f"   Global max size: {helper.GLOBAL_MAX_SIZE / 1024 / 1024:.1f}MB")
        
        print("✅ StorageHelper test PASSED")
        
    except Exception as e:
        print(f"❌ StorageHelper test FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_imports():
    """Test che tutti gli import funzionino"""
    print("\n🧪 Testing imports...")
    
    try:
        from app.services.zip_processor import ZipProcessor, ZipProcessorError
        print("✅ ZipProcessor imports OK")
        
        from app.storage_helper import StorageHelper, save_file
        print("✅ StorageHelper imports OK")
        
        from app.services.github_service import GitHubService
        print("✅ GitHubService imports OK")
        
        from app.models import Solution, SolutionFile
        print("✅ Model imports OK")
        
        from app.forms import SolutionForm
        print("✅ Form imports OK")
        
        print("✅ All imports test PASSED")
        
    except Exception as e:
        print(f"❌ Imports test FAILED: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 ZIP UPLOAD FEATURE - Component Testing")
    print("=" * 60)
    
    test_imports()
    test_zip_processor()
    test_storage_helper()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    main()
