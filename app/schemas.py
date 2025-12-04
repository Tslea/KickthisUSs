# app/schemas.py
"""
Pydantic schemas for input validation in KickthisUSs.
Provides type-safe validation for API endpoints and forms.
"""

from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
import re


# ============================================
# Base Configuration
# ============================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=0,
        validate_assignment=True,
        extra='ignore'  # Ignore extra fields
    )


# ============================================
# Project Schemas
# ============================================

class ProjectCreateSchema(BaseSchema):
    """Schema for creating a new project."""
    pitch: str = Field(
        ..., 
        min_length=30, 
        max_length=600,
        description="Project pitch (30-600 characters)"
    )
    category: str = Field(
        ..., 
        min_length=1,
        description="Project category"
    )
    project_type: Literal['commercial', 'scientific'] = Field(
        default='commercial',
        description="Type of project"
    )
    
    @field_validator('pitch')
    @classmethod
    def validate_pitch(cls, value: str) -> str:
        """Validate pitch content."""
        if not value or not value.strip():
            raise ValueError("Pitch cannot be empty")
        # Remove excessive whitespace
        value = ' '.join(value.split())
        return value
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, value: str) -> str:
        """Validate category."""
        valid_categories = [
            'tech', 'social', 'environment', 'health', 'education',
            'finance', 'art', 'science', 'other'
        ]
        value_lower = value.lower().strip()
        # Allow any category but normalize common ones
        return value


class ProjectUpdateSchema(BaseSchema):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=10000)
    pitch: Optional[str] = Field(None, min_length=30, max_length=600)
    category: Optional[str] = None
    status: Optional[Literal['active', 'completed', 'paused', 'archived']] = None


# ============================================
# Task Schemas
# ============================================

class TaskCreateSchema(BaseSchema):
    """Schema for creating a new task."""
    title: str = Field(
        ..., 
        min_length=5, 
        max_length=200,
        description="Task title"
    )
    description: str = Field(
        ..., 
        min_length=20, 
        max_length=5000,
        description="Task description"
    )
    task_type: Literal['proposal', 'implementation', 'validation'] = Field(
        default='implementation',
        description="Type of task"
    )
    phase: Optional[str] = Field(
        default='Development',
        description="Project phase"
    )
    difficulty: Literal['Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard'] = Field(
        default='Medium',
        description="Task difficulty"
    )
    equity_reward: float = Field(
        ..., 
        gt=0, 
        le=100,
        description="Shares reward for completing the task"
    )
    is_private: bool = Field(default=False)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Validate and clean title."""
        value = ' '.join(value.split())  # Normalize whitespace
        return value
    
    @field_validator('equity_reward')
    @classmethod
    def validate_equity(cls, value: float) -> float:
        """Ensure equity is reasonable."""
        if value <= 0:
            raise ValueError("Shares reward must be positive")
        if value > 100:
            raise ValueError("Shares reward cannot exceed 100")
        return round(value, 2)


class TaskUpdateSchema(BaseSchema):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    status: Optional[Literal['open', 'in_progress', 'completed', 'cancelled', 'suggested']] = None
    is_private: Optional[bool] = None


# ============================================
# Solution Schemas
# ============================================

class SolutionSubmitSchema(BaseSchema):
    """Schema for submitting a solution."""
    content: str = Field(
        ..., 
        min_length=50, 
        max_length=20000,
        description="Solution content"
    )
    github_pr_url: Optional[str] = Field(
        None, 
        max_length=500,
        description="GitHub Pull Request URL"
    )
    
    @field_validator('github_pr_url')
    @classmethod
    def validate_github_url(cls, value: Optional[str]) -> Optional[str]:
        """Validate GitHub PR URL format."""
        if value is None or not value.strip():
            return None
        
        value = value.strip()
        # Basic GitHub PR URL pattern
        github_pattern = r'^https?://github\.com/[\w\-]+/[\w\-]+/pull/\d+/?.*$'
        if not re.match(github_pattern, value, re.IGNORECASE):
            raise ValueError("Invalid GitHub Pull Request URL format")
        return value


# ============================================
# Comment Schemas
# ============================================

class CommentCreateSchema(BaseSchema):
    """Schema for creating a comment."""
    content: str = Field(
        ..., 
        min_length=1, 
        max_length=5000,
        description="Comment content"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate comment content."""
        if not v or not v.strip():
            raise ValueError("Comment cannot be empty")
        return v.strip()


# ============================================
# User Schemas
# ============================================

class UserRegistrationSchema(BaseSchema):
    """Schema for user registration."""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username (alphanumeric and underscores only)"
    )
    email: EmailStr = Field(..., description="User email")
    password: str = Field(
        ..., 
        min_length=8,
        description="Password (minimum 8 characters)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        return v


class UserProfileUpdateSchema(BaseSchema):
    """Schema for updating user profile."""
    bio: Optional[str] = Field(None, max_length=500)
    skills: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)
    linkedin: Optional[str] = Field(None, max_length=200)
    github: Optional[str] = Field(None, max_length=200)


# ============================================
# Chat/AI Schemas
# ============================================

class ChatMessageSchema(BaseSchema):
    """Schema for chat messages."""
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=5000,
        description="Chat message content"
    )
    context_doc: Optional[str] = Field(None, max_length=50000)
    project_id: Optional[int] = Field(None, gt=0)
    history: Optional[List[dict]] = Field(default_factory=list)


class DocumentGenerateSchema(BaseSchema):
    """Schema for document generation."""
    project_id: int = Field(..., gt=0)
    doc_type: str = Field(..., min_length=1, max_length=100)


# ============================================
# Wiki Schemas
# ============================================

class WikiPageCreateSchema(BaseSchema):
    """Schema for creating a wiki page."""
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Page title"
    )
    content: str = Field(
        default='',
        max_length=100000,
        description="Page content in Markdown"
    )
    parent_id: Optional[int] = Field(None, description="Parent page ID")
    is_folder: bool = Field(default=False)


class WikiPageUpdateSchema(BaseSchema):
    """Schema for updating a wiki page."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=100000)


# ============================================
# Validation Helpers
# ============================================

def validate_request_data(schema_class: type[BaseSchema], data: dict) -> tuple[bool, BaseSchema | dict]:
    """
    Validate request data against a Pydantic schema.
    
    Returns:
        tuple: (is_valid: bool, result: schema instance or error dict)
    
    Usage:
        is_valid, result = validate_request_data(ProjectCreateSchema, request.json)
        if not is_valid:
            return jsonify(result), 400
        # Use result.pitch, result.category, etc.
    """
    try:
        validated = schema_class(**data)
        return True, validated
    except Exception as e:
        # Extract validation errors
        if hasattr(e, 'errors'):
            errors = []
            for err in e.errors():
                field = '.'.join(str(loc) for loc in err['loc'])
                message = err['msg']
                errors.append({'field': field, 'message': message})
            return False, {'errors': errors, 'message': 'Validation failed'}
        return False, {'errors': [{'message': str(e)}], 'message': 'Validation failed'}

