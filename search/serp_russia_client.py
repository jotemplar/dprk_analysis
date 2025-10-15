"""SERP API client for Yandex and Google Russia searches"""

import os
import time
import re
from typing import List, Dict, Optional
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()


class SerpRussiaClient:
    """Client for SERP API Yandex and Google Russia searches"""

    def __init__(self):
        self.api_key = os.getenv("SERP_API_KEY")
        if not self.api_key:
            raise ValueError("SERP_API_KEY not found in environment variables")
        self.rate_limit = int(os.getenv("SEARCH_RATE_LIMIT", 400))

    def search_yandex(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Execute Yandex search query

        Args:
            query: The search query string
            num_results: Number of results to retrieve (default 10)

        Returns:
            List of search result dictionaries
        """
        try:
            all_results = []
            pages_needed = (num_results - 1) // 10 + 1  # Yandex returns up to 10 results per page

            for page in range(pages_needed):
                if len(all_results) >= num_results:
                    break

                params = {
                    "api_key": self.api_key,
                    "engine": "yandex",
                    "text": query,
                    "p": page,  # Pagination parameter (correct name)
                    "yandex_domain": "yandex.ru",  # Russian Yandex domain
                    "lang": "ru",  # Russian language
                    "lr": "213"  # Location ID for Russia (Moscow region)
                }

                print(f"  Searching Yandex: {query[:80]}... (page {page + 1})")

                search = GoogleSearch(params)  # Use GoogleSearch class for all engines
                results = search.get_dict()

                # Debug: Print search metadata
                if "search_metadata" in results:
                    print(f"    Status: {results['search_metadata'].get('status', 'Unknown')}")

                # Extract organic results
                if "organic_results" in results:
                    for result in results["organic_results"]:
                        if len(all_results) >= num_results:
                            break

                        result_data = {
                            "url": result.get("link", ""),
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "position": result.get("position", len(all_results) + 1),
                            "source_domain": self._extract_domain(result.get("link", "")),
                            "date": result.get("date"),
                            "type": "organic",
                            "engine": "yandex"
                        }

                        all_results.append(result_data)

                # Rate limiting
                time.sleep(1.0 / self.rate_limit)

                # Check if we have more pages
                if len(all_results) < num_results and "serpapi_pagination" in results:
                    if "next" not in results["serpapi_pagination"]:
                        break
                else:
                    break

            print(f"  Found {len(all_results)} Yandex results")
            return all_results

        except Exception as e:
            print(f"Error searching Yandex: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_google_russia(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Execute Google search with Russia location

        Args:
            query: The search query string
            num_results: Number of results to retrieve (default 10)

        Returns:
            List of search result dictionaries
        """
        try:
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
                    "hl": "ru",  # Russian language
                    "gl": "ru",  # Russia location
                    "safe": "off",
                    "lr": "lang_ru"  # Results in Russian
                }

                print(f"  Searching Google Russia: {query[:80]}... (page {page + 1})")

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
                            "position": result.get("position", len(all_results) + 1),
                            "source_domain": self._extract_domain(result.get("link", "")),
                            "date": result.get("date"),
                            "type": "organic",
                            "engine": "google_russia"
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
                            "type": "news",
                            "engine": "google_russia"
                        }

                        all_results.append(result_data)

                # Rate limiting
                time.sleep(1.0 / self.rate_limit)

                # Check if we have more pages
                if "serpapi_pagination" not in results or "next" not in results["serpapi_pagination"]:
                    break

            print(f"  Found {len(all_results)} Google Russia results")
            return all_results

        except Exception as e:
            print(f"Error searching Google Russia: {e}")
            return []

    def search(self, query: str, engine: str = "yandex", num_results: int = 10) -> List[Dict]:
        """
        Execute search using specified engine

        Args:
            query: The search query string
            engine: 'yandex' or 'google' (defaults to yandex)
            num_results: Number of results to retrieve (default 10)

        Returns:
            List of search result dictionaries
        """
        engine_lower = engine.lower()

        if engine_lower == "yandex":
            return self.search_yandex(query, num_results)
        elif engine_lower == "google":
            return self.search_google_russia(query, num_results)
        else:
            print(f"Warning: Unknown engine '{engine}', defaulting to Yandex")
            return self.search_yandex(query, num_results)

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

    def search_with_retries(self, query: str, engine: str = "yandex",
                           num_results: int = 10, max_retries: int = 3) -> List[Dict]:
        """
        Search with retry logic for failed requests

        Args:
            query: The search query
            engine: 'yandex' or 'google'
            num_results: Number of results to retrieve
            max_retries: Maximum number of retry attempts

        Returns:
            List of search results
        """
        for attempt in range(max_retries):
            try:
                return self.search(query, engine, num_results)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   Failed after {max_retries} attempts: {e}")
                    return []

        return []
