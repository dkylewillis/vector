
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

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")

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

    def _get_system_prompt(self, prompt_type: str = "default") -> str:
        """
        Get system prompt from research configuration.
        
        Args:
            prompt_type: Type of prompt to retrieve (default, question_generator, report_compiler)
            
        Returns:
            System prompt string
        """
        research_config = self._load_research_config()
        system_prompts = research_config.get('system_prompts', {})
        
        # Default fallback prompt if not found in config
        default_prompt = (
            "You are a professional civil engineering assistant specialized in land development and site design. "
            "Your job is to extract and provide accurate, relevant information from the given context based on the user's prompt."
        )
        
        return system_prompts.get(prompt_type, default_prompt)

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

        # Get system prompt from configuration
        system_prompt = self._get_system_prompt("default")
        
        return self.ai_model_instance.generate_response(enhanced_prompt, system_prompt, max_tokens=max_tokens)

    def research(self, topic: str, depth: str = "medium", additional_questions: List[str] = None) -> Dict[str, Any]:
        """
        Comprehensive research on a topic using multi-step analysis.
        
        Args:
            topic: The topic to research
            depth: Research depth - "shallow", "medium", "comprehensive"
            additional_questions: Optional list of user-provided questions to include
            
        Returns:
            Dictionary with research findings and report
        """
        print(f"🔬 Starting research on: {topic}")
        
        # Step 1: Generate research questions
        research_questions = self._generate_research_questions(topic, depth)
        
        # Add user-provided questions if any
        if additional_questions:
            research_questions.extend(additional_questions)
            print(f"📝 Generated {len(research_questions) - len(additional_questions)} questions + {len(additional_questions)} user questions")
        else:
            print(f"📝 Generated {len(research_questions)} research questions")
        
        # Step 2: Answer each question using the ask function
        findings = {}
        research_config = self._load_research_config()
        depth_config = research_config.get('research_depths', {}).get(depth, {})
        max_tokens = depth_config.get('max_tokens_per_question', 600)
        
        for i, question in enumerate(research_questions, 1):
            print(f"🔍 Researching question {i}/{len(research_questions)}: {question[:60]}...")
            answer = self.ask(question, use_context=True, max_tokens=max_tokens)
            findings[question] = answer
        
        # Step 3: Generate comprehensive report
        print("📊 Compiling research report...")
        report = self._compile_research_report(topic, research_questions, findings, depth)
        
        # Step 4: Get source documents for reference
        source_docs = self.search(topic, top_k=15, score_threshold=0.3)
        
        return {
            "topic": topic,
            "depth": depth,
            "research_questions": research_questions,
            "findings": findings,
            "report": report,
            "source_documents": len(source_docs),
            "key_sources": [doc['metadata'].get('filename', 'Unknown') for doc in source_docs[:5]]
        }

    def _load_research_config(self) -> Dict[str, Any]:
        """Load research configuration from yaml file."""
        import yaml
        from pathlib import Path
        
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "research.yaml"
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            print(f"⚠️  Could not load research config: {e}")
            return {}

    def _generate_research_questions(self, topic: str, depth: str = "medium") -> List[str]:
        """
        Generate targeted research questions for a given topic.
        
        Args:
            topic: The research topic
            depth: Research depth level
            
        Returns:
            List of research questions
        """
        research_config = self._load_research_config()
        depth_config = research_config.get('research_depths', {}).get(depth, {'question_count': 6})
        num_questions = depth_config.get('question_count', 6)
        
        # Get question templates
        templates = research_config.get('question_templates', {})
        
        # Determine topic category for better templates
        topic_category = self._categorize_topic(topic.lower())
        relevant_templates = templates.get(topic_category, templates.get('general', []))
        
        # Build prompt with templates as examples
        template_examples = "\n".join([f"- {template.format(topic='[TOPIC]')}" for template in relevant_templates[:3]])
        system_prompt = research_config.get('system_prompts', {}).get(
            'question_generator',
            "Generate specific research questions for regulatory and civil engineering topics."
        )

        prompt = (
            f"Generate {num_questions} specific, actionable research questions about \"{topic}\" "
            "for civil engineering and regulatory compliance.\n\n"
            "Examples of good question formats:\n"
            f"{template_examples}"
        )
        
        response = self.ai_model_instance.generate_response(prompt, system_prompt, max_tokens=600)
        
        # Parse questions from response
        questions = self._parse_questions_from_response(response, num_questions)
        
        return questions

    def _categorize_topic(self, topic: str) -> str:
        """Categorize topic to select appropriate question templates."""
        if any(word in topic for word in ['setback', 'height', 'density', 'zoning', 'parking', 'landscape']):
            return 'zoning'
        elif any(word in topic for word in ['drainage', 'stormwater', 'detention', 'pipe', 'erosion']):
            return 'drainage'
        elif any(word in topic for word in ['utility', 'utilities', 'easement', 'cover', 'separation']):
            return 'utilities'
        else:
            return 'general'

    def _parse_questions_from_response(self, response: str, target_count: int) -> List[str]:
        """Parse questions from AI response."""
        questions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Remove numbering and clean up
                question = line.split('.', 1)[-1].split('-', 1)[-1].split('•', 1)[-1].strip()
                if question and ('?' in question or question.endswith('?')):
                    # Ensure question ends with ?
                    if not question.endswith('?'):
                        question = question.split('?')[0] + '?'
                    questions.append(question)
        
        return questions[:target_count]

    def _compile_research_report(self, topic: str, questions: List[str], findings: Dict[str, str], depth: str) -> str:
        """
        Compile research findings into a comprehensive report.
        
        Args:
            topic: Research topic
            questions: List of research questions
            findings: Dictionary mapping questions to answers
            depth: Research depth level
            
        Returns:
            Formatted research report
        """
        research_config = self._load_research_config()
        depth_config = research_config.get('research_depths', {}).get(depth, {})
        max_tokens = depth_config.get('report_max_tokens', 1500)
        
        system_prompt = research_config.get('system_prompts', {}).get('report_compiler',
            "Create comprehensive technical reports for civil engineering professionals.")
        
        report_prompt = (
            f'Based on the research findings below, create a comprehensive report about "{topic}".\n\n'
            "Research Findings:\n"
            f"{self._format_findings_for_report(questions, findings)}"
        )
        
        return self.ai_model_instance.generate_response(report_prompt, system_prompt, max_tokens=max_tokens)

    def _format_findings_for_report(self, questions: List[str], findings: Dict[str, str]) -> str:
        """Format research findings for report generation."""
        formatted = ""
        for i, question in enumerate(questions, 1):
            answer = findings.get(question, "No answer found")
            formatted += f"\nQ{i}: {question}\nA{i}: {answer}\n{'-'*50}\n"
        return formatted

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