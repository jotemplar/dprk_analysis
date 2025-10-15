#!/usr/bin/env python3
"""Content scraping pipeline for article URLs from search results"""

import sys
import os
import time
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from database.article_models import ArticleResult, ArticleContent
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


class ArticleContentProcessor:
    """Process article URLs and extract content using Firecrawl"""

    def __init__(self):
        self.session = get_session()
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0

        # Firecrawl configuration
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment variables")

        self.firecrawl_base_url = "https://api.firecrawl.dev/v1"

        # Will initialize connector when needed
        self.connector = None

    async def process_pending_articles(self, limit: int = None, batch_size: int = 50):
        """
        Process pending article URLs for content extraction

        Args:
            limit: Maximum number of articles to process
            batch_size: Number of concurrent requests
        """
        print("=" * 60)
        print("ARTICLE CONTENT SCRAPING PROCESSOR")
        print("=" * 60)

        # Get pending articles (URLs without content)
        pending_query = self.session.execute(text("""
            SELECT ar.id, ar.url, ar.title, ar.snippet, ar.source_domain,
                   ar.search_id, ar.position
            FROM article_results ar
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            WHERE ac.result_id IS NULL
            AND ar.url IS NOT NULL
            AND ar.url != ''
            AND ar.scrape_status = 'pending'
            ORDER BY ar.search_id, ar.position
        """))

        pending_articles = pending_query.fetchall()
        total_pending = len(pending_articles)

        if limit and limit < total_pending:
            pending_articles = pending_articles[:limit]
            print(f"📊 Found {total_pending} pending articles")
            print(f"📌 Processing limited to {limit} articles")
        else:
            print(f"📊 Processing {total_pending} articles for content extraction")

        if total_pending == 0:
            print("✅ No pending articles to process!")
            return

        print(f"🔄 Batch size: {batch_size} concurrent requests")
        print(f"🚀 Optimized for Firecrawl's 50-concurrent limit")

        # Process in batches
        start_time = datetime.now()

        for i in range(0, len(pending_articles), batch_size):
            batch = pending_articles[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(pending_articles) - 1) // batch_size + 1

            print(f"\n🔍 Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")

            await self._process_batch(batch)

            # Progress indicator for large batches
            if self.processed_count % 100 == 0 and self.processed_count > 0:
                elapsed = datetime.now() - start_time
                rate = self.processed_count / elapsed.total_seconds()
                remaining = len(pending_articles) - self.processed_count
                eta = remaining / rate if rate > 0 else 0
                print(f"   📈 Progress: {self.processed_count}/{len(pending_articles)} | "
                      f"Rate: {rate:.1f}/s | ETA: {eta/60:.1f}m")

        # Final statistics
        duration = datetime.now() - start_time
        success_rate = (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0

        print("\n" + "=" * 60)
        print("✅ CONTENT SCRAPING COMPLETED")
        print("=" * 60)
        print(f"📊 Total processed: {self.processed_count}")
        print(f"✅ Successful extractions: {self.success_count}")
        print(f"❌ Failed extractions: {self.error_count}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        print(f"⏱️  Total duration: {duration}")
        print(f"🔄 Average per article: {duration.total_seconds() / self.processed_count:.1f}s")

    async def _process_batch(self, batch: List):
        """Process a batch of articles concurrently"""

        tasks = []
        for article in batch:
            task = self._scrape_article_content(article)
            tasks.append(task)

        # Execute batch concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        batch_success = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"      ❌ {batch[i].url[:60]}... - {str(result)[:50]}")
                self.error_count += 1
            elif result:
                print(f"      ✅ {batch[i].url[:60]}... - {len(result.get('content', ''))} chars")
                batch_success += 1
                self.success_count += 1
            else:
                print(f"      ⚠️  {batch[i].url[:60]}... - No content extracted")
                self.error_count += 1

            self.processed_count += 1

        print(f"   Batch result: {batch_success}/{len(batch)} successful")

    async def _scrape_article_content(self, article) -> Optional[Dict]:
        """Scrape content from a single article URL"""

        try:
            # Prepare Firecrawl API request
            url = article.url

            # Skip if URL is invalid
            if not url or not url.startswith('http'):
                raise ValueError(f"Invalid URL: {url}")

            # Make API request to Firecrawl
            timeout = aiohttp.ClientTimeout(total=45)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'Authorization': f'Bearer {self.firecrawl_api_key}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'url': url,
                    'formats': ['markdown', 'html'],
                    'onlyMainContent': True,
                    'removeBase64Images': True,
                    'timeout': 30000  # 30 seconds
                }

                async with session.post(
                    f"{self.firecrawl_base_url}/scrape",
                    json=payload,
                    headers=headers
                ) as response:

                    if response.status == 200:
                        result = await response.json()

                        # Extract content and metadata
                        content_data = {
                            'markdown_content': result.get('data', {}).get('markdown', ''),
                            'raw_html': result.get('data', {}).get('html', ''),
                            'cleaned_text': result.get('data', {}).get('markdown', ''),  # Use markdown as cleaned text
                            'word_count': self._count_words(result.get('data', {}).get('markdown', '')),
                            'language': result.get('data', {}).get('metadata', {}).get('language', 'unknown'),
                            'scraped_at': datetime.utcnow(),
                            'scrape_success': True,
                            'scrape_method': 'firecrawl'
                        }

                        # Store in database
                        await self._store_content(article.id, content_data)

                        return content_data

                    else:
                        error_msg = f"HTTP {response.status}"
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get('error', error_msg)
                        except:
                            pass

                        # Store error in database
                        await self._store_error(article.id, error_msg, 'firecrawl')
                        raise Exception(error_msg)

        except Exception as e:
            # Store error in database
            await self._store_error(article.id, str(e), 'firecrawl')
            raise e

    async def _store_content(self, result_id: int, content_data: Dict):
        """Store successful content extraction in database"""

        content_record = ArticleContent(
            result_id=result_id,
            markdown_content=content_data['markdown_content'],
            raw_html=content_data['raw_html'],
            cleaned_text=content_data['cleaned_text'],
            word_count=content_data['word_count'],
            language=content_data['language'],
            scraped_at=content_data['scraped_at'],
            scrape_success=content_data['scrape_success'],
            scrape_method=content_data['scrape_method']
        )

        try:
            self.session.add(content_record)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # Handle duplicate - update existing record
            existing = self.session.query(ArticleContent).filter_by(result_id=result_id).first()
            if existing:
                for key, value in content_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.session.commit()

    async def _store_error(self, result_id: int, error_message: str, method: str):
        """Store failed content extraction in database"""

        error_record = ArticleContent(
            result_id=result_id,
            scrape_success=False,
            scrape_method=method,
            error_message=error_message,
            scraped_at=datetime.utcnow()
        )

        try:
            self.session.add(error_record)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

    def _count_words(self, text: str) -> int:
        """Count words in text content"""
        if not text:
            return 0
        return len(text.split())

    def get_content_statistics(self):
        """Get statistics about scraped content"""

        # Overall statistics
        total_results = self.session.execute(text("SELECT COUNT(*) FROM article_results")).scalar()
        total_content = self.session.execute(text("SELECT COUNT(*) FROM article_content")).scalar()
        successful_content = self.session.execute(text("""
            SELECT COUNT(*) FROM article_content WHERE scrape_success = true
        """)).scalar()
        failed_content = self.session.execute(text("""
            SELECT COUNT(*) FROM article_content WHERE scrape_success = false
        """)).scalar()

        # Content by domain
        domain_stats = self.session.execute(text("""
            SELECT ar.source_domain,
                   COUNT(ac.id) as scraped_count,
                   COUNT(CASE WHEN ac.scrape_success = true THEN 1 END) as success_count,
                   AVG(ac.word_count) as avg_word_count
            FROM article_results ar
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            WHERE ar.source_domain IS NOT NULL
            GROUP BY ar.source_domain
            HAVING COUNT(ac.id) > 0
            ORDER BY success_count DESC
        """)).fetchall()

        print(f"\n📊 Article Content Statistics:")
        print(f"   Total article URLs: {total_results}")
        print(f"   Total scraped attempts: {total_content}")
        print(f"   Successful extractions: {successful_content}")
        print(f"   Failed extractions: {failed_content}")

        if total_content > 0:
            success_rate = successful_content / total_content * 100
            print(f"   Success rate: {success_rate:.1f}%")

        print(f"\n📋 By Source Domain:")
        for domain, scraped, success, avg_words in domain_stats:
            success_rate = (success / scraped * 100) if scraped > 0 else 0
            avg_words = int(avg_words) if avg_words else 0
            print(f"   {domain}: {success}/{scraped} successful ({success_rate:.0f}%), avg {avg_words} words")


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Process article content scraping')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of articles to process')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of concurrent requests per batch (optimized for Firecrawl limit)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics, do not process')

    args = parser.parse_args()

    processor = ArticleContentProcessor()

    if args.stats_only:
        processor.get_content_statistics()
        return

    # Run async processing
    try:
        asyncio.run(processor.process_pending_articles(
            limit=args.limit,
            batch_size=args.batch_size
        ))

        # Show final statistics
        processor.get_content_statistics()

    except Exception as e:
        print(f"\n❌ Content processing failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        processor.session.close()


if __name__ == "__main__":
    main()