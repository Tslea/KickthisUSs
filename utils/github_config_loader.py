"""
Wrapper per evitare conflitti tra config.py e config/ directory
Import questo file invece di config.github_config direttamente
"""

import os
import sys
import importlib.util

# Load github_config module
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
github_config_path = os.path.join(project_root, "config", "github_config.py")

spec = importlib.util.spec_from_file_location("github_config_module", github_config_path)
github_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(github_config_module)

# Export all from github_config
GITHUB_TOKEN = github_config_module.GITHUB_TOKEN
GITHUB_ORG = github_config_module.GITHUB_ORG
GITHUB_API_BASE = github_config_module.GITHUB_API_BASE
GITHUB_TIMEOUT = github_config_module.GITHUB_TIMEOUT
GITHUB_MAX_RETRIES = github_config_module.GITHUB_MAX_RETRIES
GITHUB_RETRY_DELAY = github_config_module.GITHUB_RETRY_DELAY
PROJECT_STRUCTURE = github_config_module.PROJECT_STRUCTURE
REPO_TEMPLATE = github_config_module.REPO_TEMPLATE
SUPPORTED_FILE_FORMATS = github_config_module.SUPPORTED_FILE_FORMATS
get_content_type_from_extension = github_config_module.get_content_type_from_extension
FILE_SIZE_LIMITS = github_config_module.FILE_SIZE_LIMITS
is_file_allowed_for_project = github_config_module.is_file_allowed_for_project
MIME_TYPE_MAPPING = github_config_module.MIME_TYPE_MAPPING
GITHUB_ENABLED = github_config_module.GITHUB_ENABLED
HARDWARE_FILE_FORMATS = github_config_module.HARDWARE_FILE_FORMATS
