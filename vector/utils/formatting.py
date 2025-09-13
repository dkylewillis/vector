"""Formatting utilities for Vector."""

from typing import List, Dict, Any

from ..interfaces import SearchResult, ResultFormatter


class CLIFormatter(ResultFormatter):
    """Formatter for CLI output."""

    def format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results for CLI display."""
        if not results:
            return "No results found."

        formatted = ["🔍 Search Results:\n"]
        for i, result in enumerate(results, 1):
            formatted.append(f"Result {i} (Score: {result.score:.3f})")
            formatted.append(f"📄 {result.filename}")
            formatted.append(f"📂 Source: {result.source}")
            formatted.append(f"📁 Filename: {result.filename}")
            formatted.append(f"📝 Content: {result.text[:200]}...")
            
            if result.chunk_info:
                formatted.append(f"🔢 {result.chunk_info}")
            formatted.append("-" * 50)

        return "\n".join(formatted)

    def format_info(self, info: Dict[str, Any]) -> str:
        """Format collection info for CLI display."""
        if not info:
            return "No information available."

        formatted = [
            f"📊 Collection: {info.get('name', 'Unknown')}",
            f"📈 Status: {info.get('status', 'Unknown')}",
            f"📄 Documents: {info.get('points_count', 0):,}",
            f"🔢 Vectors: {info.get('vectors_count', 0):,}",
            "",
            "⚙️ Configuration:",
            f"  • Distance: {info.get('config', {}).get('distance', 'Unknown')}",
            f"  • Vector Size: {info.get('config', {}).get('size', 'Unknown')}"
        ]
        return "\n".join(formatted)

    def format_metadata_summary(self, summary: Dict[str, Any]) -> str:
        """Format metadata summary for CLI display."""
        if not summary:
            return "No metadata available."

        formatted = [
            f"📋 Metadata Summary (Total: {summary.get('total_documents', 0)} documents)\n"
        ]

        # Files
        filenames = summary.get('filenames', [])
        if filenames:
            formatted.append("📁 Files:")
            for filename in filenames:
                formatted.append(f"  • {filename}")
            formatted.append("")

        # Sources
        sources = summary.get('sources', [])
        if sources:
            formatted.append("📂 Sources:")
            for source in sources:
                formatted.append(f"  • {source}")
            formatted.append("")

        # Headings
        headings = summary.get('headings', [])
        if headings:
            formatted.append("📋 Headings:")
            for heading in headings[:20]:  # Limit to first 20 headings
                formatted.append(f"  • {heading}")
            if len(headings) > 20:
                formatted.append(f"  ... and {len(headings) - 20} more")

        return "\n".join(formatted)

    def format_collections_list(self, client) -> str:
        """Format list of collections."""
        try:
            collections = client.get_collections().collections
            if not collections:
                return "No collections found."

            formatted = ["📚 Available Collections:\n"]
            for collection in collections:
                info = client.get_collection(collection.name)
                count = info.points_count or 0
                formatted.append(f"• {collection.name} ({count:,} documents)")

            return "\n".join(formatted)
        except Exception as e:
            return f"❌ Error listing collections: {e}"
