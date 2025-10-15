#!/usr/bin/env python3
"""Article search processor for DPRK search terms pack 3"""

import sys
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from database.connection import get_session
from database.article_models import ArticleSearch, ArticleResult
from search.serp_web_client import SerpWebClient
from search_terms.dprk_images_search_terms_3 import search_packs
from sqlalchemy.exc import IntegrityError


class ArticleSearchProcessor:
    """Process article searches from search terms pack 3"""

    def __init__(self):
        self.serp_client = SerpWebClient()
        self.session = get_session()
        self.processed_count = 0
        self.total_results = 0

    def process_all_searches(self, results_per_query: int = 50):
        """
        Process all search terms from pack 3

        Args:
            results_per_query: Number of results to collect per search query
        """
        print("\n" + "=" * 60)
        print("DPRK ARTICLE SEARCH PROCESSOR")
        print("=" * 60)
        print(f"📊 Processing {len(search_packs)} categories")

        total_queries = sum(len(queries) for queries in search_packs.values())
        print(f"📋 Total search queries: {total_queries}")
        print(f"🎯 Results per query: {results_per_query}")
        print(f"📈 Expected total results: ~{total_queries * results_per_query}")

        try:
            for category, search_terms in search_packs.items():
                print(f"\n🔍 Processing category: {category}")
                print(f"   📝 {len(search_terms)} search terms")

                self._process_category(category, search_terms, results_per_query)

            print(f"\n✅ Search processing completed!")
            print(f"   📊 Processed queries: {self.processed_count}")
            print(f"   📈 Total results collected: {self.total_results}")

        except Exception as e:
            print(f"\n❌ Error in search processing: {e}")
            raise
        finally:
            self.session.close()

    def _process_category(self, category: str, search_terms: List[str], results_per_query: int):
        """Process all search terms in a category"""

        for i, search_term in enumerate(search_terms, 1):
            print(f"\n   [{i}/{len(search_terms)}] Processing: {search_term[:80]}...")

            try:
                # Store search term in database
                search_record = self._store_search_term(category, search_term)

                # Execute search
                site_filter = self._extract_site_filter(search_term)
                clean_query = self._clean_query(search_term)

                print(f"      🔍 Executing search...")
                results = self.serp_client.search_web(
                    query=clean_query,
                    num_results=results_per_query,
                    site_filter=site_filter
                )

                # Store results
                stored_count = self._store_results(search_record.id, results)
                self.total_results += stored_count

                print(f"      ✅ Collected {stored_count} results")
                self.processed_count += 1

            except Exception as e:
                print(f"      ❌ Error processing search term: {e}")
                continue

    def _store_search_term(self, category: str, search_term: str) -> ArticleSearch:
        """Store search term in database"""

        # Check if already exists
        existing = self.session.query(ArticleSearch).filter_by(
            search_term=search_term
        ).first()

        if existing:
            print(f"      ⚠️  Search term already exists, using existing record")
            return existing

        # Create new search record
        search_record = ArticleSearch(
            category=category,
            search_term=search_term,
            language=self._detect_language(search_term),
            search_type=self._detect_search_type(search_term),
            site_filter=self._extract_site_filter(search_term)
        )

        try:
            self.session.add(search_record)
            self.session.commit()
            return search_record
        except IntegrityError:
            self.session.rollback()
            # Handle race condition - get existing record
            existing = self.session.query(ArticleSearch).filter_by(
                search_term=search_term
            ).first()
            return existing

    def _store_results(self, search_id: int, results: List[Dict]) -> int:
        """Store search results in database"""

        stored_count = 0

        for result in results:
            url = result.get('url', '')
            if not url:
                continue

            # Check if result already exists for this search
            existing = self.session.query(ArticleResult).filter_by(
                search_id=search_id,
                url=url
            ).first()

            if existing:
                continue

            # Create new result record
            result_record = ArticleResult(
                search_id=search_id,
                url=url,
                title=result.get('title', ''),
                snippet=result.get('snippet', ''),
                position=result.get('position', 0),
                source_domain=result.get('source_domain', ''),
                published_date=self._parse_date(result.get('date'))
            )

            try:
                self.session.add(result_record)
                stored_count += 1
            except Exception as e:
                print(f"        ⚠️  Error storing result: {e}")
                continue

        try:
            self.session.commit()
            return stored_count
        except IntegrityError as e:
            self.session.rollback()
            if "duplicate key" in str(e) or "_search_url_uc" in str(e):
                print(f"        ⚠️  Some results already exist for this search (skipping duplicates)")
                return 0
            else:
                print(f"        ❌ Database integrity error: {e}")
                return 0
        except Exception as e:
            self.session.rollback()
            print(f"        ❌ Error committing results: {e}")
            return 0

    def _extract_site_filter(self, search_term: str) -> str:
        """Extract site filter from search term"""
        if 'site:' in search_term:
            # Extract site:domain.com pattern
            import re
            match = re.search(r'site:([^\s]+)', search_term)
            if match:
                return match.group(1)
        return None

    def _clean_query(self, search_term: str) -> str:
        """Clean search term for API submission"""
        # If it's a direct URL, return as-is
        if search_term.startswith('http'):
            return search_term

        # Remove site: filters for the main query
        import re
        cleaned = re.sub(r'site:[^\s]+\s*', '', search_term)
        return cleaned.strip()

    def _detect_language(self, search_term: str) -> str:
        """Detect language of search term"""
        # Simple language detection based on character sets
        if any('\u0400' <= char <= '\u04FF' for char in search_term):  # Cyrillic
            return 'ru'
        elif any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF' for char in search_term):  # Japanese/Chinese
            if '朝鲜' in search_term or '俄罗斯' in search_term:
                return 'zh'
            return 'ko'
        else:
            return 'en'

    def _detect_search_type(self, search_term: str) -> str:
        """Detect type of search"""
        if search_term.startswith('http'):
            return 'direct_url'
        elif 'site:' in search_term:
            return 'site_specific'
        else:
            return 'web'

    def _parse_date(self, date_str: str):
        """Parse date string to datetime object"""
        if not date_str:
            return None

        try:
            # Try different date formats
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None

    def get_search_statistics(self):
        """Get statistics about processed searches"""

        total_searches = self.session.query(ArticleSearch).count()
        total_results = self.session.query(ArticleResult).count()

        # Get results by category
        from sqlalchemy import func
        category_stats = self.session.query(
            ArticleSearch.category,
            func.count(ArticleSearch.id).label('search_count'),
            func.count(ArticleResult.id).label('result_count')
        ).outerjoin(ArticleResult).group_by(ArticleSearch.category).all()

        print(f"\n📊 Article Search Statistics:")
        print(f"   Total searches: {total_searches}")
        print(f"   Total results: {total_results}")
        print(f"\n📋 By Category:")

        for category, search_count, result_count in category_stats:
            avg_results = result_count / search_count if search_count > 0 else 0
            print(f"   {category}: {search_count} searches, {result_count} results (avg: {avg_results:.1f})")


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Process DPRK article searches')
    parser.add_argument('--results-per-query', type=int, default=50,
                       help='Number of results to collect per search query')
    parser.add_argument('--category', type=str, default=None,
                       help='Process only specific category')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics, do not process')

    args = parser.parse_args()

    processor = ArticleSearchProcessor()

    if args.stats_only:
        processor.get_search_statistics()
        return

    if args.category:
        if args.category in search_packs:
            print(f"🎯 Processing only category: {args.category}")
            processor._process_category(
                args.category,
                search_packs[args.category],
                args.results_per_query
            )
        else:
            print(f"❌ Category '{args.category}' not found")
            print(f"Available categories: {list(search_packs.keys())}")
            return
    else:
        processor.process_all_searches(args.results_per_query)

    # Show final statistics
    processor.get_search_statistics()


if __name__ == "__main__":
    main()