"""SERP API client for Google Image searches"""

import os
import time
import json
from typing import List, Dict, Optional
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

class SerpImageClient:
    """Client for SERP API Google Image searches"""

    def __init__(self):
        self.api_key = os.getenv("SERP_API_KEY")
        if not self.api_key:
            raise ValueError("SERP_API_KEY not found in environment variables")
        self.rate_limit = int(os.getenv("SEARCH_RATE_LIMIT", 400))

    def search_images(self, query: str, num_results: int = 100) -> List[Dict]:
        """
        Execute Google Image search query

        Args:
            query: The search query string
            num_results: Number of image results to retrieve

        Returns:
            List of image result dictionaries
        """
        try:
            all_results = []
            pages_needed = (num_results - 1) // 100 + 1  # Google Images returns up to 100 per page

            for page in range(pages_needed):
                if len(all_results) >= num_results:
                    break

                params = {
                    "api_key": self.api_key,
                    "engine": "google_images",
                    "q": query,
                    "num": min(100, num_results - len(all_results)),
                    "ijn": page,  # Image page number
                    "hl": "en",
                    "gl": "us",
                    "safe": "off"  # Include all results
                }

                # Add date filter for recent images
                params["tbs"] = "qdr:y5"  # Last 5 years

                search = GoogleSearch(params)
                results = search.get_dict()

                # Extract image results
                images_results = results.get("images_results", [])

                for i, result in enumerate(images_results):
                    if len(all_results) >= num_results:
                        break

                    processed_result = {
                        "position": len(all_results) + 1,
                        "title": result.get("title", ""),
                        "image_url": result.get("original", ""),
                        "thumbnail_url": result.get("thumbnail", ""),
                        "source_url": result.get("link", ""),
                        "source_domain": result.get("source", ""),
                        "width": result.get("original_width"),
                        "height": result.get("original_height"),
                        "is_product": result.get("is_product", False)
                    }
                    all_results.append(processed_result)

                # Delay between pagination requests
                if page < pages_needed - 1:
                    time.sleep(0.5)

            print(f"   Found {len(all_results)} images for query: {query[:50]}...")
            return all_results

        except Exception as e:
            print(f"   ❌ Error searching images for '{query[:50]}...': {e}")
            return []

    def search_web_for_images(self, query: str, num_results: int = 50) -> List[Dict]:
        """
        Execute regular web search but extract pages likely to contain images

        Args:
            query: The search query string with image-related terms
            num_results: Number of results to retrieve

        Returns:
            List of web pages likely containing relevant images
        """
        try:
            all_results = []
            pages_needed = (num_results - 1) // 10 + 1

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
                    "tbm": "nws"  # News results often have images
                }

                search = GoogleSearch(params)
                results = search.get_dict()

                organic_results = results.get("organic_results", [])

                for result in organic_results:
                    if len(all_results) >= num_results:
                        break

                    # Check if result likely has images
                    has_thumbnail = result.get("thumbnail") is not None
                    has_rich_snippet = "rich_snippet" in result

                    processed_result = {
                        "position": len(all_results) + 1,
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "source": result.get("source", ""),
                        "date": self._extract_date(result),
                        "thumbnail": result.get("thumbnail"),
                        "likely_has_images": has_thumbnail or has_rich_snippet
                    }
                    all_results.append(processed_result)

                if page < pages_needed - 1:
                    time.sleep(0.5)

            print(f"   Found {len(all_results)} web results for: {query[:50]}...")
            return all_results

        except Exception as e:
            print(f"   ❌ Error in web search for '{query[:50]}...': {e}")
            return []

    def _extract_date(self, result: Dict) -> Optional[str]:
        """Extract date from search result if available"""
        if "date" in result:
            return result["date"]

        if "rich_snippet" in result:
            if "top" in result["rich_snippet"]:
                if "detected_extensions" in result["rich_snippet"]["top"]:
                    extensions = result["rich_snippet"]["top"]["detected_extensions"]
                    if "date" in extensions:
                        return extensions["date"]

        return None

    def process_all_queries(self, queries: List[str], search_type: str = "images", delay: float = 1.5) -> Dict[str, List[Dict]]:
        """
        Process multiple queries sequentially

        Args:
            queries: List of search queries
            search_type: 'images' or 'web'
            delay: Delay between queries in seconds

        Returns:
            Dictionary mapping queries to their results
        """
        all_results = {}
        total = len(queries)

        print(f"\n🔍 Processing {total} {search_type} search queries")
        print("=" * 50)

        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{total}] Searching: {query}")

            # Execute appropriate search
            if search_type == "images":
                results = self.search_images(query)
            else:
                results = self.search_web_for_images(query)

            all_results[query] = results

            # Rate limiting
            if i < total:
                time.sleep(delay)

        print(f"\n✅ Completed {total} {search_type} searches")
        return all_results

    def search_with_retries(self, query: str, search_type: str = "images", max_retries: int = 3, num_results: int = 100) -> List[Dict]:
        """
        Search with retry logic for failed requests

        Args:
            query: The search query
            search_type: 'images' or 'web'
            max_retries: Maximum number of retry attempts
            num_results: Number of results to retrieve

        Returns:
            List of search results
        """
        for attempt in range(max_retries):
            try:
                if search_type == "images":
                    return self.search_images(query, num_results)
                else:
                    return self.search_web_for_images(query, num_results)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Failed after {max_retries} attempts: {e}")
                    return []

        return []