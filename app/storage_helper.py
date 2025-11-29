"""
Storage Helper
Gestisce il salvataggio dei file con strategia basata su dimensione.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app
from datetime import datetime


class StorageHelper:
    """Helper per gestire il salvataggio dei file con strategia intelligente"""
    
    # Configurazione
    LOCAL_MAX_SIZE = 10485760  # 10MB
    GLOBAL_MAX_SIZE = 52428800  # 50MB
    
    def __init__(self):
        self.upload_folder = self._get_upload_folder()
        self._ensure_upload_folder_exists()
    
    def _get_upload_folder(self) -> str:
        """Ottieni la cartella di upload configurata"""
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        
        # Se path relativo, rendilo assoluto rispetto a instance_path
        if not os.path.isabs(upload_folder):
            upload_folder = os.path.join(current_app.instance_path, upload_folder)
        
        return upload_folder
    
    def _ensure_upload_folder_exists(self):
        """Crea la cartella di upload se non esiste"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder, exist_ok=True)
            current_app.logger.info(f"Created upload folder: {self.upload_folder}")
    
    def save_file(
        self, 
        file: FileStorage, 
        subfolder: Optional[str] = None,
        custom_filename: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Salva un file con strategia basata su dimensione.
        
        Args:
            file: FileStorage object da Flask
            subfolder: Sottocartella opzionale (es: 'solutions', 'projects')
            custom_filename: Nome file personalizzato (se None, usa timestamp + filename)
        
        Returns:
            Dict {
                'success': bool,
                'path': str,  # Path relativo da instance_path
                'full_path': str,  # Path assoluto
                'size': int,
                'storage_type': str,  # 'local' o 's3'
                'filename': str,
                'error': str  # Solo se success=False
            }
        """
        try:
            # Ottieni dimensione file
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            # Verifica dimensione massima
            if file_size > self.GLOBAL_MAX_SIZE:
                return {
                    'success': False,
                    'error': f"File troppo grande: {file_size / 1024 / 1024:.2f}MB. "
                            f"Massimo consentito: {self.GLOBAL_MAX_SIZE / 1024 / 1024:.0f}MB"
                }
            
            # Genera filename sicuro
            if custom_filename:
                filename = secure_filename(custom_filename)
            else:
                timestamp = int(datetime.now().timestamp())
                original_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{original_filename}"
            
            # Determina path di salvataggio
            if subfolder:
                save_folder = os.path.join(self.upload_folder, subfolder)
                os.makedirs(save_folder, exist_ok=True)
            else:
                save_folder = self.upload_folder
            
            full_path = os.path.join(save_folder, filename)
            
            # Determina strategia di storage
            if file_size <= self.LOCAL_MAX_SIZE:
                # File piccolo - salva su filesystem locale
                storage_type = 'local'
                file.save(full_path)
                current_app.logger.info(f"Saved file to local storage: {filename} ({file_size} bytes)")
            else:
                # File grande (10MB-50MB) - per ora su filesystem, in futuro S3
                storage_type = 'local'  # In futuro: 's3'
                file.save(full_path)
                current_app.logger.warning(
                    f"Saved large file to local storage: {filename} ({file_size / 1024 / 1024:.2f}MB). "
                    "Consider implementing S3 storage for large files."
                )
            
            # Calcola path relativo da instance_path
            try:
                relative_path = os.path.relpath(full_path, current_app.instance_path)
            except ValueError:
                # Se non è possibile calcolare path relativo, usa il path assoluto
                relative_path = full_path
            
            return {
                'success': True,
                'path': relative_path.replace('\\', '/'),  # Unix-style path
                'full_path': full_path,
                'size': file_size,
                'storage_type': storage_type,
                'filename': filename
            }
            
        except Exception as e:
            current_app.logger.error(f"Error saving file: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Errore durante il salvataggio del file: {str(e)}"
            }


def save_file(file: FileStorage, subfolder: Optional[str] = None) -> Dict[str, any]:
    """
    Helper function per salvare un file.
    Wrapper per StorageHelper.save_file()
    """
    helper = StorageHelper()
    return helper.save_file(file, subfolder=subfolder)


def get_storage_helper() -> StorageHelper:
    """Ottieni un'istanza di StorageHelper"""
    return StorageHelper()
