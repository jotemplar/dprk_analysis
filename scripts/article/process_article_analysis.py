#!/usr/bin/env python3
"""Article content analysis pipeline using Gemma3:12b"""

import sys
import os
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from database.article_models import ArticleContent, ArticleAnalysis
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from utils.ollama_analyzer import OllamaAnalyzer


class ArticleAnalysisProcessor:
    """Analyze article content using Gemma3:12b model"""

    def __init__(self):
        self.session = get_session()
        self.ollama_analyzer = OllamaAnalyzer(model="gemma3:12b")
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0

    async def process_pending_analysis(self, limit: int = None, max_concurrent: int = 3):
        """
        Process articles without analysis

        Args:
            limit: Maximum number of articles to analyze
            max_concurrent: Maximum concurrent analysis tasks
        """
        print("=" * 60)
        print("ARTICLE CONTENT ANALYSIS PROCESSOR")
        print("=" * 60)

        # Get articles with content but no analysis
        pending_query = self.session.execute(text("""
            SELECT ac.id, ac.result_id, ar.title, ac.markdown_content,
                   ac.word_count, ac.language, ar.url, ar.source_domain, ar.snippet
            FROM article_content ac
            JOIN article_results ar ON ac.result_id = ar.id
            LEFT JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE ac.scrape_success = true
            AND ac.markdown_content IS NOT NULL
            AND ac.markdown_content != ''
            AND aa.result_id IS NULL
            ORDER BY ac.word_count DESC
        """))

        pending_articles = pending_query.fetchall()
        total_pending = len(pending_articles)

        if limit and limit < total_pending:
            pending_articles = pending_articles[:limit]
            print(f"📊 Found {total_pending} articles with content")
            print(f"📌 Processing limited to {limit} articles")
        else:
            print(f"📊 Processing {total_pending} articles for analysis")

        if total_pending == 0:
            print("✅ No articles pending analysis!")
            return

        print(f"🤖 Using Gemma3:12b model for analysis")
        print(f"🔄 Max concurrent: {max_concurrent} tasks")

        # Process with controlled concurrency
        start_time = datetime.now()
        semaphore = asyncio.Semaphore(max_concurrent)

        # Create tasks
        tasks = []
        for article in pending_articles:
            task = self._analyze_with_semaphore(semaphore, article)
            tasks.append(task)

        # Execute all tasks
        await asyncio.gather(*tasks, return_exceptions=True)

        # Final statistics
        duration = datetime.now() - start_time
        success_rate = (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0

        print("\n" + "=" * 60)
        print("✅ ARTICLE ANALYSIS COMPLETED")
        print("=" * 60)
        print(f"📊 Total processed: {self.processed_count}")
        print(f"✅ Successful analyses: {self.success_count}")
        print(f"❌ Failed analyses: {self.error_count}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        print(f"⏱️  Total duration: {duration}")
        if self.processed_count > 0:
            print(f"🔄 Average per article: {duration.total_seconds() / self.processed_count:.1f}s")

    async def _analyze_with_semaphore(self, semaphore: asyncio.Semaphore, article):
        """Analyze single article with semaphore control"""
        async with semaphore:
            try:
                result = await self._analyze_article_content(article)
                if result:
                    self.success_count += 1
                    print(f"✅ [{self.processed_count + 1}] {article.title[:60]}... - {result.get('concern_level', 'unknown')}")
                else:
                    self.error_count += 1
                    print(f"❌ [{self.processed_count + 1}] {article.title[:60]}... - Analysis failed")
            except Exception as e:
                self.error_count += 1
                print(f"❌ [{self.processed_count + 1}] {article.title[:60]}... - {str(e)[:50]}")

            self.processed_count += 1

    async def _analyze_article_content(self, article) -> Optional[Dict]:
        """Analyze article content using Gemma3:12b"""

        try:
            # Prepare content for analysis (limit to avoid token limits)
            content = article.markdown_content[:8000] if article.markdown_content else ""
            title = article.title or ""
            description = article.snippet or ""

            # Create analysis prompt
            prompt = self._create_analysis_prompt(title, description, content, article.url)

            # Get analysis from Gemma3:12b
            start_time = time.time()

            response = await asyncio.to_thread(
                self.ollama_analyzer.generate_text_response,
                prompt
            )

            processing_time = time.time() - start_time

            if not response:
                raise Exception("No response from Gemma3:12b")

            # Parse response into structured data
            analysis_data = self._parse_analysis_response(response, processing_time)

            # Store in database
            await self._store_analysis(article.result_id, analysis_data)

            return analysis_data

        except Exception as e:
            # Store error in database
            await self._store_error(article.result_id, str(e))
            raise e

    def _create_analysis_prompt(self, title: str, description: str, content: str, url: str) -> str:
        """Create analysis prompt for Gemma3:12b"""

        return f"""You are analyzing an article for DPRK (North Korea) related content and concerns.

Article Information:
Title: {title}
URL: {url}
Description: {description}

Content:
{content}

Please analyze this article and provide a JSON response with the following structure:

{{
    "concern_level": "low|medium|high|critical",
    "summary": "brief summary of the article content and its significance",
    "key_insights": ["key", "insights", "from", "the", "analysis"],
    "concern_indicators": ["specific", "indicators", "of", "concern"],
    "human_rights_issues": ["identified", "human", "rights", "concerns"],
    "corporate_involvement": ["companies", "or", "corporations", "mentioned"],
    "government_entities": ["government", "agencies", "or", "officials"],
    "worker_conditions": "description of worker or labor conditions if mentioned",
    "refugee_mentions": true/false,
    "original_language": "detected language of original content",
    "confidence_score": 0.85
}}

Focus on:
1. DPRK sanctions violations or circumvention
2. Labor trafficking and exploitation
3. Illicit financial activities
4. Human rights violations
5. Military/weapons programs
6. International cooperation with DPRK
7. Refugee and defector situations

Rate concern levels:
- low: General news, background information
- medium: Potential violations or concerning activities
- high: Clear violations or significant developments
- critical: Immediate threats or major violations requiring urgent attention

Provide only valid JSON in your response."""

    def _parse_analysis_response(self, response: str, processing_time: float) -> Dict:
        """Parse Gemma3:12b response into structured data"""

        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                analysis = json.loads(response)
            else:
                # Extract JSON from response if wrapped in text
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")

            # Validate and clean the analysis to match database schema
            cleaned_analysis = {
                'concern_level': self._validate_concern_level(analysis.get('concern_level', 'low')),
                'summary': analysis.get('summary', '')[:2000],
                'key_insights': self._clean_list(analysis.get('key_insights', []))[:10],
                'concern_indicators': self._clean_list(analysis.get('concern_indicators', []))[:10],
                'human_rights_issues': self._clean_list(analysis.get('human_rights_issues', []))[:10],
                'corporate_involvement': self._clean_list(analysis.get('corporate_involvement', []))[:10],
                'government_entities': self._clean_list(analysis.get('government_entities', []))[:10],
                'worker_conditions': analysis.get('worker_conditions', '')[:1000],
                'refugee_mentions': bool(analysis.get('refugee_mentions', False)),
                'original_language': analysis.get('original_language', 'unknown')[:10],
                'confidence_score': float(analysis.get('confidence_score', 0.5)),
                'processing_time': processing_time,
                'analyzed_at': datetime.now(),
                'analysis_model': 'gemma3:12b'
            }

            return cleaned_analysis

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing response: {e}")

    def _validate_concern_level(self, level: str) -> str:
        """Validate concern level"""
        valid_levels = ['low', 'medium', 'high', 'critical']
        return level if level in valid_levels else 'low'


    def _clean_list(self, items: List) -> List[str]:
        """Clean and limit list items"""
        if not isinstance(items, list):
            return []

        cleaned = []
        for item in items:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip()[:200])  # Limit item length

        return cleaned

    async def _store_analysis(self, result_id: int, analysis_data: Dict):
        """Store successful analysis in database"""

        # Map the analysis data to the actual database fields
        analysis_record = ArticleAnalysis(
            result_id=result_id,
            summary=analysis_data['summary'],
            concern_level=analysis_data['concern_level'],
            key_insights=analysis_data['key_insights'],
            concern_indicators=analysis_data['concern_indicators'],
            human_rights_issues=analysis_data['human_rights_issues'],
            corporate_involvement=analysis_data['corporate_involvement'],
            government_entities=analysis_data['government_entities'],
            worker_conditions=analysis_data['worker_conditions'],
            refugee_mentions=analysis_data['refugee_mentions'],
            original_language=analysis_data['original_language'],
            confidence_score=analysis_data['confidence_score'],
            processing_time=analysis_data['processing_time'],
            analysis_model=analysis_data['analysis_model'],
            analyzed_at=analysis_data['analyzed_at']
        )

        try:
            self.session.add(analysis_record)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            print("        ⚠️  Analysis already exists for this result")

    async def _store_error(self, result_id: int, error_message: str):
        """Store failed analysis in database"""

        error_record = ArticleAnalysis(
            result_id=result_id,
            summary="Analysis failed",
            error_message=error_message,
            analysis_model='gemma3:12b',
            analyzed_at=datetime.now()
        )

        try:
            self.session.add(error_record)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

    def get_analysis_statistics(self):
        """Get statistics about article analyses"""

        # Overall statistics
        total_content = self.session.execute(text("""
            SELECT COUNT(*) FROM article_content WHERE scrape_success = true
        """)).scalar()

        total_analyzed = self.session.execute(text("SELECT COUNT(*) FROM article_analysis")).scalar()

        successful_analyses = self.session.execute(text("""
            SELECT COUNT(*) FROM article_analysis WHERE error_message IS NULL
        """)).scalar()

        failed_analyses = self.session.execute(text("""
            SELECT COUNT(*) FROM article_analysis WHERE error_message IS NOT NULL
        """)).scalar()

        # Analysis by concern level
        concern_stats = self.session.execute(text("""
            SELECT concern_level, COUNT(*) as count
            FROM article_analysis
            WHERE error_message IS NULL
            AND concern_level IS NOT NULL
            GROUP BY concern_level
            ORDER BY
                CASE concern_level
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC
        """)).fetchall()

        # Success rate by model
        model_stats = self.session.execute(text("""
            SELECT analysis_model, COUNT(*) as count
            FROM article_analysis
            WHERE error_message IS NULL
            GROUP BY analysis_model
            ORDER BY count DESC
        """)).fetchall()

        print(f"\n📊 Article Analysis Statistics:")
        print(f"   Articles with content: {total_content}")
        print(f"   Total analysis attempts: {total_analyzed}")
        print(f"   Successful analyses: {successful_analyses}")
        print(f"   Failed analyses: {failed_analyses}")

        if total_analyzed > 0:
            success_rate = successful_analyses / total_analyzed * 100
            print(f"   Success rate: {success_rate:.1f}%")

        print(f"\n📈 Concern Level Distribution:")
        for level, count in concern_stats:
            percentage = count * 100 / successful_analyses if successful_analyses > 0 else 0
            bar = "█" * int(percentage / 5)
            print(f"   {level.upper():8s}: {count:4d} ({percentage:5.1f}%) {bar}")

        print(f"\n🤖 Analysis by Model:")
        for model, count in model_stats:
            percentage = count * 100 / successful_analyses if successful_analyses > 0 else 0
            print(f"   {model or 'Unknown':12s}: {count:4d} ({percentage:5.1f}%)")

        # Top concerning articles
        concerning_query = self.session.execute(text("""
            SELECT ar.title, aa.concern_level, aa.summary, ar.url
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.concern_level IN ('high', 'critical')
            AND aa.error_message IS NULL
            ORDER BY
                CASE aa.concern_level
                    WHEN 'critical' THEN 2
                    WHEN 'high' THEN 1
                    ELSE 0
                END DESC
            LIMIT 5
        """)).fetchall()

        if concerning_query:
            print(f"\n🚨 Most Concerning Articles:")
            for i, (title, level, summary, url) in enumerate(concerning_query, 1):
                print(f"   {i}. [{level.upper()}] {title[:80]}...")
                print(f"      {summary[:120]}...")
                print(f"      {url[:80]}...")
                print()


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Process article content analysis')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of articles to analyze')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent analysis tasks')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics, do not process')

    args = parser.parse_args()

    processor = ArticleAnalysisProcessor()

    if args.stats_only:
        processor.get_analysis_statistics()
        return

    # Run async processing
    try:
        asyncio.run(processor.process_pending_analysis(
            limit=args.limit,
            max_concurrent=args.max_concurrent
        ))

        # Show final statistics
        processor.get_analysis_statistics()

    except Exception as e:
        print(f"\n❌ Analysis processing failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        processor.session.close()


if __name__ == "__main__":
    main()