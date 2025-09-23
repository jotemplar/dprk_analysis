#!/usr/bin/env python3
"""Process images missing LLaVA analysis with parallel processing"""

import asyncio
import time
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from database.connection import get_session
from database.models import ContentAnalysis, CapturedImage, SearchResult
from utils.ollama_analyzer import OllamaAnalyzer
from utils.image_preprocessor import ImagePreprocessor
from sqlalchemy import text
import ollama


class ParallelLLaVAProcessor:
    """Process images with LLaVA model using parallel requests"""

    def __init__(self, max_concurrent=4, max_size=896):
        """Initialize with parallel processing settings"""
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.analyzer = OllamaAnalyzer(model="llava")
        self.client = ollama.AsyncClient()

        print(f"✨ Initialized Parallel LLaVA Processor")
        print(f"   Model: llava")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Image standardization: {max_size}x{max_size}")

    async def analyze_image_async(self, image_path: str):
        """Analyze a single image asynchronously"""
        async with self.semaphore:
            try:
                # Standardize image in thread pool
                loop = asyncio.get_event_loop()
                image_base64 = await loop.run_in_executor(
                    self.executor,
                    self.preprocessor.standardize_image,
                    image_path
                )

                # Create analysis prompt
                prompt = self.analyzer._create_analysis_prompt()

                # Call Ollama async
                start_time = time.time()
                response = await self.client.generate(
                    model="llava",
                    prompt=prompt,
                    images=[image_base64],
                    options={
                        "temperature": 0.3,
                        "num_predict": 1000
                    }
                )
                processing_time = time.time() - start_time

                # Parse response
                analysis = self.analyzer._parse_analysis_response(response['response'])
                analysis['processing_time'] = processing_time
                analysis['analysis_model'] = 'llava'

                return analysis

            except Exception as e:
                print(f"   ✗ Error analyzing {Path(image_path).name}: {e}")
                return {'error_message': str(e)}

    async def process_batch(self, batch_data, session):
        """Process a batch of images in parallel"""
        tasks = []

        for result_id, image_path in batch_data:
            task = self.analyze_image_async(image_path)
            tasks.append((result_id, image_path, task))

        # Wait for all analyses to complete
        results = []
        for result_id, image_path, task in tasks:
            try:
                analysis = await task
                results.append((result_id, image_path, analysis))
            except Exception as e:
                print(f"   ✗ Failed {Path(image_path).name}: {e}")
                results.append((result_id, image_path, {'error_message': str(e)}))

        return results

    async def process_all_missing(self, limit=None):
        """Process all images missing LLaVA analysis"""
        session = get_session()

        print("="*60)
        print("PARALLEL LLAVA PROCESSING")
        print("="*60)

        try:
            # Find images needing LLaVA analysis
            query = session.execute(text("""
                SELECT sr.id, ci.file_path
                FROM search_results sr
                JOIN captured_images ci ON sr.id = ci.result_id
                LEFT JOIN content_analysis ca ON sr.id = ca.result_id
                WHERE ca.id IS NULL
                AND ci.file_path IS NOT NULL
                ORDER BY sr.id
            """))

            missing_data = query.fetchall()
            total_missing = len(missing_data)

            if limit and limit < total_missing:
                missing_data = missing_data[:limit]
                print(f"📊 Found {total_missing} images missing LLaVA analysis")
                print(f"📌 Processing limited to {limit} images")
            else:
                print(f"📊 Processing {total_missing} images missing LLaVA analysis")

            if total_missing == 0:
                print("✅ All images already have LLaVA analysis!")
                return

            # Process in batches
            batch_size = self.max_concurrent * 2  # Process 2x concurrent for efficiency
            processed_count = 0
            failed_count = 0
            start_time = time.time()

            print(f"🚀 Starting parallel processing at {datetime.now().strftime('%H:%M:%S')}")
            print("="*60)

            for i in range(0, len(missing_data), batch_size):
                batch = missing_data[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(missing_data) + batch_size - 1) // batch_size

                print(f"\n[Batch {batch_num}/{total_batches}] Processing {len(batch)} images...")

                # Process batch
                results = await self.process_batch(batch, session)

                # Save results to database
                for result_id, image_path, analysis in results:
                    if 'error_message' in analysis:
                        print(f"   ✗ Failed: {Path(image_path).name}")
                        failed_count += 1
                        continue

                    # Create ContentAnalysis record
                    content_analysis = ContentAnalysis(
                        result_id=result_id,
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
                        analysis_model='llava',
                        confidence_score=analysis.get('confidence_score', 0.0),
                        processing_time=analysis.get('processing_time', 0.0)
                    )
                    session.add(content_analysis)
                    processed_count += 1
                    print(f"   ✓ {Path(image_path).name}: {analysis.get('concern_level', 'low')}")

                # Commit batch
                session.commit()

                # Progress update
                elapsed = (time.time() - start_time) / 60
                rate = processed_count / elapsed if elapsed > 0 else 0
                remaining = len(missing_data) - (i + len(batch))
                eta = remaining / rate if rate > 0 else 0

                print(f"   📊 Progress: {processed_count}/{len(missing_data)} | "
                      f"Rate: {rate:.1f}/min | ETA: {eta:.1f} min")

            # Final summary
            elapsed_total = (time.time() - start_time) / 60

            print("\n" + "="*60)
            print("✅ LLAVA PROCESSING COMPLETED")
            print("="*60)
            print(f"⏱️  Total time: {elapsed_total:.1f} minutes")
            print(f"✓ Successfully processed: {processed_count}")
            print(f"✗ Failed: {failed_count}")
            print(f"🚀 Processing rate: {processed_count/elapsed_total:.1f} images/minute")
            print(f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}")

            # Show cache stats
            cache_stats = self.preprocessor.get_cache_stats()
            print(f"\n📁 Image cache: {cache_stats['cached_images']} files, "
                  f"{cache_stats['cache_size_mb']} MB")

        except Exception as e:
            print(f"\n❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()

        finally:
            session.close()
            self.executor.shutdown()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Process missing LLaVA analyses in parallel')
    parser.add_argument('--concurrent', type=int, default=4,
                        help='Number of concurrent requests (default: 4)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of images to process')
    parser.add_argument('--max-size', type=int, default=896,
                        help='Maximum image dimension (default: 896)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - process only 10 images')

    args = parser.parse_args()

    if args.test:
        print("🧪 TEST MODE - Processing 10 images only")
        args.limit = 10

    # Initialize processor
    processor = ParallelLLaVAProcessor(
        max_concurrent=args.concurrent,
        max_size=args.max_size
    )

    # Test Ollama connection
    if not processor.analyzer.test_connection():
        print("❌ Ollama not available. Please ensure ollama is running")
        return

    # Run processing
    await processor.process_all_missing(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())