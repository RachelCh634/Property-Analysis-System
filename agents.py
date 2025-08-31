from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from pydantic import PrivateAttr
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from scraper import ZIMASSearchScraper 
from search_integration import TavilySearcher
from llm_integration import LLMProcessor
from langsmith import traceable
import os
from datetime import datetime

os.environ["LANGCHAIN_TRACING_V2"] = "true"

logger = logging.getLogger(__name__)

class ScraperTool(BaseTool):
    name: str = "Property Scraper"
    description: str = "ZIMAS LA City Property Scraper"
    
    _scrapers: Dict[int, ZIMASSearchScraper] = PrivateAttr(default_factory=dict)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._scrapers = {}
        self._lock = threading.Lock()
    
    def _get_scraper(self):
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._scrapers:
                self._scrapers[thread_id] = ZIMASSearchScraper(headless=True, debug=False)
            return self._scrapers[thread_id]

    @traceable
    def _run(self, address_data: str) -> Dict:
        try:
            if isinstance(address_data, str):
                parts = address_data.strip().split(' ', 1)
                if len(parts) >= 2:
                    house_number = parts[0]
                    street_name = parts[1]
                else:
                    house_number = ""
                    street_name = address_data
                
                address_data = {
                    'house_number': house_number,
                    'street_name': street_name
                }
            
            scraper = self._get_scraper()
            result = scraper.comprehensive_address_search(address_data)
            return result
            
        except Exception as e:
            logger.error(f"ScraperTool failed for {address_data}: {str(e)}", exc_info=True)
            return {
                "search_successful": False,
                "error": f"Scraping failed: {str(e)}",
                "address_data": address_data
            }
    
    def __getstate__(self):
        state = self.__dict__.copy()
        if '_scrapers' in state:
            del state['_scrapers']
        if '_lock' in state:
            del state['_lock']
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._scrapers = {}
        self._lock = threading.Lock()

class SearcherTool(BaseTool):
    name: str = "Property Searcher"
    description: str = "Search for property information online"
    
    _searchers: Dict[int, TavilySearcher] = PrivateAttr(default_factory=dict)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._searchers = {}
        self._lock = threading.Lock()
    
    def _get_searcher(self):
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._searchers:
                self._searchers[thread_id] = TavilySearcher()
            return self._searchers[thread_id]

    @traceable
    def _run(self, query: str) -> List:
        try:
            searcher = self._get_searcher()
            return searcher.search_property_info(query)
        except Exception as e:
            logger.error(f"SearcherTool failed for query '{query}': {str(e)}", exc_info=True)
            return []
    
    def __getstate__(self):
        state = self.__dict__.copy()
        if '_searchers' in state:
            del state['_searchers']
        if '_lock' in state:
            del state['_lock']
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._searchers = {}
        self._lock = threading.Lock()

class LLMTool(BaseTool):
    name: str = "LLM Processor"
    description: str = "Process and analyze data using LLM"
    
    _llms: Dict[int, LLMProcessor] = PrivateAttr(default_factory=dict)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._llms = {}
        self._lock = threading.Lock()
    
    def _get_llm(self):
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._llms:
                self._llms[thread_id] = LLMProcessor()
            return self._llms[thread_id]

    @traceable
    def _run(self, data: str) -> Dict:
        try:
            llm = self._get_llm()
            return llm.analyze_property_data(data, [])
        except Exception as e:
            logger.error(f"LLMTool failed: {str(e)}", exc_info=True)
            return {"error": f"LLM processing failed: {str(e)}"}
    
    def __getstate__(self):
        state = self.__dict__.copy()
        if '_llms' in state:
            del state['_llms']
        if '_lock' in state:
            del state['_lock']
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._llms = {}
        self._lock = threading.Lock()

