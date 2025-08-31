import os
from openai import OpenAI
from typing import Dict, Any, List, Optional
import logging
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()
logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    OpenRouter LLM integration for property analysis - returns raw strings with complete data
    Now includes chat functionality for follow-up questions
    """
    
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = "qwen/qwen-2.5-72b-instruct"  
    
    @traceable
    def analyze_property_data(
        self, 
        scraped_data: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Analyze property data using LLM - pass ALL data without filtering
        """
        
        logger.info("=== LLM ANALYSIS DEBUG ===")
        logger.info(f"Model: {self.model}")
        logger.info("This version passes COMPLETE DATA to LLM")
        
        prompt = self._create_analysis_prompt(scraped_data, search_results)
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        try:
            logger.info("Sending request to LLM...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a real estate analysis expert specializing in Los Angeles properties. 
Analyze the complete property data provided and generate comprehensive insights.
Focus on specific zoning details, development opportunities, regulatory requirements,
and actionable recommendations based on the actual data provided."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            logger.info("LLM response received!")
            raw_response = response.choices[0].message.content
            logger.info(f"Raw LLM response length: {len(raw_response)}")
            logger.info(f"Raw LLM response preview: {raw_response[:200]}...")
            
            return raw_response
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return f"LLM Analysis Error: {str(e)}"
    
    def process_chat_message(
        self,
        message: str,
        analysis_context: Optional[str] = None,
        address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Process a follow-up question about a property analysis using the same LLM.
        """
        try:
            logger.info(f"Processing chat message for session {session_id or 'unknown'}: {message[:100]}...")
            
            prompt = self._create_chat_prompt(message, analysis_context, address)
            logger.info(f"Chat prompt length: {len(prompt)} characters")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional real estate analysis assistant specializing in Los Angeles properties. 
You help users understand property analysis results by answering follow-up questions in a clear, 
professional manner. Focus on providing specific, actionable insights based on the analysis data provided.
Answer briefly and professionally. Limit to 50-800 words."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3, 
                max_tokens=1000
            )
            
            chat_response = response.choices[0].message.content
            logger.info(f"Chat LLM response generated for session {session_id or 'unknown'}")
            logger.info(f"Chat response length: {len(chat_response)}")
            
            return chat_response
            
        except Exception as e:
            logger.error(f"Chat message processing failed: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties processing your question. Please try again."
    
    def _create_chat_prompt(self, message: str, context: Optional[str], address: Optional[str]) -> str:
        """Create optimized prompt for chat interactions."""
        
        prompt_parts = []
        prompt_parts.append(f"User's question: {message}")
        
        if address:
            prompt_parts.append(f"Property address: {address}")
        
        if context and context.strip():
            prompt_parts.append(f"""
Previous property analysis:
{context}

Please answer the user's question based on this analysis. Be specific and reference relevant details from the analysis data.""")
        else:
            prompt_parts.append("""
No previous analysis context is available. Please inform the user that they need to complete a property analysis first to get specific insights about a property.""")
        
        prompt_parts.append("""
Guidelines for your response:
- Be professional and helpful
- Use specific details from the analysis when available
- If you cannot answer based on the provided information, be honest about limitations
- Keep responses focused and relevant to real estate analysis
- Format your response in clear, readable paragraphs
- Provide actionable insights when possible""")
        
        return "\n".join(prompt_parts)
    
    @traceable
    def _create_analysis_prompt(
        self,
        scraped_data: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> str:
        """Create prompt for full property analysis with all sections and full content."""
        
        scraped_summary = self._pass_complete_scraped_data(scraped_data)
        search_summary = self._pass_complete_search_results(search_results)
        
        prompt = f"""
Analyze this Los Angeles property using ALL available data below. Provide a complete and structured property analysis including all sections.

{scraped_summary}

{search_summary}

Instructions:
- Use all data provided; do NOT assume or generalize.
- If the data has an all_extracted_fields field, it will refer to all of its data and bring it into the relevant categories!!
- You will add information from all existing fields in the prompt and all their content!!!
- Do NOT include any fields where the value is exactly "View" (these indicate files or links that should be ignored).
- Include all of the following sections explicitly in your response:
  1. Property Identification
  2. Location Details
  3. Zoning Information
  4. Planning & Development Opportunities
  5. Permits & Compliance
  6. Transit & Location Advantages
  7. Historic Preservation Requirements
  8. Market Context
  9. Investment and Actionable Insights
- Ensure each section is clearly labeled.
- Include any relevant details from raw text and web search results.
- Maintain professional, readable formatting.
- Base all insights strictly on the data provided.
"""
        return prompt
    
    def _pass_complete_scraped_data(self, scraped_data: Dict[str, Any], chunk_size: int = 2000) -> str:
        """Pass all scraped ZIMAS data directly to LLM in full, split into chunks."""
        if not scraped_data:
            return "No ZIMAS data available"
        
        output = ["COMPLETE ZIMAS PROPERTY DATA"]
        output.append(f"ZIMAS Search: {'SUCCESSFUL' if scraped_data.get('search_successful') else 'FAILED'}")
        
        property_data = scraped_data.get('property_data', {})
        structured_data = property_data.get('structured_data', {})
        all_fields = structured_data.get('all_extracted_fields', {})
        
        if all_fields:
            output.append(f"ALL EXTRACTED PROPERTY FIELDS ({len(all_fields)} total):")
            for key, value in all_fields.items():
                output.append(f"{key}: {value}")
        
        all_tables = property_data.get('all_tables', [])
        if all_tables:
            output.append(f"ALL TABLE DATA ({len(all_tables)} tables):")
            for i, table in enumerate(all_tables):
                output.append(f"Table {i+1}: {table.get('name', 'Unnamed')}")
                data_dict = table.get('data_dict', {})
                if data_dict:
                    for key, value in data_dict.items():
                        output.append(f"{key}: {value}")
                rows = table.get('rows', [])
                if rows and not data_dict:
                    for row in rows:
                        if row and any(str(cell).strip() for cell in row):
                            output.append(" | ".join(str(cell) for cell in row))
        
        sections = ['property_identification', 'location_details', 
                    'zoning_information', 'planning_details', 'permits_compliance']
        for section in sections:
            section_data = structured_data.get(section, {})
            if section_data:
                output.append(f"{section.upper()}:")
                for key, value in section_data.items():
                    output.append(f"{key}: {value}")
        
        raw_text = property_data.get('raw_text', '')
        if raw_text:
            output.append("RAW PAGE TEXT:")
            for i in range(0, len(raw_text), chunk_size):
                output.append(raw_text[i:i+chunk_size])
        
        return '\n'.join(output)
    
    def _pass_complete_search_results(self, search_results: List[Dict[str, Any]], chunk_size: int = 1000) -> str:
        """Pass all web search results directly to LLM in full, split into chunks."""
        if not search_results:
            return "NO WEB SEARCH RESULTS AVAILABLE"
        
        output = [f"COMPLETE WEB SEARCH RESULTS ({len(search_results)} results)"]
        
        for i, result in enumerate(search_results):
            output.append(f"RESULT {i+1}:")
            title = result.get('title', 'No title')
            url = result.get('url', 'No URL')
            score = result.get('score', 'No score')
            content = result.get('content', '')
            
            output.append(f"Title: {title}")
            output.append(f"URL: {url}")
            output.append(f"Relevance Score: {score}")
            
            if content:
                output.append("Content:")
                for j in range(0, len(content), chunk_size):
                    output.append(content[j:j+chunk_size])
        
        return '\n'.join(output)