import json
from openai import OpenAI

class AutoTagger:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.tag_structure = {
            "Action": ["Lecture", "Assignment", "Reading", "Exercise", "Quiz", "Lab", "Project", "Discussion", "Demonstration"],
            "Relationships": ["Student-Led", "Group Work", "Prerequisite", "Follow-up", "Reference", "Supplemental", "Core", "Optional", "Collaborative"],
            "Discipline": ["Mathematics", "Biology", "Chemistry", "Physics", "Computer Science", "Literature", "History", "Psychology", "Economics", "Art", "Music"],
            "Purpose": ["Conceptual Understanding", "Skill Building", "Assessment", "Critical Thinking", "Application", "Review", "Introduction", "Analysis", "Synthesis"]
        }
        
    def tag_document(self, document_text, filename):
        """Automatically tag document using GPT"""
        # Extract a representative sample to save tokens
        sample = self._extract_sample(document_text)
        
        # Create prompt for GPT
        prompt = self._create_tagging_prompt(sample, filename)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use 3.5 for cost efficiency
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Analyze this document and assign tags:\n\nFilename: {filename}\n\nContent sample: {sample}"}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            tags = json.loads(response.choices[0].message.content)
            return self._validate_tags(tags)
            
        except Exception as e:
            print(f"Error in auto-tagging: {e}")
            return self._generate_fallback_tags(filename)
    
    def _extract_sample(self, text, max_length=2000):
        """Extract a representative sample from the document"""
        if len(text) <= max_length:
            return text
            
        # Take beginning, middle and end
        third = max_length // 3
        beginning = text[:third]
        middle_start = len(text) // 2 - third // 2
        middle = text[middle_start:middle_start + third]
        end = text[-third:]
        
        return f"{beginning}\n\n[...]\n\n{middle}\n\n[...]\n\n{end}"
    
    def _create_tagging_prompt(self, sample, filename):
        """Create a prompt for the tagging model"""
        return f"""You are an expert educational content classifier. Your task is to analyze educational content and assign the most appropriate tags from each category.

Please assign tags for this document from these four categories:

{json.dumps(self.tag_structure, indent=2)}

Analyze the document and return ONLY a JSON object with these four categories as keys, and arrays of applicable tags as values.
Choose 1-3 most appropriate tags for each category.
Do not invent new tags - only use tags from the provided categories.
"""
    
    def _validate_tags(self, tags):
        """Ensure all tags are valid according to our structure"""
        validated = {}
        
        for category, values in self.tag_structure.items():
            if category in tags and isinstance(tags[category], list):
                # Only keep valid tags that are in our structure
                valid_tags = [tag for tag in tags[category] if tag in values]
                if valid_tags:
                    validated[category] = valid_tags
                else:
                    # Fallback if no valid tags found
                    validated[category] = [values[0]]
            else:
                # Default tag if category is missing
                validated[category] = [values[0]]
                
        return validated
    
    def _generate_fallback_tags(self, filename):
        """Generate basic tags based on filename if tagging fails"""
        return {category: [values[0]] for category, values in self.tag_structure.items()} 