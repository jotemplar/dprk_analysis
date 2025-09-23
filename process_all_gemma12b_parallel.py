#!/usr/bin/env python3
"""Process all images with gemma3:12b model using parallel processing"""

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


class ParallelGemma12bProcessor:
    """Process images with gemma3:12b model using parallel requests"""

    def __init__(self, max_concurrent=4, max_size=896):
        """Initialize with parallel processing settings"""
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.analyzer = OllamaAnalyzer(model="gemma3:12b")
        self.client = ollama.AsyncClient()

        print(f"✨ Initialized Parallel Gemma3:12b Processor")
        print(f"   Model: gemma3:12b")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Image standardization: {max_size}x{max_size}")

    async def analyze_image_async(self, image_path: str):
        """Analyze a single image asynchronously with gemma3:12b"""
        async with self.semaphore:
            try:
                # Standardize image in thread pool
                loop = asyncio.get_event_loop()
                image_base64 = await loop.run_in_executor(
                    self.executor,
                    self.preprocessor.standardize_image,
                    image_path
                )

                # Create humanitarian-focused prompt for gemma3:12b
                prompt = """Analyze this image from a humanitarian perspective. Focus on identifying:

1. Living conditions and housing quality
2. Work environment safety and conditions
3. Signs of overcrowding or inadequate facilities
4. Evidence of proper supervision or control
5. Access to basic amenities and safety equipment
6. Any indicators of exploitation or poor treatment

Provide a detailed description emphasizing humanitarian concerns.
Format your response as:

DESCRIPTION: [detailed scene description]
HUMANITARIAN_INDICATORS: [list key concerns observed]
CONCERN_LEVEL: [rate as low/medium/high/critical]
CONFIDENCE: [your confidence in this assessment 0-1]"""

                # Call Ollama async
                start_time = time.time()
                response = await self.client.generate(
                    model="gemma3:12b",
                    prompt=prompt,
                    images=[image_base64],
                    options={
                        "temperature": 0.3,
                        "num_predict": 1500
                    }
                )
                processing_time = time.time() - start_time

                # Parse response
                analysis = self._parse_gemma_response(response['response'])
                analysis['processing_time'] = processing_time
                analysis['analysis_model'] = 'gemma3:12b'

                return analysis

            except Exception as e:
                print(f"   ✗ Error analyzing {Path(image_path).name}: {e}")
                return {'error_message': str(e)}

    def _parse_gemma_response(self, response_text: str) -> dict:
        """Parse gemma3:12b response into structured format"""
        lines = response_text.strip().split('\n')
        result = {
            'gemma12b_description': '',
            'gemma12b_indicators': [],
            'gemma12b_concern_level': 'low',
            'confidence_score': 0.5
        }

        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith('DESCRIPTION:'):
                current_section = 'description'
                result['gemma12b_description'] = line[12:].strip()
            elif line.startswith('HUMANITARIAN_INDICATORS:'):
                current_section = 'indicators'
                indicators = line[24:].strip()
                if indicators:
                    result['gemma12b_indicators'] = [i.strip() for i in indicators.split(',')]
            elif line.startswith('CONCERN_LEVEL:'):
                concern = line[14:].strip().lower()
                if concern in ['low', 'medium', 'high', 'critical']:
                    result['gemma12b_concern_level'] = concern
            elif line.startswith('CONFIDENCE:'):
                try:
                    result['confidence_score'] = float(line[11:].strip())
                except:
                    result['confidence_score'] = 0.5
            elif current_section == 'description' and line:
                result['gemma12b_description'] += ' ' + line
            elif current_section == 'indicators' and line:
                result['gemma12b_indicators'].extend([i.strip() for i in line.split(',') if i.strip()])

        return result

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

    async def process_all_images(self, limit=None, skip_existing=False):
        """Process all images with gemma3:12b"""
        session = get_session()

        print("="*60)
        print("PARALLEL GEMMA3:12B PROCESSING")
        print("="*60)

        try:
            # Find images to process
            if skip_existing:
                # Only process images without gemma12b analysis
                query = session.execute(text("""
                    SELECT sr.id, ci.file_path
                    FROM search_results sr
                    JOIN captured_images ci ON sr.id = ci.result_id
                    LEFT JOIN content_analysis ca ON sr.id = ca.result_id
                    WHERE ci.file_path IS NOT NULL
                    AND ca.id IS NOT NULL
                    AND ca.gemma12b_description IS NULL
                    ORDER BY sr.id
                """))
            else:
                # Process all images with existing content analysis
                query = session.execute(text("""
                    SELECT sr.id, ci.file_path
                    FROM search_results sr
                    JOIN captured_images ci ON sr.id = ci.result_id
                    JOIN content_analysis ca ON sr.id = ca.result_id
                    WHERE ci.file_path IS NOT NULL
                    ORDER BY sr.id
                """))

            image_data = query.fetchall()
            total_images = len(image_data)

            if limit and limit < total_images:
                image_data = image_data[:limit]
                print(f"📊 Found {total_images} images to process")
                print(f"📌 Processing limited to {limit} images")
            else:
                print(f"📊 Processing {total_images} images with gemma3:12b")

            if total_images == 0:
                print("✅ No images to process!")
                return

            # Process in batches
            batch_size = self.max_concurrent * 2  # Process 2x concurrent for efficiency
            processed_count = 0
            failed_count = 0
            start_time = time.time()

            print(f"🚀 Starting parallel processing at {datetime.now().strftime('%H:%M:%S')}")
            print("="*60)

            for i in range(0, len(image_data), batch_size):
                batch = image_data[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(image_data) + batch_size - 1) // batch_size

                print(f"\n[Batch {batch_num}/{total_batches}] Processing {len(batch)} images...")

                # Process batch
                results = await self.process_batch(batch, session)

                # Update database with gemma12b results
                for result_id, image_path, analysis in results:
                    if 'error_message' in analysis:
                        print(f"   ✗ Failed: {Path(image_path).name}")
                        failed_count += 1
                        continue

                    # Update existing ContentAnalysis record
                    content_analysis = session.query(ContentAnalysis).filter_by(
                        result_id=result_id
                    ).first()

                    if content_analysis:
                        content_analysis.gemma12b_description = analysis.get('gemma12b_description', '')
                        content_analysis.gemma12b_concern_level = analysis.get('gemma12b_concern_level', 'low')
                        content_analysis.gemma12b_indicators = analysis.get('gemma12b_indicators', [])
                        content_analysis.gemma12b_processing_time = analysis.get('processing_time', 0.0)

                        processed_count += 1
                        print(f"   ✓ {Path(image_path).name}: {analysis.get('gemma12b_concern_level', 'low')}")

                # Commit batch
                session.commit()

                # Progress update
                elapsed = (time.time() - start_time) / 60
                rate = processed_count / elapsed if elapsed > 0 else 0
                remaining = len(image_data) - (i + len(batch))
                eta = remaining / rate if rate > 0 else 0

                print(f"   📊 Progress: {processed_count}/{len(image_data)} | "
                      f"Rate: {rate:.1f}/min | ETA: {eta:.1f} min")

            # Final summary
            elapsed_total = (time.time() - start_time) / 60

            print("\n" + "="*60)
            print("✅ GEMMA3:12B PROCESSING COMPLETED")
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
    parser = argparse.ArgumentParser(description='Process images with gemma3:12b in parallel')
    parser.add_argument('--concurrent', type=int, default=4,
                        help='Number of concurrent requests (default: 4)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of images to process')
    parser.add_argument('--max-size', type=int, default=896,
                        help='Maximum image dimension (default: 896)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip images that already have gemma12b analysis')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - process only 10 images')

    args = parser.parse_args()

    if args.test:
        print("🧪 TEST MODE - Processing 10 images only")
        args.limit = 10

    # Initialize processor
    processor = ParallelGemma12bProcessor(
        max_concurrent=args.concurrent,
        max_size=args.max_size
    )

    # Test Ollama connection with gemma3:12b
    try:
        # Test if model exists
        models = ollama.list()
        model_names = [m['name'] for m in models['models']]
        if 'gemma3:12b' not in model_names and 'gemma3:12b:latest' not in model_names:
            print("❌ gemma3:12b model not found. Please pull it first:")
            print("   ollama pull gemma3:12b")
            return
        print("✅ gemma3:12b model available")
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("Please ensure ollama is running")
        return

    # Run processing
    await processor.process_all_images(
        limit=args.limit,
        skip_existing=args.skip_existing
    )


if __name__ == "__main__":
    asyncio.run(main())