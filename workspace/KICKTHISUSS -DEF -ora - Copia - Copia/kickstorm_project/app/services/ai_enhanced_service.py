# app/services/ai_enhanced_service.py
"""
Enhanced AI Service using LangChain for improved capabilities.
Provides structured outputs, better error handling, and caching.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import LangChain components
LANGCHAIN_AVAILABLE = False
try:
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.output_parsers import PydanticOutputParser
    from langchain_core.runnables import RunnablePassthrough
    LANGCHAIN_AVAILABLE = True
    logger.info("LangChain components loaded successfully")
except ImportError as e:
    logger.warning(f"LangChain not available, using fallback: {e}")


class EnhancedAIService:
    """
    Enhanced AI service with LangChain integration.
    Falls back to basic OpenAI client if LangChain is unavailable.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.llm = None
        self.provider = None
        self.model = None
        self.available = False
        
        self._initialize()
        self._initialized = True
    
    def _initialize(self):
        """Initialize the AI service with available provider."""
        provider = os.environ.get('AI_PROVIDER', 'deepseek')
        
        if provider == 'grok':
            api_key = os.environ.get('GROK_API_KEY')
            base_url = "https://api.x.ai/v1"
            model = os.environ.get('GROK_MODEL', 'grok-4-fast')
        else:
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            base_url = "https://api.deepseek.com/v1"
            model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
        
        if not api_key:
            logger.warning(f"No API key found for {provider}")
            return
        
        try:
            if LANGCHAIN_AVAILABLE:
                self.llm = ChatOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    temperature=0.7,
                    max_tokens=2000
                )
                logger.info(f"LangChain ChatOpenAI initialized with {provider}/{model}")
            else:
                # Fallback to basic OpenAI client
                from openai import OpenAI
                import httpx
                self.llm = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=httpx.Client(proxies={})
                )
                logger.info(f"Basic OpenAI client initialized with {provider}/{model}")
            
            self.provider = provider
            self.model = model
            self.available = True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            self.available = False
    
    def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Optional[Dict] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from AI.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            output_schema: Expected output structure (for validation)
            temperature: Generation temperature
            
        Returns:
            Parsed JSON response or error dict
        """
        if not self.available:
            return {"error": "AI service not available"}
        
        try:
            if LANGCHAIN_AVAILABLE:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                response = self.llm.invoke(messages)
                content = response.content
            else:
                # Fallback to basic client
                response = self.llm.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
            
            # Parse JSON from response
            return self._parse_json_response(content)
            
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return {"error": str(e)}
    
    def chat_with_context(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Chat with conversation history and optional context.
        
        Args:
            messages: List of {role, content} message dicts
            context: Optional context document
            system_prompt: Optional system instructions
            
        Returns:
            AI response string
        """
        if not self.available:
            return "AI service not available. Please check configuration."
        
        default_system = (
            "Sei un AI Startup Mentor esperto. Il tuo obiettivo è guidare il fondatore "
            "nella creazione di una startup di successo. Sii conciso, pratico e diretto."
        )
        
        full_system = system_prompt or default_system
        if context:
            full_system += f"\n\nCONTESTO:\n{context}"
        
        try:
            if LANGCHAIN_AVAILABLE:
                lc_messages = [SystemMessage(content=full_system)]
                for msg in messages:
                    if msg['role'] == 'user':
                        lc_messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        lc_messages.append(AIMessage(content=msg['content']))
                
                response = self.llm.invoke(lc_messages)
                return response.content
            else:
                all_messages = [{"role": "system", "content": full_system}]
                all_messages.extend(messages)
                
                response = self.llm.chat.completions.create(
                    model=self.model,
                    messages=all_messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "Mi dispiace, si è verificato un errore."
    
    def generate_document(
        self,
        doc_type: str,
        project_context: Dict[str, Any]
    ) -> str:
        """
        Generate document content for Hub Agents.
        
        Args:
            doc_type: Document type (e.g., 'mvp_definition.md')
            project_context: Project information dict
            
        Returns:
            Generated document content
        """
        if not self.available:
            return "AI service not available."
        
        # Build context string
        context_parts = [
            f"Nome Progetto: {project_context.get('name', 'N/A')}",
            f"Pitch: {project_context.get('pitch', 'N/A')}",
            f"Descrizione: {project_context.get('description', 'N/A')}",
            f"Categoria: {project_context.get('category', 'N/A')}",
            f"Tipo: {project_context.get('project_type', 'commercial')}"
        ]
        
        if project_context.get('ai_mvp_guide'):
            context_parts.append(f"Guida MVP: {project_context['ai_mvp_guide'][:500]}")
        
        context_str = "\n".join(context_parts)
        
        system_prompt = f"""Sei un esperto business analyst e startup advisor.
Genera il contenuto per il documento '{doc_type}' basandoti sul contesto del progetto.

CONTESTO PROGETTO:
{context_str}

ISTRUZIONI:
- Scrivi in formato Markdown
- Sii specifico e dettagliato
- Adatta il contenuto al tipo di progetto
- Usa esempi concreti quando possibile
- Struttura il documento con sezioni chiare"""

        user_prompt = f"Genera il contenuto completo per: {doc_type}"
        
        try:
            if LANGCHAIN_AVAILABLE:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = self.llm.invoke(messages)
                return response.content
            else:
                response = self.llm.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Document generation error: {e}")
            return f"Errore nella generazione: {str(e)}"
    
    def analyze_solution(
        self,
        task_title: str,
        task_description: str,
        solution_content: str
    ) -> Dict[str, Any]:
        """
        Analyze a submitted solution for coherence and completeness.
        
        Returns:
            Dict with scores and motivations
        """
        system_prompt = """Sei un esperto revisore di soluzioni per task di progetto.
Valuta la soluzione su due metriche:
1. Coerenza: Quanto è pertinente e allineata con i requisiti (0.0 - 1.0)
2. Completezza: Quanto indirizza tutti gli aspetti del task (0.0 - 1.0)

Rispondi in JSON con: coherence_score, coherence_motivation, completeness_score, completeness_motivation"""

        user_prompt = f"""Titolo Task: {task_title}
Descrizione: {task_description}

Soluzione Proposta:
{solution_content}"""

        return self.generate_structured_output(system_prompt, user_prompt)
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from AI response, handling code blocks."""
        if not content:
            return {"error": "Empty response"}
        
        # Try to extract JSON from code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"error": "Failed to parse JSON response", "raw": content[:500]}


# Global instance
enhanced_ai_service = EnhancedAIService()


# ============================================
# Convenience Functions
# ============================================

def get_ai_service() -> EnhancedAIService:
    """Get the enhanced AI service instance."""
    return enhanced_ai_service


def is_ai_available() -> bool:
    """Check if AI service is available."""
    return enhanced_ai_service.available

