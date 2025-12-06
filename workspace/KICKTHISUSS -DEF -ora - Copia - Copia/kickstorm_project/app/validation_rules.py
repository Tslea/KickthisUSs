# app/validation_rules.py
"""Centralized validation rules shared between backend and frontend."""

VALIDATION_RULES = {
    "project": {
        "name": {
            "label": "Nome progetto",
            "min_length": 3,
            "max_length": 150,
            "pattern": r"^[A-Za-z0-9À-ÖØ-öø-ÿ&'’\".,!?()\\-\\s]+$",
            "required": False
        },
        "pitch": {
            "label": "Pitch iniziale",
            "min_length": 30,
            "max_length": 600
        },
        "description": {
            "label": "Descrizione del progetto",
            "max_length": 8000,
            "allow_markdown": True,
            "required": False
        }
    },
    "milestone": {
        "title": {
            "label": "Titolo milestone",
            "min_length": 3,
            "max_length": 180
        },
        "description": {
            "label": "Descrizione milestone",
            "max_length": 2000,
            "allow_markdown": True,
            "required": False
        }
    },
    "wiki": {
        "title": {
            "label": "Titolo pagina Wiki",
            "min_length": 3,
            "max_length": 160
        },
        "content": {
            "label": "Contenuto Wiki",
            "max_length": 20000,
            "allow_markdown": True,
            "required": True
        }
    },
    "comment": {
        "content": {
            "label": "Commento",
            "min_length": 1,
            "max_length": 1500
        }
    }
}

