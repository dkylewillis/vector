
import warnings
import numpy as np
from typing import List, Dict, Any, Optional
from ..ai_models import AIModelFactory
from config import config
from ..data_pipeline.vector_database import VectorDatabase
from ..data_pipeline.embedder import Embedder
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)))))

load_dotenv()


warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="torch.nn.modules.module")


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
        embedder_model = embedder_model or self.config.get(
            'embedder.model_name', 'all-MiniLM-L6-v2')
        collection_name = collection_name or self.config.get(
            'vector_database.collection_name', 'documents')

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
            "You are a professional civil engineering assistant specialized "
            "in land development and site design. Your job is to extract and "
            "provide accurate, relevant information from the given context "
            "based on the user's prompt."
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

    def build_context_prompt(
            self, prompt: str,
            context: Optional[List[Dict[str, Any]]] = None) -> str:
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

    def ask(self, user_prompt: str, use_context: bool = True,
            max_tokens: Optional[int] = None) -> str:
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
            "of key terms and related concepts that are likely to appear "
            "in regulatory or ordinance text."
        )

        context_search_prompt = self.ai_model_instance.generate_response(
            user_prompt, preprocess_prompt, 512)

        if use_context:
            # Get relevant context from vector search
            context = self.search(context_search_prompt, top_k=20, score_threshold=0.5)
            enhanced_prompt = self.build_context_prompt(user_prompt, context)
        else:
            enhanced_prompt = user_prompt

        # Get system prompt from configuration
        system_prompt = self._get_system_prompt("default")

        return self.ai_model_instance.generate_response(
            enhanced_prompt, system_prompt, max_tokens=max_tokens)

    def research(self, topic: str = None, depth: str = "medium",
                 additional_questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate civil engineering due diligence report from topics.yaml.
        
        Args:
            topic: Specific topic to research (if None, researches all topics)
            depth: Research depth - affects detail level
            additional_questions: Optional additional questions

        Returns:
            Dictionary with findings and markdown report
        """
        # Load topics configuration
        topics = self._load_topics_config()
        if not topics:
            print("❌ Could not load topics configuration")
            return {}

        # Filter to specific topic if requested
        if topic:
            topic_key = self._find_matching_topic_key(topic, topics)
            if topic_key:
                topics = {topic_key: topics[topic_key]}
                print(f"🔬 Researching: {topic_key.replace('_', ' ')}")
            else:
                print(f"❌ Topic '{topic}' not found in topics.yaml")
                return {}
        else:
            print("🔬 Generating comprehensive due diligence report")

        # Research all topics
        print(f"📋 Processing {self._count_total_queries(topics)} research items...")
        findings = {}
        
        for topic_name, content in topics.items():
            print(f"\n🏗️ {topic_name.replace('_', ' ').title()}")
            topic_findings = self._research_topic(topic_name, content)
            findings[topic_name] = topic_findings

        # Add additional questions if provided
        if additional_questions:
            print(f"\n🔍 Additional Questions")
            additional_findings = {}
            for question in additional_questions:
                print(f"   • {question[:60]}...")
                answer = self._research_single_item(question)
                additional_findings[question] = answer
            findings['Additional_Questions'] = additional_findings

        # Generate markdown report
        print("\n📊 Compiling due diligence report...")
        markdown_report = self._create_markdown_report(findings, topic)
        
        # Save the report to file
        report_file_path = self._save_markdown_report(markdown_report, topic)
        
        return {
            "topics_researched": list(topics.keys()),
            "total_items": self._count_total_queries(topics),
            "findings": findings,
            "markdown_report": markdown_report,
            "report_file_path": report_file_path,
            "report_type": "civil_engineering_due_diligence"
        }

    def _load_research_config(self) -> Dict[str, Any]:
        """Load research configuration from yaml file."""
        import yaml
        from pathlib import Path

        try:
            config_path = Path(__file__).parent.parent.parent / \
                "config" / "research.yaml"
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            print(f"⚠️  Could not load research config: {e}")
            return {}

    def _load_topics_config(self) -> Dict[str, Any]:
        """Load topics configuration from topics.yaml file."""
        import yaml
        from pathlib import Path

        try:
            config_path = Path(__file__).parent.parent.parent / \
                "config" / "topics.yaml"
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            print(f"⚠️  Could not load topics config: {e}")
            return {}

    def _find_matching_topic_key(self, topic: str, topics_data: Dict[str, Any]) -> str:
        """Find matching topic key in topics_data for a given topic string."""
        topic_lower = topic.lower().replace(' ', '_')
        
        # Direct match
        for key in topics_data.keys():
            if key.lower() == topic_lower:
                return key
        
        # Partial match
        for key in topics_data.keys():
            if topic_lower in key.lower() or key.lower() in topic_lower:
                return key
        
        return None

    def _count_total_queries(self, topics_data: Dict[str, Any]) -> int:
        """Count total number of queries that will be processed."""
        total = 0
        for topic_content in topics_data.values():
            total += self._count_queries_in_structure(topic_content)
        return total

    def _count_queries_in_structure(self, structure) -> int:
        """Recursively count queries in a topic structure."""
        if isinstance(structure, list):
            return len(structure)
        elif isinstance(structure, dict):
            total = 0
            for value in structure.values():
                total += self._count_queries_in_structure(value)
            return total
        else:
            return 1  # Single item

    def _research_topic(self, topic_name: str, content) -> Dict[str, Any]:
        """Research a topic and all its subtopics."""
        findings = {}
        
        if isinstance(content, list):
            # Simple list of items to research
            for item in content:
                if isinstance(item, dict):
                    # Handle nested dictionaries within lists
                    for sub_key, sub_value in item.items():
                        print(f"   📂 {sub_key.replace('_', ' ')}")
                        findings[sub_key] = self._research_topic(f"{topic_name}_{sub_key}", sub_value)
                else:
                    # Handle simple string items
                    print(f"   • {item}")
                    findings[item] = self._research_single_item(f"{topic_name.replace('_', ' ')}: {item}")
                
        elif isinstance(content, dict):
            # Nested structure with subcategories
            for subcat_name, subcat_content in content.items():
                print(f"   📂 {subcat_name.replace('_', ' ')}")
                findings[subcat_name] = self._research_topic(f"{topic_name}_{subcat_name}", subcat_content)
        
        return findings

    def _research_single_item(self, query: str) -> str:
        """Research a single item with vector database context."""
        # Search for relevant context
        context_docs = self.search(query, top_k=10, score_threshold=0.4)
        
        if not context_docs:
            return "No relevant information found in the knowledge base."
        
        # Build context for AI
        context_text = "Based on the following regulatory documents:\n\n"
        for i, doc in enumerate(context_docs[:5], 1):  # Limit to top 5 for clarity
            content = doc.get('text', '')[:300]  # Limit content length
            filename = doc['metadata'].get('filename', 'Unknown')
            context_text += f"**Source {i}** ({filename}):\n{content}...\n\n"
        
        # Create focused prompt for civil engineering due diligence
        enhanced_query = f"""
        {context_text}
        
        Provide specific regulatory requirements and compliance information for: {query}
        
        Focus on:
        - Specific standards, dimensions, or requirements
        - Compliance procedures or approval processes
        - Key considerations for land development projects
        - Any exceptions or special conditions
        
        Keep the response concise but comprehensive for due diligence purposes.
        """
        
        system_prompt = (
            "You are a civil engineering consultant providing regulatory compliance "
            "information for land development due diligence. Extract specific, "
            "actionable requirements from the provided context."
        )
        
        return self.ai_model_instance.generate_response(
            enhanced_query, system_prompt, max_tokens=500)

    def _create_markdown_report(self, findings: Dict[str, Any], focus_topic: str = None) -> str:
        """Generate a professional markdown report for civil engineering due diligence."""
        from datetime import datetime
        
        # Report header
        title = f"Land Development Due Diligence Report"
        if focus_topic:
            title += f": {focus_topic.replace('_', ' ').title()}"
        
        report = f"""# {title}

**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  
**Purpose:** Civil Engineering Due Diligence Analysis  
**Source:** Regulatory document analysis via RegScout  

---

## Executive Summary

This report provides a comprehensive analysis of regulatory requirements for land development projects based on current ordinances and regulations. Each section below outlines specific compliance requirements, standards, and procedures that must be considered during project planning and design.

---

"""
        
        # Process each topic
        for topic_name, topic_findings in findings.items():
            # Format topic header
            topic_title = topic_name.replace('_', ' ').title()
            report += f"## {topic_title}\n\n"
            
            # Add topic content
            report += self._format_findings_to_markdown(topic_findings, level=3)
            report += "\n---\n\n"
        
        # Add footer
        report += f"""## Important Notes

- **Verification Required:** All requirements should be verified with current local ordinances
- **Professional Review:** Consult with local authorities and qualified professionals
- **Updates:** Regulations may change; ensure compliance with most current versions
- **Site-Specific:** Additional requirements may apply based on specific site conditions

---

*This report was generated using RegScout document analysis. Please verify all requirements with current local regulations and consult qualified professionals for site-specific guidance.*
"""
        
        return report

    def _save_markdown_report(self, markdown_content: str, focus_topic: str = None) -> str:
        """Save the markdown report to a file and return the file path."""
        from datetime import datetime
        from pathlib import Path
        
        # Create reports directory if it doesn't exist
        reports_dir = Path(__file__).parent.parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if focus_topic:
            filename = f"due_diligence_{focus_topic.lower().replace(' ', '_')}_{timestamp}.md"
        else:
            filename = f"due_diligence_comprehensive_{timestamp}.md"
        
        file_path = reports_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"📄 Report saved: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"⚠️  Error saving report: {e}")
            return ""

    def _format_findings_to_markdown(self, findings, level: int = 3) -> str:
        """Convert findings to markdown format."""
        markdown = ""
        header_prefix = "#" * level
        
        if isinstance(findings, dict):
            for key, value in findings.items():
                # Create section header
                section_title = key.replace('_', ' ').title()
                markdown += f"{header_prefix} {section_title}\n\n"
                
                if isinstance(value, str):
                    # Clean up the response and format it
                    cleaned_value = value.strip()
                    if cleaned_value and cleaned_value != "No relevant information found in the knowledge base.":
                        # Split into paragraphs for better readability
                        paragraphs = [p.strip() for p in cleaned_value.split('\n') if p.strip()]
                        for para in paragraphs:
                            if para.startswith('•') or para.startswith('-'):
                                markdown += f"{para}\n"
                            else:
                                markdown += f"{para}\n\n"
                    else:
                        markdown += "*No specific requirements found in available documents.*\n\n"
                else:
                    markdown += self._format_findings_to_markdown(value, level + 1)
                    
        elif isinstance(findings, list):
            for item in findings:
                markdown += f"- {item}\n"
            markdown += "\n"
        else:
            markdown += f"{findings}\n\n"
        
        return markdown

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