class ReportFormatterTool(BaseTool):
    name: str = "Report Formatter"
    description: str = "Format property reports"
    
    def __init__(self, **data):
        super().__init__(**data)
    
    @traceable
    def _run(self, analysis_data: str) -> Dict:
        try:
            if isinstance(analysis_data, str):
                import json
                try:
                    analysis_data = json.loads(analysis_data)
                except:
                    analysis_data = {"data": analysis_data}
            
            return {
                "title": f"Property Analysis Report - {analysis_data.get('address', 'Unknown')}",
                "generated_date": datetime.now().isoformat(),
                "status": analysis_data.get('status', 'completed'),
                "data_quality": analysis_data.get('summary', {}).get('analysis_completeness', 'Unknown'),
                "zimas_successful": analysis_data.get('summary', {}).get('zimas_search_successful', False),
                "sections_found": len(analysis_data.get('summary', {}).get('sections_found', [])),
                "key_findings": analysis_data.get('summary', {}).get('key_findings', [])[:3]
            }
        except Exception as e:
            logger.error(f"ReportFormatterTool failed: {str(e)}", exc_info=True)
            return {"error": f"Report formatting failed: {str(e)}"}

class PropertyAnalysisSystem:
    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self.progress_callback = progress_callback
        self.scraper_tool = ScraperTool()
        self.searcher_tool = SearcherTool()
        self.llm_tool = LLMTool()
        self.formatter_tool = ReportFormatterTool()
        self._setup_langchain_agents()
    
    def _report_progress(self, progress: int, message: str):
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Progress: {progress}% - {message}")
    
    @traceable
    def _setup_langchain_agents(self):
        try:
            self.llm = ChatOpenAI(
                openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
                openai_api_base="https://openrouter.ai/api/v1",
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.3,
                max_tokens=4000
            )
            
            self.scraping_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are an expert at navigating ZIMAS and extracting structured property information from LA City Planning."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            self.research_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You specialize in finding relevant property information from various online sources."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            self.analysis_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are a real estate analyst who synthesizes data into actionable insights."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            self.report_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You format property analysis data into structured reports."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            self.scraping_agent = create_openai_functions_agent(
                self.llm,
                [self.scraper_tool],
                self.scraping_prompt
            )
            
            self.research_agent = create_openai_functions_agent(
                self.llm,
                [self.searcher_tool],
                self.research_prompt
            )
            
            self.analysis_agent = create_openai_functions_agent(
                self.llm,
                [self.llm_tool],
                self.analysis_prompt
            )
            
            self.report_agent = create_openai_functions_agent(
                self.llm,
                [self.formatter_tool],
                self.report_prompt
            )
            
            self.scraping_executor = AgentExecutor(
                agent=self.scraping_agent,
                tools=[self.scraper_tool],
                verbose=False,
                max_iterations=3
            )
            
            self.research_executor = AgentExecutor(
                agent=self.research_agent,
                tools=[self.searcher_tool],
                verbose=False,
                max_iterations=3
            )
            
            self.analysis_executor = AgentExecutor(
                agent=self.analysis_agent,
                tools=[self.llm_tool],
                verbose=False,
                max_iterations=3
            )
            
            self.report_executor = AgentExecutor(
                agent=self.report_agent,
                tools=[self.formatter_tool],
                verbose=False,
                max_iterations=3
            )
            
        except Exception as e:
            logger.error(f"Agent setup failed: {str(e)}", exc_info=True)
            raise

    @traceable
    async def analyze_property(self, address: str) -> Dict[str, Any]:
        step_completed = "initialization"
        property_data = {}
        
        try:
            logger.info(f"Starting property analysis for: {address}")
            
            step_completed = "zimas_search"
            self._report_progress(20, "Agent 1: Starting ZIMAS property search...")
            
            try:
                property_data = self.scraper_tool._run(address)
                
                if not property_data.get('search_successful', False):
                    error_message = property_data.get('error', 'No data found for this address')
                    logger.warning(f"ZIMAS search failed for {address}: {error_message}")
                    self._report_progress(20, f"Analysis stopped: ZIMAS search failed")
                    
                    return {
                        "address": address,
                        "status": "failed_zimas_search",
                        "error": error_message,
                        "message": "No data found in ZIMAS for this address. Please verify the address and try again.",
                        "raw_data": {
                            "zimas_data": property_data,
                            "search_results": []
                        },
                        "summary": {
                            "data_sources": ["ZIMAS Property Search (Failed)"],
                            "zimas_search_successful": False,
                            "property_fields_extracted": 0,
                            "sections_found": [],
                            "analysis_completeness": "Failed",
                            "key_findings": ["ZIMAS search failed - no data found for this address"]
                        }
                    }
                else:
                    logger.info(f"ZIMAS search completed successfully for {address}")
                    self._report_progress(40, "Agent 1: ZIMAS search completed successfully")
                    
            except Exception as zimas_error:
                logger.error(f"ZIMAS search failed for {address}: {str(zimas_error)}", exc_info=True)
                error_message = f"ZIMAS search error: {str(zimas_error)}"
                self._report_progress(20, f"Analysis failed: {error_message}")
                
                return {
                    "address": address,
                    "status": "error_zimas_search",
                    "error": str(zimas_error),
                    "message": "An error occurred during ZIMAS search. Please try again later.",
                    "raw_data": {
                        "zimas_data": {"search_successful": False, "error": str(zimas_error)},
                        "search_results": []
                    },
                    "summary": {
                        "data_sources": ["ZIMAS Property Search (Error)"],
                        "zimas_search_successful": False,
                        "property_fields_extracted": 0,
                        "sections_found": [],
                        "analysis_completeness": "Error",
                        "key_findings": [f"ZIMAS search error: {str(zimas_error)}"]
                    }
                }
            
            step_completed = "web_search"
            self._report_progress(50, "Agent 2: Searching for additional property information...")
            
            try:
                search_results = self.searcher_tool._run(address)
                result_count = len(search_results) if isinstance(search_results, list) else 0
                logger.info(f"Web search completed for {address}: {result_count} results")
                self._report_progress(65, f"Agent 2: Found {result_count} supplementary sources")
            except Exception as search_error:
                logger.error(f"Web search failed for {address}: {str(search_error)}", exc_info=True)
                search_results = []
                self._report_progress(65, "Agent 2: Web search completed with limited results")
            
            step_completed = "ai_analysis"
            self._report_progress(70, "Agent 3: Starting AI analysis...")
            
            try:
                analysis_result = self.llm_tool._get_llm().analyze_property_data(property_data, search_results)
                logger.info(f"LLM analysis completed successfully for {address}")
                self._report_progress(80, "Agent 3: AI analysis completed")
            except Exception as llm_error:
                logger.warning(f"LLM analysis failed for {address}, using fallback: {str(llm_error)}")
                analysis_result = self._create_comprehensive_fallback_analysis(property_data, search_results)
                self._report_progress(80, "Agent 3: Analysis completed with fallback method")
            
            intermediate_result = self._create_result_structure(address, property_data, search_results, analysis_result)
            
            step_completed = "report_formatting"
            self._report_progress(85, "Agent 4: Formatting report...")
            
            try:
                import json
                formatted_report = self.formatter_tool._run(json.dumps(intermediate_result))
                intermediate_result['formatted_report'] = formatted_report
                self._report_progress(95, "Agent 4: Report formatting completed")
            except Exception as format_error:
                logger.warning(f"Report formatting failed: {str(format_error)}")
                intermediate_result['formatted_report'] = {"error": f"Formatting failed: {str(format_error)}"}
                self._report_progress(95, "Agent 4: Using basic format")
            
            self._report_progress(100, "All 4 agents completed!")
            logger.info(f"Analysis completed successfully for: {address}")
            return intermediate_result
            
        except Exception as e:
            logger.error(f"Critical failure in analyze_property for {address}")
            logger.error(f"Failed at step: {step_completed}")
            logger.error(f"Error: {str(e)}", exc_info=True)
            
            if self.progress_callback:
                self.progress_callback(0, f"Analysis failed at {step_completed}: {str(e)}")
            
            return {
                "address": address,
                "status": "failed",
                "error": str(e),
                "step_failed": step_completed,
                "message": f"Analysis failed: {str(e)}",
                "partial_data": {
                    "zimas_data": property_data,
                    "search_data": {}
                }
            }
    
    def _create_result_structure(self, address: str, property_data: dict, search_results: list, analysis_result: Any) -> Dict[str, Any]:
        return {
            "address": address,
            "status": "completed", 
            "raw_data": {
                "zimas_data": property_data,
                "search_results": search_results
            },
            "analysis": analysis_result,
            "summary": {
                "data_sources": ["ZIMAS Property Search", "Web Search"],
                "zimas_search_successful": property_data.get('search_successful', False),
                "property_fields_extracted": len(property_data.get('property_data', {}).get('structured_data', {}).get('all_extracted_fields', {})),
                "sections_found": self._count_zimas_sections(property_data),
                "analysis_completeness": self._calculate_completeness(property_data, search_results),
                "key_findings": self._extract_key_findings(analysis_result)
            }
        }
    
    def _count_zimas_sections(self, zimas_data: dict) -> List[str]:
        sections_found = []
        property_data = zimas_data.get('property_data', {})
        
        section_names = [
            ('address_legal', 'Address/Legal'),
            ('jurisdictional', 'Jurisdictional'),
            ('permitting_zoning', 'Permitting & Zoning'),
            ('planning_zoning', 'Planning & Zoning'),
            ('assessor', 'Assessor'),
            ('case_numbers', 'Case Numbers'),
            ('additional', 'Additional'),
            ('environmental', 'Environmental'),
            ('seismic_hazards', 'Seismic Hazards'),
            ('economic_development', 'Economic Development'),
            ('housing', 'Housing'),
            ('public_safety', 'Public Safety')
        ]
        
        for section_key, section_display in section_names:
            if property_data.get(section_key):
                sections_found.append(section_display)
        
        return sections_found
    
    def _calculate_completeness(self, zimas_data: dict, search_results: dict) -> str:
        score = 0
        
        if zimas_data and zimas_data.get('search_successful'):
            score += 50
            
            property_data = zimas_data.get('property_data', {})
            structured_data = property_data.get('structured_data', {})
            all_fields = structured_data.get('all_extracted_fields', {})
            
            if len(all_fields) > 50:
                score += 20
            elif len(all_fields) > 20:
                score += 10
            
            sections_count = len(self._count_zimas_sections(zimas_data))
            if sections_count > 8:
                score += 15
            elif sections_count > 4:
                score += 10
        
        if search_results:
            score += 15
        
        if score >= 85:
            return "High"
        elif score >= 65:
            return "Medium"
        else:
            return "Low"
    
    def _extract_key_findings(self, analysis_result) -> List[str]:
        findings = []
        
        if isinstance(analysis_result, str):
            lines = analysis_result.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['key', 'important', 'finding', 'recommend']):
                    if len(line) > 20:
                        clean_line = line.lstrip('•-*123456789. #').strip()
                        if clean_line:
                            findings.append(clean_line)
                elif line.startswith(('•', '-', '*')) or (line and line[0].isdigit() and '.' in line[:5]):
                    if len(line) > 15:
                        clean_line = line.lstrip('•-*123456789. ').strip()
                        if clean_line:
                            findings.append(clean_line)
            
            if not findings:
                lines = analysis_result.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 30 and not line.startswith('#'):
                        findings.append(line)
                        if len(findings) >= 3:
                            break
        
        elif isinstance(analysis_result, dict):
            for section_name, content in analysis_result.items():
                if 'finding' in section_name.lower() or 'key' in section_name.lower():
                    if isinstance(content, list):
                        findings.extend(content[:3])
                    elif isinstance(content, str) and content.strip():
                        findings.append(content.strip())
        
        return findings[:5] if findings else ["Analysis completed - see full analysis for details"]
    
    def _create_comprehensive_fallback_analysis(self, zimas_data: dict, search_results: list) -> dict:
        analysis = {
            "Property Overview": "",
            "ZIMAS Search Results": "",
            "Web Search Results": "",
            "Property Data Summary": {},
            "Sections Found": [],
            "Key Findings": [],
            "Recommendations": [],
            "Data Quality": "",
            "Analysis Type": "Fallback Analysis (No LLM)"
        }
        
        if zimas_data:
            search_success = zimas_data.get('search_successful', False)
            property_data = zimas_data.get('property_data', {})
            
            analysis["ZIMAS Search Results"] = f"Search Status: {'Successful' if search_success else 'Failed'}"
            
            if search_success and property_data:
                structured_data = property_data.get('structured_data', {})
                all_fields = structured_data.get('all_extracted_fields', {})
                
                analysis["ZIMAS Search Results"] += f"\n• Extracted {len(all_fields)} property data fields"
                analysis["ZIMAS Search Results"] += f"\n• Processed {len(property_data.get('all_tables', []))} data tables"
                
                key_info = {}
                important_fields = ['Site Address', 'ZIP Code', 'Zoning', 'General Plan Land Use', 
                                  'Community Plan Area', 'Council District', 'PIN Number']
                
                for field in important_fields:
                    if field in all_fields:
                        key_info[field] = all_fields[field]
                
                if key_info:
                    analysis["Property Data Summary"] = key_info
                    analysis["Key Findings"].append(f"Retrieved comprehensive property data including zoning and planning information")
                
                sections_found = self._count_zimas_sections(zimas_data)
                analysis["Sections Found"] = sections_found
                if len(sections_found) > 5:
                    analysis["Key Findings"].append(f"Found data in {len(sections_found)} ZIMAS sections")
        
        if search_results:
            analysis["Web Search Results"] = f"Found {len(search_results)} web search results"
            
            titles = [result.get('title', '') for result in search_results[:5]]
            non_empty_titles = [title for title in titles if title]
            if non_empty_titles:
                analysis["Web Search Results"] += f"\nTop results: {'; '.join(non_empty_titles)}"
            
            high_score_results = [r for r in search_results if r.get('score', 0) > 0.7]
            if high_score_results:
                analysis["Key Findings"].append(f"Found {len(high_score_results)} highly relevant web results")
        
        address = zimas_data.get('address_data', {}).get('house_number', '') + ' ' + zimas_data.get('address_data', {}).get('street_name', '') if zimas_data else 'Unknown address'
        analysis["Property Overview"] = f"Property analysis for {address}"
        if zimas_data and zimas_data.get('search_successful'):
            analysis["Property Overview"] += f"\nComprehensive property data successfully retrieved from ZIMAS"
        else:
            analysis["Property Overview"] += f"\nLimited property data available"
        
        if zimas_data and zimas_data.get('search_successful'):
            analysis["Recommendations"].append("Review ZIMAS property data for comprehensive planning and zoning information")
            if analysis["Sections Found"]:
                analysis["Recommendations"].append("Examine specific ZIMAS sections for detailed property characteristics")
        
        if search_results:
            analysis["Recommendations"].append("Review web search results for additional property context")
        
        if not zimas_data or not zimas_data.get('search_successful'):
            analysis["Recommendations"].append("Consider alternative data sources or verify address format for property analysis")
        
        quality_score = 0
        if zimas_data and zimas_data.get('search_successful'):
            quality_score += 60
            property_data = zimas_data.get('property_data', {})
            if len(property_data.get('structured_data', {}).get('all_extracted_fields', {})) > 50:
                quality_score += 20
        
        if search_results:
            quality_score += 20
        
        if quality_score >= 80:
            analysis["Data Quality"] = "High - Comprehensive ZIMAS data available"
        elif quality_score >= 50:
            analysis["Data Quality"] = "Medium - Partial data available"
        else:
            analysis["Data Quality"] = "Low - Limited data available"
        
        if not analysis["Key Findings"]:
            analysis["Key Findings"] = ["Basic property search completed with available data sources"]
        
        return analysis