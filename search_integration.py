from tavily import TavilyClient
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TavilySearcher:
    """
    Tavily API integration for web search
    """

    def __init__(self):
        self.client = TavilyClient(
            api_key=os.getenv("TAVILY_API_KEY")
        )

    def search_property_info(
        self,
        address: str,
        additional_context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for property-related information
        """

        queries = self._generate_search_queries(address, additional_context)
        all_results = []

        for query in queries:
            try:
                results = self.client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )

                all_results.extend(self._process_results(results))

            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")

        return all_results

    def _generate_search_queries(
        self,
        address: str,
        context: Dict[str, Any] = None
    ) -> List[str]:
        """Generate optimized search queries"""

        queries = [
            f"{address} Los Angeles property information",
            f"{address} zoning regulations",
            f"{address} property value assessment",
            f"{address} neighborhood development plans",
            f"{address} recent sales comparable properties"
        ]

        if context and 'zoning' in context:
            queries.append(f"Los Angeles {context['zoning']} zoning requirements")

        return queries

    def _process_results(
        self,
        raw_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process and filter search results"""

        processed = []

        if 'results' in raw_results:
            for result in raw_results['results']:
                processed.append({
                    'title': result.get('title'),
                    'url': result.get('url'),
                    'content': result.get('content'),
                    'score': result.get('score', 0)
                })

        processed.sort(key=lambda x: x['score'], reverse=True)

        return processed