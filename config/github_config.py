import os

# Flag per attivare/disattivare l'integrazione GitHub
GITHUB_ENABLED = os.getenv('GITHUB_ENABLED', 'False').lower() == 'true'

# Configurazione GitHub OAuth App
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'kickthisuss-projects')
GITHUB_API_BASE = 'https://api.github.com'

# Template repository per nuovi progetti
REPO_TEMPLATE = os.getenv('GITHUB_TEMPLATE', 'project-template')

# Struttura directory per progetti
PROJECT_STRUCTURE = {
    'software': {
        'src': 'Source code',
        'docs': 'Documentation',
        'tests': 'Test files',
        'examples': 'Example usage'
    },
    'hardware': {
        'schematics': 'Electrical schematics',
        'pcb': 'PCB design files',
        '3d-models': '3D CAD models',
        'bom': 'Bill of Materials',
        'photos': 'Prototype photos',
        'docs': 'Documentation'
    },
    'design': {
        'logos': 'Logo files (SVG, AI, PNG)',
        'branding': 'Brand guidelines and assets',
        'mockups': 'UI/UX designs and wireframes',
        'illustrations': 'Graphics, icons and illustrations',
        'assets': 'Source design files (PSD, Figma, Sketch)',
        'exports': 'Final exported files',
        'fonts': 'Typography and font files',
        'style-guides': 'Design system documentation'
    },
    'documentation': {
        'guides': 'User guides and tutorials',
        'technical': 'Technical documentation',
        'business': 'Business plans and strategy',
        'legal': 'Legal documents and contracts',
        'presentations': 'Slide decks and pitch materials',
        'research': 'Research papers and reports',
        'api-docs': 'API documentation'
    },
    'media': {
        'videos': 'Video content and demos',
        'audio': 'Audio files and podcasts',
        'images': 'Photography and imagery',
        'animations': 'Animated content (GIF, Lottie, video)',
        'promotional': 'Marketing and promotional materials',
        'screenshots': 'App/product screenshots'
    },
    'mixed': {
        'code': 'Source code and scripts',
        'designs': 'Design files and assets',
        'docs': 'Documentation',
        'media': 'Media files',
        'assets': 'Other project assets',
        'resources': 'Additional resources'
    }
}

# ⭐ ESTENSIONE: Formati file supportati per tutti i tipi di contenuto
SUPPORTED_FILE_FORMATS = {
    # Software/Codice
    'software': [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.cpp', '.c', '.h', '.hpp',
        '.java', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.cs',
        '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env'
    ],
    
    # Hardware
    'hardware': {
        'kicad': ['.kicad_pcb', '.kicad_sch', '.kicad_pro'],
        'eagle': ['.brd', '.sch'],
        'cad_3d': ['.stl', '.step', '.stp', '.iges', '.igs', '.f3d', '.obj', '.3ds'],
        'gerber': ['.gbr', '.gbl', '.gtl', '.gbs', '.gts', '.gko', '.drl'],
        'fusion360': ['.f3d', '.f3z'],
        'solidworks': ['.sldprt', '.sldasm', '.slddrw'],
        'autocad': ['.dwg', '.dxf']
    },
    
    # Design Grafico
    'design': {
        # Vettoriali
        'vector': ['.svg', '.ai', '.eps', '.pdf'],
        # Raster
        'raster': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'],
        # Design tools
        'figma': ['.fig'],
        'sketch': ['.sketch'],
        'xd': ['.xd'],
        'photoshop': ['.psd', '.psb'],
        'illustrator': ['.ai', '.ait'],
        'indesign': ['.indd', '.idml'],
        'affinity': ['.afdesign', '.afphoto', '.afpub'],
        # 3D/Animation
        'blender': ['.blend'],
        'cinema4d': ['.c4d'],
        'after_effects': ['.aep'],
        # Fonts
        'fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
    },
    
    # Documenti/Testi
    'documentation': {
        'text': ['.md', '.txt', '.rtf'],
        'office': ['.doc', '.docx', '.odt', '.pages'],
        'spreadsheet': ['.xls', '.xlsx', '.ods', '.numbers', '.csv'],
        'presentation': ['.ppt', '.pptx', '.odp', '.key'],
        'pdf': ['.pdf'],
        'ebook': ['.epub', '.mobi', '.azw'],
        'latex': ['.tex', '.bib'],
        'markdown': ['.md', '.markdown', '.mdown']
    },
    
    # Media
    'media': {
        # Video
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'],
        # Audio
        'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'],
        # Immagini (alta qualità)
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.raw', '.cr2', '.nef'],
        # Animazioni
        'animations': ['.gif', '.lottie', '.json', '.apng'],
        # Subtitles
        'subtitles': ['.srt', '.vtt', '.ass', '.ssa']
    }
}

