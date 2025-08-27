import asyncio
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from typing import Dict, Any, List, Tuple

class ZIMASSearchScraper:
    
    def __init__(self, headless=False, debug=True):
        self.headless = headless
        self.debug = debug
        self.base_url = "https://zimas.lacity.org"
        
        self.core_categories = [
            'address_legal', 'planning_zoning', 'assessor',
            'case_numbers', 'citywide_code_amendment', 'housing'
        ]
        
        self.category_mapping = {
            'address_legal': 'Address/Legal',
            'planning_zoning': 'Planning and Zoning',
            'assessor': 'Assessor',
            'case_numbers': 'Case Numbers',
            'citywide_code_amendment': 'Citywide/Code Amendment Cases',
            'housing': 'Housing'
        }

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.implicitly_wait(5)
        
        return driver

    def handle_terms_agreement(self, driver) -> bool:
        print("Handling terms and conditions agreement...")
        try:
            time.sleep(2)
            
            accept_button = driver.find_element(By.XPATH, "//input[@value='Accept']")
            if accept_button.is_displayed() and accept_button.is_enabled():
                accept_button.click()
                print("Terms agreement accepted")
                time.sleep(2)
                return True
        except Exception:
            pass
        
        if "search by address" in driver.page_source.lower():
            print("Already past terms agreement")
            return True
            
        return False

    def perform_address_search(self, driver, house_number: str, street_name: str) -> bool:
        print(f"Searching for: {house_number} {street_name}")
        
        try:
            time.sleep(3)
            
            house_number_field = driver.find_element(By.ID, "txtHouseNumber")
            house_number_field.clear()
            house_number_field.send_keys(house_number)
            
            street_name_field = driver.find_element(By.ID, "txtStreetName")
            street_name_field.clear()
            street_name_field.send_keys(street_name)
            
            go_button = driver.find_element(By.ID, "btnSearchGo")
            go_button.click()
            
            print("Search submitted, waiting for results...")
            time.sleep(5)
            
            page_source = driver.page_source.lower()
            
            no_results_indicators = [
                "your search return no results",
                "Your search return NO RESULTS.",
                "no results found",
                "below are some suggestions",
                "suggestions of what you might have been looking for",
            ]
            
            if any(indicator in page_source for indicator in no_results_indicators):
                print("ZIMAS returned NO RESULTS - address not found")
                return False
            
            success_indicators = ["address/legal", "site address", "assessor"]
            has_success_indicators = any(indicator in page_source for indicator in success_indicators)
            
            if has_success_indicators:
                print("ZIMAS search successful - found property data")
                return True
            else:
                print("ZIMAS search failed - no property data found")
                return False
                
        except Exception as e:
            print(f"Search error: {e}")
            return False

    async def extract_table_async(self, table_html: str, table_name: str) -> Dict[str, Any]:
        """Extract table data from HTML string asynchronously using BeautifulSoup"""
        soup = BeautifulSoup(table_html, 'html.parser')
        
        table_data = {
            'name': table_name,
            'rows': [],
            'data_dict': {}
        }
        
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            
            if row_data and any(cell for cell in row_data):
                table_data['rows'].append(row_data)
                
                if len(row_data) == 2 and row_data[0] and row_data[1]:
                    key = row_data[0].replace(":", "").strip()
                    value = row_data[1].strip()
                    if key and value and len(key) < 100:
                        table_data['data_dict'][key] = value
        
        return table_data if table_data['rows'] else None

    async def extract_all_data_single_pass_async(self, driver) -> Dict[str, Any]:
        """Extract all data in a single pass - tables, sections, and structure together - ASYNC VERSION"""
        print("Starting optimized single-pass data extraction (ASYNC)...")
        
        property_data = {
            'all_tables': [],
            'raw_text': '',
            'structured_data': {'all_extracted_fields': {}}
        }
        
        for category in self.core_categories:
            property_data[category] = {}
        
        try:
            property_data['raw_text'] = driver.find_element(By.TAG_NAME, "body").text
            
            self.expand_sections_optimized(driver)
            
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"Found {len(tables)} tables - processing asynchronously...")
            
            table_htmls = [(table.get_attribute('outerHTML'), f"Table_{i+1}") 
                          for i, table in enumerate(tables)]
            
            valid_tables = await self.process_tables_async(table_htmls)
            property_data['all_tables'] = valid_tables
            
            all_extracted = {}
            for table in property_data['all_tables']:
                all_extracted.update(table['data_dict'])
            
            property_data['structured_data']['all_extracted_fields'] = all_extracted
            
            self.categorize_data_fast(all_extracted, property_data)
            
            print(f"Extraction completed - {len(property_data['all_tables'])} tables, {len(all_extracted)} fields")
            
        except Exception as e:
            print(f"Error in single-pass extraction: {e}")
            
        return property_data

    async def process_tables_async(self, table_htmls: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Process all tables asynchronously"""
        tasks = [self.extract_table_async(html, name) for html, name in table_htmls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_tables = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Table extraction error: {result}")
            elif result is not None:
                valid_tables.append(result)
        
        return valid_tables

    def expand_sections_optimized(self, driver):
        """Optimized section expansion - single pass through clickable elements"""
        print("Expanding sections (optimized)...")
        
        target_sections = set(self.category_mapping.values())
        skip_sections = {
            'Jurisdictional', 'Permitting and Zoning Compliance', 'Additional',
            'Environmental', 'Seismic Hazards', 'Economic Development Areas', 'Public Safety'
        }
        
        clickable_elements = driver.find_elements(By.XPATH, "//*[@onclick]")
        print(f"Found {len(clickable_elements)} clickable elements")
        
        expanded = set()
        for element in clickable_elements:
            if len(expanded) >= len(target_sections):
                break
                
            try:
                element_text = element.text.strip()
                if not element_text or len(element_text) > 50:
                    continue
                
                matching_section = None
                for target in target_sections:
                    if target in element_text and not any(skip in element_text for skip in skip_sections):
                        matching_section = target
                        break
                
                if matching_section and matching_section not in expanded:
                    onclick = element.get_attribute('onclick') or ''
                    if not any(word in onclick.lower() for word in ['tooltip', 'popup', 'info', 'help']):
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            expanded.add(matching_section)
                            print(f"Expanded: {matching_section}")
                            time.sleep(0.5)
                        except:
                            continue
                            
            except:
                continue
        
        print(f"Successfully expanded {len(expanded)} sections")

    def categorize_data_fast(self, all_data: Dict[str, str], property_data: Dict[str, Any]):
        """Fast categorization using keyword matching"""
        
        category_keywords = {
            'address_legal': ['address', 'legal', 'pin', 'parcel', 'ain'],
            'planning_zoning': ['zoning', 'plan', 'land use', 'specific'],
            'assessor': ['assessor', 'assessed', 'tax', 'roll', 'year built'],
            'case_numbers': ['case', 'hearing', 'decision', 'appeal'],
            'citywide_code_amendment': ['amendment', 'ordinance', 'council'],
            'housing': ['housing', 'affordable', 'density', 'overlay']
        }
        
        for key, value in all_data.items():
            key_lower = key.lower()
            
            for category, keywords in category_keywords.items():
                if any(keyword in key_lower for keyword in keywords):
                    property_data[category][key] = value
                    break

    async def comprehensive_address_search_async(self, address_data: Dict[str, str]) -> Dict[str, Any]:
        """ASYNC VERSION - Main search function"""
        house_number = address_data.get('house_number', '')
        street_name = address_data.get('street_name', '')
        
        print(f"ASYNC ZIMAS search for: {house_number} {street_name}")
        print("=" * 60)
        
        driver = self.setup_driver()
        search_data = {
            'address_data': address_data,
            'search_successful': False,
            'property_data': {},
            'categories_extracted': self.core_categories,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            driver.get(self.base_url)
            time.sleep(2)
            
            if not self.handle_terms_agreement(driver):
                print("Warning: Could not handle terms agreement")
            
            search_successful = self.perform_address_search(driver, house_number, street_name)
            search_data['search_successful'] = search_successful
            
            if search_successful:
                property_data = await self.extract_all_data_single_pass_async(driver)
                search_data['property_data'] = property_data
            
        except Exception as e:
            print(f"Error: {e}")
            search_data['error'] = str(e)
            
        finally:
            driver.quit()
        
        return search_data

    def comprehensive_address_search(self, address_data: Dict[str, str]) -> Dict[str, Any]:
        """SYNC wrapper - runs the async version using existing event loop"""
        try:
            loop = asyncio.get_running_loop()
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_async_search, address_data)
                return future.result()
                
        except RuntimeError:
            return asyncio.run(self.comprehensive_address_search_async(address_data))
    
    def _run_async_search(self, address_data: Dict[str, str]) -> Dict[str, Any]:
        """Helper to run async search in new event loop"""
        return asyncio.run(self.comprehensive_address_search_async(address_data))