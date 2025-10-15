#!/usr/bin/env python3
"""Main pipeline for DPRK image capture with deduplication and theme tracking"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from database.models import (
    SearchQuery, SearchResult, CapturedImage,
    Screenshot, ContentAnalysis, SearchSession
)
from search.serp_image_client import SerpImageClient
from capture.screenshot_capture import ScreenshotCapture
from capture.image_downloader import ImageDownloader
from utils.ollama_analyzer import OllamaAnalyzer
from search_terms.dprk_images_search_terms_combined import search_terms_with_themes

load_dotenv()

class DPRKImagePipeline:
    """Main pipeline for image search, capture, and analysis with deduplication"""

    def __init__(self):
        self.serp_client = SerpImageClient()
        self.screenshot_capture = ScreenshotCapture()
        self.image_downloader = ImageDownloader()
        self.analyzer = OllamaAnalyzer()
        self.session = get_session()
        self.existing_image_urls = set()  # Cache for deduplication
        self.duplicate_count = 0
        self.new_image_count = 0

    def load_existing_image_urls(self):
        """Load all existing image URLs for deduplication"""
        existing_images = self.session.query(CapturedImage.file_path, SearchResult.image_url).join(
            SearchResult
        ).all()

        for _, image_url in existing_images:
            if image_url:
                self.existing_image_urls.add(image_url)

        print(f"📊 Loaded {len(self.existing_image_urls)} existing image URLs for deduplication")

    async def run_pipeline(self, limit_queries: int = None, skip_analysis: bool = False):
        """
        Run the complete pipeline with deduplication

        Args:
            limit_queries: Limit number of queries to process (for testing)
            skip_analysis: Skip the AI analysis phase (useful for just capturing)
        """
        print("\n" + "=" * 60)
        print("DPRK IMAGE CAPTURE PIPELINE - WITH DEDUPLICATION")
        print("=" * 60)

        try:
            # Test Ollama connection if analysis is enabled
            if not skip_analysis:
                print("\n🔧 Testing Ollama connection...")
                if not self.analyzer.test_connection():
                    print("❌ Ollama is not available. Please start Ollama first.")
                    return
                print("✅ Ollama is ready")

            # Load existing URLs for deduplication
            self.load_existing_image_urls()

            # Create search session
            search_session = SearchSession(
                session_name=f"Themed Search - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            self.session.add(search_session)
            self.session.commit()

            # Process search terms with themes
            queries_to_process = search_terms_with_themes[:limit_queries] if limit_queries else search_terms_with_themes

            print(f"\n📋 Processing {len(queries_to_process)} search queries")
            print(f"🔍 Deduplication enabled against {len(self.existing_image_urls)} existing images")

            total_results = 0
            total_captured = 0
            total_screenshots = 0
            total_analyzed = 0

            for i, search_item in enumerate(queries_to_process, 1):
                search_term = search_item['term']
                theme = search_item['theme']
                source = search_item['source']

                print(f"\n[{i}/{len(queries_to_process)}] Searching: {search_term[:50]}...")
                print(f"   Theme: {theme} | Source: {source}")

                # Search images
                results = self.search_images(search_term, theme)

                if results:
                    print(f"   Found {len(results)} results")
                    total_results += len(results)

                    # Filter out duplicates before processing
                    new_results = []
                    skipped_duplicates = 0

                    for result in results:
                        if result.image_url not in self.existing_image_urls:
                            new_results.append(result)
                            self.existing_image_urls.add(result.image_url)  # Add to cache
                        else:
                            skipped_duplicates += 1
                            self.duplicate_count += 1

                    if skipped_duplicates > 0:
                        print(f"   ⚠️  Skipped {skipped_duplicates} duplicate images")

                    if new_results:
                        # Capture screenshots for new results only
                        screenshots = await self.capture_screenshots(new_results)
                        total_screenshots += len(screenshots)

                        # Download new images
                        downloaded = await self.download_images(new_results)
                        total_captured += len(downloaded)
                        self.new_image_count += len(downloaded)

                        # Analyze images if enabled and not skipped
                        if not skip_analysis and downloaded:
                            # Limit analysis to 5 images per query for speed
                            image_paths = [img['file_path'] for img in downloaded[:5]]
                            analyzed = await self.analyze_images(image_paths, new_results[:5])
                            total_analyzed += len(analyzed)
                    else:
                        print(f"   ℹ️  All images were duplicates, skipping")
                else:
                    print(f"   No results found")

                # Small delay between queries
                await asyncio.sleep(1)

            # Update session stats
            search_session.completed_at = datetime.now()
            self.session.commit()

            # Final summary
            print("\n" + "=" * 60)
            print("PIPELINE COMPLETED")
            print("=" * 60)
            print(f"✅ Search queries processed: {len(queries_to_process)}")
            print(f"📊 Total results found: {total_results}")
            print(f"🔁 Duplicate images skipped: {self.duplicate_count}")
            print(f"🆕 New unique images: {self.new_image_count}")
            print(f"📸 Screenshots captured: {total_screenshots}")
            print(f"💾 Images downloaded: {total_captured}")
            if not skip_analysis:
                print(f"🤖 Images analyzed: {total_analyzed}")
            if search_session.completed_at and search_session.started_at:
                duration = (search_session.completed_at - search_session.started_at).total_seconds()
                print(f"⏱️  Duration: {duration:.1f} seconds")

            return True

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.session.close()
            await self.screenshot_capture.close()

    def search_images(self, query: str, theme: str) -> List[SearchResult]:
        """Search for images and store results with theme"""
        try:
            # Check if query already exists
            existing_query = self.session.query(SearchQuery).filter_by(
                search_term=query
            ).first()

            if not existing_query:
                # Create search query record with theme
                search_query = SearchQuery(
                    search_term=query,
                    theme=theme  # Store the theme
                )

                # Detect language
                if any(ord(c) > 0x3000 for c in query[:20]):
                    if any(0xAC00 <= ord(c) <= 0xD7AF for c in query[:20]):
                        search_query.language = 'ko'
                    elif any(0x4E00 <= ord(c) <= 0x9FFF for c in query[:20]):
                        search_query.language = 'zh'
                elif any(0x0400 <= ord(c) <= 0x04FF for c in query[:20]):
                    search_query.language = 'ru'
                elif 'nord-coréen' in query.lower():
                    search_query.language = 'fr'
                else:
                    search_query.language = 'en'

                self.session.add(search_query)
                self.session.commit()
                query_id = search_query.id
            else:
                # Update theme if different
                if existing_query.theme != theme:
                    existing_query.theme = theme
                    self.session.commit()
                query_id = existing_query.id

            # Check if we already have results for this query
            existing_results = self.session.query(SearchResult).filter_by(
                query_id=query_id
            ).all()

            if existing_results:
                print(f"   ℹ️  Using {len(existing_results)} existing results from database")
                return existing_results

            # Search images (not async) - returns a list
            results = self.serp_client.search_images(query)

            if results:
                search_results = []
                seen_urls = set()  # Track URLs within this search

                for img in results:  # results is already a list
                    image_url = img.get('image_url')

                    # Skip if we've seen this URL in this search (SERP duplicates)
                    if image_url in seen_urls:
                        continue
                    seen_urls.add(image_url)

                    # Check if this result already exists for this query
                    existing_result = self.session.query(SearchResult).filter_by(
                        query_id=query_id,
                        url=img.get('source_url', '')
                    ).first()

                    if not existing_result:
                        # Create search result
                        result = SearchResult(
                            query_id=query_id,
                            title=img.get('title', '')[:500],
                            url=img.get('source_url', ''),
                            image_url=image_url,
                            page_url=img.get('source_url', ''),
                            source_domain=img.get('domain', ''),
                            position=img.get('position', 0)
                        )
                        self.session.add(result)
                        search_results.append(result)
                    else:
                        search_results.append(existing_result)

                try:
                    self.session.commit()
                except Exception as commit_error:
                    self.session.rollback()
                    print(f"   ⚠️  Commit failed, using rollback: {str(commit_error)[:100]}")
                    # Try to return existing results instead
                    existing_results = self.session.query(SearchResult).filter_by(
                        query_id=query_id
                    ).all()
                    return existing_results

                return search_results

            return []

        except Exception as e:
            self.session.rollback()
            print(f"   ❌ Search failed: {e}")
            return []

    async def capture_screenshots(self, results: List[SearchResult]) -> List[Screenshot]:
        """Capture screenshots of source pages"""
        screenshots = []
        print(f"   📸 Capturing screenshots for {len(results)} results...")

        for result in results[:5]:  # Limit screenshots for speed
            try:
                screenshot_path = await self.screenshot_capture.capture_page_screenshot(
                    result.url
                )

                if screenshot_path:
                    screenshot = Screenshot(
                        result_id=result.id,
                        file_path=str(screenshot_path),
                        capture_type='full_page',
                        viewport_width=1920,
                        viewport_height=1080
                    )
                    self.session.add(screenshot)
                    screenshots.append(screenshot)

            except Exception as e:
                print(f"      ❌ Screenshot failed for {result.url}: {e}")
                continue

        self.session.commit()
        print(f"      ✓ Captured {len(screenshots)} screenshots")
        return screenshots

    async def download_images(self, results: List[SearchResult]) -> List[Dict]:
        """Download images from URLs"""
        downloaded = []
        print(f"   💾 Downloading {len(results)} images...")

        # Prepare download tasks
        tasks = []
        for result in results:
            if result.image_url:
                tasks.append(self.image_downloader.download_image(
                    result.image_url,
                    f"result_{result.id}"  # Convert to string category
                ))

        # Download in parallel
        if tasks:
            downloads = await asyncio.gather(*tasks, return_exceptions=True)

            for i, download in enumerate(downloads):
                if isinstance(download, dict) and download.get('file_path'):
                    result = results[i]

                    # Store in database
                    captured = CapturedImage(
                        result_id=result.id,
                        file_path=download['file_path'],
                        file_size=download.get('file_size', 0),
                        image_format=download.get('image_format', ''),
                        image_width=download.get('image_width'),
                        image_height=download.get('image_height'),
                        exif_data=download.get('exif_data', {}),
                        location_data=download.get('location_data', {})
                    )
                    self.session.add(captured)
                    downloaded.append(download)

            self.session.commit()

        print(f"      ✓ Downloaded {len(downloaded)} images")
        return downloaded

    async def analyze_images(self, image_paths: List[str], results: List[SearchResult]) -> List[ContentAnalysis]:
        """Analyze images with Ollama"""
        analyses = []
        print(f"   🤖 Analyzing {len(image_paths)} images...")

        for path, result in zip(image_paths, results):
            try:
                analysis = self.analyzer.analyze_image(path)

                if analysis and 'error_message' not in analysis:
                    # Check if analysis already exists
                    existing = self.session.query(ContentAnalysis).filter_by(
                        result_id=result.id
                    ).first()

                    if not existing:
                        content_analysis = ContentAnalysis(
                            result_id=result.id,
                            scene_description=analysis.get('scene_description', ''),
                            location_assessment=analysis.get('location_assessment', ''),
                            environment_type=analysis.get('environment_type', 'unknown'),
                            personnel_count=analysis.get('personnel_count', 0),
                            personnel_types=analysis.get('personnel_types', []),
                            uniform_identification=analysis.get('uniform_identification', ''),
                            activity_type=analysis.get('activity_type', 'unknown'),
                            activity_description=analysis.get('activity_description', ''),
                            concern_level=analysis.get('concern_level', 'low'),
                            concern_indicators=analysis.get('concern_indicators', []),
                            supervision_present=analysis.get('supervision_present', False),
                            restriction_indicators=analysis.get('restriction_indicators', []),
                            analysis_model=analysis.get('analysis_model', ''),
                            confidence_score=analysis.get('confidence_score', 0.0),
                            processing_time=analysis.get('processing_time', 0.0)
                        )
                        self.session.add(content_analysis)
                        analyses.append(content_analysis)

                    # Update search result status
                    result.analysis_status = 'completed'

            except Exception as e:
                print(f"      ❌ Analysis failed: {e}")
                result.analysis_status = 'failed'

        self.session.commit()
        print(f"      ✓ Analyzed {len(analyses)} images")
        return analyses

async def main():
    """Run the pipeline with deduplication"""
    pipeline = DPRKImagePipeline()

    # Check command line arguments
    skip_analysis = '--skip-analysis' in sys.argv

    # Check for limit argument
    limit = None
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])
            print(f"ℹ️  Limiting to {limit} queries")

    if skip_analysis:
        print("ℹ️  Skipping AI analysis phase (capture only)")

    # Run with themed search terms
    success = await pipeline.run_pipeline(limit_queries=limit, skip_analysis=skip_analysis)

    if success:
        print("\n✅ Pipeline completed successfully!")
        print(f"📊 Total new unique images captured: {pipeline.new_image_count}")
        print(f"🔁 Total duplicates skipped: {pipeline.duplicate_count}")
    else:
        print("\n❌ Pipeline failed!")

if __name__ == "__main__":
    asyncio.run(main())