#!/usr/bin/env python3
"""
JFK Files Custom GPT Configuration

This module defines the configuration for the JFK Files Custom GPT, including:
- GPT name and description
- System message
- Conversation starters
- Capabilities configuration

This configuration is used when uploading the GPT to the OpenAI platform.
"""

import json
import os
import datetime

class GPTConfig:
    """Configuration manager for the JFK Files Custom GPT."""
    
    def __init__(self):
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Basic GPT information
        self.name = "JFK Files Archivist"
        self.description = (
            "A specialized GPT for exploring and analyzing declassified documents "
            "from the JFK Assassination Records Collection. Access over 1,100 documents "
            "from the National Archives and receive expert assistance with historical context, "
            "document analysis, and connections between files."
        )
        
        # System message that defines the GPT's behavior
        self.system_message = """
You are the JFK Files Archivist, an expert on the JFK Assassination Records Collection declassified by the National Archives.

Your knowledge encompasses over 1,100 documents from this collection, allowing you to:
1. Retrieve specific documents by their record ID (e.g., "104-10004-10143")
2. Search for information across all documents on specific topics, people, or events
3. Provide historical context for documents and their significance
4. Analyze connections between different documents
5. Explain terminology, abbreviations, and agency names found in the documents

When responding to queries:
- Provide accurate, factual information based solely on the JFK Files in your knowledge base
- Clearly distinguish between what is directly stated in the documents and any necessary context you provide
- Include document references (IDs) when quoting or summarizing specific documents
- Use neutral, archival language and avoid speculative or conspiratorial interpretations
- When discussing sensitive historical topics, maintain an objective, scholarly tone
- If asked about information not contained in your knowledge base, clearly state that limitation

For document retrieval requests:
- Respond with document metadata and a detailed summary of the content
- Include key information such as document date, agencies involved, and subjects discussed
- Format important quotes verbatim with proper citation

For analytical questions:
- Provide comprehensive analysis based solely on document content
- Organize information logically with appropriate headings and structure
- Include relevant document IDs to support your analysis
"""

        # Conversation starters for the GPT interface
        self.conversation_starters = [
            # Document-specific queries
            "What information do you have on document 104-10004-10143?",
            "Show me the contents of record 104-10003-10041",
            "Summarize the key points from document 104-10009-10222",
            
            # Topic-based queries
            "Tell me about Lee Harvey Oswald's connections to the Soviet Union based on the files",
            "What do these documents reveal about Jack Ruby?",
            "What information exists about the CIA's involvement in the investigation?",
            "Show me documents related to the Warren Commission's findings",
            "What was the FBI's role according to these documents?",
            
            # Comparative analysis
            "What documents mention both the CIA and FBI?",
            "Compare what different documents say about the Dallas Police Department's actions",
            "Find connections between Oswald and Cuba in these files",
            
            # Historical context
            "Explain the significance of the 'Mexico City' documents in the collection",
            "How did Cold War tensions appear in these documents?",
            "What was the timeline of events according to these records?",
            
            # Documentary evidence
            "What physical evidence is mentioned in these files?",
            "Show me documents that discuss the rifle used in the assassination",
            "Are there any documents about the autopsy findings?",
            
            # General exploration
            "What are the most significant documents in this collection?",
            "Which documents contain surprising or contradictory information?",
            "Help me understand the structure and organization of the JFK files"
        ]
        
        # Capabilities configuration (features to enable)
        self.capabilities = {
            "web_browsing": True,  # Allow web search for supplementary information
            "image_input": True,   # Allow users to upload images of documents
            "code_interpreter": False,
            "file_upload": True,   # Allow users to upload related files
            "plugins": []
        }
    
    def save_config(self, output_path="lite_llm/gpt_configuration.json"):
        """Save the GPT configuration to a JSON file."""
        config_data = {
            "timestamp": self.timestamp,
            "gpt_name": self.name,
            "gpt_description": self.description,
            "system_message": self.system_message.strip(),
            "conversation_starters": self.conversation_starters,
            "capabilities": self.capabilities
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        return output_path

    def get_config_summary(self):
        """Return a summary of the GPT configuration."""
        return f"""
GPT Configuration Summary:
--------------------------
Name: {self.name}
Created: {self.timestamp}

Description: 
{self.description}

Conversation Starters: {len(self.conversation_starters)} defined
System Message: {len(self.system_message.strip())} characters
Capabilities: {', '.join([k for k, v in self.capabilities.items() if v])}
"""


if __name__ == "__main__":
    # Create and save the GPT configuration
    config = GPTConfig()
    output_file = config.save_config()
    print(f"GPT configuration saved to: {output_file}")
    print(config.get_config_summary())
