import os
from openai import OpenAI
from typing import Dict, Any, List
import logging
from dotenv import load_dotenv
from langsmith import traceable
import json

load_dotenv()
logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    OpenRouter LLM integration for property analysis - returns raw strings with complete data
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
    
    @traceable
    def _create_analysis_prompt(
        self,
        scraped_data: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> str:
        """Create prompt with complete raw data - no filtering or summarization"""
        
        scraped_summary = self._pass_complete_scraped_data(scraped_data)
        search_summary = self._pass_complete_search_results(search_results)
        
        prompt = f"""
        Analyze this Los Angeles property using ALL the available data below.
        Extract and synthesize insights from the complete dataset provided.
        
        {scraped_summary}
        
        {search_summary}
        
        Provide a comprehensive property analysis using ALL relevant information from both sources.
        Focus on:
        - Specific zoning requirements and implications
        - Development opportunities and constraints
        - Transit and location advantages
        - Historic preservation requirements
        - Market context from web sources
        - Actionable investment insights
        
        Use the actual data values provided rather than general assumptions.
        """
        
        return prompt
    
    def _pass_complete_scraped_data(self, scraped_data: Dict[str, Any]) -> str:
        """Pass ALL scraped ZIMAS data directly to LLM without filtering"""
        if not scraped_data:
            return "No ZIMAS data available"
        
        try:
            # Include the complete property data structure
            output = ["=== COMPLETE ZIMAS PROPERTY DATA ==="]
            
            if scraped_data.get('search_successful'):
                output.append("✓ ZIMAS Search: SUCCESSFUL")
            else:
                output.append("✗ ZIMAS Search: FAILED")
                
            property_data = scraped_data.get('property_data', {})
            
            structured_data = property_data.get('structured_data', {})
            all_fields = structured_data.get('all_extracted_fields', {})
            
            if all_fields:
                output.append(f"\n--- ALL EXTRACTED PROPERTY FIELDS ({len(all_fields)} total) ---")
                for key, value in all_fields.items():
                    output.append(f"{key}: {value}")
            
            all_tables = property_data.get('all_tables', [])
            if all_tables:
                output.append(f"\n--- ALL TABLE DATA ({len(all_tables)} tables) ---")
                for i, table in enumerate(all_tables):
                    output.append(f"\nTable {i+1}: {table.get('name', 'Unnamed')}")
                    data_dict = table.get('data_dict', {})
                    if data_dict:
                        for key, value in data_dict.items():
                            output.append(f"  {key}: {value}")
                    
                    rows = table.get('rows', [])
                    if rows and not data_dict:
                        output.append("  Raw rows:")
                        for row in rows[:5]:  
                            if row and any(cell.strip() for cell in row):
                                output.append(f"    {' | '.join(str(cell) for cell in row)}")
            
            categorized_sections = ['property_identification', 'location_details', 
                                  'zoning_information', 'planning_details', 'permits_compliance']
            
            for section in categorized_sections:
                section_data = structured_data.get(section, {})
                if section_data:
                    output.append(f"\n--- {section.upper().replace('_', ' ')} ---")
                    for key, value in section_data.items():
                        output.append(f"{key}: {value}")
            
            raw_text = property_data.get('raw_text', '')
            if raw_text and len(raw_text) > 100:
                output.append(f"\n--- RAW PAGE TEXT (first 1000 chars) ---")
                output.append(raw_text[:1000] + "..." if len(raw_text) > 1000 else raw_text)
            
            return '\n'.join(output)
            
        except Exception as e:
            logger.warning(f"Error formatting scraped data: {e}")
            try:
                return f"=== COMPLETE ZIMAS DATA (JSON) ===\n{json.dumps(scraped_data, indent=2, ensure_ascii=False)[:5000]}"
            except:
                return f"=== COMPLETE ZIMAS DATA (STRING) ===\n{str(scraped_data)[:5000]}"
    
    def _pass_complete_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """Pass ALL search results directly to LLM"""
        if not search_results:
            return "\n=== NO WEB SEARCH RESULTS AVAILABLE ==="
        
        try:
            output = [f"\n=== COMPLETE WEB SEARCH RESULTS ({len(search_results)} results) ==="]
            
            for i, result in enumerate(search_results):
                output.append(f"\n--- RESULT {i+1} ---")
                
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                score = result.get('score', 'No score')
                content = result.get('content', 'No content')
                
                output.append(f"Title: {title}")
                output.append(f"URL: {url}")
                output.append(f"Relevance Score: {score}")
                output.append(f"Content: {content[:500]}{'...' if len(content) > 500 else ''}")
            
            return '\n'.join(output)
            
        except Exception as e:
            logger.warning(f"Error formatting search results: {e}")
            try:
                return f"\n=== COMPLETE WEB SEARCH RESULTS (JSON) ===\n{json.dumps(search_results, indent=2, ensure_ascii=False)[:3000]}"
            except:
                return f"\n=== COMPLETE WEB SEARCH RESULTS (STRING) ===\n{str(search_results)[:3000]}"