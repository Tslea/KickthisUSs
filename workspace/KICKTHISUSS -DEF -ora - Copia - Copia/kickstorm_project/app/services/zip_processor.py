"""
ZIP Processor Service
Gestisce l'estrazione, validazione e analisi di file ZIP per i contributi.
"""
import os
import zipfile
import tarfile
import tempfile
import shutil
import difflib
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from werkzeug.datastructures import FileStorage
from flask import current_app


class ZipProcessorError(Exception):
    """Eccezione personalizzata per errori di processing ZIP"""
    pass


class ZipProcessor:
    """Gestisce l'estrazione e l'analisi di file ZIP/TAR per contributi"""
    
    MAX_FILE_SIZE = 52428800  # 50MB default fallback
    MAX_FILES = 1000  # Massimo numero di file in un ZIP
    ALLOWED_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', 
                         '.scss', '.json', '.md', '.txt', '.yml', '.yaml', '.xml',
                         '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php',
                         '.sh', '.bat', '.ps1', '.sql', '.vue', '.svelte', '.astro',
                         '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
                         '.pdf', '.docx', '.xlsx', '.pptx', '.csv', '.mp4', '.webm',
                         '.mp3', '.wav', '.zip', '.tar', '.gz', '.gitignore', '.env.example'}
    
    FORBIDDEN_PATHS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 
                      'env', 'dist', 'build', 'target', '.idea', '.vscode'}
    
    def __init__(self):
        self.temp_dir = None
        self.extracted_files: List[Dict] = []
        max_zip_bytes = current_app.config.get('PROJECT_WORKSPACE_MAX_ZIP_BYTES', self.MAX_FILE_SIZE)
        self.max_archive_bytes = max_zip_bytes
        # Consenti espansione fino al doppio per file estratti (override configurabile)
        self.max_extracted_bytes = current_app.config.get(
            'PROJECT_WORKSPACE_MAX_EXTRACTED_BYTES',
            max_zip_bytes * 2
        )
        self.max_file_count = current_app.config.get('PROJECT_WORKSPACE_MAX_FILES', self.MAX_FILES)
    
    def extract_zip(self, zip_file: FileStorage) -> List[Dict]:
        """
        Estrae i file da un archivio ZIP/TAR
        
        Args:
            zip_file: FileStorage object da Flask
            
        Returns:
            List di dict con info sui file estratti: {path, content, size, type}
            
        Raises:
            ZipProcessorError: Se l'estrazione fallisce
        """
        # Validazione dimensione
        zip_file.seek(0, os.SEEK_END)
        file_size = zip_file.tell()
        zip_file.seek(0)
        
        if file_size > self.max_archive_bytes:
            raise ZipProcessorError(
                f"File troppo grande: {file_size / 1024 / 1024:.2f}MB. "
                f"Massimo consentito: {self.max_archive_bytes / 1024 / 1024:.0f}MB"
            )
        
        # Crea directory temporanea
        self.temp_dir = tempfile.mkdtemp(prefix='kickthisuss_zip_')
        
        try:
            filename = zip_file.filename.lower()
            
            # Estrai in base al tipo di archivio
            if filename.endswith('.zip'):
                self._extract_zip_archive(zip_file)
            elif filename.endswith(('.tar', '.tar.gz', '.tgz')):
                self._extract_tar_archive(zip_file)
            else:
                raise ZipProcessorError("Formato archivio non supportato")
            
            # Valida struttura estratta
            self._validate_extracted_structure()
            
            # Leggi i file estratti
            self._read_extracted_files()
            
            return self.extracted_files
            
        except zipfile.BadZipFile:
            raise ZipProcessorError("File ZIP corrotto o non valido")
        except tarfile.TarError:
            raise ZipProcessorError("File TAR corrotto o non valido")
        except Exception as e:
            current_app.logger.error(f"Errore estrazione ZIP: {e}", exc_info=True)
            raise ZipProcessorError(f"Errore durante l'estrazione: {str(e)}")
    
    def _extract_zip_archive(self, zip_file: FileStorage):
        """Estrae un archivio ZIP"""
        with zipfile.ZipFile(zip_file.stream, 'r') as zf:
            allowed_members: List[str] = []
            for info in zf.infolist():
                name = info.filename
                if not name or name.endswith('/'):
                    continue
                relative_path = Path(name)
                if self._is_forbidden_path(relative_path):
                    continue
                allowed_members.append(name)

            if len(allowed_members) > self.max_file_count:
                raise ZipProcessorError(
                    f"Troppi file nell'archivio: {len(allowed_members)}. "
                    f"Massimo consentito: {self.max_file_count}"
                )

            base_dir = Path(self.temp_dir).resolve()
            for member in allowed_members:
                member_path = (base_dir / Path(member)).resolve()
                if not str(member_path).startswith(str(base_dir)):
                    raise ZipProcessorError(f"Path non sicuro rilevato: {member}")
                zf.extract(member, self.temp_dir)
    
    def _extract_tar_archive(self, tar_file: FileStorage):
        """Estrae un archivio TAR/TAR.GZ"""
        mode = 'r:gz' if tar_file.filename.lower().endswith(('.gz', '.tgz')) else 'r'
        
        with tarfile.open(fileobj=tar_file.stream, mode=mode) as tf:
            file_members = [m for m in tf.getmembers() if not m.isdir()]
            allowed_members = []
            for member in file_members:
                path_obj = Path(member.name)
                if self._is_forbidden_path(path_obj):
                    continue
                allowed_members.append(member)

            if len(allowed_members) > self.max_file_count:
                raise ZipProcessorError(
                    f"Troppi file nell'archivio: {len(allowed_members)}. "
                    f"Massimo consentito: {self.max_file_count}"
                )

            base_dir = Path(self.temp_dir).resolve()
            for member in allowed_members:
                member_path = (base_dir / Path(member.name)).resolve()
                if not str(member_path).startswith(str(base_dir)):
                    raise ZipProcessorError(f"Path non sicuro rilevato: {member.name}")
                tf.extract(member, self.temp_dir)
    
    def _validate_extracted_structure(self):
        """Valida la struttura dei file estratti"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.temp_dir):
            # Rimuovi directory forbidden
            dirs[:] = [d for d in dirs if d not in self.FORBIDDEN_PATHS]
            
            for file in files:
                file_path = Path(root) / file
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # Verifica estensione
                if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS and not file_path.name.startswith('.'):
                    current_app.logger.warning(f"File con estensione non consentita: {file_path}")
        
        if file_count == 0:
            raise ZipProcessorError("Nessun file valido trovato nell'archivio")
        
        if total_size > self.max_extracted_bytes:
            raise ZipProcessorError(
                f"Dimensione totale estratta troppo grande: {total_size / 1024 / 1024:.2f}MB "
                f"(limite {self.max_extracted_bytes / 1024 / 1024:.0f}MB)"
            )
    
    def _read_extracted_files(self):
        """Legge i file estratti e li memorizza (solo metadati per performance)"""
        file_count = 0
        for root, dirs, files in os.walk(self.temp_dir):
            # Rimuovi directory forbidden
            dirs[:] = [d for d in dirs if d not in self.FORBIDDEN_PATHS]
            
            for file in files:
                file_path = Path(root) / file
                
                # Path relativo dalla root temporanea
                relative_path = file_path.relative_to(self.temp_dir)
                
                # Determina tipo file
                file_type = self._get_file_type(file_path)
                
                # NON leggere il contenuto qui - troppo lento per file grandi
                # Il contenuto verrà letto solo quando necessario
                content = None
                
                # Log progresso ogni 100 file per debug
                file_count += 1
                if file_count % 100 == 0:
                    current_app.logger.debug(f"Processed {file_count} files...")
                
                self.extracted_files.append({
                    'path': str(relative_path).replace('\\', '/'),  # Unix-style path
                    'full_path': str(file_path),
                    'content': content,  # None per performance
                    'size': file_path.stat().st_size,
                    'type': file_type,
                    'extension': file_path.suffix.lower()
                })
        
        current_app.logger.debug(f"Total files processed: {file_count}")
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determina il tipo di file"""
        text_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', 
                          '.scss', '.json', '.md', '.txt', '.yml', '.yaml', '.xml',
                          '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php',
                          '.sh', '.bat', '.ps1', '.sql', '.vue', '.svelte', '.astro'}
        
        if file_path.suffix.lower() in text_extensions:
            return 'text'
        return 'binary'
    
    def detect_project_type(self, files: List[Dict]) -> str:
        """
        Rileva il tipo di progetto basandosi sui file
        
        Returns:
            str: 'python', 'javascript', 'typescript', 'react', 'vue', 'design', etc.
        """
        file_names = {f['path'].lower() for f in files}
        extensions = {f['extension'] for f in files}
        
        # Python
        if 'requirements.txt' in file_names or 'pyproject.toml' in file_names:
            return 'python'
        if '.py' in extensions:
            return 'python'
        
        # JavaScript/TypeScript/React/Vue
        if 'package.json' in file_names:
            # Leggi package.json per dettagli
            pkg_json = next((f for f in files if f['path'].lower() == 'package.json'), None)
            if pkg_json and pkg_json['content']:
                import json
                try:
                    pkg_data = json.loads(pkg_json['content'])
                    deps = {**pkg_data.get('dependencies', {}), **pkg_data.get('devDependencies', {})}
                    
                    if 'react' in deps or 'next' in deps:
                        return 'react'
                    if 'vue' in deps:
                        return 'vue'
                    if 'typescript' in deps or '.ts' in extensions or '.tsx' in extensions:
                        return 'typescript'
                except:
                    pass
            
            return 'javascript'
        
        # Design
        if extensions & {'.fig', '.sketch', '.xd', '.psd', '.ai'}:
            return 'design'
        
        # Media
        if extensions & {'.mp4', '.webm', '.mp3', '.wav', '.mov'}:
            return 'media'
        
        # Documentation
        if extensions == {'.md', '.txt', '.pdf', '.docx'}:
            return 'documentation'
        
        # Mixed
        if len(extensions) > 5:
            return 'mixed'
        
        return 'unknown'
    
    def compare_files(self, uploaded_file_content: str, base_file_content: Optional[str]) -> List[str]:
        """
        Confronta due file di testo e restituisce il diff
        
        Args:
            uploaded_file_content: Contenuto del file caricato
            base_file_content: Contenuto del file base (None se nuovo file)
            
        Returns:
            List di righe di diff in formato unified
        """
        if base_file_content is None:
            # Nuovo file - tutto è "aggiunto"
            return [f"+ {line}" for line in uploaded_file_content.splitlines()]
        
        base_lines = base_file_content.splitlines(keepends=True)
        uploaded_lines = uploaded_file_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            base_lines, 
            uploaded_lines,
            lineterm='',
            n=3  # Linee di contesto
        ))
        
        return diff
    
    def calculate_diff_stats(self, files: List[Dict], base_files: Optional[Dict[str, str]] = None) -> Dict:
        """
        Calcola statistiche sui cambiamenti
        
        Args:
            files: Lista di file estratti
            base_files: Dict {path: content} dei file base nel repo (None se nuova soluzione)
            
        Returns:
            Dict con {lines_added, lines_deleted, files_modified, files_added}
        """
        stats = {
            'lines_added': 0,
            'lines_deleted': 0,
            'files_modified': 0,
            'files_added': 0,
            'files_deleted': 0
        }
        
        if base_files is None:
            # Tutti i file sono nuovi
            stats['files_added'] = len([f for f in files if f['type'] == 'text'])
            stats['lines_added'] = sum(
                len(f['content'].splitlines()) 
                for f in files 
                if f['type'] == 'text' and f['content']
            )
            return stats
        
        uploaded_paths = {f['path']: f for f in files}
        
        # Analizza file modificati e aggiunti
        for path, file_info in uploaded_paths.items():
            if file_info['type'] != 'text' or not file_info['content']:
                continue
            
            if path in base_files:
                # File modificato
                diff = self.compare_files(file_info['content'], base_files[path])
                
                # Conta righe aggiunte/rimosse
                added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                deleted = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
                
                if added > 0 or deleted > 0:
                    stats['files_modified'] += 1
                    stats['lines_added'] += added
                    stats['lines_deleted'] += deleted
            else:
                # File aggiunto
                stats['files_added'] += 1
                stats['lines_added'] += len(file_info['content'].splitlines())
        
        # File eliminati (nel base ma non nell'upload)
        for path in base_files:
            if path not in uploaded_paths:
                stats['files_deleted'] += 1
                stats['lines_deleted'] += len(base_files[path].splitlines())
        
        return stats
    
    
    def extract_code_summary(self, extracted_files: List[Dict], max_chars: int = 8000) -> str:
        """
        Estrae un summary intelligente del codice per l'analisi AI.
        Priorità: README > file principali > altri file di codice
        
        Args:
            extracted_files: Lista di file estratti dal ZIP
            max_chars: Caratteri massimi da estrarre (per limiti token AI)
            
        Returns:
            str: Summary del codice concatenato
        """
        summary_parts = []
        current_length = 0
        
        # Priorità 1: README (se esiste)
        readme_file = next(
            (f for f in extracted_files 
             if 'readme' in f['path'].lower() and f['type'] == 'text'),
            None
        )
        if readme_file and readme_file.get('content'):
            content = readme_file['content'][:500]
            summary_parts.append(f"=== README ===\n{content}\n")
            current_length += len(content) + 20
        
        # Priorità 2: File principali (main.py, index.js, app.py, main.ts, etc.)
        main_patterns = ['main', 'index', 'app', 'server', '__init__']
        main_files = [
            f for f in extracted_files
            if any(pattern in f['path'].lower() for pattern in main_patterns)
            and f['type'] == 'text'
            and f.get('content')
        ]
        
        for file_info in main_files[:3]:  # Max 3 file principali
            if current_length >= max_chars:
                break
                
            # Leggi contenuto se non già presente
            if not file_info.get('content'):
                try:
                    with open(file_info['full_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        file_info['content'] = f.read()
                except Exception:
                    continue
            
            content_to_add = file_info['content'][:1000]
            summary_parts.append(f"=== {file_info['path']} ===\n{content_to_add}\n")
            current_length += len(content_to_add) + len(file_info['path']) + 10
        
        # Priorità 3: Altri file di codice (sample)
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.go', '.rs'}
        other_code_files = [
            f for f in extracted_files
            if f not in main_files
            and f['extension'] in code_extensions
            and f['type'] == 'text'
        ]
        
        for file_info in other_code_files[:5]:  # Max 5 altri file
            if current_length >= max_chars:
                break
            
            # Leggi contenuto se non già presente
            if not file_info.get('content'):
                try:
                    with open(file_info['full_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        file_info['content'] = f.read()
                except Exception:
                    continue
            
            content_to_add = file_info['content'][:500]
            summary_parts.append(f"=== {file_info['path']} ===\n{content_to_add}\n")
            current_length += len(content_to_add) + len(file_info['path']) + 10
        
        # Priorità 4: File documentazione (se c'è spazio)
        doc_files = [
            f for f in extracted_files
            if f['extension'] in {'.md', '.txt'}
            and 'readme' not in f['path'].lower()
            and f['type'] == 'text'
        ]
        
        for file_info in doc_files[:2]:  # Max 2 doc file
            if current_length >= max_chars:
                break
            
            if not file_info.get('content'):
                try:
                    with open(file_info['full_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        file_info['content'] = f.read()
                except Exception:
                    continue
            
            content_to_add = file_info['content'][:300]
            summary_parts.append(f"=== {file_info['path']} ===\n{content_to_add}\n")
            current_length += len(content_to_add) + len(file_info['path']) + 10
        
        # Combina e limita
        summary = "\n".join(summary_parts)
        
        # Aggiungi statistiche finali
        file_types = {}
        for f in extracted_files:
            ext = f['extension'] or 'other'
            file_types[ext] = file_types.get(ext, 0) + 1
        
        stats_summary = "\n\n=== Project Statistics ===\n"
        stats_summary += f"Total files: {len(extracted_files)}\n"
        stats_summary += "File types: " + ", ".join(f"{ext}: {count}" for ext, count in sorted(file_types.items())[:5])
        
        summary += stats_summary
        
        return summary[:max_chars]
    
    def cleanup(self):

        """Pulisce la directory temporanea"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                current_app.logger.warning(f"Impossibile rimuovere temp dir {self.temp_dir}: {e}")
    
    def __del__(self):
        """Cleanup automatico alla distruzione dell'oggetto"""
        self.cleanup()

    def _is_forbidden_path(self, path_obj: Path) -> bool:
        return any(part in self.FORBIDDEN_PATHS for part in path_obj.parts)


def validate_zip_structure(files: List[Dict]) -> Tuple[bool, str]:
    """
    Valida la struttura di un progetto
    
    Args:
        files: Lista di file estratti
        
    Returns:
        (is_valid, error_message)
    """
    if not files:
        return False, "Nessun file trovato nell'archivio"
    
    # Verifica che ci siano file con contenuto
    text_files = [f for f in files if f['type'] == 'text' and f['content']]
    if not text_files and len(files) < 5:
        return False, "L'archivio sembra vuoto o non contiene file validi"
    
    # Verifica dimensione totale
    total_size = sum(f['size'] for f in files)
    max_total = ZipProcessor.MAX_FILE_SIZE * 2
    try:
        max_total = current_app.config.get('PROJECT_WORKSPACE_MAX_EXTRACTED_BYTES', max_total)
    except RuntimeError:
        pass
    if total_size > max_total:
        return False, f"Dimensione totale troppo grande: {total_size / 1024 / 1024:.2f}MB"
    
    return True, ""


def analyze_project_changes(uploaded_files: List[Dict], base_repo_files: Optional[Dict[str, str]] = None) -> Dict:
    """
    Analizza i cambiamenti in un progetto
    
    Args:
        uploaded_files: File caricati dall'utente
        base_repo_files: File base dal repository (None se nuovo progetto)
        
    Returns:
        Dict con {added: [], modified: [], deleted: [], stats: {}}
    """
    processor = ZipProcessor()
    
    try:
        stats = processor.calculate_diff_stats(uploaded_files, base_repo_files)
        
        uploaded_paths = {f['path'] for f in uploaded_files}
        base_paths = set(base_repo_files.keys()) if base_repo_files else set()
        
        result = {
            'added': list(uploaded_paths - base_paths),
            'modified': [],
            'deleted': list(base_paths - uploaded_paths),
            'stats': stats
        }
        
        # Identifica file modificati
        if base_repo_files:
            for file_info in uploaded_files:
                if file_info['path'] in base_repo_files and file_info['type'] == 'text':
                    if file_info['content'] != base_repo_files[file_info['path']]:
                        result['modified'].append(file_info['path'])
        
        return result
        
    finally:
        processor.cleanup()
