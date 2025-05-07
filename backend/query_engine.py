from openai import OpenAI

class QueryEngine:
    def __init__(self, vector_store, openai_api_key):
        self.vector_store = vector_store
        self.openai_client = OpenAI(api_key=openai_api_key)
        
    def process_query(self, query, filters=None, top_k=20):
        """Process a query using RAG"""
        # Retrieve relevant chunks
        results = self.vector_store.search(query, filters, top_k)
        
        if not results:
            return {
                "relevant_chunks": [],
                "suggestions": "No relevant content found for this query."
            }
            
        # Format chunks for GPT
        formatted_chunks = self._format_chunks_for_gpt(results)
        
        # Generate response using GPT
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": f"Query: {query}\n\nRelevant Materials:\n{formatted_chunks}"}
            ]
        )
        
        suggestions = response.choices[0].message.content
        
        # Format the response
        return {
            "query": query,
            "suggestions": suggestions,
            "relevant_chunks": [
                {
                    "text": self._get_chunk_preview(match.metadata.get("text", ""), query),
                    "source": match.metadata.get("source", "Unknown"),
                    "tags": match.metadata.get("tags", {}),
                    "confidence": match.score
                }
                for match in results
            ]
        }
        
    def _format_chunks_for_gpt(self, results):
        """Format chunks for GPT prompt"""
        formatted = ""
        for i, match in enumerate(results):
            metadata = match.metadata
            formatted += f"CHUNK {i+1} [Source: {metadata.get('source', 'Unknown')}]\n"
            formatted += f"Tags: {metadata.get('tags', {})}\n"
            formatted += f"Text: {metadata.get('text', '')[:500]}...\n\n"
        return formatted
        
    def _create_system_prompt(self):
        """Create system prompt for GPT"""
        return """You are an educational content assistant. Your task is to help professors find relevant materials for their lessons.

Based on the query and the provided chunks of educational content, provide:
1. A summary of the most relevant materials
2. Suggestions for how these materials could be used in a lesson
3. Any connections between materials that might be useful

Focus on being helpful, practical, and specific."""
        
    def _get_chunk_preview(self, text, query, context_size=100):
        """Create a preview of the chunk, focusing on relevant parts"""
        # Simple approach: return the beginning
        return text[:300] + "..." 