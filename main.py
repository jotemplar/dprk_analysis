#!/usr/bin/env python3
"""Main pipeline for DPRK image capture and analysis system"""

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
from dprk_images_search_terms import search_terms_comprehensive

load_dotenv()

class DPRKImagePipeline:
    """Main pipeline for image search, capture, and analysis"""

    def __init__(self):
        self.serp_client = SerpImageClient()
        self.screenshot_capture = ScreenshotCapture()
        self.image_downloader = ImageDownloader()
        self.analyzer = OllamaAnalyzer()
        self.session = get_session()

    async def run_pipeline(self, limit_queries: int = None):
        """
        Run the complete pipeline

        Args:
            limit_queries: Limit number of queries to process (for testing)
        """
        print("\n" + "=" * 60)
        print("DPRK IMAGE CAPTURE AND ANALYSIS PIPELINE")
        print("=" * 60)

        try:
            # Test Ollama connection
            if not self.analyzer.test_connection():
                print("⚠ Warning: Ollama not available. Analysis will be skipped.")
                self.analyzer = None

            # Create search session
            search_session = SearchSession(
                session_name=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                started_at=datetime.now()
            )
            self.session.add(search_session)
            self.session.commit()

            # Get search queries
            queries = self.session.query(SearchQuery).limit(limit_queries).all() if limit_queries else \
                     self.session.query(SearchQuery).all()

            total_queries = len(queries)
            print(f"\n📋 Processing {total_queries} search queries")

            total_images_captured = 0
            total_screenshots = 0
            total_analyses = 0

            for idx, query in enumerate(queries, 1):
                print(f"\n{'='*60}")
                print(f"[{idx}/{total_queries}] Query: {query.search_term[:100]}")
                print(f"Language: {query.language} | Category: {query.category}")
                print('-' * 60)

                # Update session with current query
                search_session.query_id = query.id
                self.session.commit()

                # 1. Execute search
                print("\n1️⃣ Searching for images...")
                search_results = self.serp_client.search_images(query.search_term, num_results=20)

                if not search_results:
                    print("   No results found")
                    continue

                print(f"   Found {len(search_results)} images")

                # 2. Store search results in database
                print("\n2️⃣ Storing search results...")
                db_results = []
                seen_urls = set()  # Track URLs we've already processed

                for result in search_results:
                    url = result.get('source_url', '')

                    # Skip if we've already seen this URL in this batch
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Check if result already exists in database
                    existing = self.session.query(SearchResult).filter_by(
                        query_id=query.id,
                        url=url
                    ).first()

                    if not existing:
                        db_result = SearchResult(
                            query_id=query.id,
                            url=url,
                            image_url=result.get('image_url', ''),
                            page_url=result.get('source_url', ''),
                            title=result.get('title', ''),
                            snippet='',
                            position=result.get('position', 0),
                            source_domain=result.get('source_domain', '')
                        )
                        self.session.add(db_result)
                        db_results.append(db_result)
                    else:
                        db_results.append(existing)

                self.session.commit()
                print(f"   Stored {len(db_results)} results")

                # 3. Capture screenshots
                print("\n3️⃣ Capturing screenshots...")
                image_urls = [r.get('image_url') for r in search_results[:10] if r.get('image_url')]

                if image_urls:
                    gallery_screenshot = await self.screenshot_capture.capture_image_gallery(
                        image_urls, query.search_term
                    )

                    if gallery_screenshot:
                        # Store screenshot in database
                        for db_result in db_results[:10]:
                            screenshot = Screenshot(
                                result_id=db_result.id,
                                file_path=gallery_screenshot,
                                file_name=Path(gallery_screenshot).name,
                                screenshot_type='gallery',
                                page_url=db_result.page_url
                            )
                            self.session.add(screenshot)
                            db_result.screenshot_status = 'completed'

                        self.session.commit()
                        total_screenshots += 1
                        print(f"   Gallery screenshot captured")

                # 4. Download images
                print("\n4️⃣ Downloading images...")
                images_to_download = [
                    (r.get('image_url'), query.category)
                    for r in search_results[:10]
                    if r.get('image_url')
                ]

                downloaded_images = await self.image_downloader.download_images_batch(
                    images_to_download,
                    max_concurrent=3
                )

                print(f"   Downloaded {len(downloaded_images)} images")

                # Store downloaded images in database
                for img_data in downloaded_images:
                    # Find corresponding search result
                    for db_result in db_results:
                        if db_result.image_url == img_data['download_url']:
                            captured_img = CapturedImage(
                                result_id=db_result.id,
                                file_path=img_data['file_path'],
                                file_name=img_data['file_name'],
                                file_size=img_data['file_size'],
                                image_width=img_data['image_width'],
                                image_height=img_data['image_height'],
                                image_format=img_data['image_format'],
                                download_url=img_data['download_url'],
                                exif_data=img_data.get('exif_data'),
                                location_data=img_data.get('location_data')
                            )
                            self.session.add(captured_img)
                            db_result.image_download_status = 'completed'
                            break

                self.session.commit()
                total_images_captured += len(downloaded_images)

                # 5. Analyze images with Ollama
                if self.analyzer and downloaded_images:
                    print("\n5️⃣ Analyzing images with local LLM...")
                    image_paths = [img['file_path'] for img in downloaded_images[:5]]  # Limit to 5 for speed

                    analyses = self.analyzer.batch_analyze(image_paths)

                    # Create a mapping of image paths to their analyses
                    analysis_by_path = {}
                    for i, analysis in enumerate(analyses):
                        if i < len(image_paths):
                            analysis_by_path[image_paths[i]] = analysis

                    # Track which result_ids we've already processed to avoid duplicates
                    processed_result_ids = set()

                    for img_path, analysis in analysis_by_path.items():
                        # Find the specific captured image and its result
                        captured = self.session.query(CapturedImage).filter_by(
                            file_path=img_path
                        ).first()

                        if captured and captured.result_id not in processed_result_ids:
                            # Check if ContentAnalysis already exists for this result
                            existing_analysis = self.session.query(ContentAnalysis).filter_by(
                                result_id=captured.result_id
                            ).first()

                            if not existing_analysis:
                                content_analysis = ContentAnalysis(
                                    result_id=captured.result_id,
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
                                
                                # Mark the search result as analyzed
                                db_result = self.session.query(SearchResult).filter_by(
                                    id=captured.result_id
                                ).first()
                                if db_result:
                                    db_result.analysis_status = 'completed'
                                
                                processed_result_ids.add(captured.result_id)
                            else:
                                # Analysis already exists, just update status
                                db_result = self.session.query(SearchResult).filter_by(
                                    id=captured.result_id
                                ).first()
                                if db_result:
                                    db_result.analysis_status = 'completed'

                    self.session.commit()
                    total_analyses += len(processed_result_ids)
                    print(f"   Analyzed {len(analyses)} images")

                # Update session statistics
                search_session.total_results += len(db_results)
                search_session.images_captured += len(downloaded_images)
                search_session.screenshots_taken += 1 if gallery_screenshot else 0
                search_session.analyses_completed += len(analyses) if self.analyzer else 0
                self.session.commit()

                # Rate limiting
                if idx < total_queries:
                    await asyncio.sleep(2)

            # Finalize session
            search_session.completed_at = datetime.now()
            search_session.current_status = 'completed'
            self.session.commit()

            # Print summary
            print("\n" + "=" * 60)
            print("PIPELINE COMPLETED")
            print("=" * 60)
            print(f"✓ Queries processed: {total_queries}")
            print(f"✓ Images captured: {total_images_captured}")
            print(f"✓ Screenshots taken: {total_screenshots}")
            print(f"✓ Analyses completed: {total_analyses}")

            # Get storage statistics
            stats = self.image_downloader.get_storage_statistics()
            print(f"\n📊 Storage Statistics:")
            print(f"   Total images: {stats['total_images']}")
            print(f"   Total size: {stats['total_size_mb']:.1f} MB")
            print(f"   Formats: {stats['format_distribution']}")

        except Exception as e:
            print(f"\n❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup
            await self.screenshot_capture.close()
            self.session.close()

    async def run_test(self):
        """Run a test with limited queries"""
        print("\n🧪 Running test pipeline with 2 queries...")
        await self.run_pipeline(limit_queries=2)

async def main():
    """Main entry point"""
    pipeline = DPRKImagePipeline()

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        await pipeline.run_test()
    else:
        await pipeline.run_pipeline()

if __name__ == "__main__":
    asyncio.run(main())