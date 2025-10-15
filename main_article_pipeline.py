#!/usr/bin/env python3
"""Main article processing pipeline orchestrator for DPRK search terms pack 3"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from database.article_models import ArticleSearch, ArticleResult, ArticleContent, ArticleAnalysis
from sqlalchemy import text
from scripts.article.process_article_searches import ArticleSearchProcessor
from scripts.article.process_article_content import ArticleContentProcessor
from scripts.article.process_article_analysis import ArticleAnalysisProcessor


class ArticlePipelineOrchestrator:
    """Orchestrate the complete article processing pipeline"""

    def __init__(self):
        self.session = get_session()
        self.start_time = datetime.now()

    def get_pipeline_status(self):
        """Get current status of the article processing pipeline"""

        # Get statistics for each stage
        stats = self.session.execute(text("""
            SELECT
                COUNT(DISTINCT as_table.id) as total_searches,
                COUNT(DISTINCT ar.id) as total_results,
                COUNT(DISTINCT ac.id) as total_content,
                COUNT(DISTINCT aa.id) as total_analyses,
                COUNT(CASE WHEN ac.scrape_success = true THEN 1 END) as successful_content,
                COUNT(CASE WHEN aa.id IS NOT NULL THEN 1 END) as successful_analyses
            FROM article_searches as_table
            LEFT JOIN article_results ar ON as_table.id = ar.search_id
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            LEFT JOIN article_analysis aa ON ar.id = aa.result_id
        """)).fetchone()

        # Get high-priority content count
        high_priority = self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM article_analysis
            WHERE concern_level IN ('high', 'critical')
        """)).scalar()

        return {
            'searches': stats.total_searches or 0,
            'results': stats.total_results or 0,
            'content': stats.total_content or 0,
            'successful_content': stats.successful_content or 0,
            'analyses': stats.total_analyses or 0,
            'successful_analyses': stats.successful_analyses or 0,
            'high_priority': high_priority or 0
        }

    async def run_full_pipeline(self, search_limit=None, content_limit=None, analysis_limit=None,
                              results_per_query=50, content_batch_size=50, analysis_max_concurrent=3):
        """
        Run the complete article processing pipeline

        Args:
            search_limit: Limit search queries to process
            content_limit: Limit articles to scrape
            analysis_limit: Limit articles to analyze
            results_per_query: Results per search query
            content_batch_size: Concurrent content scraping
            analysis_max_concurrent: Concurrent analysis tasks
        """

        print("=" * 80)
        print("DPRK ARTICLE PROCESSING PIPELINE")
        print("=" * 80)
        print(f"🚀 Starting full pipeline at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Initial status
        initial_status = self.get_pipeline_status()
        print(f"\n📊 Initial Status:")
        self._print_status(initial_status)

        total_phases = 3
        current_phase = 0

        try:
            # Phase 1: Search Processing
            current_phase += 1
            print(f"\n{'='*60}")
            print(f"📋 PHASE {current_phase}/{total_phases}: SEARCH PROCESSING")
            print(f"{'='*60}")

            search_processor = ArticleSearchProcessor()

            if search_limit:
                # Process specific number of searches
                from search_terms.dprk_images_search_terms_3 import search_packs
                all_terms = []
                for category, terms in search_packs.items():
                    all_terms.extend([(category, term) for term in terms])

                limited_terms = all_terms[:search_limit]
                for category, term in limited_terms:
                    search_processor._process_category(category, [term], results_per_query)
            else:
                # Process all searches
                search_processor.process_all_searches(results_per_query)

            # Phase 2: Content Scraping
            current_phase += 1
            print(f"\n{'='*60}")
            print(f"🔍 PHASE {current_phase}/{total_phases}: CONTENT SCRAPING")
            print(f"{'='*60}")

            content_processor = ArticleContentProcessor()
            await content_processor.process_pending_articles(
                limit=content_limit,
                batch_size=content_batch_size
            )

            # Phase 3: Content Analysis
            current_phase += 1
            print(f"\n{'='*60}")
            print(f"🤖 PHASE {current_phase}/{total_phases}: CONTENT ANALYSIS")
            print(f"{'='*60}")

            analysis_processor = ArticleAnalysisProcessor()
            await analysis_processor.process_pending_analysis(
                limit=analysis_limit,
                max_concurrent=analysis_max_concurrent
            )

            # Final status and summary
            final_status = self.get_pipeline_status()
            duration = datetime.now() - self.start_time

            print(f"\n{'='*80}")
            print("✅ PIPELINE COMPLETED SUCCESSFULLY")
            print(f"{'='*80}")
            print(f"⏱️  Total duration: {duration}")
            print(f"\n📊 Final Status:")
            self._print_status(final_status)

            print(f"\n📈 Progress Summary:")
            print(f"   Searches processed: {final_status['searches'] - initial_status['searches']}")
            print(f"   Results collected: {final_status['results'] - initial_status['results']}")
            print(f"   Content extracted: {final_status['successful_content'] - initial_status['successful_content']}")
            print(f"   Articles analyzed: {final_status['successful_analyses'] - initial_status['successful_analyses']}")
            print(f"   High-priority found: {final_status['high_priority'] - initial_status['high_priority']}")

            return final_status

        except Exception as e:
            print(f"\n❌ Pipeline failed at phase {current_phase}: {e}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            self.session.close()

    def run_specific_phase(self, phase: str, **kwargs):
        """
        Run a specific phase of the pipeline

        Args:
            phase: 'search', 'content', or 'analysis'
            **kwargs: Phase-specific arguments
        """

        print(f"🎯 Running specific phase: {phase.upper()}")

        if phase == 'search':
            processor = ArticleSearchProcessor()
            if kwargs.get('category'):
                from search_terms.dprk_images_search_terms_3 import search_packs
                if kwargs['category'] in search_packs:
                    processor._process_category(
                        kwargs['category'],
                        search_packs[kwargs['category']],
                        kwargs.get('results_per_query', 50)
                    )
                else:
                    print(f"❌ Category '{kwargs['category']}' not found")
                    return
            else:
                processor.process_all_searches(kwargs.get('results_per_query', 50))

        elif phase == 'content':
            async def run_content():
                processor = ArticleContentProcessor()
                await processor.process_pending_articles(
                    limit=kwargs.get('limit'),
                    batch_size=kwargs.get('batch_size', 10)
                )
            asyncio.run(run_content())

        elif phase == 'analysis':
            async def run_analysis():
                processor = ArticleAnalysisProcessor()
                await processor.process_pending_analysis(
                    limit=kwargs.get('limit'),
                    max_concurrent=kwargs.get('max_concurrent', 3)
                )
            asyncio.run(run_analysis())

        else:
            print(f"❌ Unknown phase: {phase}")
            print("Valid phases: search, content, analysis")

    def _print_status(self, status):
        """Print pipeline status in formatted way"""
        print(f"   🔍 Searches executed: {status['searches']}")
        print(f"   📄 Results collected: {status['results']}")
        print(f"   📝 Content extracted: {status['successful_content']}/{status['content']}")
        print(f"   🤖 Articles analyzed: {status['successful_analyses']}/{status['analyses']}")
        print(f"   🚨 High-priority articles: {status['high_priority']}")

        if status['results'] > 0:
            content_rate = status['successful_content'] / status['results'] * 100
            print(f"   📈 Content extraction rate: {content_rate:.1f}%")

        if status['successful_content'] > 0:
            analysis_rate = status['successful_analyses'] / status['successful_content'] * 100
            print(f"   📈 Analysis completion rate: {analysis_rate:.1f}%")

    def generate_summary_report(self):
        """Generate comprehensive pipeline summary"""

        status = self.get_pipeline_status()

        # Get top concerning articles
        concerning_articles = self.session.execute(text("""
            SELECT ac.title, aa.concern_level, aa.dprk_relevance,
                   aa.summary, ar.url, ar.source_domain
            FROM article_analysis aa
            JOIN article_content ac ON aa.content_id = ac.id
            JOIN article_results ar ON ac.result_id = ar.id
            WHERE aa.analysis_status = 'success'
            AND aa.concern_level IN ('high', 'critical')
            ORDER BY
                CASE aa.concern_level
                    WHEN 'critical' THEN 3
                    WHEN 'high' THEN 2
                    ELSE 1
                END DESC,
                CASE aa.dprk_relevance
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC
            LIMIT 10
        """)).fetchall()

        # Get search category statistics
        category_stats = self.session.execute(text("""
            SELECT as_table.category,
                   COUNT(DISTINCT as_table.id) as searches,
                   COUNT(DISTINCT ar.id) as results,
                   COUNT(DISTINCT CASE WHEN ac.scraping_status = 'success' THEN ac.id END) as content,
                   COUNT(DISTINCT CASE WHEN aa.analysis_status = 'success' THEN aa.id END) as analyses
            FROM article_searches as_table
            LEFT JOIN article_results ar ON as_table.id = ar.search_id
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            LEFT JOIN article_analysis aa ON ac.id = aa.content_id
            GROUP BY as_table.category
            ORDER BY analyses DESC
        """)).fetchall()

        print(f"\n{'='*80}")
        print("📋 ARTICLE PIPELINE SUMMARY REPORT")
        print(f"{'='*80}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\n📊 Overall Statistics:")
        self._print_status(status)

        print(f"\n📋 Results by Category:")
        for category, searches, results, content, analyses in category_stats:
            print(f"   {category}:")
            print(f"     Searches: {searches}, Results: {results}")
            print(f"     Content: {content}, Analyses: {analyses}")

        if concerning_articles:
            print(f"\n🚨 High-Priority Articles Found:")
            for i, (title, level, relevance, summary, url, domain) in enumerate(concerning_articles, 1):
                print(f"\n   {i}. [{level.upper()}] {title[:100]}...")
                print(f"      DPRK Relevance: {relevance}")
                print(f"      Source: {domain}")
                print(f"      Summary: {summary[:200]}...")
                print(f"      URL: {url[:100]}...")

        return status


def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(
        description='DPRK Article Processing Pipeline Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with default settings
  python main_article_pipeline.py --full

  # Run full pipeline with limits
  python main_article_pipeline.py --full --search-limit 10 --content-limit 100

  # Run specific phase
  python main_article_pipeline.py --phase search --results-per-query 30
  python main_article_pipeline.py --phase content --batch-size 50
  python main_article_pipeline.py --phase analysis --max-concurrent 2

  # Process specific category only
  python main_article_pipeline.py --phase search --category "Refugees_Communities"

  # Show current status
  python main_article_pipeline.py --status

  # Generate summary report
  python main_article_pipeline.py --report
        """
    )

    # Main operation modes
    parser.add_argument('--full', action='store_true',
                       help='Run the complete pipeline (search -> content -> analysis)')
    parser.add_argument('--phase', choices=['search', 'content', 'analysis'],
                       help='Run specific phase only')
    parser.add_argument('--status', action='store_true',
                       help='Show current pipeline status')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive summary report')

    # Search phase options
    parser.add_argument('--search-limit', type=int,
                       help='Limit number of search queries to process')
    parser.add_argument('--results-per-query', type=int, default=50,
                       help='Number of results per search query')
    parser.add_argument('--category', type=str,
                       help='Process only specific search category')

    # Content phase options
    parser.add_argument('--content-limit', type=int,
                       help='Limit number of articles to scrape')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Concurrent content scraping batch size (optimized for Firecrawl limit)')

    # Analysis phase options
    parser.add_argument('--analysis-limit', type=int,
                       help='Limit number of articles to analyze')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent analysis tasks')

    args = parser.parse_args()

    orchestrator = ArticlePipelineOrchestrator()

    try:
        if args.status:
            status = orchestrator.get_pipeline_status()
            print("\n📊 Current Pipeline Status:")
            orchestrator._print_status(status)

        elif args.report:
            orchestrator.generate_summary_report()

        elif args.full:
            asyncio.run(orchestrator.run_full_pipeline(
                search_limit=args.search_limit,
                content_limit=args.content_limit,
                analysis_limit=args.analysis_limit,
                results_per_query=args.results_per_query,
                content_batch_size=args.batch_size,
                analysis_max_concurrent=args.max_concurrent
            ))

        elif args.phase:
            phase_kwargs = {}

            if args.phase == 'search':
                phase_kwargs.update({
                    'results_per_query': args.results_per_query,
                    'category': args.category
                })
            elif args.phase == 'content':
                phase_kwargs.update({
                    'limit': args.content_limit,
                    'batch_size': args.batch_size
                })
            elif args.phase == 'analysis':
                phase_kwargs.update({
                    'limit': args.analysis_limit,
                    'max_concurrent': args.max_concurrent
                })

            orchestrator.run_specific_phase(args.phase, **phase_kwargs)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        orchestrator.session.close()


if __name__ == "__main__":
    main()