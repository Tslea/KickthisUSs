import os
import mimetypes
from typing import Dict, List, Tuple
from werkzeug.datastructures import FileStorage

from config.github_config import HARDWARE_FILE_FORMATS


class HardwareFileHandler:
    """Gestisce parsing e organizzazione file hardware"""
    
    def __init__(self):
        self.supported_formats = HARDWARE_FILE_FORMATS
    
    def organize_files(self, files: List[FileStorage], project_type: str) -> Dict[str, List[Dict]]:
        """
        Organizza file caricati in struttura appropriata per GitHub
        Returns: Dict con path GitHub come chiave e info file come valore
        """
        organized = {
            'schematics': [],
            'pcb': [],
            '3d-models': [],
            'gerber': [],
            'bom': [],
            'photos': [],
            'docs': [],
            'other': []
        }
        
        for file in files:
            if file and file.filename:
                category = self._categorize_file(file.filename)
                file_info = {
                    'name': file.filename,
                    'content': file.read(),
                    'path': f"{category}/{file.filename}",
                    'size': len(file.read()),
                    'mimetype': file.mimetype or mimetypes.guess_type(file.filename)[0]
                }
                file.seek(0)  # Reset file pointer
                
                organized[category].append(file_info)
        
        return organized
    
    def _categorize_file(self, filename: str) -> str:
        """Categorizza file in base all'estensione"""
        ext = os.path.splitext(filename)[1].lower()
        
        # KiCad files
        if ext in self.supported_formats['kicad']:
            if 'pcb' in ext:
                return 'pcb'
            elif 'sch' in ext:
                return 'schematics'
        
        # Eagle files
        elif ext in self.supported_formats['eagle']:
            if ext == '.brd':
                return 'pcb'
            elif ext == '.sch':
                return 'schematics'
        
        # 3D CAD files
        elif ext in self.supported_formats['cad_3d']:
            return '3d-models'
        
        # Gerber files
        elif ext in self.supported_formats['gerber']:
            return 'gerber'
        
        # Images
        elif ext in self.supported_formats['images']:
            # Se contiene "schematic" nel nome -> schematics
            if 'schematic' in filename.lower() or 'circuit' in filename.lower():
                return 'schematics'
            else:
                return 'photos'
        
        # Documents
        elif ext in self.supported_formats['documents']:
            # Se contiene "bom" nel nome -> bom
            if 'bom' in filename.lower() or 'bill' in filename.lower():
                return 'bom'
            else:
                return 'docs'
        
        return 'other'
    
    def validate_files(self, files: List[FileStorage]) -> Tuple[bool, List[str]]:
        """
        Valida file caricati
        Returns: (is_valid, error_messages)
        """
        errors = []
        
        for file in files:
            if not file or not file.filename:
                continue
            
            # Check estensione supportata
            ext = os.path.splitext(file.filename)[1].lower()
            if not self._is_supported_format(ext):
                errors.append(f"File format not supported: {file.filename}")
            
            # Check dimensione (max 50MB per file)
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            if size > 50 * 1024 * 1024:  # 50MB
                errors.append(f"File too large (max 50MB): {file.filename}")
        
        return (len(errors) == 0, errors)
    
    def _is_supported_format(self, ext: str) -> bool:
        """Verifica se estensione è supportata"""
        for formats in self.supported_formats.values():
            if ext in formats:
                return True
        return False
    
    def parse_bom(self, file_content: str) -> List[Dict]:
        """
        Parse Bill of Materials da file CSV o testo
        Returns: Lista di componenti
        """
        import csv
        from io import StringIO
        
        components = []
        
        try:
            # Prova parsing CSV
            reader = csv.DictReader(StringIO(file_content))
            for row in reader:
                components.append({
                    'designator': row.get('Designator', ''),
                    'value': row.get('Value', ''),
                    'package': row.get('Package', ''),
                    'quantity': int(row.get('Quantity', 1)),
                    'description': row.get('Description', ''),
                    'manufacturer': row.get('Manufacturer', ''),
                    'part_number': row.get('Part Number', '')
                })
        except Exception as e:
            # Fallback: parsing semplice linea per linea
            for line in file_content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        components.append({
                            'designator': parts[0].strip(),
                            'value': parts[1].strip() if len(parts) > 1 else '',
                            'quantity': 1
                        })
        
        return components
    
    def generate_bom_markdown(self, components: List[Dict]) -> str:
        """Genera BOM in formato Markdown per GitHub"""
        md = "# Bill of Materials\n\n"
        md += "| Designator | Value | Package | Qty | Description | Manufacturer | Part # |\n"
        md += "|------------|-------|---------|-----|-------------|--------------|--------|\n"
        
        for comp in components:
            md += f"| {comp.get('designator', '')} "
            md += f"| {comp.get('value', '')} "
            md += f"| {comp.get('package', '')} "
            md += f"| {comp.get('quantity', 1)} "
            md += f"| {comp.get('description', '')} "
            md += f"| {comp.get('manufacturer', '')} "
            md += f"| {comp.get('part_number', '')} |\n"
        
        md += f"\n**Total Components:** {len(components)}\n"
        md += f"**Total Quantity:** {sum(c.get('quantity', 1) for c in components)}\n"
        
        return md
