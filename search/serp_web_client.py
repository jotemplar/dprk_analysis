"""SERP API client for Google Web searches (articles/text content)"""

import os
import time
import re
from typing import List, Dict, Optional
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

class SerpWebClient:
    """Client for SERP API Google Web searches"""

    def __init__(self):
        self.api_key = os.getenv("SERP_API_KEY")
        if not self.api_key:
            raise ValueError("SERP_API_KEY not found in environment variables")
        self.rate_limit = int(os.getenv("SEARCH_RATE_LIMIT", 400))

    def search_web(self, query: str, num_results: int = 50, site_filter: str = None) -> List[Dict]:
        """
        Execute Google Web search query

        Args:
            query: The search query string
            num_results: Number of results to retrieve (default 50)
            site_filter: Optional site to filter (e.g., "vk.com")

        Returns:
            List of web result dictionaries
        """
        try:
            # Handle site-specific queries
            if site_filter:
                query = f"site:{site_filter} {query}"
            elif query.startswith("http"):
                # Direct URL - return it as a result
                return [{
                    "url": query,
                    "title": "Direct URL",
                    "snippet": "Direct URL for scraping",
                    "position": 1,
                    "source_domain": self._extract_domain(query),
                    "type": "direct_url"
                }]

            all_results = []
            pages_needed = (num_results - 1) // 10 + 1  # Google returns up to 10 organic results per page

            for page in range(pages_needed):
                if len(all_results) >= num_results:
                    break

                params = {
                    "api_key": self.api_key,
                    "engine": "google",
                    "q": query,
                    "num": min(10, num_results - len(all_results)),
                    "start": page * 10,
                    "hl": "en",
                    "gl": "us",
                    "safe": "off"
                }

                print(f"  Searching: {query[:50]}... (page {page + 1})")

                search = GoogleSearch(params)
                results = search.get_dict()

                # Extract organic results
                if "organic_results" in results:
                    for result in results["organic_results"]:
                        if len(all_results) >= num_results:
                            break

                        result_data = {
                            "url": result.get("link", ""),
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "position": result.get("position", 0),
                            "source_domain": self._extract_domain(result.get("link", "")),
                            "date": result.get("date"),  # Some results include date
                            "type": "organic"
                        }

                        all_results.append(result_data)

                # Also check news results if present
                if "news_results" in results:
                    for news in results["news_results"]:
                        if len(all_results) >= num_results:
                            break

                        result_data = {
                            "url": news.get("link", ""),
                            "title": news.get("title", ""),
                            "snippet": news.get("snippet", ""),
                            "source_domain": news.get("source", ""),
                            "date": news.get("date"),
                            "type": "news"
                        }

                        all_results.append(result_data)

                # Rate limiting
                time.sleep(1.0 / self.rate_limit)

                # Check if we have more pages
                if "serpapi_pagination" not in results or "next" not in results["serpapi_pagination"]:
                    break

            print(f"  Found {len(all_results)} results")
            return all_results

        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ""

        # Remove protocol
        url = re.sub(r'^https?://', '', url)

        # Extract domain
        domain = url.split('/')[0]

        # Remove www
        domain = domain.replace('www.', '')

        return domain

    def search_multiple(self, queries: List[str], num_per_query: int = 20) -> Dict[str, List[Dict]]:
        """
        Execute multiple search queries

        Args:
            queries: List of search queries
            num_per_query: Number of results per query

        Returns:
            Dictionary mapping queries to their results
        """
        results = {}

        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] Processing query: {query[:100]}...")

            # Extract site filter if present
            site_filter = None
            if "site:" in query:
                parts = query.split("site:")
                if len(parts) > 1:
                    site_parts = parts[1].split()
                    if site_parts:
                        site_filter = site_parts[0]
                        # Remove site filter from query
                        query = query.replace(f"site:{site_filter}", "").strip()

            results[query] = self.search_web(query, num_per_query, site_filter)

            # Rate limiting between queries
            time.sleep(2)

        return results