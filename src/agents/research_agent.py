
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from data_pipeline.embedder import Embedder
from data_pipeline.vector_database import VectorDatabase
from config import config
from ai_models import AIModelFactory
from typing import List, Dict, Any, Optional
import numpy as np

SYSTEM_PROMPT = (
    "You are a professional civil engineering assistant specialized in land development and site design. "
    "Your job is to extract and provide accurate, relevant information from the given context based on the user's prompt.\n\n"
    "The context may include civil engineering documents, design standards, ordinances, grading plans, hydrology reports, or utility layout descriptions. You must:\n\n"
    "• Identify the most relevant parts of the context to answer the user’s question.\n"
    "• Include all dimensions, units, and specific details from the context.\n"
    "• Use terminology consistent with industry practices (e.g., grading, drainage, erosion control, easements, impervious cover, detention basins).\n"
    "• If the question is about regulations, refer only to content in the provided context (e.g., local ordinance excerpts).\n"
    "• If no relevant information is found in the context, state that clearly instead of guessing.\n"
    "• Avoid generic responses—prioritize specificity based on context.\n"
    "• Always respond in a clear, concise, and technically accurate manner, as if advising a licensed civil engineer or reviewing engineer."
    "• Always include the headings of the document you are referencing.\n\n"
)


class ResearchAgent:
    """
    ResearchAgent handles all search processing, research tasks, and AI interactions.
    It directly uses the vector database and AI models without unnecessary abstractions.
    """

    def __init__(self, 
                 ai_model: Optional[str] = None,
                 embedder_model: Optional[str] = None,
                 collection_name: Optional[str] = None):
        """
        Initialize the research agent with embedder, vector database, and AI model.
        
        Args:
            ai_model: Name of the AI model (defaults to config)
            embedder_model: Name of the sentence transformer model (defaults to config)
            collection_name: Name of the vector collection (defaults to config)
        """  # Load configuration
        self.config = config
        
        # Set defaults from config if not provided
        embedder_model = embedder_model or self.config.get('embedder.model_name', 'all-MiniLM-L6-v2')
        collection_name = collection_name or self.config.get('vector_database.collection_name', 'documents')
        
        # Initialize components
        self.embedder = Embedder(model_name=embedder_model)
        self.vector_db = VectorDatabase(collection_name=collection_name)
        self.collection_name = collection_name
        
        # Initialize AI model through factory
        ai_config = self.config.get_section('ai_model')
        model_type = ai_config.get('provider', 'openai')
        ai_model_name = ai_config.get('name', 'gpt-3.5-turbo')
        
        self.ai_model_instance = AIModelFactory.create_model(
            model_type=model_type,
            model_name=ai_model_name,
            **ai_config
        )
    
    def setup_collection(self):
        """
        Setup the vector database collection with appropriate dimensions.
        """
        vector_size = self.embedder.get_embedding_dimension()
        self.vector_db.create_collection(vector_size=vector_size)
        return vector_size

    def search(self, 
               question: str, 
               top_k: int = 5, 
               score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on search term.
        
        Args:
            question: The question or search text
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with scores and metadata
        """
        # Generate embedding for the query
        query_embedding = self.embedder.embed_text(question)
        
        # Search vector database
        results = self.vector_db.search(
            query_embedding=query_embedding[0],
            top_k=top_k,
            score_threshold=score_threshold
        )
        
        return results

    def build_context_prompt(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Build a context-aware prompt by combining the user prompt with relevant document context.
        
        Args:
            prompt: The user's question or prompt
            context: List of relevant documents with content and metadata
            
        Returns:
            Enhanced prompt with context
        """
        if not context:
            return prompt
        
        context_text = "\n\n--- RELEVANT DOCUMENTS ---\n"
        for i, doc in enumerate(context, 1):
            content = doc.get('content', doc.get('text', ''))
            metadata = doc.get('metadata', {})
            headings = metadata.get('headings', [])

            context_text += f"\n[Headings: {' > '.join(headings)}]\n{content}\n"

        context_text += "\n--- END DOCUMENTS ---\n\n"
        
        return f"{context_text}\n Based on the above documents, please answer: {prompt}"

    def ask(self, user_prompt: str, use_context: bool = True, max_tokens: Optional[int] = None) -> str:
        """
        Ask a question using AI model with optional context from the knowledge base.

        Args:
            prompt: The question to ask
            use_context: Whether to include relevant documents as context

        Returns:
            AI-generated response
        """
        preprocess_prompt = (
            "Given a user question, rephrase or expand it into a list "
            "of key terms and related concepts that are likely to appear in regulatory or ordinance text."
        )

        context_search_prompt = self.ai_model_instance.generate_response(user_prompt, preprocess_prompt, 512)
        
        if use_context:
            # Get relevant context from vector search
            context = self.search(context_search_prompt, top_k=20, score_threshold=0.5)
            enhanced_prompt = self.build_context_prompt(user_prompt, context)
        else:
            enhanced_prompt = user_prompt

        return self.ai_model_instance.generate_response(enhanced_prompt, SYSTEM_PROMPT, max_tokens=max_tokens)

    def research(self, topic: str) -> Dict[str, Any]:
        """
        Comprehensive research on a topic.
        
        Args:
            topic: The topic to research
            
        Returns:
            Dictionary with research findings
        """
        results = self.search(topic, top_k=10)
        
        if not results:
            return {"topic": topic, "findings": "No relevant information found"}
        
        # Generate comprehensive response
        summary = self.ai_model_instance.generate_response(
            f"Provide a comprehensive summary about: {topic}", 
            results
        )
        
        return {
            "topic": topic,
            "summary": summary,
            "source_documents": len(results),
            "key_findings": results[:3]  # Top 3 most relevant
        }

    def summarize(self, documents: List[Dict[str, Any]]) -> str:
        """
        Summarize the provided documents using AI.
        
        Args:
            documents: List of documents to summarize
            
        Returns:
            Summary of the documents
        """
        if not documents:
            return "No documents to summarize"
        
        return self.ai_model_instance.generate_response(
            "Summarize the following documents:",
            documents
        )

    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the knowledge base.
        
        Returns:
            Dictionary with collection information
        """
        collection_info = self.vector_db.get_collection_info()
        embedding_dim = self.embedder.get_embedding_dimension()
        
        return {
            "collection_name": self.collection_name,
            "embedding_model": self.embedder.model_name,
            "embedding_dimension": embedding_dim,
            "collection_info": collection_info
        }