# ⭐ NUOVO: Mappatura MIME types per validazione upload
MIME_TYPE_MAPPING = {
    # Design
    '.psd': 'image/vnd.adobe.photoshop',
    '.ai': 'application/postscript',
    '.fig': 'application/octet-stream',
    '.sketch': 'application/octet-stream',
    '.xd': 'application/octet-stream',
    
    # 3D Models
    '.stl': 'model/stl',
    '.obj': 'model/obj',
    '.blend': 'application/octet-stream',
    '.f3d': 'application/octet-stream',
    
    # Documents
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    
    # Media
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav'
}

# ⭐ NUOVO: Limiti dimensione file per tipo (in MB)
FILE_SIZE_LIMITS = {
    'software': 10,      # 10 MB per file codice
    'hardware': 50,      # 50 MB per file CAD
    'design': 100,       # 100 MB per file design (PSD possono essere grandi)
    'documentation': 20, # 20 MB per documenti
    'media': 500,        # 500 MB per video/audio
    'default': 50        # 50 MB default
}

# ⭐ NUOVO: Categorizzazione automatica per estensione
def get_content_type_from_extension(extension):
    """Determina il tipo di contenuto dall'estensione del file"""
    extension = extension.lower()
    
    # ⭐ Priority overrides per file ambigui
    priority_map = {
        '.pdf': 'documentation',  # PDF è principalmente per documenti
        '.gif': 'media',  # GIF è principalmente per animazioni/media
        '.png': 'design',  # PNG per design
        '.jpg': 'design',  # JPG per design
        '.jpeg': 'design',  # JPEG per design
    }
    
    if extension in priority_map:
        return priority_map[extension]
    
    # Software
    if extension in SUPPORTED_FILE_FORMATS['software']:
        return 'software'
    
    # Hardware
    for hw_type, extensions in SUPPORTED_FILE_FORMATS['hardware'].items():
        if extension in extensions:
            return 'hardware'
    
    # Documentation (check before design per priority)
    for doc_type, extensions in SUPPORTED_FILE_FORMATS['documentation'].items():
        if doc_type != 'pdf' and extension in extensions:  # Skip PDF già gestito
            return 'documentation'
    
    # Media (check before design per priority)
    for media_type, extensions in SUPPORTED_FILE_FORMATS['media'].items():
        if extension in extensions:
            return 'media'
    
    # Design
    for design_type, extensions in SUPPORTED_FILE_FORMATS['design'].items():
        if extension in extensions:
            return 'design'
    
    return 'mixed'  # Default per file non categorizzati

# ⭐ NUOVO: Validazione file per tipo progetto
def is_file_allowed_for_project(file_extension, project_type):
    """Verifica se un file è permesso per un tipo di progetto"""
    if project_type == 'mixed':
        return True  # Mixed projects accettano tutto
    
    content_type = get_content_type_from_extension(file_extension)
    return content_type == project_type or content_type == 'documentation'  # Docs sempre permessi

# Manteniamo retrocompatibilità
HARDWARE_FILE_FORMATS = SUPPORTED_FILE_FORMATS['hardware']

# Timeout per operazioni GitHub (secondi)
GITHUB_TIMEOUT = 30

# Retry policy
GITHUB_MAX_RETRIES = 3
GITHUB_RETRY_DELAY = 2  # secondi
